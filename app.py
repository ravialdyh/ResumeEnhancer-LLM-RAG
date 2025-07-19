# app.py (updated)
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

# Page configuration
st.set_page_config(
    page_title="Resume Optimization Tool",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

def initialize_session_state():
    """Initialize session state variables"""
    # Initialize database service
    if 'db_service' not in st.session_state:
        st.session_state.db_service = DatabaseService()
    
    # Initialize session ID for database tracking
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
        # Create session in database
        try:
            st.session_state.db_service.create_or_update_session(st.session_state.session_id)
        except Exception as e:
            st.error(f"Database connection failed: {str(e)}")
    
    if 'resume_text' not in st.session_state:
        st.session_state.resume_text = ""
    if 'job_description' not in st.session_state:
        st.session_state.job_description = ""
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None
    if 'optimized_resume' not in st.session_state:
        st.session_state.optimized_resume = ""
    if 'improvements' not in st.session_state:
        st.session_state.improvements = []
    if 'current_analysis_id' not in st.session_state:
        st.session_state.current_analysis_id = None
    # New state for the success page
    if 'generation_successful' not in st.session_state:
        st.session_state.generation_successful = False


def populate_html_template(resume_data: dict) -> str:
    """
    Populates the standardized HTML template with optimized resume data.
    Sections are included only if they have content.
    """
    # Helper to build experience HTML
    def build_experience_html(experiences):
        html = ""
        for exp in experiences:
            tasks_html = ""
            for task in exp.get('tasks', []):
                bullets_html = "".join([f"<li>{bullet}</li>" for bullet in task.get('bullets', [])])
                tools = task.get('tools', '')
                if bullets_html:
                    tasks_html += f"<ul>{bullets_html}</ul>"
                if tools:
                    tasks_html += f'<div class="tools">{tools}</div>'
            additional = exp.get('additional', '')
            if additional:
                tasks_html += f"<p>{additional}</p>"
            html += f"""
            <div class="experience-item">
                <div class="institution">{exp.get('company', '')}</div>
                <div class="location">{exp.get('location', '')}</div>
                <div class="clear"></div>
                <div class="position">{exp.get('position', '')}</div>
                <div class="date">{exp.get('dates', '')}</div>
                <div class="clear"></div>
                {tasks_html}
            </div>
            """
        return html if html else ""

    # Helper to build achievements HTML
    def build_achievements_html(achievements):
        html = ""
        for ach in achievements:
            html += f"""
            <div class="experience-item">
                <div class="position">{ach.get('title', '')}</div>
                <div class="clear"></div>
                <p>{ach.get('description', '')}</p>
            </div>
            """
        return html if html else ""

    # Helper to build projects HTML
    def build_projects_html(projects):
        html = ""
        for proj in projects:
            bullets_html = "".join([f"<li>{bullet}</li>" for bullet in proj.get('bullets', [])])
            tools = proj.get('tools', '')
            html += f"""
            <div class="project-item">
                <div class="position">{proj.get('name', '')}</div>
                <div class="clear"></div>
                <ul>{bullets_html}</ul>
                <div class="tools">{tools}</div>
            </div>
            """
        return html if html else ""

    # Helper to build education HTML
    def build_education_html(educations):
        html = ""
        class_name = "education-item1"  # Alternate classes if multiple, but simplify to one
        for edu in educations:
            html += f"""
            <div class="{class_name}">
                <div class="institution">{edu.get('institution', '')}</div>
                <div class="date">{edu.get('dates', '')}</div>
                <div class="clear"></div>
                <p>{edu.get('details', '')}</p>
            </div>
            """
            class_name = "education-item2" if class_name == "education-item1" else "education-item1"
        return html if html else ""

    # Helper to build volunteering HTML
    def build_volunteering_html(volunteerings):
        html = ""
        for vol in volunteerings:
            bullets_html = "".join([f"<li>{bullet}</li>" for bullet in vol.get('bullets', [])])
            html += f"""
            <div class="experience-item">
                <div class="institution">{vol.get('organization', '')}</div>
                <div class="clear"></div>
                <div class="position">{vol.get('position', '')}</div>
                <div class="date">{vol.get('dates', '')}</div>
                <div class="clear"></div>
                <ul>{bullets_html}</ul>
            </div>
            """
        return html if html else ""

    # Helper to build certifications HTML
    def build_certifications_html(certifications):
        html = "".join([f"<li>{cert}</li>" for cert in certifications])
        return f"<ul>{html}</ul>" if html else ""

    # Helper to build skills HTML
    def build_skills_html(skills):
        technical = skills.get('technical', '')
        interests = skills.get('interests', '')
        html = ""
        if technical:
            html += f"<ul><strong>Technical:</strong> {technical}<br></ul>"
        if interests:
            html += f"<ul><strong>Interests:</strong> {interests}</ul>"
        return f"<p>{html}</p>" if html else ""

    # Build contact details
    contact = resume_data.get('contact_info', {})
    name = contact.get('name', '')
    details = []
    if contact.get('email'): details.append(contact['email'])
    if contact.get('phone'): details.append(contact['phone'])
    email_phone = ' • '.join(details)
    other_links = []
    if contact.get('linkedin'): other_links.append(f'<a href="{contact["linkedin"]}">{contact["linkedin"]}</a>')
    if contact.get('other_links'): other_links.append(contact['other_links'])
    links_line = ' • '.join(other_links) if other_links else ''
    contact_html = f'<p class="contact-line">{email_phone}</p><p class="contact-line">• {links_line}</p>' if email_phone or links_line else ''

    # Generate section HTML only if data exists
    summary_html = f'<div class="section-title">SUMMARY</div><p>{resume_data.get("summary", "")}</p>' if resume_data.get('summary') else ''
    experience_html = f'<div class="section-title">EXPERIENCE</div>{build_experience_html(resume_data.get("experience", []))}' if resume_data.get('experience') else ''
    achievements_html = f'<div class="section-title">ACHIEVEMENT</div>{build_achievements_html(resume_data.get("achievements", []))}' if resume_data.get('achievements') else ''
    projects_html = f'<div class="section-title">NOTABLE PROJECTS</div>{build_projects_html(resume_data.get("projects", []))}' if resume_data.get('projects') else ''
    education_html = f'<div class="section-title">EDUCATION</div>{build_education_html(resume_data.get("education", []))}' if resume_data.get('education') else ''
    volunteering_html = f'<div class="section-title">VOLUNTEERING</div>{build_volunteering_html(resume_data.get("volunteering", []))}' if resume_data.get('volunteering') else ''
    certifications_html = f'<div class="section-title">RELATED INTERNATIONAL CERTIFICATION</div>{build_certifications_html(resume_data.get("certifications", []))}' if resume_data.get('certifications') else ''
    skills_html = f'<div class="section-title">SKILLS & INTERESTS</div>{build_skills_html(resume_data.get("skills", {}))}' if resume_data.get('skills') else ''

    # Full HTML template
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{name} - CV</title>
        <style>
            @font-face {{
                font-family: 'Arial';
                src: url('fonts/Arial.ttf');
            }}
            body {{ font-family: 'Arial', sans-serif; line-height: 1.4; margin: 0 auto; padding: 18px; max-width: 1100px; font-size: 11pt; }}
            h1 {{ text-align: center; margin-bottom: 5px; border-bottom: 2px solid black; padding-bottom: 7px; font-size: 20pt; }}
            .contact-info {{ text-align: center; margin-bottom: 15px; font-size: 10pt; }}
            .section-title {{ border-bottom: 1px solid black; text-transform: uppercase; font-weight: bold; margin-top: 15px; margin-bottom: 7px; padding-bottom: 3px; font-size: 11pt; }}
            .experience-item, .project-item {{ margin-bottom: 10px; margin-top: 10px; }}
            .education-item1 {{ margin-bottom: 20px; margin-top: 20px; }}
            .education-item2 {{ margin-bottom: 20px; margin-top: 20px; padding-top: 20px; page-break-inside: avoid; }}
            .institution {{ font-weight: bold; display: inline-block; }}
            .location {{ float: right; font-style: italic; }}
            .position {{ font-weight: bold; }}
            .date {{ float: right; }}
            ul {{ margin-top: 4px; margin-bottom: 6px; padding-left: 22px; }}
            li {{ margin-bottom: 3px; }}
            ul ul {{ margin-top: 2px; margin-bottom: 2px; }}
            .clear {{ clear: both; }}
            .profile-picture {{ text-align: center; margin-bottom: 12px; }}
            .profile-picture img {{ width: 150px; height: auto; border-radius: 5px; }}
            .skills-container {{ display: flex; justify-content: space-between; }}
            .skills-column {{ width: 48%; }}
            p {{ margin-top: 4px; margin-bottom: 4px; }}
            .contact-line {{ margin: 1px 0; line-height: 1.3; }}
            .tools {{ font-style: italic; font-size: 10pt; margin-top: 1px; margin-bottom: 4px; margin-left: 22px; }}
        </style>
    </head>
    <body>
        <h1>{name}</h1>
        <div class="contact-info">
            {contact_html}
        </div>
        {summary_html}
        {experience_html}
        {achievements_html}
        {projects_html}
        {education_html}
        {volunteering_html}
        {certifications_html}
        {skills_html}
    </body>
    </html>
    """
    return html_template

def generate_templated_pdf(resume_data: dict) -> bytes:
    """Generate a PDF from the structured resume data using an HTML template."""
    html_content = populate_html_template(resume_data)
    
    result = BytesIO()
    pdf = pisa.CreatePDF(BytesIO(html_content.encode("UTF-8")), dest=result)
    
    if not pdf.err:
        return result.getvalue()
    else:
        st.error(f"Error converting HTML to PDF: {pdf.err}")
        return None


def main():
    initialize_session_state()

    # Inject custom CSS to make the default sidebar collapse button always visible
    st.markdown(
        """
        <style>
            [data-testid="stSidebarHeader"] button {
                visibility: visible;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    # Header
    st.title("🚀 Resume Optimization Tool")
    st.markdown("Enhance your resume with AI-powered analysis and targeted improvements")
    
    with st.sidebar:
        st.header("Configuration")
        
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        if not gemini_api_key:
            st.error("⚠️ GEMINI_API_KEY environment variable not found!")
            st.session_state.api_key_validated = False
        elif not st.session_state.get('api_key_validated', False):
            with st.spinner("Validating API key..."):
                try:
                    genai.configure(api_key=gemini_api_key)
                    next(genai.list_models())
                    st.session_state.api_key_validated = True
                    st.rerun() 
                except (google_exceptions.PermissionDenied, google_exceptions.Unauthenticated):
                    st.error("🚫 Invalid Gemini API key. Please check your credentials.")
                    st.session_state.api_key_validated = False
                except Exception as e:
                    st.error(f"API key validation failed. Please ensure you have internet access. Error: {e}")
                    st.session_state.api_key_validated = False

        if st.session_state.get('api_key_validated', False):
            st.success("✅ Gemini API key configured and validated")
        else:
            st.warning("Please provide a valid API key to proceed.")
        
        st.markdown("---")
        
        st.subheader("Progress")
        progress_items = [
            ("Resume uploaded", bool(st.session_state.resume_text)),
            ("Job description added", bool(st.session_state.job_description)),
            ("Analysis completed", bool(st.session_state.analysis_results)),
            ("Optimized resume generated", bool(st.session_state.optimized_resume))
        ]
        
        for item, completed in progress_items:
            icon = "✅" if completed else "⭕"
            st.markdown(f"{icon} {item}")
        
        st.markdown("---")
        
        if hasattr(st.session_state, 'db_service'):
            try:
                stats = st.session_state.db_service.get_session_stats(st.session_state.session_id)
                if stats:
                    st.subheader("Session Stats")
                    st.metric("Analyses Done", stats.get('total_analyses', 0))
                    if stats.get('average_match_score', 0) > 0:
                        st.metric("Avg Match Score", f"{stats['average_match_score']:.1f}%")
                    
                    if stats.get('total_analyses', 0) > 0:
                        with st.expander("📈 Recent Analyses"):
                            history = st.session_state.db_service.get_analysis_history(st.session_state.session_id, 5)
                            for h in history:
                                job_title = h.job_title or "Analysis"
                                score = f"{h.match_score}%" if h.match_score else "N/A"
                                st.markdown(f"**{job_title[:30]}{'...' if len(job_title) > 30 else ''}**")
                                st.markdown(f"Score: {score} | {h.created_at.strftime('%m/%d %H:%M')}")
                                st.markdown("---")
                    
                    st.markdown("---")
            except Exception as e:
                st.warning(f"Database statistics unavailable: {e}")
        
        if st.button("🔄 Clear Session", type="secondary"):
            keys_to_delete = [key for key in st.session_state.keys() if key not in ['db_service', 'session_id']]
            for key in keys_to_delete:
                del st.session_state[key]
            st.rerun()
    
    # --- Simplified Main Control Flow ---
    if not st.session_state.analysis_results:
        handle_upload_and_input()
    else:
        # If analysis results exist, show them, along with a summary of the inputs.
        st.header("📄 Input Summary")
        col1, col2, col3 = st.columns([3, 3, 2])
        with col1:
            st.metric("Resume", "Uploaded", f"{len(st.session_state.resume_text)} chars")
        with col2:
            st.metric("Job Description", "Added", f"{len(st.session_state.job_description)} chars")
        with col3:
            # This button allows the user to go back and edit their inputs.
            if st.button("✏️ Edit Inputs & Re-analyze", type="secondary"):
                # Clear results to go back to the input page
                st.session_state.analysis_results = None
                st.session_state.optimized_resume = ""
                st.session_state.generation_successful = False
                st.rerun()

        st.markdown("---")
        handle_analysis()

def handle_upload_and_input():
    """Handle resume upload, job description input, and trigger analysis."""
    st.header("Step 1: Upload Resume & Job Description")
    _render_input_form()
    
    st.markdown("<br>", unsafe_allow_html=True)

    # Analysis trigger is now always shown on the input page.
    col1, col2, col3 = st.columns([2, 3, 2])
    with col2:
        is_api_key_valid = st.session_state.get('api_key_validated', False)
        inputs_ready = bool(st.session_state.resume_text and st.session_state.job_description)

        # The button is disabled if the API key is invalid OR inputs are not ready.
        if st.button("🔍 Analyze Resume", type="primary", use_container_width=True, disabled=not (is_api_key_valid and inputs_ready)):
            with st.spinner("Analyzing resume... Please wait, this may take up to 1 minute."):
                try:
                    analyzer = ResumeAnalyzer()
                    results = analyzer.analyze_resume(
                        st.session_state.resume_text,
                        st.session_state.job_description
                    )
                    st.session_state.analysis_results = results
                    
                    # Save analysis to the database.
                    try:
                        analysis = st.session_state.db_service.save_analysis(
                            session_id=st.session_state.session_id,
                            resume_text=st.session_state.resume_text,
                            job_description=st.session_state.job_description,
                            analysis_results=results,
                            original_filename=getattr(st.session_state, 'uploaded_filename', '')
                        )
                        st.session_state.current_analysis_id = analysis.id
                    except Exception as db_error:
                        st.warning(f"Analysis completed but couldn't save to database: {str(db_error)}")
                    
                    st.success("✅ Analysis completed!")
                    st.balloons()
                    st.rerun() # This rerun will now correctly show the analysis page.
                except Exception as e:
                    st.error(f"❌ Analysis failed: {str(e)}")

        st.caption("Analysis may take 30-60 seconds depending on document size and AI processing.")


def _render_input_form():
    """Render the input form for resume and job description"""
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📎 Upload Resume")
        
        uploaded_file = st.file_uploader(
            "Choose your resume file",
            type=['pdf', 'docx'],
            help="Upload your resume in PDF or DOCX format"
        )
        
        if uploaded_file is not None:
            try:
                with st.spinner("Parsing document..."):
                    st.session_state.uploaded_filename = uploaded_file.name
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_file_path = tmp_file.name
                    
                    parser = DocumentParser()
                    resume_text = parser.parse_document(tmp_file_path)
                    
                    os.unlink(tmp_file_path)
                    
                    if resume_text:
                        st.session_state.resume_text = resume_text
                        st.success(f"✅ Resume parsed successfully! ({len(resume_text)} characters)")
                        
                        with st.expander("📖 Resume Preview"):
                            st.text_area("Content", value=resume_text[:1000] + "..." if len(resume_text) > 1000 else resume_text, height=150, disabled=True)
                    else:
                        st.error("❌ Failed to parse resume. Please check the file format.")
                        
            except Exception as e:
                st.error(f"❌ Error processing file: {str(e)}")
    
    with col2:
        st.subheader("💼 Job Description")
        job_description = st.text_area(
            "Enter the job description or role requirements",
            value=st.session_state.job_description,
            height=320, # Adjusted height to better balance the layout
            help="Paste the complete job description, requirements, and qualifications"
        )
        
        if job_description != st.session_state.job_description:
            st.session_state.job_description = job_description
        
        if job_description:
            st.success(f"✅ Job description entered ({len(job_description)} characters)")

def handle_analysis():
    """Handle analysis results display"""
    if not st.session_state.analysis_results:
        return

    # --- NEW: Success Page Flow ---
    if st.session_state.get('generation_successful', False):
        st.header("🎉 Optimized Resume Generated Successfully!")
        st.balloons()
        st.markdown("Your new resume is ready. You can download it below.")

        col1, col2 = st.columns(2)
        with col1:
             pdf_data = generate_templated_pdf(st.session_state.optimized_resume)
             st.download_button(
                label="📄 Download Optimized Resume (PDF)",
                data=pdf_data,
                file_name="optimized_resume.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary"
            )
        with col2:
            report_str = json.dumps(st.session_state.analysis_results, indent=2)
            st.download_button(
                label="📊 Download Analysis Report (JSON)",
                data=report_str,
                file_name="resume_analysis_report.json",
                mime="application/json",
                use_container_width=True
            )
        return # End the function here to only show the success page

    # --- Original Analysis Display (Now with Popovers) ---
    st.header("🔍 AI Analysis Results")
    
    results = st.session_state.analysis_results
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Match Score", f"{results.get('match_score', 0)}%")
    with col2:
        st.metric("Missing Keywords", results.get('missing_keywords_count', 0))
    with col3:
        st.metric("Improvements", len(results.get('improvements', [])))
    with col4:
        st.metric("Overall Rating", results.get('overall_rating', 'N/A'))
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- NEW: Popover Buttons ---
    col1, col2 = st.columns([1, 1])
    with col1:
        with st.popover("🎯 View Key Findings", use_container_width=True):
            st.markdown("<h5>Key Findings</h5>", unsafe_allow_html=True)
            if results.get('missing_keywords'):
                st.markdown("<h6>Missing Important Keywords:</h6>", unsafe_allow_html=True)
                for keyword in results['missing_keywords']:
                    st.markdown(f"• {keyword}")
            if results.get('strengths'):
                st.markdown("<h6>Strengths:</h6>", unsafe_allow_html=True)
                for strength in results['strengths']:
                    st.markdown(f"✅ {strength}")

    with col2:
        with st.popover("🔧 View Recommended Improvements", use_container_width=True):
            st.markdown("<h5>Recommended Improvements</h5>", unsafe_allow_html=True)
            if results.get('improvements'):
                for i, improvement in enumerate(results['improvements']):
                    st.markdown(f"<h6>Improvement {i+1}: {improvement.get('category', 'General')}</h6>", unsafe_allow_html=True)
                    st.markdown(f"**Issue:** {improvement.get('issue', 'N/A')}")
                    st.markdown(f"**Suggestion:** {improvement.get('suggestion', 'N/A')}")
                    if improvement.get('priority'):
                        priority_color = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
                        st.markdown(f"**Priority:** {priority_color.get(improvement['priority'], '⚪')} {improvement['priority']}")
                    if i < len(results['improvements']) - 1:
                        st.markdown("---")


    st.markdown("---")

    # --- Generate Button with Repositioned Caption ---
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("✨ Generate Optimized Resume", type="primary", use_container_width=True):
            with st.spinner("Generating optimized resume... Please wait, this may take up to 1 minute."):
                try:
                    analyzer = ResumeAnalyzer()
                    resume_structure = analyzer.parse_resume_to_structure(st.session_state.resume_text)
                    
                    optimized_structure = analyzer.generate_optimized_resume(
                        resume_structure,
                        st.session_state.job_description
                    )
                    
                    st.session_state.optimized_resume = optimized_structure
                    st.session_state.generation_successful = True # Set flag for success page
                    
                    if st.session_state.current_analysis_id:
                        try:
                            optimized_text = json.dumps(optimized_structure, indent=2)
                            st.session_state.db_service.update_optimized_resume(
                                st.session_state.current_analysis_id,
                                optimized_text
                            )
                        except Exception as db_error:
                            st.warning(f"Optimized resume generated but couldn't update database: {str(db_error)}")
                    
                    st.rerun()
                except json.JSONDecodeError as json_error:
                    st.error(f"❌ Failed to parse AI response. The model did not return valid JSON. Error: {json_error}")
                except Exception as e:
                    st.error(f"❌ Failed to generate optimized resume: {str(e)}")
        
        st.caption("Optimization may take 30-60 seconds depending on document size and AI processing.")

if __name__ == "__main__":
    main()