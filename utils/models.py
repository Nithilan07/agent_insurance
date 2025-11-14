# models.py
import sqlite3
import os

DB = "claims.db"

def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS claims (
        id TEXT PRIMARY KEY,
        name TEXT,
        insuranceId TEXT,
        policyName TEXT,
        status TEXT,
        currentStage TEXT,
        createdAt TEXT,
        updatedAt TEXT,
        resultJson TEXT
    );
    """)
    conn.commit()
    conn.close()

def save_claim(id, name, insuranceId, policyName, status):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO claims (id, name, insuranceId, policyName, status, currentStage, createdAt, updatedAt)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'));
    """, (id, name, insuranceId, policyName, status, "pending"))
    conn.commit()
    conn.close()

def update_claim(id, stage=None, status=None, resultJson=None):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        UPDATE claims
        SET currentStage = COALESCE(?, currentStage),
            status = COALESCE(?, status),
            resultJson = COALESCE(?, resultJson),
            updatedAt = datetime('now')
        WHERE id = ?;
    """, (stage, status, resultJson, id))
    conn.commit()
    conn.close()

def get_all_claims():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id, name, insuranceId, policyName, status, currentStage, createdAt FROM claims ORDER BY createdAt DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_claim(id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT * FROM claims WHERE id = ?", (id,))
    row = cur.fetchone()
    conn.close()
    return row
