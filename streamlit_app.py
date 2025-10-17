import streamlit as st
import pandas as pd
import json

# Import modular components and utilities
import database as db
from utils import load_local_css, parse_csv, call_ai, generate_docx
from kb_wizard import show_kb_wizard
from auth import show_login_button, get_token_from_code

def show_new_user_registration(auth_info):
    """Displays a form for a new user to create an organization."""
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader(f"Welcome, {auth_info.get('name', 'new user')}!")
    st.info("Since this is your first time, please create an organization to get started.")
    org_name = st.text_input("Enter your organization's name:")
    
    if st.button("Create Organization", use_container_width=True, type="primary"):
        if org_name:
            with st.spinner("Setting up your account..."):
                new_user = db.create_user_and_organization(auth_info, org_name)
                if new_user:
                    # Set the user and rerun to enter the main app
                    st.session_state.user = new_user
                    st.rerun()
        else:
            st.warning("Please enter an organization name.")
    st.markdown('</div>', unsafe_allow_html=True)

def show_main_application():
    """Renders the main application UI after the user is fully authenticated and set up."""
    user = st.session_state.user
    
    st.sidebar.header(f"Welcome, {user['name']}!")
    st.sidebar.write(f"Organization: **{user['org_name']}**")
    
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    kb = db.get_kb_for_organization(user['org_id'])
    if not kb:
        st.warning("Your organization's Knowledge Base is not set up yet.")
        st.info("Please complete the wizard below to configure the AI for your team.")
        show_kb_wizard(user['org_id'])
    else:
        st.title("Docsplain Assistant")
        st.header("Generate Release Notes")
        st.markdown("This tool uses your organization's configured Knowledge Base and your uploaded CSV files to generate professional release notes.")
        
        uploaded_files = {}
        uploaded_files['epics'] = st.file_uploader("Upload Epics CSV", type="csv")
        uploaded_files['stories'] = st.file_uploader("Upload Stories CSV", type="csv")
        uploaded_files['fixes'] = st.file_uploader("Upload Bug Fixes CSV", type="csv")
        
        if st.button("Generate Release Notes", type="primary", use_container_width=True):
            if any(uploaded_files.values()):
                with st.spinner("Analyzing data and generating notes..."):
                    csv_data = {key: parse_csv(file) for key, file in uploaded_files.items() if file}
                    prompt = "Generate release notes from the following CSV data..."
                    full_prompt = f"{prompt}\n\nKnowledge Base:\n{json.dumps(kb, indent=2)}\n\nCSV Data:\n{json.dumps(csv_data, indent=2)}"
                    release_notes_md = call_ai(full_prompt)
                    st.session_state.generated_notes = release_notes_md
            else:
                st.warning("Please upload at least one CSV file.")

        if "generated_notes" in st.session_state and st.session_state.generated_notes:
            st.subheader("Generated Release Notes")
            st.markdown("---")
            docx_bytes = generate_docx(st.session_state.generated_notes)
            st.download_button(
                label="Download Release Notes (.docx)",
                data=docx_bytes,
                file_name="release_notes.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )

def main():
    """The main application entry point and router."""
    st.set_page_config(page_title="Docsplain", layout="wide")
    load_local_css("style.css")

    try:
        db.setup_database()

        # Check for user in session state first
        if "user" in st.session_state and st.session_state.user:
            show_main_application()
            return

        # If no user, check for auth code in URL
        query_params = st.query_params
        auth_code = query_params.get("code")

        if auth_code:
            with st.spinner("Finalizing login..."):
                auth_info = get_token_from_code(auth_code)
                st.query_params.clear() # Clean URL after getting code

                if auth_info:
                    local_user = db.get_user_by_email(auth_info['email'])
                    if local_user:
                        st.session_state.user = local_user
                        st.rerun() # Logged in, show main app
                    else:
                        # New user, show registration form
                        show_new_user_registration(auth_info)
                else:
                    st.error("Authentication failed. Please try to log in again.")
                    show_login_button()
        else:
            # No user and no auth code, show the login button
            show_login_button()

    except Exception as e:
        st.error("An unexpected error occurred. Please see the details below.")
        st.exception(e)

if __name__ == "__main__":
    main()

