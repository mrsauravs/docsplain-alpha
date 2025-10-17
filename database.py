import streamlit as st
import psycopg2
import json

# --- Database Connection ---
def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(st.secrets["DATABASE_URL"])
        return conn
    except psycopg2.OperationalError as e:
        st.error(f"Database Connection Error: Could not connect to the database. Please check your DATABASE_URL secret. Details: {e}")
        return None

# --- Table Creation ---
def create_tables():
    """Creates the necessary tables in the database if they don't exist."""
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS organizations (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id VARCHAR(255) PRIMARY KEY, -- Auth0 user ID
                        email VARCHAR(255) UNIQUE NOT NULL,
                        name VARCHAR(255),
                        organization_id INTEGER REFERENCES organizations(id),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge_bases (
                        id SERIAL PRIMARY KEY,
                        organization_id INTEGER UNIQUE REFERENCES organizations(id),
                        content JSONB NOT NULL,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
            conn.commit()
        finally:
            conn.close()

# --- User and Organization Functions ---
def get_user_by_email(email):
    """Retrieves a user and their organization from the database by email."""
    conn = get_db_connection()
    user_data = None
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT u.id, u.email, u.name, u.organization_id, o.name FROM users u LEFT JOIN organizations o ON u.organization_id = o.id WHERE u.email = %s;", (email,))
                result = cur.fetchone()
                if result:
                    user_data = {"id": result[0], "email": result[1], "name": result[2], "org_id": result[3], "org_name": result[4]}
        finally:
            conn.close()
    return user_data

def create_user_and_organization(user_info, org_name):
    """Creates a new organization and a new user, linking them together."""
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                # Create organization first
                cur.execute("INSERT INTO organizations (name) VALUES (%s) RETURNING id;", (org_name,))
                org_id = cur.fetchone()[0]
                
                # Create user and link to the new organization
                cur.execute(
                    "INSERT INTO users (id, email, name, organization_id) VALUES (%s, %s, %s, %s);",
                    (user_info['sub'], user_info['email'], user_info['name'], org_id)
                )
            conn.commit()
            return {"id": user_info['sub'], "email": user_info['email'], "name": user_info['name'], "org_id": org_id, "org_name": org_name}
        finally:
            conn.close()

# --- Knowledge Base Functions ---
def save_knowledge_base(org_id, kb_content):
    """Saves or updates a knowledge base for a given organization."""
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                # Use INSERT ... ON CONFLICT to handle both new and existing KBs
                cur.execute("""
                    INSERT INTO knowledge_bases (organization_id, content)
                    VALUES (%s, %s)
                    ON CONFLICT (organization_id)
                    DO UPDATE SET content = EXCLUDED.content, updated_at = CURRENT_TIMESTAMP;
                """, (org_id, json.dumps(kb_content)))
            conn.commit()
        finally:
            conn.close()

def get_knowledge_base(org_id):
    """Retrieves the knowledge base for a given organization."""
    conn = get_db_connection()
    kb_content = None
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT content FROM knowledge_bases WHERE organization_id = %s;", (org_id,))
                result = cur.fetchone()
                if result:
                    kb_content = result[0]
        finally:
            conn.close()
    return kb_content