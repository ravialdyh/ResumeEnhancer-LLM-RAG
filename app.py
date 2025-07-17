import streamlit as st
import os
import tempfile
import json
import uuid

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from dotenv import load_dotenv
load_dotenv()

from fpdf import FPDF

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

def populate_html_template(resume_data: dict) -> str:
    """
    Populates the HTML template with optimized resume data.
    This function dynamically builds the HTML for sections like experience.
    """
    # Helper to build experience HTML
    def build_experience_html(experiences):
        html = ""
        for job in experiences:
            bullets_html = "".join([f"<li>{bullet}</li>" for bullet in job.get('bullets', [])])
            html += f"""
            <div class="experience-item">
                <div class="institution">{job.get('company_location', '')}</div>
                <div class="location">{job.get('location', ' ')}</div>
                <div class="clear"></div>
                <div class="position">{job.get('title', '')}</div>
                <div class="date">{job.get('dates', '')}</div>
                <div class="clear"></div>
                <ul>{bullets_html}</ul>
            </div>
            """
        return html

    # The main HTML structure from your example
    # Note: We are injecting data using f-string formatting.
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Resume</title>
        <style>
            @font-face {{
                font-family: 'Arial';
                src: url('fonts/Arial.ttf');
            }}
            body {{ font-family: 'Arial', sans-serif; line-height: 1.4; margin: 0 auto; padding: 18px; max-width: 1100px; font-size: 11pt; }}
            h1 {{ text-align: center; margin-bottom: 5px; border-bottom: 2px solid black; padding-bottom: 7px; font-size: 20pt; }}
            .contact-info {{ text-align: center; margin-bottom: 15px; font-sze: 10pt; }}
            .section-title {{ border-bottom: 1px solid black; text-transform: uppercase; font-weight: bold; margin-top: 15px; margin-bottom: 7px; padding-bottom: 3px; font-size: 11pt; }}
            .experience-item {{ margin-bottom: 10px; margin-top: 10px; }}
            .institution {{ font-weight: bold; display: inline-block; }}
            .location {{ float: right; }}
            .position {{ font-weight: bold; }}
            .date {{ float: right; }}
            ul {{ margin-top: 4px; margin-bottom: 6px; padding-left: 22px; }}
            li {{ margin-bottom: 3px; }}
            .clear {{ clear: both; }}
            p {{ margin-top: 4px; margin-bottom: 4px; }}
            .contact-line {{ margin: 1px 0; line-height: 1.3; }}
        </style>
    </head>
    <body>
        <h1>{resume_data.get('contact_info', {}).get('name', '')}</h1>
        <div class="contact-info">
            <p class="contact-line">{resume_data.get('contact_info', {}).get('details', '').replace('•', '•<br/>')}</p>
        </div>

        <div class="section-title">SUMMARY</div>
        <p>{resume_data.get('summary', '')}</p>

        <div class="section-title">EXPERIENCE</div>
        {build_experience_html(resume_data.get('experience', []))}

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
    
    # The custom sidebar toggle logic has been removed to use the default Streamlit sidebar.
    # The CSS injected above makes its collapse button always visible.
    with st.sidebar:
        st.header("Configuration")
        
        # API Key check and validation
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        if not gemini_api_key:
            st.error("⚠️ GEMINI_API_KEY environment variable not found!")
            st.session_state.api_key_validated = False
        # Only validate if the key exists and hasn't been validated yet.
        elif not st.session_state.get('api_key_validated', False):
            with st.spinner("Validating API key..."):
                try:
                    genai.configure(api_key=gemini_api_key)
                    # Use a lightweight call like listing models to validate the key.
                    next(genai.list_models())
                    st.session_state.api_key_validated = True
                    st.rerun() # Rerun to update the UI immediately after validation
                except (google_exceptions.PermissionDenied, google_exceptions.Unauthenticated):
                    st.error("🚫 Invalid Gemini API key. Please check your credentials.")
                    st.session_state.api_key_validated = False
                except Exception as e:
                    st.error(f"API key validation failed. Please ensure you have internet access. Error: {e}")
                    st.session_state.api_key_validated = False

        # Display the final status of the API key
        if st.session_state.get('api_key_validated', False):
            st.success("✅ Gemini API key configured and validated")
        else:
            st.warning("Please provide a valid API key to proceed.")
        
        st.markdown("---")
        
        # Progress indicator
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
        
        # Session statistics
        if hasattr(st.session_state, 'db_service'):
            try:
                stats = st.session_state.db_service.get_session_stats(st.session_state.session_id)
                if stats:
                    st.subheader("Session Stats")
                    st.metric("Analyses Done", stats.get('total_analyses', 0))
                    if stats.get('average_match_score', 0) > 0:
                        st.metric("Avg Match Score", f"{stats['average_match_score']:.1f}%")
                    
                    # Analysis history
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
        
        # Clear session button
        if st.button("🔄 Clear Session", type="secondary"):
            keys_to_delete = [key for key in st.session_state.keys() if key not in ['db_service', 'session_id']]
            for key in keys_to_delete:
                del st.session_state[key]
            st.rerun()
    
    # Dynamic content based on progress
    has_inputs = st.session_state.resume_text and st.session_state.job_description
    
    if not has_inputs:
        handle_upload_and_input()
    elif not st.session_state.analysis_results:
        handle_upload_and_input()
        st.markdown("---")
        handle_analysis()
    else:
        handle_analysis()
        # Removed the call to handle_comparison() as comparison is not needed

