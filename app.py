import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io
from database import init_db, get_maliyetler, save_maliyet, delete_maliyet, get_giderler, save_gider, delete_gider

st.set_page_config(
    page_title="İdea Soft | Kar Takip",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded"
)
init_db()

IPTAL_DURUMLAR  = {"cancelled"}
ODEME_BASARISIZ = {"failed"}


def para(x):
    return f"₺{x:,.2f}"


def _norm(s):
    return str(s).lower().replace("ş","s").replace("ı","i").replace("ö","o").replace("ü","u").replace("ğ","g").replace("ç","c")

def _bul(df, *anahtar):
    for col in df.columns:
        n = _norm(col)
        if all(k in n for k in anahtar):
            return col
    return None

def parse_excel(dosya):
    df_raw = pd.read_excel(dosya, engine="openpyxl")
    df_raw = df_raw[df_raw.iloc[:, 0].notna()].reset_index(drop=True)

    col_no     = df_raw.columns[0]
    col_tutar  = _bul(df_raw, "tutar")
    col_durum  = _bul(df_raw, "siparis", "durumu") or _bul(df_raw, "durum")
    col_odeme  = _bul(df_raw, "odeme")
    col_tarih  = _bul(df_raw, "tarih")

    # Müşteri: tek sütun (ad soyad) veya iki ayrı sütun (ad + soyad)
    col_musteri_tek = _bul(df_raw, "ad", "soyad")
    col_ad          = _bul(df_raw, "musteri", "adi") or _bul(df_raw, "ad")
    col_soyad       = _bul(df_raw, "soyad")
    if col_musteri_tek:
        musteri = df_raw[col_musteri_tek].fillna("").astype(str)
    elif col_ad and col_soyad:
        musteri = df_raw[col_ad].fillna("").astype(str) + " " + df_raw[col_soyad].fillna("").astype(str)
    else:
        musteri = pd.Series([""] * len(df_raw))

    return pd.DataFrame({
        "siparis_no": df_raw[col_no].astype(str),
        "musteri":    musteri.str.strip(),
        "durum":      df_raw[col_durum].fillna("").astype(str).str.strip() if col_durum else "",
        "odeme":      df_raw[col_odeme].fillna("").astype(str).str.strip() if col_odeme else "",
        "tutar":      pd.to_numeric(df_raw[col_tutar], errors="coerce").fillna(0) if col_tutar else 0,
        "tarih":      df_raw[col_tarih].astype(str).str[:10] if col_tarih else "",
    })


# ── Sidebar ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🦷 İdea Soft")
    st.caption("Kar Takip Sistemi")
    st.markdown("---")

    sayfa = st.radio(
        "Menü",
        ["📂 Excel Yükle", "💰 Ürün Maliyetleri", "📋 Giderler", "📊 Rapor"],
        label_visibility="collapsed"
    )
    st.markdown("---")

    if st.session_state.get("df") is not None:
        df = st.session_state["df"]
        aktif = df[df["durum"].isin(AKTIF_DURUMLAR) & df["odeme"].isin(ODEME_BASARILI)]
        st.success(f"✅ {len(df)} sipariş yüklü")
        st.metric("Aktif Gelir", para(aktif["tutar"].sum()))
    else:
        st.info("Excel henüz yüklenmedi")


