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

    # Tablo şeması yanlışsa (eski sürüm) sil ve yeniden oluştur
    c.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'is_urunler')
            AND NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'is_urunler' AND column_name = 'adet'
            ) THEN
                DROP TABLE is_urunler;
            END IF;
        END $$;
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS is_urunler (
            id SERIAL PRIMARY KEY,
            urun_adi TEXT UNIQUE NOT NULL,
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


@st.cache_data(ttl=60)
def get_urunler():
    conn = get_connection()
    return pd.read_sql("SELECT * FROM is_urunler ORDER BY urun_adi", conn)


def upsert_urun(urun_adi, adet, birim_maliyet):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO is_urunler (urun_adi, adet, birim_maliyet, toplam_maliyet)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (urun_adi) DO UPDATE SET
            adet           = EXCLUDED.adet,
            birim_maliyet  = EXCLUDED.birim_maliyet,
            toplam_maliyet = EXCLUDED.toplam_maliyet
    """, (urun_adi.strip(), int(adet), float(birim_maliyet), int(adet) * float(birim_maliyet)))
    conn.commit()
    get_urunler.clear()


def add_urun(urun_adi):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO is_urunler (urun_adi, adet, birim_maliyet, toplam_maliyet)
        VALUES (%s, 0, 0, 0)
        ON CONFLICT (urun_adi) DO NOTHING
    """, (urun_adi.strip(),))
    conn.commit()
    get_urunler.clear()


def delete_urun(urun_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM is_urunler WHERE id = %s", (urun_id,))
    conn.commit()
    get_urunler.clear()


def reset_adetler():
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE is_urunler SET adet = 0, toplam_maliyet = 0")
    conn.commit()
    get_urunler.clear()


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