def handle_upload_and_input():
    """Handle resume upload and job description input"""
    # Show condensed view if already have inputs
    if st.session_state.resume_text and st.session_state.job_description:
        st.header("📄 Input Summary")
        
        col1, col2, col3 = st.columns([3, 3, 2])
        with col1:
            st.metric("Resume", "Uploaded", f"{len(st.session_state.resume_text)} chars")
        with col2:
            st.metric("Job Description", "Added", f"{len(st.session_state.job_description)} chars")
        with col3:
            if st.button("✏️ Edit Inputs", type="secondary"):
                st.session_state.show_edit_inputs = True
                st.rerun()
        
        # Show edit interface if requested
        if st.session_state.get('show_edit_inputs', False):
            st.markdown("---")
            st.subheader("Edit Inputs")
            _render_input_form()
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("💾 Save Changes", type="primary"):
                    st.session_state.show_edit_inputs = False
                    st.rerun()
            with col2:
                if st.button("❌ Cancel", type="secondary"):
                    st.session_state.show_edit_inputs = False
                    st.rerun()
    else:
        st.header("Step 1: Upload Resume & Job Description")
        _render_input_form()
        
        # Analysis trigger
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.info("Analysis may take 30-60 seconds depending on document size and AI processing.")
            is_api_key_valid = st.session_state.get('api_key_validated', False)
            if st.button("🔍 Analyze Resume", type="primary", use_container_width=True, disabled=not is_api_key_valid):
                if st.session_state.resume_text and st.session_state.job_description:
                    with st.spinner("Analyzing resume... Please wait, this may take up to 1 minute."):
                        try:
                            analyzer = ResumeAnalyzer()
                            results = analyzer.analyze_resume(
                                st.session_state.resume_text,
                                st.session_state.job_description
                            )
                            st.session_state.analysis_results = results
                            
                            # Save analysis to database
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
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Analysis failed: {str(e)}")
                else:
                    st.warning("⚠️ Please upload a resume and enter a job description first.")

