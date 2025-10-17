import streamlit as st
import pandas as pd
import json
import database as db

def show_kb_wizard():
    """Displays a wizard to create a KB and saves it to the database."""
    st.header("Knowledge Base Setup")
    
    # Initialize session state for wizard data
    if 'kb_data_input' not in st.session_state: st.session_state.kb_data_input = {}
    if 'product_categories_df' not in st.session_state:
        st.session_state.product_categories_df = pd.DataFrame([
            {"Category Name": "Platform", "Description": "Core infrastructure, performance, and backend updates.", "Keywords & Aliases (comma-separated)": "performance, infrastructure, upgrade"},
            {"Category Name": "UI/UX", "Description": "Changes to the user interface and user experience.", "Keywords & Aliases (comma-separated)": "UI, design, frontend, usability"},
        ])
    if 'terminology_df' not in st.session_state:
        st.session_state.terminology_df = pd.DataFrame([{"Term to Replace": "OldName", "Correct Term": "New Product Name"}])

    st.info("To tailor the AI to your organization, please provide the following details. This configuration will be saved for all users in your organization and can be edited later.")
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Step 1: Basic Company & Document Information")
    st.session_state.kb_data_input['company_name'] = st.text_input("Company Name", st.session_state.user.get('org_name', ''))
    
    st.subheader("Step 2: Define Product Categories")
    st.session_state.product_categories_df = st.data_editor(st.session_state.product_categories_df, num_rows="dynamic", use_container_width=True)

    st.subheader("Step 3: Establish Writing & Style Rules")
    st.session_state.kb_data_input['tone_rule'] = st.text_area("General Tone of Voice", "Adopt a neutral, professional tone (Microsoft Style Guide). State facts directly.")
    st.markdown("##### Terminology Replacements")
    st.session_state.terminology_df = st.data_editor(st.session_state.terminology_df, num_rows="dynamic", use_container_width=True)

    if st.button("Save Configuration", use_container_width=True, type="primary"):
        final_kb = {
            "company_name": st.session_state.kb_data_input.get('company_name', st.session_state.user.get('org_name', '')),
            "product_categories": {
                row["Category Name"]: {
                    "description": row["Description"],
                    "keywords_and_aliases": [k.strip() for k in row["Keywords & Aliases (comma-separated)"].split(',')]
                } for index, row in st.session_state.product_categories_df.iterrows()
            },
            "writing_style_guide": {
                "professional_tone_rule": st.session_state.kb_data_input.get('tone_rule', ''),
                 "terminology_rules": {
                    row["Term to Replace"]: row["Correct Term"]
                    for index, row in st.session_state.terminology_df.iterrows()
                }
            }
        }
        
        db.save_knowledge_base(st.session_state.user['org_id'], final_kb)
        st.success("Knowledge Base configuration saved successfully!")
        
        st.session_state.kb_content = final_kb
        st.session_state.workflow = 'selection'
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)