import streamlit as st
import os
import tempfile
from pathlib import Path
import json

from utils.document_parser import DocumentParser
from utils.rag_system import RAGSystem
from utils.resume_analyzer import ResumeAnalyzer
from utils.text_processor import TextProcessor

# Page configuration
st.set_page_config(
    page_title="Resume Optimization Tool",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

def initialize_session_state():
    """Initialize session state variables"""
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

def main():
    initialize_session_state()
    
    # Header
    st.title("🚀 Resume Optimization Tool")
    st.markdown("Enhance your resume with AI-powered analysis and targeted improvements")
    
    # Sidebar for configuration
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
        
        # Clear session button
        if st.button("🔄 Clear Session", type="secondary"):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["📄 Upload & Input", "🔍 Analysis", "📊 Comparison"])
    
    with tab1:
        handle_upload_and_input()
    
    with tab2:
        handle_analysis()
    
    with tab3:
        handle_comparison()

def handle_upload_and_input():
    """Handle resume upload and job description input"""
    st.header("Step 1: Upload Resume & Job Description")
    
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
                        st.success("✅ Analysis completed!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"❌ Analysis failed: {str(e)}")
            else:
                st.warning("⚠️ Please upload a resume and enter a job description first.")

def handle_analysis():
    """Handle analysis results display"""
    st.header("Step 2: AI Analysis Results")
    
    if not st.session_state.analysis_results:
        st.info("📋 Upload your resume and job description in the previous tab to see analysis results.")
        return
    
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
                    st.success("✅ Optimized resume generated!")
                except Exception as e:
                    st.error(f"❌ Failed to generate optimized resume: {str(e)}")

def handle_comparison():
    """Handle side-by-side comparison view"""
    st.header("Step 3: Resume Comparison")
    
    if not st.session_state.optimized_resume:
        st.info("📋 Complete the analysis in the previous tabs to see the comparison view.")
        return
    
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
