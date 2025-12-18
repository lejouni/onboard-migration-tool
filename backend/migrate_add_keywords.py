"""
Migration script to add keywords column to templates table
"""
import sqlite3
import os

# Get the database path
db_path = os.path.join(os.path.dirname(__file__), 'data', 'app.db')

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Add the keywords column
    cursor.execute('ALTER TABLE templates ADD COLUMN keywords TEXT')
    conn.commit()
    print("✅ Successfully added 'keywords' column to templates table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("ℹ️  Column 'keywords' already exists")
    else:
        print(f"❌ Error: {e}")
        raise
finally:
    conn.close()
