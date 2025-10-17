import streamlit as st
import psycopg2
from psycopg2 import sql
import json

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
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
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS organizations (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        org_id INTEGER REFERENCES organizations(id),
                        name VARCHAR(255),
                        email VARCHAR(255) UNIQUE NOT NULL,
                        picture_url TEXT
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge_bases (
                        id SERIAL PRIMARY KEY,
                        org_id INTEGER UNIQUE REFERENCES organizations(id),
                        kb_content JSONB NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
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
                    db_dict = dict(zip(columns, user_data))

                    sanitized_user = {
                        "id": int(db_dict["id"]),
                        "org_id": int(db_dict["org_id"]),
                        "name": str(db_dict.get("name") or ""),
                        "email": str(db_dict.get("email") or ""),
                        "picture_url": str(db_dict.get("picture_url") or ""),
                        "org_name": str(db_dict.get("org_name") or "")
                    }
                    return sanitized_user
        finally:
            conn.close()
    return None

def create_user_and_organization(user_info, org_name):
    """Creates a new organization and a new user, then returns the new user's sanitized data."""
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                # --- FIX: Rewritten to be atomic and avoid race conditions ---
                # 1. Create the organization and get its ID
                cur.execute("INSERT INTO organizations (name) VALUES (%s) RETURNING id;", (org_name,))
                org_id = cur.fetchone()[0]

                # 2. Create the user and get their ID
                cur.execute("""
                    INSERT INTO users (org_id, name, email, picture_url)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id;
                """, (org_id, user_info.get('name'), user_info.get('email'), user_info.get('picture')))
                user_id = cur.fetchone()[0]
                
                conn.commit()

                # 3. Construct and return a sanitized user object directly
                # This avoids a second database call and prevents the race condition.
                new_user = {
                    "id": int(user_id),
                    "org_id": int(org_id),
                    "name": str(user_info.get("name") or ""),
                    "email": str(user_info.get("email") or ""),
                    "picture_url": str(user_info.get("picture") or ""),
                    "org_name": str(org_name or "")
                }
                return new_user
                # --- END FIX ---

        except psycopg2.Error as e:
            st.error(f"Error during user registration: {e}")
            conn.rollback()
        finally:
            conn.close()
    return None


def save_kb_for_organization(org_id, kb_content):
    """Saves or updates the knowledge base for a given organization."""
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO knowledge_bases (org_id, kb_content)
                    VALUES (%s, %s)
                    ON CONFLICT (org_id) DO UPDATE SET
                        kb_content = EXCLUDED.kb_content;
                """, (org_id, json.dumps(kb_content)))
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
                    return kb_data[0]
        finally:
            conn.close()
    return None
