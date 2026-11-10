import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kiyim_ai.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Foydalanuvchi profili
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT DEFAULT 'Foydalanuvchi',
        height_cm REAL DEFAULT 175.0,
        weight_kg REAL DEFAULT 70.0,
        gender TEXT DEFAULT 'male',
        preferred_size TEXT DEFAULT 'M',
        updated_at TEXT
    );
    """)

    # Kiyimlar katalogi
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS garments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT DEFAULT 'upper_body',
        image_url TEXT NOT NULL,
        sizes TEXT DEFAULT '["S", "M", "L", "XL"]',
        created_at TEXT
    );
    """)

    # Virtual Try-On va Fit Tahlil Tarixi
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tryon_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_image_url TEXT NOT NULL,
        garment_image_url TEXT NOT NULL,
        result_image_url TEXT NOT NULL,
        fit_status TEXT DEFAULT 'perfect',
        match_percentage REAL DEFAULT 92.0,
        recommended_size TEXT DEFAULT 'M',
        fit_advice TEXT,
        body_metrics TEXT,
        created_at TEXT
    );
    """)

    # Standart profil mavjudligini tekshirish
    cursor.execute("SELECT COUNT(*) as count FROM profiles")
    if cursor.fetchone()["count"] == 0:
        cursor.execute("""
            INSERT INTO profiles (full_name, height_cm, weight_kg, gender, preferred_size, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('Xurshid', 178.0, 72.0, 'male', 'M', datetime.now().isoformat()))

    # Standart kiyimlar mavjudligini tekshirish
    cursor.execute("SELECT COUNT(*) as count FROM garments")
    if cursor.fetchone()["count"] == 0:
        default_garments = [
            ("Premium Classic Hoodie", "upper_body", "/static/garments/garment_1.jpg", json.dumps(["S", "M", "L", "XL"])),
            ("Urban Street T-Shirt", "upper_body", "/static/garments/garment_1.jpg", json.dumps(["XS", "S", "M", "L", "XL", "XXL"])),
            ("Luxury Black Blazer", "upper_body", "/static/garments/garment_1.jpg", json.dumps(["M", "L", "XL"])),
        ]
        cursor.executemany("""
            INSERT INTO garments (title, category, image_url, sizes, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, [(t, c, img, s, datetime.now().isoformat()) for t, c, img, s in default_garments])

    conn.commit()
    conn.close()

def get_profile():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles ORDER BY id ASC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {}

def update_profile(full_name, height_cm, weight_kg, gender, preferred_size):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE profiles
        SET full_name = ?, height_cm = ?, weight_kg = ?, gender = ?, preferred_size = ?, updated_at = ?
        WHERE id = 1
    """, (full_name, height_cm, weight_kg, gender, preferred_size, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return get_profile()

def get_garments():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM garments ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["sizes"] = json.loads(d["sizes"])
        except:
            d["sizes"] = ["S", "M", "L", "XL"]
        result.append(d)
    return result

def add_garment(title, category, image_url, sizes):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO garments (title, category, image_url, sizes, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (title, category, image_url, json.dumps(sizes), datetime.now().isoformat()))
    garment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return garment_id

def add_tryon_session(user_image_url, garment_image_url, result_image_url, fit_status, match_percentage, recommended_size, fit_advice, body_metrics):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tryon_sessions (
            user_image_url, garment_image_url, result_image_url,
            fit_status, match_percentage, recommended_size, fit_advice, body_metrics, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_image_url, garment_image_url, result_image_url,
        fit_status, match_percentage, recommended_size, fit_advice,
        json.dumps(body_metrics) if isinstance(body_metrics, dict) else str(body_metrics),
        datetime.now().isoformat()
    ))
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id

def get_tryon_sessions():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tryon_sessions ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["body_metrics"] = json.loads(d["body_metrics"])
        except:
            d["body_metrics"] = {}
        result.append(d)
    return result

def delete_tryon_session(session_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tryon_sessions WHERE id = ?", (session_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def clear_all_tryon_sessions():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tryon_sessions")
    conn.commit()
    conn.close()
    return True
