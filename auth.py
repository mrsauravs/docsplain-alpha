import streamlit as st
from streamlit_oauth import OAuth2Component
import database as db

def show_auth_flow():
    """
    Handles the full user authentication and registration flow using Auth0.
    Returns the user's data from the local database upon successful login.
    """
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/Okta.svg/2560px-Okta.svg.png", width=100) # Using Okta logo as Auth0 is now Okta CIC
    st.subheader("Welcome to the Doc Assistant")
    st.info("Please sign in or create an account to continue.")
    
    # The component will read these values from your secrets.toml file
    oauth2 = OAuth2Component(
        client_id=st.secrets["AUTH0_CLIENT_ID"],
        client_secret=st.secrets["AUTH0_CLIENT_SECRET"],
        authorize_endpoint=f"https://{st.secrets['AUTH0_DOMAIN']}/authorize",
        token_endpoint=f"https://{st.secrets['AUTH0_DOMAIN']}/oauth/token",
        scope="openid profile email",
    )

    if 'token' not in st.session_state:
        result = oauth2.authorize_button(
            name="Login / Sign Up",
            icon="https://www.google.com.tw/favicon.ico",
            use_container_width=True,
        )
        if result and "token" in result:
            st.session_state.token = result['token']
            st.rerun()
    else:
        user_info = st.session_state.token.get('userinfo')
        if user_info:
            local_user = db.get_user_by_email(user_info['email'])
            
            if local_user:
                st.markdown('</div>', unsafe_allow_html=True)
                return local_user
            else:
                st.subheader("Welcome! Let's set up your organization.")
                st.info("Since this is your first time, please create an organization. All users with your email domain will be able to join.")
                org_name = st.text_input("Enter your organization's name:")
                if st.button("Create Organization", use_container_width=True):
                    if org_name:
                        new_user = db.create_user_and_organization(user_info, org_name)
                        st.success(f"Organization '{org_name}' created successfully!")
                        st.rerun()
                    else:
                        st.warning("Please enter an organization name.")
    
    st.markdown('</div>', unsafe_allow_html=True)
    return None