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
        CREATE TABLE IF NOT EXISTS is_urunler (
            urun_adi TEXT PRIMARY KEY,
            satis_fiyati REAL DEFAULT 0,
            maliyet REAL DEFAULT 0
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


@st.cache_data(ttl=300)
def get_urun_map():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT urun_adi, satis_fiyati, maliyet FROM is_urunler")
    return {r[0]: {"satis_fiyati": r[1], "maliyet": r[2]} for r in c.fetchall()}


def save_urun(urun_adi, satis_fiyati, maliyet):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO is_urunler (urun_adi, satis_fiyati, maliyet)
        VALUES (%s, %s, %s)
        ON CONFLICT (urun_adi) DO UPDATE SET
            satis_fiyati = EXCLUDED.satis_fiyati,
            maliyet      = EXCLUDED.maliyet
    """, (urun_adi, satis_fiyati, maliyet))
    conn.commit()
    get_urun_map.clear()


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
