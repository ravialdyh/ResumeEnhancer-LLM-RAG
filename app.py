import streamlit as st
import os
import time
import requests
from io import BytesIO
from xhtml2pdf import pisa
from dotenv import load_dotenv
from jose import jwt, JWTError

load_dotenv()

st.set_page_config(
    page_title="Align Your Resume Now!",
    page_icon=":material/rocket_launch:",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
SECRET_KEY = os.getenv("JWT_SECRET") 
ALGORITHM = "HS256" 

# Styling
st.markdown(r"""
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300..700&family=Space+Mono:ital,wght@0,400;0,700;1,400;1,700&display=swap');
    .progress-pill { background-color: #f0f0ec; color: #3d3a2a; border-radius: 9999px; padding: 0.5rem 1rem; margin-bottom: 0.5rem; font-weight: 500; display: flex; align-items: center; border: 1px solid #d3d2ca; }
    .progress-pill.completed { background-color: #a25f48; color: white; border-color: #a25f48; }
    .progress-pill .emoji { margin-right: 0.75rem; font-size: 1.1rem; }
    .stApp { background-color: #fdfdf8; }
    h1, h2, h3, h4, h5, h6 { font-family: 'Space Grotesk', sans-serif; }
    h1 { margin-top: 0 !important; margin-bottom: 0.25rem !important; }
    h4 { margin-top: 0 !important; margin-bottom: 0.1rem !important; }
    .block-container { padding-top: 1rem !important; }
    </style>
    """, 
    unsafe_allow_html=True)


def initialize_session_state():
    """Initialize frontend-specific session state variables."""
    keys_to_init = {
        'token': None,
        'resume_bytes': None,
        'resume_mime_type': "",
        'job_description': "",
        'analysis_results': None,
        'optimized_resume': None,
        'current_analysis_id': None,
        'uploaded_filename': "",
        'analysis_status': 'NOT_STARTED'
    }
    for key, default_value in keys_to_init.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def populate_html_template(resume_data: dict) -> str:
    """
    Populates the HTML template for PDF generation.
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
                <table class="experience-header-table">
                    <tbody>
                        <tr>
                            <td class="position">{exp.get('position', '')}</td>
                            <td class="date">{exp.get('dates', '')}</td>
                        </tr>
                        <tr>
                            <td class="institution">{exp.get('company', '')}</td>
                            <td class="location">{exp.get('location', '')}</td>
                        </tr>
                    </tbody>
                </table>
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
            html += f"""<div class="experience-item"><div class="job-header"><span class="position">{proj.get('name', '')} {link}</span></div><ul>{bullets_html}</ul><div class="tools">Tools: {tools}</div></div>"""
        return html if html else ""
        
    def build_education_html(educations):
        html = ""
        for edu in educations:
            html += f"""<div class="experience-item"><div class="job-header"><span class="institution">{edu.get('institution', '')}</span><span class="date">{edu.get('dates', '')}</span></div><p>{edu.get('details', '')}</p></div>"""
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
            
            .experience-header-table {{
                width: 100%;
                border-collapse: collapse; /* Removes space between table cells */
                margin-bottom: 5px; /* Adds a little space before the job description bullets */
            }}
            .experience-header-table td {{
                padding: 0;
                vertical-align: top;
            }}
            .position, .institution {{
                font-weight: bold;
                text-align: left;
            }}
            .date, .location {{
                font-style: italic;
                color: #555;
                text-align: right;
            }}
            
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
    html_content = populate_html_template(resume_data)
    result = BytesIO()
    font_path = os.path.join(os.getcwd(), 'static', 'fonts')
    pdf = pisa.CreatePDF(BytesIO(html_content.encode("UTF-8")), dest=result, link_callback=lambda uri, rel: os.path.join(font_path, os.path.basename(uri)))
    if not pdf.err:
        return result.getvalue()
    else:
        st.toast(f"Error converting HTML to PDF: {pdf.err}", icon=":material/error:")
        return None


def main():
    """Main application flow."""
    initialize_session_state()

    if not st.session_state.token:
        handle_auth()
        st.stop()

    with st.sidebar:
        handle_sidebar()

    st.title(":material/rocket_launch: Align Your Resume Now")
    st.markdown("<h4>Generate optimized resume given your existing CV and dream job description with AI</h4>", unsafe_allow_html=True)
    st.write("")

    if st.session_state.analysis_status in ['NOT_STARTED', 'FAILED']:
        handle_upload_and_input()
    elif st.session_state.analysis_status in ['PENDING', 'OPTIMIZING']:
        handle_polling()
    elif st.session_state.analysis_status == 'COMPLETED':
        if st.session_state.optimized_resume:
            render_success_page()
        else:
            handle_analysis_display()

def handle_auth():
    """Render Login and Sign Up forms."""
    st.title("Login or Sign Up")
    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            if st.form_submit_button("Login"):
                try:
                    response = requests.post(f"{API_BASE_URL}/token", data={"username": username, "password": password})
                    if response.status_code == 200:
                        st.session_state.token = response.json()["access_token"]
                        st.success("Logged in successfully!")
                        st.rerun()
                    else:
                        st.error(f"Login failed: {response.json().get('detail', 'Invalid credentials')}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Connection error: {e}")

    with signup_tab:
        with st.form("signup_form"):
            new_username = st.text_input("New Username", key="signup_username")
            new_password = st.text_input("New Password", type="password", key="signup_password")
            if st.form_submit_button("Sign Up"):
                try:
                    response = requests.post(f"{API_BASE_URL}/users", json={"username": new_username, "password": new_password})
                    if 200 <= response.status_code < 300:
                        st.success("Sign up successful! Please login.")
                    else:
                        try:
                            detail = response.json().get('detail', response.text)
                        except requests.exceptions.JSONDecodeError:
                            detail = response.text
                        st.error(f"Sign up failed: {detail}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Connection error: {e}")

def handle_upload_and_input():
    """Handle resume upload, job description input, and trigger analysis via API."""
    if st.session_state.analysis_status == 'FAILED':
        st.error("The previous analysis failed. Please try again.")
        st.session_state.analysis_status = 'NOT_STARTED'

    col1, col2 = st.columns(2, gap="medium")
    with col1.container(border=True):
        st.markdown("##### :material/description: Your Resume")
        uploaded_file = st.file_uploader("Upload your resume (PDF, DOCX, TXT)", type=['pdf', 'docx', 'txt'], label_visibility="collapsed")
        if uploaded_file:
            st.session_state.resume_bytes = uploaded_file.getvalue()
            st.session_state.resume_mime_type = uploaded_file.type
            st.session_state.uploaded_filename = uploaded_file.name
        if st.session_state.resume_bytes:
            st.success(f"Loaded: **{st.session_state.uploaded_filename}**", icon=":material/check_circle:")

    with col2.container(border=True):
        st.markdown("##### :material/ads_click: Target Job Description")

        job_url = st.text_input("Paste Job Posting URL (e.g., from LinkedIn)", "")
        if st.button("Scrape Job Description", use_container_width=True):
            if job_url:
                with st.spinner("Scraping job description..."):
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    try:
                        response = requests.post(f"{API_BASE_URL}/v1/scrape-job", headers=headers, json={"url": job_url})
                        if response.status_code == 200:
                            st.session_state.job_description = response.json()["job_description"]
                            st.success("Scraping successful! Job description populated below.")
                        else:
                            st.error(f"Scraping failed: {response.json().get('detail', 'Unknown error')}")
                    except requests.exceptions.RequestException as e:
                        st.error(f"Failed to connect to the scraping service: {e}")
            else:
                st.warning("Please enter a URL to scrape.")
        
        st.session_state.job_description = st.text_area(
            "Paste the full job description here", 
            value=st.session_state.job_description, 
            height=250, 
            label_visibility="collapsed", 
            placeholder="Paste the job description you are applying for, or scrape it from a URL above."
        )
        if st.session_state.job_description:
            st.success("Job description added.", icon=":material/check_circle:")

    _, center_col, _ = st.columns([2, 3, 2])
    with center_col:
        is_ready = bool(st.session_state.resume_bytes and st.session_state.job_description)
        if st.button("Analyze & Optimize", icon=":material/auto_awesome:", type="primary", use_container_width=True, disabled=not is_ready):
            headers = {"Authorization": f"Bearer {st.session_state.token}"}
            files = {"resume_file": (st.session_state.uploaded_filename, st.session_state.resume_bytes, st.session_state.resume_mime_type)}
            data = {"job_description": st.session_state.job_description}
            try:
                response = requests.post(f"{API_BASE_URL}/v1/analyze", headers=headers, files=files, data=data)
                response.raise_for_status()
                analysis_info = response.json()
                st.session_state.current_analysis_id = analysis_info["analysis_id"]
                st.session_state.analysis_status = 'PENDING'
                st.rerun()
            except requests.exceptions.RequestException as e:
                st.error(f"Failed to connect to the analysis service: {e}")

        if not is_ready:
            st.caption("Please upload a resume and paste a job description.")

def handle_sidebar():
    """Render the sidebar content."""
    st.markdown("### :material/settings: Settings")
    st.success("Logged in.", icon=":material/check_circle:")
    
    try:
        payload = jwt.decode(st.session_state.token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get('sub', 'User')
        st.markdown(f"Logged in as: **{username}**", unsafe_allow_html=True)
    except JWTError:
        st.markdown("Logged in as: **User**", unsafe_allow_html=True)
    
    if st.button("Logout"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

    st.divider()
    st.markdown("#### :material/checklist: Progress")
    progress_items = [
        ("Resume uploaded", bool(st.session_state.resume_bytes)),
        ("Job description added", bool(st.session_state.job_description)),
        ("Analysis completed", st.session_state.analysis_status == 'COMPLETED' and st.session_state.analysis_results is not None),
        ("Resume generated", st.session_state.analysis_status == 'COMPLETED' and st.session_state.optimized_resume is not None)
    ]
    for item, completed in progress_items:
        icon_name = "check_circle" if completed else "hourglass_top"
        status_class = "completed" if completed else ""
        
        st.markdown(f"""
            <div class="progress-pill {status_class}">
                <span class="material-icons emoji">{icon_name}</span>
                {item}
            </div>
        """, unsafe_allow_html=True)

    st.divider()
    if st.button("Start New Session", icon=":material/refresh:", type="secondary", use_container_width=True):
        token = st.session_state.token
        for key in st.session_state.keys():
            del st.session_state[key]
        st.session_state.token = token
        initialize_session_state()
        st.rerun()

def handle_polling():
    """Poll the API for analysis results and handle the response."""
    status_message = "Optimizing your resume with AI..." if st.session_state.analysis_status == 'OPTIMIZING' else "Analyzing your resume... This may take up to 1 - 3 minutes."
    with st.spinner(status_message):
        start_time = time.time()  # Track start time for progress
        progress_bar = st.progress(0)  # Initialize progress bar
        st.toast("Polling for results...", icon=":material/hourglass_top:")  # Toast notification with material icon
        
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        while True:
            try:
                result_response = requests.get(f"{API_BASE_URL}/v1/analysis/{st.session_state.current_analysis_id}", headers=headers)
                if result_response.status_code == 200:
                    data = result_response.json()
                    if data["status"] == "COMPLETED":
                        st.session_state.analysis_results = data.get("results")
                        st.session_state.optimized_resume = data.get("optimized_resume")
                        st.session_state.analysis_status = "COMPLETED"
                        st.rerun()
                        break
                    elif data["status"] == "FAILED":
                        st.session_state.analysis_status = "FAILED"
                        st.rerun()
                        break
                    # If still PENDING or OPTIMIZING, update progress
                    elapsed = time.time() - start_time
                    progress_bar.progress(min(elapsed / 180, 1.0))
                else:
                    st.session_state.analysis_status = "FAILED"
                    st.error("Could not retrieve analysis results.")
                    st.rerun()
                    break
            except requests.exceptions.RequestException as e:
                st.session_state.analysis_status = "FAILED"
                st.error(f"Connection error while polling: {e}")
                st.rerun()
                break
            time.sleep(5)  # Poll every 5 seconds

def handle_analysis_display():
    """Display analysis results and the button to generate the optimized resume."""
    st.markdown("<h5>Review Analysis & Generate Your New Resume</h5>", unsafe_allow_html=True)
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
        st.markdown('<h5><span class="material-icons" style="vertical-align: middle; margin-right: 0.5rem;">thumb_up</span>Strengths</h5>', unsafe_allow_html=True)
        for strength in results.get('strengths', ["No strengths identified."]):
            st.markdown(f"- {strength}")
            
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown('<h5><span class="material-icons" style="vertical-align: middle; margin-right: 0.5rem;">key_off</span>Missing Keywords</h5>', unsafe_allow_html=True)
        for keyword in results.get('missing_keywords', ["No missing keywords."]):
            st.markdown(f"- `{keyword}`")

    with col2.container(border=True):
        st.markdown('<h5><span class="material-icons" style="vertical-align: middle; margin-right: 0.5rem;">construction</span>Recommended Improvements</h5>', unsafe_allow_html=True)
        if not results.get('improvements'):
            st.info("No specific improvements were suggested.")
        else:
            for imp in results.get('improvements', []):
                priority_color_map = {"High": "#ef4444", "Medium": "#fbbf24", "Low": "#059669"}
                color = priority_color_map.get(imp.get('priority', 'Low'), "#059669")
                st.markdown(f"""<div style="margin-bottom: 0.5rem;"><strong style="color:{color};">[{imp.get('priority', 'Low')}] {imp.get('category', 'General')}:</strong> <span>{imp.get('suggestion', 'No suggestion.')}</span></div>""", unsafe_allow_html=True)
                st.caption(f"Issue: {imp.get('issue', 'N/A')}")

    st.divider()
    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        if st.button("Generate My Optimized Resume!", icon=":material/auto_awesome:", type="primary", use_container_width=True):
            headers = {"Authorization": f"Bearer {st.session_state.token}"}
            try:
                response = requests.post(f"{API_BASE_URL}/v1/optimize/{st.session_state.current_analysis_id}", headers=headers)
                response.raise_for_status()
                st.session_state.analysis_status = 'OPTIMIZING'
                st.rerun()
            except requests.exceptions.RequestException as e:
                st.error(f"Failed to start optimization task: {e}")

def render_success_page():
    """Displays the final success page with download options."""
    st.balloons()
    st.markdown('<h1><span class="material-icons" style="vertical-align: -0.1em; font-size: 1.1em; margin-right: 0.2em;">celebration</span>Your Optimized Resume is Ready!</h1>', unsafe_allow_html=True)
    st.markdown("Your resume has been tailored to the job description. Download it below or start a new session.")

    pdf_data = generate_templated_pdf(st.session_state.optimized_resume)
    if pdf_data:
        file_name = f"Optimized_Resume_{os.path.splitext(st.session_state.uploaded_filename)[0]}.pdf" if st.session_state.uploaded_filename else "Optimized_Resume.pdf"
        st.download_button(
            label="Download Optimized Resume (PDF)",
            data=pdf_data,
            file_name=file_name,
            mime="application/pdf",
            type="primary",
            use_container_width=True,
            icon=":material/download:"
        )

    with st.expander("View Raw Optimized Data (JSON)"):
        st.json(st.session_state.optimized_resume)

if __name__ == "__main__":
    main()