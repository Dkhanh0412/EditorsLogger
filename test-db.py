import os
import sqlite3

# Test 1: Check old database
old_path = os.path.expanduser("~/Documents/EditorLog_Projects/projects.db")
print(f"Old database: {old_path}")
print(f"Exists: {os.path.exists(old_path)}")

if os.path.exists(old_path):
    conn = sqlite3.connect(old_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM projects")
    projects = cursor.fetchall()
    conn.close()
    print(f"Projects in old DB: {[p[0] for p in projects]}")

# Test 2: Check what the bundle would use
import sys
print(f"\nIs frozen (bundled): {getattr(sys, 'frozen', False)}")

if getattr(sys, 'frozen', False):
    if sys.platform == 'darwin':
        base_dir = os.path.dirname(os.path.dirname(sys.executable))
        if base_dir.endswith('.app/Contents/MacOS'):
            base_dir = base_dir.replace('Contents/MacOS', '')
        bundle_path = os.path.join(base_dir, 'Resources', 'EditorLog_Projects', 'projects.db')
        print(f"Bundle would use: {bundle_path}")
        print(f"Exists: {os.path.exists(bundle_path)}")
        
        if os.path.exists(bundle_path):
            conn = sqlite3.connect(bundle_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM projects")
            bundle_projects = cursor.fetchall()
            conn.close()
            print(f"Projects in bundle DB: {[p[0] for p in bundle_projects]}")