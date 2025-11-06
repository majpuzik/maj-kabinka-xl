#!/usr/bin/env python3
"""
Database model pro Virtual Fitting Room
"""

import sqlite3
from datetime import datetime
import json
import os

DB_PATH = 'virtual_fitting_room.db'

def init_db():
    """Initialize database with schema"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Generation history table
    c.execute('''
        CREATE TABLE IF NOT EXISTS generations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_name TEXT NOT NULL,
            person_image_path TEXT NOT NULL,
            garment_name TEXT NOT NULL,
            garment_image_path TEXT NOT NULL,
            result_image_path TEXT,
            generation_type TEXT NOT NULL,
            generation_time REAL,
            rating INTEGER DEFAULT 0,
            cost REAL DEFAULT 0,
            status TEXT DEFAULT 'pending',
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Generation variants table
    c.execute('''
        CREATE TABLE IF NOT EXISTS generation_variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            is_paid BOOLEAN DEFAULT 0,
            cost_per_generation REAL DEFAULT 0,
            is_enabled BOOLEAN DEFAULT 1,
            avg_time REAL DEFAULT 0,
            max_time REAL DEFAULT 180,
            is_blacklisted BOOLEAN DEFAULT 0,
            blacklist_reason TEXT
        )
    ''')

    # Insert default variants
    variants = [
        ('local', 'Local (Free)', 0, 0, 1, 45, 180, 0, None),
        ('local_paid', 'Local Premium', 1, 0.50, 1, 30, 180, 0, None),
        ('cloud_free', 'Cloud Free', 0, 0, 1, 60, 180, 0, None),
        ('cloud_paid', 'Cloud Premium', 1, 1.00, 1, 20, 180, 0, None),
    ]

    c.executemany('''
        INSERT OR IGNORE INTO generation_variants
        (name, display_name, is_paid, cost_per_generation, is_enabled, avg_time, max_time, is_blacklisted, blacklist_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', variants)

    conn.commit()
    conn.close()

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def save_generation(person_name, person_path, garment_name, garment_path, generation_type):
    """Save new generation to database"""
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO generations
        (person_name, person_image_path, garment_name, garment_image_path, generation_type, status)
        VALUES (?, ?, ?, ?, ?, 'processing')
    ''', (person_name, person_path, garment_name, garment_path, generation_type))
    gen_id = c.lastrowid
    conn.commit()
    conn.close()
    return gen_id

def update_generation(gen_id, result_path=None, generation_time=None, status='completed', error_message=None, cost=0):
    """Update generation with results"""
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        UPDATE generations
        SET result_image_path = ?, generation_time = ?, status = ?, error_message = ?, cost = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (result_path, generation_time, status, error_message, cost, gen_id))
    conn.commit()
    conn.close()

def update_rating(gen_id, rating):
    """Update generation rating"""
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE generations SET rating = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (rating, gen_id))
    conn.commit()
    conn.close()

def get_all_generations():
    """Get all generations ordered by date"""
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT * FROM generations
        ORDER BY created_at DESC
    ''')
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_generation(gen_id):
    """Get specific generation"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM generations WHERE id = ?', (gen_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_available_variants():
    """Get available generation variants"""
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT * FROM generation_variants
        WHERE is_enabled = 1 AND is_blacklisted = 0
        ORDER BY is_paid, cost_per_generation
    ''')
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_variant_time(variant_name, generation_time):
    """Update variant average time and blacklist if needed"""
    conn = get_db()
    c = conn.cursor()

    # Get current avg_time
    c.execute('SELECT avg_time FROM generation_variants WHERE name = ?', (variant_name,))
    row = c.fetchone()

    if row:
        current_avg = row[0]
        # Calculate new average (simple moving average)
        new_avg = (current_avg * 0.8 + generation_time * 0.2)

        # Blacklist if consistently over 3 minutes
        is_blacklisted = 0
        blacklist_reason = None
        if new_avg > 180:
            is_blacklisted = 1
            blacklist_reason = f'Průměrná doba generování {new_avg:.1f}s přesáhla 3 minuty'

        c.execute('''
            UPDATE generation_variants
            SET avg_time = ?, is_blacklisted = ?, blacklist_reason = ?
            WHERE name = ?
        ''', (new_avg, is_blacklisted, blacklist_reason, variant_name))

    conn.commit()
    conn.close()

def delete_generation(gen_id):
    """Delete generation"""
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM generations WHERE id = ?', (gen_id,))
    conn.commit()
    conn.close()

# Initialize database on import
if not os.path.exists(DB_PATH):
    init_db()
