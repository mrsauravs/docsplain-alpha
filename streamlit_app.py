import streamlit as st
import pandas as pd
import json

# Import modular components and utilities
import database as db
from utils import load_local_css, parse_csv, call_ai, generate_docx
from kb_wizard import show_kb_wizard
from auth import show_auth_flow

def show_main_application():
    """Renders the main application UI after the user has logged in."""

    # --- FIX: Add robust validation for the user object ---
    # This prevents errors if the user object is not a valid dictionary.
    if not isinstance(st.session_state.get("user"), dict) or "name" not in st.session_state.user:
        st.error("User session is invalid. Please try logging in again.")
        # Provide a way to reset the state
        if st.button("Return to Login"):
            st.session_state.user = None
            st.rerun()
        return
    # --- END FIX ---

    try:
        # Now it's safe to render the sidebar
        st.sidebar.header(f"Welcome, {st.session_state.user['name']}!")
        st.sidebar.write(f"Organization: **{st.session_state.user['org_name']}**")
        
        if st.sidebar.button("Logout"):
            st.session_state.user = None
            st.rerun()

        # Onboarding: Check if a knowledge base exists for this organization
        kb = db.get_kb_for_organization(st.session_state.user['org_id'])
        
        if not kb:
            st.warning("Your organization's Knowledge Base is not set up yet.")
            st.info("Please complete the wizard below to configure the AI for your team.")
            show_kb_wizard(st.session_state.user['org_id'])
        else:
            # Main application router
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

    except Exception as e:
        st.error("An error occurred while loading the main application. Please see details below.")
        st.exception(e)


def main():
    """The main application entry point."""
    st.set_page_config(page_title="Docsplain", layout="wide")
    load_local_css("style.css")

    try:
        # Initialize database connection and tables
        db.setup_database()

        # Main application logic
        if "user" not in st.session_state or st.session_state.user is None:
            show_auth_flow()
        else:
            show_main_application()

    except Exception as e:
        st.error("An unexpected error occurred at the application root. Please see the details below.")
        st.exception(e)


if __name__ == "__main__":
    main()
