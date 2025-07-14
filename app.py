import streamlit as st
import os
import tempfile
from pathlib import Path
import json
import uuid

from utils.document_parser import DocumentParser
from utils.rag_system import RAGSystem
from utils.resume_analyzer import ResumeAnalyzer
from utils.text_processor import TextProcessor
from database.service import DatabaseService

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

def main():
    initialize_session_state()
    
    # Header
    st.title("🚀 Resume Optimization Tool")
    st.markdown("Enhance your resume with AI-powered analysis and targeted improvements")
    
    # Sidebar toggle
    if 'sidebar_visible' not in st.session_state:
        st.session_state.sidebar_visible = True
    
    # Sidebar toggle button in main area
    col1, col2 = st.columns([1, 8])
    with col1:
        if st.button("☰" if not st.session_state.sidebar_visible else "✕", 
                    help="Toggle sidebar", key="sidebar_toggle"):
            st.session_state.sidebar_visible = not st.session_state.sidebar_visible
            st.rerun()
    
    # Conditional sidebar
    if st.session_state.sidebar_visible:
        with st.sidebar:
            st.header("Configuration")
            
            # API Key check
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            if not gemini_api_key:
                st.error("⚠️ GEMINI_API_KEY environment variable not found!")
                st.info("Please set your Gemini API key in the environment variables.")
                return
            else:
                st.success("✅ Gemini API key configured")
            
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
                            st.metric("Avg Match Score", f"{stats['average_match_score']}%")
                        
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
                    st.warning("Database statistics unavailable")
            
            # Clear session button
            if st.button("🔄 Clear Session", type="secondary"):
                for key in st.session_state.keys():
                    if key not in ['sidebar_visible', 'db_service', 'session_id']:  # Preserve essential state
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
        st.markdown("---")
        handle_comparison()

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
            if st.button("🔍 Analyze Resume", type="primary", use_container_width=True):
                if st.session_state.resume_text and st.session_state.job_description:
                    with st.spinner("Analyzing resume..."):
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
                st.info("💡 If file upload isn't working, you can paste your resume text manually below")
        
        # Manual text input as fallback
        st.markdown("**Or paste your resume text:**")
        manual_resume_text = st.text_area(
            "Paste your resume content here",
            value=st.session_state.resume_text if not uploaded_file else "",
            height=300,
            help="Copy and paste your resume text as a backup option",
            key="manual_resume_input"
        )
        
        if manual_resume_text and manual_resume_text != st.session_state.resume_text:
            st.session_state.resume_text = manual_resume_text
            st.success(f"✅ Resume text added manually! ({len(manual_resume_text)} characters)")
    
    with col2:
        st.subheader("💼 Job Description")
        job_description = st.text_area(
            "Enter the job description or role requirements",
            value=st.session_state.job_description,
            height=300,
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
        if st.button("✨ Generate Optimized Resume", type="primary", use_container_width=True):
            with st.spinner("Generating optimized resume..."):
                try:
                    analyzer = ResumeAnalyzer()
                    optimized_resume = analyzer.generate_optimized_resume(
                        st.session_state.resume_text,
                        st.session_state.job_description,
                        results
                    )
                    st.session_state.optimized_resume = optimized_resume
                    
                    # Update database with optimized resume
                    if st.session_state.current_analysis_id:
                        try:
                            st.session_state.db_service.update_optimized_resume(
                                st.session_state.current_analysis_id,
                                optimized_resume
                            )
                        except Exception as db_error:
                            st.warning(f"Optimized resume generated but couldn't update database: {str(db_error)}")
                    
                    st.success("✅ Optimized resume generated!")
                except Exception as e:
                    st.error(f"❌ Failed to generate optimized resume: {str(e)}")

def handle_comparison():
    """Handle side-by-side comparison view"""
    if not st.session_state.optimized_resume:
        return
    
    st.header("📊 Resume Comparison")
    
    # Comparison view
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📄 Original Resume")
        st.text_area(
            "Original Content",
            value=st.session_state.resume_text,
            height=600,
            disabled=True,
            key="original_resume"
        )
    
    with col2:
        st.subheader("✨ Optimized Resume")
        st.text_area(
            "Optimized Content",
            value=st.session_state.optimized_resume,
            height=600,
            disabled=True,
            key="optimized_resume"
        )
    
    # Improvement highlights
    if st.session_state.analysis_results and st.session_state.analysis_results.get('improvements'):
        st.markdown("---")
        st.subheader("🎯 Key Improvements Made")
        
        improvements = st.session_state.analysis_results['improvements']
        for i, improvement in enumerate(improvements[:3]):  # Show top 3 improvements
            with st.expander(f"✅ {improvement.get('category', 'Improvement')} - {improvement.get('issue', '')[:50]}..."):
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.markdown("**Before:**")
                    st.info(improvement.get('before_text', 'Original text section'))
                with col2:
                    st.markdown("**After:**")
                    st.success(improvement.get('after_text', improvement.get('suggestion', 'Improved text section')))
    
    # Export options
    st.markdown("---")
    st.subheader("📥 Export Options")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.download_button(
            label="📄 Download Optimized Resume (TXT)",
            data=st.session_state.optimized_resume,
            file_name="optimized_resume.txt",
            mime="text/plain",
            use_container_width=True
        ):
            st.success("✅ Resume downloaded!")
    
    with col2:
        # Generate improvement report
        if st.session_state.analysis_results:
            report = generate_improvement_report(st.session_state.analysis_results)
            st.download_button(
                label="📊 Download Analysis Report (JSON)",
                data=json.dumps(report, indent=2),
                file_name="resume_analysis_report.json",
                mime="application/json",
                use_container_width=True
            )
    
    with col3:
        # Copy to clipboard functionality
        if st.button("📋 Copy Optimized Resume", use_container_width=True):
            st.code(st.session_state.optimized_resume, language=None)
            st.info("💡 Use Ctrl+A to select all, then Ctrl+C to copy")

def generate_improvement_report(analysis_results):
    """Generate a comprehensive improvement report"""
    return {
        "analysis_date": str(st.session_state.get('analysis_date', 'N/A')),
        "match_score": analysis_results.get('match_score', 0),
        "overall_rating": analysis_results.get('overall_rating', 'N/A'),
        "missing_keywords": analysis_results.get('missing_keywords', []),
        "strengths": analysis_results.get('strengths', []),
        "improvements": analysis_results.get('improvements', []),
        "recommendations": analysis_results.get('recommendations', [])
    }

if __name__ == "__main__":
    main()
