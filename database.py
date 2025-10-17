import streamlit as st
import psycopg2
from psycopg2 import sql
import json

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        # This function fetches the DATABASE_URL from Streamlit's secrets manager.
        conn = psycopg2.connect(st.secrets["DATABASE_URL"])
        return conn
    except Exception as e:
        st.error(f"Database Connection Error: Could not connect to the database. Please check your DATABASE_URL secret. Details: {e}")
        return None

def setup_database():
    """Creates the necessary tables in the database if they don't exist."""
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                # Create organizations table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS organizations (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL
                    );
                """)
                # Create users table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        org_id INTEGER REFERENCES organizations(id),
                        name VARCHAR(255),
                        email VARCHAR(255) UNIQUE NOT NULL,
                        picture_url TEXT
                    );
                """)
                # Create knowledge_bases table
                # --- FIX: Completed the SQL statement with a closing parenthesis and quotes ---
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge_bases (
                        id SERIAL PRIMARY KEY,
                        org_id INTEGER UNIQUE REFERENCES organizations(id),
                        kb_content JSONB NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                # --- END FIX ---
            conn.commit()
        except psycopg2.Error as e:
            st.error(f"Database Schema Error: Could not set up tables. Details: {e}")
        finally:
            conn.close()

def get_user_by_email(email):
    """Retrieves a user and their organization from the database by email."""
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT u.id, u.org_id, u.name, u.email, u.picture_url, o.name as org_name
                    FROM users u
                    JOIN organizations o ON u.org_id = o.id
                    WHERE u.email = %s;
                """, (email,))
                user_data = cur.fetchone()
                if user_data:
                    columns = [desc[0] for desc in cur.description]
                    return dict(zip(columns, user_data))
        finally:
            conn.close()
    return None

def create_user_and_organization(user_info, org_name):
    """Creates a new organization and a new user in the database."""
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                # Create the organization
                cur.execute("INSERT INTO organizations (name) VALUES (%s) RETURNING id;", (org_name,))
                org_id = cur.fetchone()[0]

                # Create the user
                cur.execute("""
                    INSERT INTO users (org_id, name, email, picture_url)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id;
                """, (org_id, user_info.get('name'), user_info.get('email'), user_info.get('picture')))
                user_id = cur.fetchone()[0]
                
                conn.commit()
                # Return the newly created user's full details
                return get_user_by_email(user_info.get('email'))

        except psycopg2.Error as e:
            st.error(f"Error during user registration: {e}")
            conn.rollback() # Rollback changes on error
        finally:
            conn.close()
    return None


def save_kb_for_organization(org_id, kb_content):
    """Saves or updates the knowledge base for a given organization."""
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                # Use INSERT ... ON CONFLICT to either create a new KB or update the existing one
                cur.execute("""
                    INSERT INTO knowledge_bases (org_id, kb_content)
                    VALUES (%s, %s)
                    ON CONFLICT (org_id) DO UPDATE SET
                        kb_content = EXCLUDED.kb_content;
                """, (org_id, json.dumps(kb_content))) # Ensure content is a JSON string
                conn.commit()
        finally:
            conn.close()

def get_kb_for_organization(org_id):
    """Retrieves the knowledge base content for a given organization."""
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT kb_content FROM knowledge_bases WHERE org_id = %s;", (org_id,))
                kb_data = cur.fetchone()
                if kb_data:
                    return kb_data[0] # The content is already a dict/JSONB
        finally:
            conn.close()
    return None
