import streamlit as st
import database as db
import requests
import json
from jose import jwt
import urllib.parse

def get_auth0_auth_url():
    """Constructs the authorization URL to redirect the user to Auth0."""
    domain = st.secrets["AUTH0_DOMAIN"]
    client_id = st.secrets["AUTH0_CLIENT_ID"]
    redirect_uri = "https://docsplain-alpha.streamlit.app"
    
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "openid profile email",
        "audience": f"https://{domain}/api/v2/",  # Request an audience for user management
        "prompt": "login" # Ensures login prompt is always shown
    }
    
    auth_url = f"https://{domain}/authorize?{urllib.parse.urlencode(params)}"
    return auth_url

def get_token_from_code(auth_code):
    """Exchanges the authorization code for an access token and user info."""
    domain = st.secrets["AUTH0_DOMAIN"]
    client_id = st.secrets["AUTH0_CLIENT_ID"]
    client_secret = st.secrets["AUTH0_CLIENT_SECRET"]
    redirect_uri = "https://docsplain-alpha.streamlit.app"

    token_url = f"https://{domain}/oauth/token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": auth_code,
        "redirect_uri": redirect_uri,
    }
    headers = {'content-type': 'application/json'}
    
    try:
        response = requests.post(token_url, json=payload, headers=headers)
        response.raise_for_status()
        token_data = response.json()
        
        id_token = token_data.get('id_token')
        if id_token:
            jwks_url = f"https://{domain}/.well-known/jwks.json"
            jwks = requests.get(jwks_url).json()
            unverified_header = jwt.get_unverified_header(id_token)
            rsa_key = {}
            for key in jwks["keys"]:
                if key["kid"] == unverified_header["kid"]:
                    rsa_key = { "kty": key["kty"], "kid": key["kid"], "use": key["use"], "n": key["n"], "e": key["e"] }
            if rsa_key:
                user_info = jwt.decode(
                    id_token, rsa_key, algorithms=["RS256"],
                    audience=client_id, issuer=f"https://{domain}/"
                )
                return user_info
    except requests.exceptions.RequestException as e:
        st.error(f"Error exchanging authorization code: {e}")
        st.error(f"Response from server: {e.response.text if e.response else 'No response'}")
    return None

def show_login_button():
    """Displays the login button and handles the redirect logic."""
    if st.session_state.get("do_auth_redirect", False):
        del st.session_state.do_auth_redirect
        auth_url = get_auth0_auth_url()
        js_redirect = f'<script>window.top.location.href = "{auth_url}"</script>'
        st.html(js_redirect)
        st.stop()

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/Okta.svg/2560px-Okta.svg.png", width=100)
    st.subheader("Welcome to Docsplain")
    st.info("Please sign in or create an account to continue.")
    if st.button("Login / Sign Up", use_container_width=True, type="primary"):
        st.session_state.do_auth_redirect = True
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