# ════════════════════════════════════════════════════════════════
# EXCEL YÜKLE
# ════════════════════════════════════════════════════════════════
if sayfa == "📂 Excel Yükle":
    st.title("📂 Excel Yükle")
    st.markdown("İdea Soft panelinden indirdiğin sipariş raporunu yükle.")

    dosya = st.file_uploader("Sipariş raporu (.xlsx)", type=["xlsx"])

    if dosya:
        df = parse_excel(dosya)
        st.session_state["df"] = df

        aktif  = df[~df["durum"].isin(IPTAL_DURUMLAR) & ~df["odeme"].isin(ODEME_BASARISIZ)]
        iptal  = df[df["durum"].isin(IPTAL_DURUMLAR)]
        bekler = df[df["odeme"].isin(ODEME_BASARISIZ)]

        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Toplam Sipariş", len(df))
        c2.metric("Aktif & Ödendi",  len(aktif),  help="fulfilled/approved/delivered + success")
        c3.metric("İptal",           len(iptal))
        c4.metric("Bekleyen",        len(bekler))

        st.markdown("---")
        d1, d2, d3 = st.columns(3)
        d1.metric("Aktif Gelir",    para(aktif["tutar"].sum()))
        d2.metric("İptal Bedeli",   para(iptal["tutar"].sum()))
        d3.metric("Bekleyen Bedel", para(bekler["tutar"].sum()))

        st.session_state["aktif_gelir"]  = aktif["tutar"].sum()
        st.session_state["tarih_aralik"] = f"{df['tarih'].min()[:10]} – {df['tarih'].max()[:10]}"

        # ── Kargo Hesaplayıcı ──────────────────────────────────
        st.markdown("---")
        st.markdown("#### 🚚 Kargo")
        aktif_siparis = len(aktif)
        kc1, kc2, kc3 = st.columns(3)
        with kc1:
            st.metric("Aktif Sipariş Sayısı", aktif_siparis)
        with kc2:
            kargo_birim = st.number_input(
                "Birim Kargo Ücreti (₺)",
                min_value=0.0, step=1.0, format="%.2f",
                value=102.0
            )
        with kc3:
            kargo_toplam = aktif_siparis * kargo_birim
            st.metric("Toplam Kargo", para(kargo_toplam))

        if st.button("🚚 Kargoyu Gidere Ekle", type="primary"):
            if kargo_toplam > 0:
                save_gider("Kargo", f"{aktif_siparis} sipariş × ₺{kargo_birim:.2f}", kargo_toplam)
                st.success(f"✅ {para(kargo_toplam)} kargo gidere eklendi!")
            else:
                st.error("Kargo ücreti 0 olamaz.")

        # Tüm sipariş tablosu
        st.markdown("---")
        st.markdown("#### Sipariş Listesi")
        goster = df[["siparis_no", "musteri", "durum", "odeme", "tutar", "tarih"]].copy()
        goster.columns = ["Sipariş No", "Müşteri", "Durum", "Ödeme", "Tutar", "Tarih"]
        st.dataframe(
            goster.style.format({"Tutar": "₺{:,.2f}"}),
            use_container_width=True, height=360
        )
    else:
        if st.session_state.get("df") is not None:
            st.info("Excel zaten yüklü. Yeni dosya seçmek için yukarıdan yükle.")


# ════════════════════════════════════════════════════════════════
# ÜRÜN MALİYETLERİ
# ════════════════════════════════════════════════════════════════
elif sayfa == "💰 Ürün Maliyetleri":
    st.title("💰 Ürün Maliyetleri")
    st.markdown("Bu dönem sattığın ürünleri, adetlerini ve birim maliyetlerini gir.")

    maliyetler = get_maliyetler()

    # Mevcut kayıtlar
    if not maliyetler.empty:
        toplam_maliyet = maliyetler["toplam_maliyet"].sum()
        toplam_adet    = int(maliyetler["adet"].sum())
        st.markdown(f"#### Kayıtlı Ürünler — {toplam_adet} adet | Toplam Maliyet: **{para(toplam_maliyet)}**")

        for _, row in maliyetler.iterrows():
            c1, c2, c3, c4, c5 = st.columns([4, 2, 2, 2, 1])
            c1.write(f"**{row['urun_adi']}**")
            c2.write(f"{int(row['adet'])} adet")
            c3.write(f"₺{row['birim_maliyet']:.2f} / adet")
            c4.write(f"**{para(row['toplam_maliyet'])}**")
            if c5.button("🗑️", key=f"sil_{row['id']}"):
                delete_maliyet(int(row["id"]))
                st.rerun()
        st.markdown("---")
    else:
        st.info("Henüz ürün eklenmedi.")
        st.markdown("---")

    # Yeni ürün ekle
    st.markdown("#### ➕ Ürün Ekle")
    mc1, mc2, mc3 = st.columns([4, 2, 2])
    with mc1:
        urun_adi = st.text_input("Ürün Adı", placeholder="GC Tooth Mousse Çilek Aroma")
    with mc2:
        adet = st.number_input("Adet", min_value=0, step=1, value=0)
    with mc3:
        birim_maliyet = st.number_input("Birim Maliyet (₺)", min_value=0.0, step=0.5, format="%.2f", value=0.0)

    if st.button("➕ Ekle", type="primary"):
        if urun_adi.strip() and adet > 0 and birim_maliyet > 0:
            save_maliyet(urun_adi.strip(), int(adet), birim_maliyet)
            st.success(f"✅ '{urun_adi}' eklendi!")
            st.rerun()
        else:
            st.error("Ürün adı, adet ve birim maliyet zorunlu.")

    if not maliyetler.empty:
        st.markdown("---")
        if st.button("🗑️ Tüm Ürünleri Temizle", type="secondary"):
            for mid in maliyetler["id"].tolist():
                delete_maliyet(int(mid))
            st.rerun()


