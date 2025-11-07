# database.py
import sqlite3

DB_PATH = "attendance.db"

def init_db():
    """Initializes the SQLite database tables."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        embedding_path TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        verified TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    conn.commit()
    conn.close()

def get_db_connection():
    """Returns a connection object with row factory set to sqlite3.Row."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

def get_all_attendance():
    """Fetches all attendance records with user names."""
    init_db() # Ensure tables exist before querying
    conn = get_db_connection()
    # Join attendance with users to show the name, and handle unrecognized entries (user_id IS NULL)
    query = """
    SELECT 
        a.timestamp,
        COALESCE(u.name, 'Unrecognized User') as name,
        a.verified
    FROM attendance a
    LEFT JOIN users u ON a.user_id = u.id
    ORDER BY a.timestamp DESC
    """
    records = conn.execute(query).fetchall()
    conn.close()
    return records