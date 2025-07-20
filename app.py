import streamlit as st
import os
import tempfile
import json
import uuid

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from dotenv import load_dotenv
load_dotenv()

from utils.document_parser import DocumentParser
from utils.resume_analyzer import ResumeAnalyzer
from database.service import DatabaseService

from io import BytesIO
from xhtml2pdf import pisa

# --- Page Configuration (MUST be the first Streamlit command) ---
st.set_page_config(
    page_title="Resume Optimization Tool",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Final UI Polish ---
st.markdown(
    r"""
    <style>
    /* --- FONT IMPORT (FROM GOOGLE FONTS API) --- */
    /* This is the most reliable method to ensure fonts are loaded correctly. */
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300..700&family=Space+Mono:ital,wght@0,400;0,700;1,400;1,700&display=swap');
    
    /* --- Hide Streamlit Header & Deploy Button --- */
    [data-testid="stToolbar"] {
        display: none;
    }
    [data-testid="stDeployButton"] {
        display: none;
    }
    
    /* --- Progress Pills (custom element that needs styling) --- */
    .progress-pill {
        background-color: #ecebe3; /* From theme */
        color: #3d3a2a; /* From theme */
        border-radius: 9999px;
        padding: 0.5rem 1rem;
        margin-bottom: 0.5rem;
        font-weight: 500;
        display: flex;
        align-items: center;
        border: 1px solid #d3d2ca; /* From theme */
    }
    .progress-pill.completed {
        background-color: #a25f48; /* A darker accent color */
        color: white;
        border-color: #a25f48;
    }
    .progress-pill .emoji {
        margin-right: 0.75rem;
        font-size: 1.1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def initialize_session_state():
    """Initialize session state variables"""
    if 'db_service' not in st.session_state:
        st.session_state.db_service = DatabaseService()
    
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
        try:
            st.session_state.db_service.create_or_update_session(st.session_state.session_id)
        except Exception as e:
            st.toast(f"Database connection failed: {str(e)}", icon="❌")
    
    for key in ['resume_text', 'job_description', 'analysis_results', 'optimized_resume', 
                'improvements', 'current_analysis_id', 'generation_successful', 'uploaded_filename', 'gemini_api_key']:
        if key not in st.session_state:
            st.session_state[key] = "" if 'text' in key or 'resume' in key or 'key' in key else None
            if key == 'improvements': st.session_state[key] = []
            if key == 'generation_successful': st.session_state[key] = False

def populate_html_template(resume_data: dict) -> str:
    """
    Populates the HTML template for PDF generation.
    This function contains its own CSS for the PDF output, which is separate
    from the Streamlit app's UI theme.
    """
    def build_experience_html(experiences):
        html = ""
        for exp in experiences:
            tasks_html = ""
            for task in exp.get('tasks', []):
                bullets_html = "".join([f"<li>{bullet}</li>" for bullet in task.get('bullets', [])])
                tools = exp.get('tools', '')
                if bullets_html: tasks_html += f"<ul>{bullets_html}</ul>"
                if tools: tasks_html += f'<div class="tools">Tools: {tools}</div>'
            additional = exp.get('additional', '')
            if additional: tasks_html += f"<p>{additional}</p>"
            html += f"""
            <div class="experience-item">
                <div class="job-header">
                    <span class="position">{exp.get('position', '')}</span>
                    <span class="date">{exp.get('dates', '')}</span>
                </div>
                <div class="company-header">
                    <span class="institution">{exp.get('company', '')}</span>
                    <span class="location">{exp.get('location', '')}</span>
                </div>
                {tasks_html}
            </div>"""
        return html if html else ""

    def build_simple_list_html(items):
        return f"<ul>{''.join([f'<li>{item}</li>' for item in items])}</ul>" if items else ""

    def build_projects_html(projects):
        html = ""
        for proj in projects:
            bullets_html = "".join([f"<li>{bullet}</li>" for bullet in proj.get('bullets', [])])
            tools = proj.get('tools', '')
            link = f'<a href="{proj.get("link", "")}">{proj.get("link", "")}</a>' if proj.get("link") else ""
            html += f"""
            <div class="experience-item">
                <div class="job-header"><span class="position">{proj.get('name', '')} {link}</span></div>
                <ul>{bullets_html}</ul>
                <div class="tools">Tools: {tools}</div>
            </div>"""
        return html if html else ""

    def build_education_html(educations):
        html = ""
        for edu in educations:
            html += f"""
            <div class="experience-item">
                 <div class="job-header">
                    <span class="institution">{edu.get('institution', '')}</span>
                    <span class="date">{edu.get('dates', '')}</span>
                </div>
                <p>{edu.get('details', '')}</p>
            </div>"""
        return html if html else ""

    contact = resume_data.get('contact_info', {})
    name = contact.get('name', '').upper()
    details_list = [contact.get('email'), contact.get('phone'), contact.get('linkedin')]
    contact_line = ' &nbsp;&bull;&nbsp; '.join(filter(None, details_list))

    summary_html = f'<h2>Summary</h2><p>{resume_data.get("summary", "")}</p>' if resume_data.get('summary') else ''
    experience_html = f'<h2>Experience</h2>{build_experience_html(resume_data.get("experience", []))}' if resume_data.get('experience') else ''
    projects_html = f'<h2>Projects</h2>{build_projects_html(resume_data.get("projects", []))}' if resume_data.get('projects') else ''
    education_html = f'<h2>Education</h2>{build_education_html(resume_data.get("education", []))}' if resume_data.get('education') else ''
    skills = resume_data.get("skills", {})
    skills_html = f'<h2>Skills</h2><p><strong>Technical:</strong> {skills.get("technical", "")}<br><strong>Interests:</strong> {skills.get("interests", "")}</p>' if skills else ''
    certifications_html = f'<h2>Certifications</h2>{build_simple_list_html(resume_data.get("certifications", []))}' if resume_data.get("certifications") else ''

    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{name} - Resume</title>
        <style>
            @font-face {{ 
                font-family: 'Space Grotesk'; 
                src: url('static/fonts/SpaceGrotesk-VariableFont_wght.ttf'); 
            }}
            @font-face {{ 
                font-family: 'Space Mono'; 
                src: url('static/fonts/SpaceMono-Regular.ttf'); 
            }}
            body {{ 
                font-family: 'Space Grotesk', sans-serif; 
                font-size: 10.5pt; 
                line-height: 1.5; 
                color: #333; 
                margin: 0.5in; 
            }}
            h1 {{ 
                font-family: 'Space Grotesk', sans-serif;
                font-size: 24pt; 
                text-align: center; 
                margin: 0; 
                padding-bottom: 10px; 
                border-bottom: 2px solid #333; 
                letter-spacing: 2px; 
            }}
            .contact-info {{ text-align: center; font-size: 10pt; margin-top: 8px; margin-bottom: 20px; }}
            h2 {{ 
                font-family: 'Space Grotesk', sans-serif;
                font-size: 14pt; 
                border-bottom: 1px solid #ccc; 
                padding-bottom: 4px; 
                margin-top: 20px; 
                margin-bottom: 10px; 
            }}
            .experience-item {{ margin-bottom: 15px; page-break-inside: avoid; }}
            .job-header, .company-header {{ display: flex; justify-content: space-between; width: 100%; }}
            .position, .institution {{ font-weight: bold; }}
            .date, .location {{ font-style: italic; color: #555; }}
            ul {{ padding-left: 20px; margin-top: 5px; margin-bottom: 5px; }}
            li {{ margin-bottom: 4px; }}
            p {{ margin: 0 0 10px 0; }}
            .tools {{ 
                font-family: 'Space Mono', monospace; 
                font-size: 9pt; 
                color: #444; 
                margin-top: 5px; 
            }}
            a {{ color: #0073B1; text-decoration: none; }}
        </style>
    </head>
    <body>
        <h1>{name}</h1>
        <div class="contact-info">{contact_line}</div>
        {summary_html}
        {experience_html}
        {projects_html}
        {education_html}
        {skills_html}
        {certifications_html}
    </body>
    </html>
    """
    return html_template

def generate_templated_pdf(resume_data: dict) -> bytes:
    """Generate a PDF from the structured resume data using an HTML template."""
    html_content = populate_html_template(resume_data)
    result = BytesIO()
    pdf = pisa.CreatePDF(BytesIO(html_content.encode("UTF-8")), dest=result, link_callback=lambda uri, rel: os.path.join(os.getcwd(), uri.replace("/", os.sep)))
    if not pdf.err:
        return result.getvalue()
    else:
        st.toast(f"Error converting HTML to PDF: {pdf.err}. Ensure font files are in 'static/fonts/'.", icon="❌")
        return None

def main():
    """Main application flow."""
    initialize_session_state()

    # --- Sidebar ---
    with st.sidebar:
        st.markdown('<h3><span style="margin-right: 0.5rem;">⚙️</span>Settings</h3>', unsafe_allow_html=True)
        
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            gemini_api_key = st.text_input("Gemini API Key", type="password", value=st.session_state.get('gemini_api_key', ''))
            st.session_state.gemini_api_key = gemini_api_key
        if not gemini_api_key:
            st.error("⚠️ GEMINI_API_KEY required!")
            return
        
        if not st.session_state.get('api_key_validated'):
            with st.spinner("Validating API key..."):
                try:
                    genai.configure(api_key=gemini_api_key)
                    next(genai.list_models())
                    st.session_state.api_key_validated = True
                    st.rerun()
                except Exception as e:
                    st.toast(f"Invalid Gemini API key: {str(e)}", icon="❌")
                    st.session_state.api_key_validated = False
        
        if st.session_state.get('api_key_validated'):
            st.success("✅ API key is valid.")
        
        st.divider()

        st.markdown('<h4><span style="margin-right: 0.5rem;">📊</span>Progress</h4>', unsafe_allow_html=True)
        progress_items = [
            ("Resume uploaded", bool(st.session_state.resume_text)),
            ("Job description added", bool(st.session_state.job_description)),
            ("Analysis completed", bool(st.session_state.analysis_results)),
            ("Resume generated", bool(st.session_state.generation_successful))
        ]
        
        for item, completed in progress_items:
            emoji = "✅" if completed else "⏳"
            status_class = "completed" if completed else ""
            st.markdown(
                f'<div class="progress-pill {status_class}">'
                f'<span class="emoji">{emoji}</span>{item}'
                f'</div>',
                unsafe_allow_html=True
            )
        
        st.divider()

        if hasattr(st.session_state, 'db_service'):
            try:
                stats = st.session_state.db_service.get_session_stats(st.session_state.session_id)
                if stats and stats.get('total_analyses', 0) > 0:
                    st.markdown('<h4><span style="margin-right: 0.5rem;">📈</span>Session Stats</h4>', unsafe_allow_html=True)
                    st.metric("Analyses Done", stats.get('total_analyses', 0))
                    if stats.get('average_match_score', 0) > 0:
                        st.metric("Avg Match Score", f"{stats['average_match_score']:.1f}%")
            except Exception:
                pass
        
        st.divider()
        if st.button("🔄 Start New Session", type="secondary", use_container_width=True):
            keys_to_clear = list(st.session_state.keys())
            for key in keys_to_clear:
                if key not in ['db_service', 'api_key_validated']:
                    del st.session_state[key]
            st.rerun()

    # --- Main Content ---
    st.markdown('<h1><span style="margin-right: 0.75rem;">🚀</span>Resume Optimization Tool</h1>', unsafe_allow_html=True)
    st.markdown("<h4>Enhance your resume with AI-powered analysis and targeted improvements.</h4>", unsafe_allow_html=True)
    st.divider()

    if not st.session_state.analysis_results:
        handle_upload_and_input()
    else:
        handle_analysis_display()

def handle_upload_and_input():
    """Handle resume upload, job description input, and trigger analysis."""
    st.markdown("<h5>Step 1: Provide Your Resume & the Job Description</h5>", unsafe_allow_html=True)
    st.write("")
    
    col1, col2 = st.columns(2, gap="medium")
    with col1.container(border=True):
        st.markdown('<h5><span style="margin-right: 0.5rem;">📄</span>Your Resume</h5>', unsafe_allow_html=True)
        _render_resume_uploader()
    
    with col2.container(border=True):
        st.markdown('<h5><span style="margin-right: 0.5rem;">🎯</span>Target Job Description</h5>', unsafe_allow_html=True)
        _render_jd_input()

    st.write("")
    st.write("")

    col1, col2, col3 = st.columns([2, 3, 2])
    with col2:
        is_ready = bool(st.session_state.resume_text and st.session_state.job_description and st.session_state.get('api_key_validated'))
        if st.button("✨ Analyze & Optimize", type="primary", use_container_width=True, disabled=not is_ready):
            with st.spinner("Analyzing resume... This may take up to a minute."):
                try:
                    analyzer = ResumeAnalyzer()
                    results = analyzer.analyze_resume(st.session_state.resume_text, st.session_state.job_description)
                    st.session_state.analysis_results = results
                    analysis = st.session_state.db_service.save_analysis(
                        session_id=st.session_state.session_id,
                        resume_text=st.session_state.resume_text,
                        job_description=st.session_state.job_description,
                        analysis_results=results,
                        original_filename=st.session_state.get('uploaded_filename', '')
                    )
                    st.session_state.current_analysis_id = analysis.id
                    st.toast("Analysis complete!", icon="✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"Analysis failed: {e}", icon="❌")
        if not is_ready:
            st.caption("Please upload a resume, paste a job description, and ensure your API key is valid to proceed.")

def _render_resume_uploader():
    """Renders the resume upload section."""
    uploaded_file = st.file_uploader("Upload your resume (PDF or DOCX)", type=['pdf', 'docx'], label_visibility="collapsed")
    if uploaded_file:
        if uploaded_file.name != st.session_state.get('uploaded_filename'):
            with st.spinner(f"Parsing '{uploaded_file.name}'..."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_file_path = tmp_file.name
                    
                    parser = DocumentParser()
                    st.session_state.resume_text = parser.parse_document(tmp_file_path)
                    st.session_state.uploaded_filename = uploaded_file.name
                    os.unlink(tmp_file_path)
                    st.toast(f"✅ Parsed '{st.session_state.uploaded_filename}'", icon="📄")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error parsing file: {e}", icon="❌")
    
    if st.session_state.resume_text:
        st.success(f"✅ Loaded: **{st.session_state.uploaded_filename}**")
        with st.expander("Preview Resume Text"):
            st.text_area("Resume Content", st.session_state.resume_text, height=200, disabled=True)

def _render_jd_input():
    """Renders the job description input section."""
    jd_text = st.text_area("Paste the full job description here", value=st.session_state.job_description, height=300, label_visibility="collapsed", placeholder="Paste the job description you are applying for...")
    if jd_text != st.session_state.job_description:
        st.session_state.job_description = jd_text
        st.rerun()
    if st.session_state.job_description:
        st.success("✅ Job description added.")

def handle_analysis_display():
    """Display analysis results and the optimized resume."""
    if st.session_state.get('generation_successful'):
        _render_success_page()
        return

    st.markdown("<h5>Step 2: Review Analysis & Generate Your New Resume</h5>", unsafe_allow_html=True)
    st.write("")

    results = st.session_state.analysis_results
    cols = st.columns(4)
    cols[0].metric("Match Score", f"{results.get('match_score', 0)}%")
    cols[1].metric("Missing Keywords", results.get('missing_keywords_count', 0))
    cols[2].metric("Improvements", len(results.get('improvements', [])))
    cols[3].metric("Overall Rating", results.get('overall_rating', 'N/A'))
    
    st.divider()

    col1, col2 = st.columns(2, gap="medium")
    with col1.container(border=True):
        st.markdown('<h5><span style="margin-right: 0.5rem;">✅</span>Strengths</h5>', unsafe_allow_html=True)
        for strength in results.get('strengths', ["No specific strengths identified."]):
            st.markdown(f"- {strength}")
        st.markdown('<br><h5><span style="margin-right: 0.5rem;">🔑</span>Missing Keywords</h5>', unsafe_allow_html=True)
        for keyword in results.get('missing_keywords', ["No missing keywords identified."]):
            st.markdown(f"- `{keyword}`")

    with col2.container(border=True):
        st.markdown('<h5><span style="margin-right: 0.5rem;">🔧</span>Recommended Improvements</h5>', unsafe_allow_html=True)
        if not results.get('improvements'):
            st.info("No specific improvements were suggested. Your resume looks well-aligned!")
        else:
            for imp in results.get('improvements', []):
                priority_color_map = {"High": "#ef4444", "Medium": "#fbbf24", "Low": "#059669"}
                color = priority_color_map.get(imp.get('priority', 'Low'), "#059669")
                
                st.markdown(f"""
                <div style="margin-bottom: 0.5rem;">
                    <strong style="color:{color};">[{imp.get('priority', 'Low')}] {imp.get('category', 'General')}:</strong>
                    <span>{imp.get('suggestion', 'No suggestion.')}</span>
                </div>
                """, unsafe_allow_html=True)
                st.caption(f"Issue: {imp.get('issue', 'N/A')}")

    st.divider()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("✨ Generate My Optimized Resume!", type="primary", use_container_width=True):
            with st.spinner("AI is crafting your new resume... This may take a moment."):
                try:
                    analyzer = ResumeAnalyzer()
                    resume_structure = analyzer.parse_resume_to_structure(st.session_state.resume_text)
                    optimized_structure = analyzer.generate_optimized_resume(resume_structure, st.session_state.job_description)
                    st.session_state.optimized_resume = optimized_structure
                    st.session_state.generation_successful = True
                    if st.session_state.current_analysis_id:
                        st.session_state.db_service.update_optimized_resume(
                            st.session_state.current_analysis_id,
                            json.dumps(optimized_structure)
                        )
                    st.toast("Resume generated successfully!", icon="🎉")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to generate optimized resume: {e}", icon="❌")

def _render_success_page():
    """Displays the final success page with download options."""
    st.balloons()
    st.markdown('<h1><span style="margin-right: 0.75rem;">🎉</span>Your Optimized Resume is Ready!</h1>', unsafe_allow_html=True)
    st.markdown("Your resume has been tailored to the job description. Download it below or start a new session.")
    
    pdf_data = generate_templated_pdf(st.session_state.optimized_resume)
    if pdf_data:
        file_name = "Optimized_Resume.pdf"
        if st.session_state.uploaded_filename:
            base_name = os.path.splitext(st.session_state.uploaded_filename)[0]
            file_name = f"Optimized_Resume_{base_name}.pdf"

        st.download_button(
            label="📄 Download Optimized Resume (PDF)",
            data=pdf_data,
            file_name=file_name,
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )

    with st.expander("View Raw Optimized Data (JSON)"):
        st.json(st.session_state.optimized_resume)

if __name__ == "__main__":
    main()