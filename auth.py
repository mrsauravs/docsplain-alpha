import streamlit as st
import database as db
import requests
import json
from jose import jwt

def get_auth0_auth_url():
    """Constructs the authorization URL to redirect the user to Auth0."""
    domain = st.secrets["AUTH0_DOMAIN"]
    client_id = st.secrets["AUTH0_CLIENT_ID"]
    # This must be the EXACT URL you configured in your Auth0 application settings
    redirect_uri = "https://docsplain-alpha. streamlit.app"
    
    url = (
        f"https://{domain}/authorize"
        f"?response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope=openid%20profile%20email"
    )
    return url

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
        response.raise_for_status()  # Will raise an exception for HTTP error codes
        token_data = response.json()
        
        # Decode the ID token to get user profile information
        id_token = token_data.get('id_token')
        if id_token:
            # We need to get the signing key from Auth0 to verify the token
            jwks_url = f"https://{domain}/.well-known/jwks.json"
            jwks = requests.get(jwks_url).json()
            unverified_header = jwt.get_unverified_header(id_token)
            rsa_key = {}
            for key in jwks["keys"]:
                if key["kid"] == unverified_header["kid"]:
                    rsa_key = {
                        "kty": key["kty"],
                        "kid": key["kid"],
                        "use": key["use"],
                        "n": key["n"],
                        "e": key["e"]
                    }
            if rsa_key:
                user_info = jwt.decode(
                    id_token,
                    rsa_key,
                    algorithms=["RS256"],
                    audience=client_id,
                    issuer=f"https://{domain}/"
                )
                return user_info
    except requests.exceptions.RequestException as e:
        st.error(f"Error exchanging authorization code: {e}")
        st.error(f"Response from server: {e.response.text if e.response else 'No response'}")

    return None

def show_auth_flow():
    """Handles the full user authentication and registration flow using Auth0."""
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/Okta.svg/2560px-Okta.svg.png", width=100)
    st.subheader("Welcome to Docsplain")

    query_params = st.query_params
    auth_code = query_params.get("code")

    if not auth_code:
        st.info("Please sign in or create an account to continue.")
        auth_url = get_auth0_auth_url()
        
        # --- MODIFICATION ---
        # Replaced the markdown link with a standard Streamlit button.
        # When clicked, it will execute a small piece of JavaScript to redirect the
        # top-level browser window, reliably breaking out of the iframe.
        if st.button("Login / Sign Up", use_container_width=True, type="primary"):
            js_redirect = f'<script>window.top.location.href = "{auth_url}"</script>'
            st.html(js_redirect)
        # --- END MODIFICATION ---

    else:
        with st.spinner("Authenticating..."):
            user_info = get_token_from_code(auth_code)
            st.query_params.clear() # Clean the URL

            if user_info:
                local_user = db.get_user_by_email(user_info['email'])
                
                if local_user:
                    st.markdown('</div>', unsafe_allow_html=True)
                    return local_user
                else:
                    st.subheader("Welcome! Let's set up your organization.")
                    st.info("Since this is your first time, please create an organization.")
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