# ════════════════════════════════════════════════════════════════
# GİDERLER
# ════════════════════════════════════════════════════════════════
elif sayfa == "📋 Giderler":
    st.title("📋 Giderler")

    giderler = get_giderler()

    if not giderler.empty:
        toplam = giderler["tutar"].sum()
        st.markdown(f"#### Kayıtlı Giderler — Toplam: **{para(toplam)}**")
        for _, row in giderler.iterrows():
            c1, c2, c3, c4 = st.columns([2, 4, 2, 1])
            c1.write(f"**{row['kategori']}**")
            c2.write(row["aciklama"] or "—")
            c3.write(f"**{para(row['tutar'])}**")
            if c4.button("🗑️", key=f"sil_{row['id']}"):
                delete_gider(int(row["id"]))
                st.rerun()
        st.markdown("---")
    else:
        st.info("Henüz gider eklenmedi.")
        st.markdown("---")

    # Diğer gider
    st.markdown("#### 📌 Diğer Gider")
    dc1, dc2, dc3 = st.columns([2, 4, 2])
    with dc1:
        g_kat  = st.text_input("Kategori", placeholder="Reklam, Vergi...")
    with dc2:
        g_acik = st.text_input("Açıklama", placeholder="Detay (opsiyonel)")
    with dc3:
        g_tutar = st.number_input("Tutar (₺)", min_value=0.0, step=1.0, format="%.2f")

    if st.button("➕ Ekle"):
        if g_tutar > 0 and g_kat.strip():
            save_gider(g_kat.strip(), g_acik.strip(), g_tutar)
            st.rerun()
        else:
            st.error("Kategori ve tutar zorunlu.")

    if not giderler.empty:
        st.markdown("---")
        if st.button("🗑️ Tüm Giderleri Temizle", type="secondary"):
            for gid in giderler["id"].tolist():
                delete_gider(int(gid))
            st.rerun()


