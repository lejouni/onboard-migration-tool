"""
Migration script to add new fields to templates table for workflow enhancement feature
Run this to update the existing database schema
"""
import sqlite3
import json
from pathlib import Path

def migrate_templates_schema():
    """Add new columns to templates table"""
    db_path = Path(__file__).parent / "data" / "secrets.db"
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        print("Creating database and tables...")
        from database import create_tables
        create_tables()
        print("✅ Database created")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(templates)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Add template_type column if it doesn't exist
        if 'template_type' not in columns:
            print("Adding template_type column...")
            cursor.execute("ALTER TABLE templates ADD COLUMN template_type VARCHAR(50) DEFAULT 'workflow'")
            # Update existing templates to 'workflow' type
            cursor.execute("UPDATE templates SET template_type = 'workflow' WHERE template_type IS NULL")
            print("✓ Added template_type column")
        else:
            print("✓ template_type column already exists")
        
        # Add category column if it doesn't exist
        if 'category' not in columns:
            print("Adding category column...")
            cursor.execute("ALTER TABLE templates ADD COLUMN category VARCHAR(100)")
            print("✓ Added category column")
        else:
            print("✓ category column already exists")
        
        # Add metadata column if it doesn't exist
        if 'meta_data' not in columns:
            print("Adding meta_data column...")
            cursor.execute("ALTER TABLE templates ADD COLUMN meta_data TEXT")  # SQLite stores JSON as TEXT
            print("✓ Added meta_data column")
        else:
            print("✓ meta_data column already exists")
        
        conn.commit()
        print("\n✅ Schema migration completed successfully!")
        
        # Show current templates
        cursor.execute("SELECT id, name, template_type FROM templates")
        templates = cursor.fetchall()
        print(f"\nCurrent templates ({len(templates)}):")
        for t in templates:
            print(f"  - {t[1]} (type: {t[2] or 'workflow'})")
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_templates_schema()
