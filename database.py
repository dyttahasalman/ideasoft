import os
import psycopg2
import pandas as pd
import streamlit as st


def _get_dsn():
    try:
        return st.secrets["DATABASE_URL"]
    except Exception:
        return os.environ.get("DATABASE_URL", "")


@st.cache_resource
def _get_pool():
    conn = psycopg2.connect(_get_dsn(), sslmode="require")
    conn.autocommit = False
    return conn


def get_connection():
    conn = _get_pool()
    try:
        conn.cursor().execute("SELECT 1")
    except Exception:
        st.cache_resource.clear()
        conn = _get_pool()
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS is_maliyetler (
            id SERIAL PRIMARY KEY,
            urun_adi TEXT NOT NULL,
            adet INTEGER DEFAULT 0,
            birim_maliyet REAL DEFAULT 0,
            toplam_maliyet REAL DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS is_giderler (
            id SERIAL PRIMARY KEY,
            kategori TEXT,
            aciklama TEXT,
            tutar REAL
        )
    """)
    conn.commit()


def get_maliyetler():
    conn = get_connection()
    return pd.read_sql("SELECT * FROM is_maliyetler ORDER BY id", conn)


def save_maliyet(urun_adi, adet, birim_maliyet):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO is_maliyetler (urun_adi, adet, birim_maliyet, toplam_maliyet)
        VALUES (%s, %s, %s, %s)
    """, (urun_adi, adet, birim_maliyet, adet * birim_maliyet))
    conn.commit()


def delete_maliyet(maliyet_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM is_maliyetler WHERE id = %s", (maliyet_id,))
    conn.commit()


def get_giderler():
    conn = get_connection()
    return pd.read_sql("SELECT * FROM is_giderler ORDER BY id DESC", conn)


def save_gider(kategori, aciklama, tutar):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO is_giderler (kategori, aciklama, tutar) VALUES (%s, %s, %s)",
        (kategori, aciklama, float(tutar))
    )
    conn.commit()


def delete_gider(gider_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM is_giderler WHERE id = %s", (gider_id,))
    conn.commit()
