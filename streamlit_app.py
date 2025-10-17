import streamlit as st
import pandas as pd
import json

# Import modular components and utilities
import database as db
from utils import load_local_css, parse_csv, call_ai, generate_docx
from kb_wizard import show_kb_wizard
from auth import show_auth_flow

# --- App Initialization ---
st.set_page_config(page_title="Doc Assistant SaaS", page_icon="✍️", layout="wide")
load_local_css("style.css")

# One-time table creation on app startup
@st.cache_resource
def init_db():
    db.create_tables()
init_db()

# Initialize session state
defaults = {'workflow': 'selection', 'user': None, 'kb_content': None, 'generated_rn': None}
for key, value in defaults.items():
    if key not in st.session_state: st.session_state[key] = value

# --- Prompt Building ---
def build_release_notes_prompt(jira_data, kb_content):
    """Builds the prompt for the AI to generate release notes."""
    prompt = f"""
    Act as an expert technical writer for {kb_content['company_name']}.
    Follow these writing rules: {json.dumps(kb_content['writing_style_guide'])}
    Categorize content based on these product categories: {json.dumps(kb_content['product_categories'])}
    
    Jira Data (in string format):
    {jira_data.to_string()}
    
    Generate the release notes now in Markdown format.
    """
    return prompt

# --- UI WORKFLOWS for Alpha ---
def show_main_selection_screen():
    st.header(f"Welcome, {st.session_state.user['name']}!")
    st.markdown(f"Organization: **{st.session_state.user['org_name']}**")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("What would you like to do?")
    if st.button("Generate Release Notes", use_container_width=True, type="primary"):
        st.session_state.workflow = 'release_notes'; st.rerun()
    # Placeholder for future Doc Plan workflow
    st.button("Generate a Documentation Plan (Coming in Beta)", use_container_width=True, disabled=True)
    st.markdown("---")
    if st.button("Edit Knowledge Base", use_container_width=True):
        st.session_state.workflow = 'kb_wizard'; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def show_release_notes_workflow_alpha():
    st.header("Generate Release Notes (Alpha)")
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Step 1: Upload Data")
    st.info("For the Alpha, please upload one or more Jira CSV exports.")
    uploaded_files = st.file_uploader("Upload Jira CSV Exports", type="csv", accept_multiple_files=True, label_visibility="collapsed")
    
    if st.button("Generate Document", use_container_width=True, type="primary"):
        if uploaded_files:
            all_dfs = [parse_csv(f) for f in uploaded_files if f]
            if all_dfs:
                with st.spinner("Analyzing data and generating notes..."):
                    jira_df = pd.concat(all_dfs, ignore_index=True)
                    prompt = build_release_notes_prompt(jira_df, st.session_state.kb_content)
                    st.session_state.generated_rn = call_ai(prompt)
        else:
            st.warning("Please upload at least one CSV file.")
    st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.generated_rn:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Step 2: Download Your Document")
        st.success("Your release notes have been generated successfully!")
        st.download_button(
            "Download .docx",
            data=generate_docx("Release Notes", st.session_state.generated_rn),
            file_name="Release_Notes.docx",
            use_container_width=True
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    if st.button("Back to Main Menu"):
        st.session_state.workflow = 'selection'; st.rerun()

# --- Main Application Router ---
def draw_header():
    st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>✍️ Doc Assistant SaaS</h1>", unsafe_allow_html=True)

draw_header()

# 1. AUTHENTICATION
if not st.session_state.user:
    st.session_state.user = show_auth_flow()
    if not st.session_state.user:
        st.stop()

# 2. KNOWLEDGE BASE CHECK
if not st.session_state.kb_content:
    st.session_state.kb_content = db.get_knowledge_base(st.session_state.user['org_id'])
    if not st.session_state.kb_content:
        st.session_state.workflow = 'kb_wizard'

# 3. WORKFLOW ROUTING
if st.session_state.workflow == 'kb_wizard':
    show_kb_wizard()
elif st.session_state.workflow == 'selection':
    show_main_selection_screen()
elif st.session_state.workflow == 'release_notes':

    show_release_notes_workflow_alpha()

