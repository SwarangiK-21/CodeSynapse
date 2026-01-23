import sqlite3
import json
import os

DB_FILE = os.path.join(os.getcwd(), "data", "codesynapse.db") if os.path.exists("/code/data") else "codesynapse.db"

def init_db():
    """Creates tables for user profile and chat history."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # User Profile Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            github TEXT,
            leetcode TEXT,
            hackerrank TEXT,
            gfg TEXT
        )
    ''')

    # Chat History Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_profile(gh, lc, hr, gfg):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_history") # Keep only latest
    cursor.execute("INSERT INTO user_history (github, leetcode, hackerrank, gfg) VALUES (?, ?, ?, ?)", 
                   (gh, lc, hr, gfg))
    conn.commit()
    conn.close()

def get_last_profile():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT github, leetcode, hackerrank, gfg FROM user_history ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"github": row[0], "leetcode": row[1], "hackerrank": row[2], "gfg": row[3]}
    return None

# --- CHAT HISTORY FUNCTIONS ---
def save_chat_message(role, content):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chat_logs (role, content) VALUES (?, ?)", (role, content))
    conn.commit()
    conn.close()

def get_chat_history():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM chat_logs ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [(row[0], row[1]) for row in rows]

def clear_chat_history():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_logs")
    conn.commit()
    conn.close()