def _render_input_form():
    """Render the input form for resume and job description"""
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📎 Upload Resume")
        
        # File upload option
        uploaded_file = st.file_uploader(
            "Choose your resume file",
            type=['pdf', 'docx'],
            help="Upload your resume in PDF or DOCX format"
        )
        
        if uploaded_file is not None:
            try:
                with st.spinner("Parsing document..."):
                    # Store filename for database
                    st.session_state.uploaded_filename = uploaded_file.name
                    
                    # Save uploaded file temporarily
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_file_path = tmp_file.name
                    
                    # Parse document
                    parser = DocumentParser()
                    resume_text = parser.parse_document(tmp_file_path)
                    
                    # Clean up temporary file
                    os.unlink(tmp_file_path)
                    
                    if resume_text:
                        st.session_state.resume_text = resume_text
                        st.success(f"✅ Resume parsed successfully! ({len(resume_text)} characters)")
                        
                        # Show preview
                        with st.expander("📖 Resume Preview"):
                            st.text_area("Content", value=resume_text[:1000] + "..." if len(resume_text) > 1000 else resume_text, height=200, disabled=True)
                    else:
                        st.error("❌ Failed to parse resume. Please check the file format.")
                        
            except Exception as e:
                st.error(f"❌ Error processing file: {str(e)}")
                # The info message about pasting manually has been removed as that option is no longer available.
        
        # The manual text input section has been removed to enforce file upload only.
    
    with col2:
        st.subheader("💼 Job Description")
        job_description = st.text_area(
            "Enter the job description or role requirements",
            value=st.session_state.job_description,
            height=455, # Adjusted height to better balance the layout
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
    
    st.header("🔍 AI Analysis Results")
    
    results = st.session_state.analysis_results
    
    # Overview metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Match Score",
            f"{results.get('match_score', 0)}%",
            delta=f"{results.get('match_score', 0) - 70}%" if results.get('match_score', 0) > 70 else None
        )
    
    with col2:
        st.metric(
            "Missing Keywords",
            results.get('missing_keywords_count', 0)
        )
    
    with col3:
        st.metric(
            "Improvements",
            len(results.get('improvements', []))
        )
    
    with col4:
        st.metric(
            "Overall Rating",
            results.get('overall_rating', 'N/A')
        )
    
    # Detailed analysis
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🎯 Key Findings")
        
        # Missing keywords
        if results.get('missing_keywords'):
            st.markdown("**Missing Important Keywords:**")
            for keyword in results['missing_keywords'][:10]:  # Show top 10
                st.markdown(f"• {keyword}")
        
        # Strengths
        if results.get('strengths'):
            st.markdown("**Strengths:**")
            for strength in results['strengths']:
                st.markdown(f"✅ {strength}")
    
    with col2:
        st.subheader("🔧 Recommended Improvements")
        
        if results.get('improvements'):
            for i, improvement in enumerate(results['improvements'][:5]):  # Show top 5
                with st.expander(f"Improvement {i+1}: {improvement.get('category', 'General')}"):
                    st.markdown(f"**Issue:** {improvement.get('issue', 'N/A')}")
                    st.markdown(f"**Suggestion:** {improvement.get('suggestion', 'N/A')}")
                    if improvement.get('priority'):
                        priority_color = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
                        st.markdown(f"**Priority:** {priority_color.get(improvement['priority'], '⚪')} {improvement['priority']}")
    
    # Generate optimized resume button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.info("Optimization may take 30-60 seconds depending on document size and AI processing.")
        if st.button("✨ Generate Optimized Resume", type="primary", use_container_width=True):
            with st.spinner("Generating optimized resume... Please wait, this may take up to 1 minute."):
                try:
                    analyzer = ResumeAnalyzer()
                    # 1. Parse the original resume text into a structured dictionary
                    resume_structure = analyzer.text_processor.parse_resume_to_structured_dict(st.session_state.resume_text)
                    
                    # 2. Send the structured data to the AI for optimization
                    optimized_structure = analyzer.generate_optimized_resume(
                        resume_structure,
                        st.session_state.job_description,
                        st.session_state.analysis_results  # Use the stored analysis results
                    )
                    
                    # 3. Store the structured result, not plain text
                    st.session_state.optimized_resume = optimized_structure
                    
                    # (Optional) Update database with the optimized JSON
                    if st.session_state.current_analysis_id:
                        try:
                            # Note: Your DB schema expects a string, so we dump the JSON
                            optimized_text = json.dumps(optimized_structure, indent=2)
                            st.session_state.db_service.update_optimized_resume(
                                st.session_state.current_analysis_id,
                                optimized_text
                            )
                        except Exception as db_error:
                            st.warning(f"Optimized resume generated but couldn't update database: {str(db_error)}")
                    
                    st.success("✅ Optimized resume generated!")
                    st.rerun()
                except json.JSONDecodeError as json_error:
                    st.error(f"❌ Failed to parse AI response. The model did not return valid JSON. Error: {json_error}")
                except Exception as e:
                    st.error(f"❌ Failed to generate optimized resume: {str(e)}")
    
    # Show PDF download if optimized resume is generated
    if st.session_state.optimized_resume:
        st.markdown("---")
        st.subheader("📥 Download Optimized Resume")
        pdf_data = generate_templated_pdf(st.session_state.optimized_resume)
        st.download_button(
            label="📄 Download Optimized Resume (PDF)",
            data=pdf_data,
            file_name="optimized_resume.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        
        # Optional: Download analysis report
        if st.session_state.analysis_results:
            report_str = json.dumps(st.session_state.analysis_results, indent=2)
            st.download_button(
                label="📊 Download Analysis Report (JSON)",
                data=report_str,
                file_name="resume_analysis_report.json",
                mime="application/json",
                use_container_width=True
            )

if __name__ == "__main__":
    main()