# ════════════════════════════════════════════════════════════════
# RAPOR
# ════════════════════════════════════════════════════════════════
elif sayfa == "📊 Rapor":
    st.title("📊 Rapor")

    aktif_gelir = st.session_state.get("aktif_gelir")
    maliyetler  = get_maliyetler()
    giderler    = get_giderler()

    if aktif_gelir is None and st.session_state.get("df") is not None:
        df = st.session_state["df"]
        aktif = df[df["durum"].isin(AKTIF_DURUMLAR) & df["odeme"].isin(ODEME_BASARILI)]
        aktif_gelir = aktif["tutar"].sum()
        st.session_state["aktif_gelir"] = aktif_gelir

    if aktif_gelir is None:
        st.warning("Önce **Excel Yükle** sayfasından sipariş raporunu yükle.")
        st.stop()

    toplam_maliyet = maliyetler["toplam_maliyet"].sum() if not maliyetler.empty else 0
    toplam_gider   = giderler["tutar"].sum() if not giderler.empty else 0
    brut_kar       = aktif_gelir - toplam_maliyet
    net_kar        = brut_kar - toplam_gider
    marj           = (net_kar / aktif_gelir * 100) if aktif_gelir > 0 else 0
    tarih_aralik   = st.session_state.get("tarih_aralik", "Tüm dönem")

    # ── Özet kartı ──
    kar_renk = "#1a7f37" if net_kar >= 0 else "#c0392b"
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#1a3a5c,#2e6da4);padding:20px 28px;'
        f'border-radius:12px;color:white;margin-bottom:16px;">'
        f'<div style="font-size:11px;opacity:.8;letter-spacing:2px;text-transform:uppercase">İdea Soft · {tarih_aralik}</div>'
        f'<div style="font-size:20px;font-weight:700;margin-top:4px;">Satış & Kar Raporu</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Aktif Gelir",      para(aktif_gelir))
    c2.metric("Ürün Maliyeti",    para(-toplam_maliyet))
    c3.metric("Diğer Giderler",   para(-toplam_gider))
    c4.metric("Brüt Kar",         para(brut_kar))
    c5.metric("NET KAR",          para(net_kar), delta=f"%{marj:.1f} marj")

    st.markdown("---")

    # ── Ürün maliyet tablosu ──
    if not maliyetler.empty:
        st.markdown("#### 📦 Ürün Maliyet Dökümü")
        goster = maliyetler[["urun_adi", "adet", "birim_maliyet", "toplam_maliyet"]].copy()
        goster.columns = ["Ürün Adı", "Adet", "Birim Maliyet", "Toplam Maliyet"]

        toplam_satir = pd.DataFrame([{
            "Ürün Adı": "TOPLAM", "Adet": int(goster["Adet"].sum()),
            "Birim Maliyet": None, "Toplam Maliyet": goster["Toplam Maliyet"].sum()
        }])
        goster = pd.concat([goster, toplam_satir], ignore_index=True)

        st.dataframe(
            goster.style.format({
                "Birim Maliyet":   "₺{:,.2f}",
                "Toplam Maliyet":  "₺{:,.2f}",
            }, na_rep="—"),
            use_container_width=True, height=400
        )
    else:
        st.warning("⚠️ Ürün maliyeti girilmemiş — **Ürün Maliyetleri** sayfasından ekle.")

    # ── Gider detayı ──
    if not giderler.empty:
        st.markdown("---")
        st.markdown("#### 📋 Gider Detayı")
        for _, g in giderler.iterrows():
            st.markdown(f"- **{g['kategori']}** — {g['aciklama'] or ''} → **{para(g['tutar'])}**")

    # ── CSV ──
    st.markdown("---")
    if not maliyetler.empty:
        csv_df = maliyetler[["urun_adi", "adet", "birim_maliyet", "toplam_maliyet"]].copy()
        csv_df.columns = ["Ürün Adı", "Adet", "Birim Maliyet", "Toplam Maliyet"]
        csv_df.loc[len(csv_df)] = ["TOPLAM", int(csv_df["Adet"].sum()), None, csv_df["Toplam Maliyet"].sum()]
        ozet_df = pd.DataFrame([{
            "Aktif Gelir": aktif_gelir, "Ürün Maliyeti": toplam_maliyet,
            "Diğer Giderler": toplam_gider, "Net Kar": net_kar, "Marj %": round(marj, 1)
        }])
        csv_out = "\n\n".join([
            "=== ÖZET ===\n" + ozet_df.to_csv(index=False, encoding="utf-8-sig"),
            "=== ÜRÜN MALİYETLERİ ===\n" + csv_df.to_csv(index=False, encoding="utf-8-sig")
        ])
        st.download_button(
            "📥 Raporu İndir (CSV)",
            data=csv_out.encode("utf-8-sig"),
            file_name=f"ideasoft_rapor_{tarih_aralik.replace(' ', '').replace('–','_')}.csv",
            mime="text/csv",
            use_container_width=True
        )
