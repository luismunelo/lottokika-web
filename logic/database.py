import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Load URL from environment variables or directly.
# Replace with the connection string provided below when running locally or on Render
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://neondb_owner:npg_GV2eMKb8IEYu@ep-sparkling-shadow-aivvgcqt-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require')

def get_db_connection():
    """
    Creates a connection to the PostgreSQL database on Supabase.
    Returns: Connection object or None if it fails.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"Error connecting to Supabase: {e}")
        return None

def test_connection():
    """
    Simple test to verify if Supabase is accessible and tables exist.
    """
    print(f"Connecting to: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # Test if table 'resultados' exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'resultados'
                );
            """)
            exists = cursor.fetchone()['exists']
            if exists:
                print("[SUCCESS] Connection successful. The 'resultados' table exists.")
                
                # Check row count
                cursor.execute("SELECT count(*) FROM resultados")
                count = cursor.fetchone()['count']
                print(f"[INFO] Total rows in 'resultados': {count}")
                
            else:
                print("[WARNING] Connection successful, BUT tables are missing.")
                print("Please run the initialization script in the Supabase SQL Editor.")
            
            cursor.close()
            
        except Exception as e:
            print(f"[ERROR] Error querying database: {e}")
        finally:
            conn.close()
    else:
        print("[ERROR] Could not establish connection.")

if __name__ == "__main__":
    test_connection()
