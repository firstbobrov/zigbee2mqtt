import sqlite3
import json

DB_NAME = "smart_center.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS groups
                 (name TEXT PRIMARY KEY, devices TEXT)''')   # JSON-список friendly_name
    c.execute('''CREATE TABLE IF NOT EXISTS scenarios
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, trigger_type TEXT, config TEXT)''')
    conn.commit()
    conn.close()

def get_groups():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT name, devices FROM groups")
    rows = c.fetchall()
    conn.close()
    return {name: json.loads(devices) for name, devices in rows}

def save_group(name, devices):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO groups (name, devices) VALUES (?, ?)",
              (name, json.dumps(devices)))
    conn.commit()
    conn.close()

def delete_group(name):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM groups WHERE name=?", (name,))
    conn.commit()
    conn.close()

def get_scenarios():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name, trigger_type, config FROM scenarios")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "trigger_type": r[2], "config": json.loads(r[3])} for r in rows]

def save_scenario(name, trigger_type, config):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO scenarios (name, trigger_type, config) VALUES (?, ?, ?)",
              (name, trigger_type, json.dumps(config)))
    conn.commit()
    conn.close()

def delete_scenario(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM scenarios WHERE id=?", (id,))
    conn.commit()
    conn.close()