import streamlit as st
import pandas as pd
from database import init_db, get_urun_map, save_urun, get_giderler, save_gider, delete_gider

st.set_page_config(
    page_title="İdea Soft | Kar Takip",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded"
)
init_db()


def para(x):
    return f"₺{x:,.2f}"


def parse_liste(metin):
    satirlar = []
    for line in metin.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.rsplit(None, 1)
        if len(parts) == 2:
            try:
                satirlar.append({"urun_adi": parts[0].strip(), "adet": int(parts[1].strip())})
            except ValueError:
                continue
    return satirlar


# ── Sidebar ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🦷 İdea Soft")
    st.caption("Kar Takip Sistemi")
    st.markdown("---")
    sayfa = st.radio(
        "Menü",
        ["📋 Veri Gir", "💰 Fiyat & Maliyet", "📋 Giderler", "📊 Rapor"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    satirlar = st.session_state.get("satirlar", [])
    if satirlar:
        st.success(f"✅ {len(satirlar)} ürün yüklü")
    else:
        st.info("Henüz ürün girilmedi")


# ════════════════════════════════════════════════════════════════
# VERİ GİR
# ════════════════════════════════════════════════════════════════
if sayfa == "📋 Veri Gir":
    st.title("📋 Ürün Listesi Gir")
    st.markdown(
        "İdea Soft panelinden kopyaladığın ürün listesini aşağıya yapıştır.  \n"
        "Format: **Ürün Adı** ve yanında **adet** sayısı olmalı."
    )

    metin = st.text_area(
        "Liste",
        height=320,
        placeholder="GC Tooth Mousse Çilek aroma    14\nOpalescence Go 8 li Nane    2\nPro Bleach Ağız Duşu    2",
        label_visibility="collapsed",
        value="\n".join(
            f"{r['urun_adi']}    {r['adet']}"
            for r in st.session_state.get("satirlar", [])
        ) if st.session_state.get("satirlar") else ""
    )

    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button("✅ Yükle", type="primary", use_container_width=True):
            sonuc = parse_liste(metin)
            if sonuc:
                st.session_state["satirlar"] = sonuc
                st.success(f"✅ {len(sonuc)} ürün yüklendi!")
                st.rerun()
            else:
                st.error("Liste okunamadı. Her satır 'Ürün Adı    Adet' formatında olmalı.")
    with c2:
        if st.button("🗑️ Temizle", use_container_width=True):
            st.session_state.pop("satirlar", None)
            st.rerun()

    if st.session_state.get("satirlar"):
        st.markdown("---")
        df = pd.DataFrame(st.session_state["satirlar"])
        df.columns = ["Ürün Adı", "Adet"]
        st.dataframe(df, use_container_width=True, height=420)


# ════════════════════════════════════════════════════════════════
# FİYAT & MALİYET
# ════════════════════════════════════════════════════════════════
elif sayfa == "💰 Fiyat & Maliyet":
    st.title("💰 Fiyat & Maliyet")

    if not st.session_state.get("satirlar"):
        st.info("Önce **Veri Gir** sayfasından ürün listesini yükle.")
        st.stop()

    urun_map = get_urun_map()
    satirlar = st.session_state["satirlar"]

    eksik = sum(1 for r in satirlar if r["urun_adi"] not in urun_map)
    if eksik:
        st.warning(f"⚠️ {eksik} ürünün fiyat/maliyet bilgisi girilmemiş.")
    else:
        st.success("✅ Tüm ürünlerin fiyat ve maliyeti kayıtlı.")

    st.markdown(f"**{len(satirlar)} ürün** — satış fiyatı ve maliyet gir, **Kaydet** tıkla.")
    st.markdown("---")

    with st.form("fiyat_form"):
        for i, row in enumerate(satirlar):
            urun_adi = row["urun_adi"]
            kayit = urun_map.get(urun_adi, {})
            mevcut_fiyat   = float(kayit.get("satis_fiyati", 0.0))
            mevcut_maliyet = float(kayit.get("maliyet", 0.0))

            st.markdown(f"**{urun_adi[:90]}**")
            c1, c2, c3 = st.columns([3, 2, 2])
            with c1:
                st.caption(f"Adet: {row['adet']}")
            with c2:
                st.number_input(
                    "Satış Fiyatı (₺)", value=mevcut_fiyat,
                    min_value=0.0, step=0.5, format="%.2f",
                    key=f"fiyat_{i}"
                )
            with c3:
                st.number_input(
                    "Maliyet (₺)", value=mevcut_maliyet,
                    min_value=0.0, step=0.5, format="%.2f",
                    key=f"mal_{i}"
                )
            st.divider()

        if st.form_submit_button("💾 Tümünü Kaydet", type="primary", use_container_width=True):
            for i, row in enumerate(satirlar):
                save_urun(
                    row["urun_adi"],
                    st.session_state.get(f"fiyat_{i}", 0.0),
                    st.session_state.get(f"mal_{i}", 0.0),
                )
            st.success("✅ Kaydedildi!")
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

    # ── Kargo hesaplayıcı ──────────────────────────────────────
    st.markdown("#### 🚚 Kargo")
    kc1, kc2, kc3 = st.columns(3)
    with kc1:
        kargo_adet  = st.number_input("Kargo Adedi", min_value=0, step=1, value=0)
    with kc2:
        kargo_birim = st.number_input("Birim Fiyat (₺)", min_value=0.0, step=1.0, format="%.2f", value=0.0)
    with kc3:
        st.metric("Toplam Kargo", para(kargo_adet * kargo_birim))

    if st.button("🚚 Kargoyu Gidere Ekle", type="primary"):
        toplam_k = kargo_adet * kargo_birim
        if toplam_k > 0:
            save_gider("Kargo", f"{kargo_adet} adet × ₺{kargo_birim:.2f}", toplam_k)
            st.rerun()
        else:
            st.error("Adet ve birim fiyat gir.")

    st.markdown("---")

    # ── Diğer gider ────────────────────────────────────────────
    st.markdown("#### 📌 Diğer Gider")
    mc1, mc2, mc3 = st.columns([2, 4, 2])
    with mc1:
        g_kat  = st.text_input("Kategori", placeholder="Reklam, Vergi...")
    with mc2:
        g_acik = st.text_input("Açıklama", placeholder="Detay (opsiyonel)")
    with mc3:
        g_tutar = st.number_input("Tutar (₺)", min_value=0.0, step=1.0, format="%.2f")

    if st.button("➕ Ekle"):
        if g_tutar > 0 and g_kat.strip():
            save_gider(g_kat.strip(), g_acik.strip(), g_tutar)
            st.rerun()
        else:
            st.error("Kategori ve tutar zorunlu.")

    # ── Tüm giderleri sıfırla ──────────────────────────────────
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

    if not st.session_state.get("satirlar"):
        st.info("Önce **Veri Gir** sayfasından ürün listesini yükle.")
        st.stop()

    satirlar  = st.session_state["satirlar"]
    urun_map  = get_urun_map()
    giderler  = get_giderler()
    toplam_gider = giderler["tutar"].sum() if not giderler.empty else 0

    rows = []
    for row in satirlar:
        urun_adi = row["urun_adi"]
        adet     = row["adet"]
        kayit    = urun_map.get(urun_adi, {})
        fiyat    = float(kayit.get("satis_fiyati", 0.0))
        maliyet  = float(kayit.get("maliyet", 0.0))
        net_satis       = fiyat * adet
        toplam_maliyet  = maliyet * adet
        rows.append({
            "urun_adi":       urun_adi,
            "adet":           adet,
            "satis_fiyati":   fiyat,
            "maliyet":        maliyet,
            "net_satis":      net_satis,
            "toplam_maliyet": toplam_maliyet,
            "brut_kar":       net_satis - toplam_maliyet,
        })

    df = pd.DataFrame(rows)

    # Gider paylaşımı
    toplam_net = df["net_satis"].sum()
    df["gider_payi"] = (df["net_satis"] / toplam_net * toplam_gider) if toplam_net > 0 else 0
    df["net_kar"]    = df["brut_kar"] - df["gider_payi"]

    net_satis_top = df["net_satis"].sum()
    maliyet_top   = df["toplam_maliyet"].sum()
    brut_kar_top  = df["brut_kar"].sum()
    net_kar_top   = df["net_kar"].sum()
    marj          = (net_kar_top / net_satis_top * 100) if net_satis_top > 0 else 0
    toplam_adet   = int(df["adet"].sum())

    # ── Metrikler ──
    st.markdown("#### Özet")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Toplam Adet",    toplam_adet)
    c2.metric("Net Satış",      para(net_satis_top))
    c3.metric("Ürün Maliyeti",  para(-maliyet_top))
    c4.metric("Diğer Giderler", para(-toplam_gider))
    c5.metric("NET KAR",        para(net_kar_top), delta=f"%{marj:.1f} marj")

    st.markdown("---")

    # ── Uyarı ──
    eksik = (df["satis_fiyati"] == 0).sum()
    if eksik:
        st.warning(f"⚠️ {eksik} ürünün fiyatı girilmemiş — **Fiyat & Maliyet** sayfasından doldur.")

    # ── Tablo ──
    goster = df[["urun_adi", "adet", "satis_fiyati", "maliyet",
                 "net_satis", "toplam_maliyet", "brut_kar", "net_kar"]].copy()
    goster.columns = ["Ürün Adı", "Adet", "Satış Fiyatı", "Birim Maliyet",
                      "Net Satış", "Toplam Maliyet", "Brüt Kar", "Net Kar"]

    # Toplam satırı
    toplam_satir = pd.DataFrame([{
        "Ürün Adı": "TOPLAM", "Adet": toplam_adet,
        "Satış Fiyatı": None, "Birim Maliyet": None,
        "Net Satış": net_satis_top, "Toplam Maliyet": maliyet_top,
        "Brüt Kar": brut_kar_top, "Net Kar": net_kar_top
    }])
    goster = pd.concat([goster, toplam_satir], ignore_index=True)

    def renk_kar(val):
        try:
            f = float(val)
            if f > 0: return "color:#28a745;font-weight:bold"
            if f < 0: return "color:#dc3545;font-weight:bold"
        except Exception:
            pass
        return ""

    st.dataframe(
        goster.style.format({
            "Satış Fiyatı":   "₺{:,.2f}",
            "Birim Maliyet":  "₺{:,.2f}",
            "Net Satış":      "₺{:,.2f}",
            "Toplam Maliyet": "₺{:,.2f}",
            "Brüt Kar":       "₺{:,.2f}",
            "Net Kar":        "₺{:,.2f}",
        }, na_rep="—").map(renk_kar, subset=["Brüt Kar", "Net Kar"]),
        use_container_width=True,
        height=460
    )

    # ── Gider detayı ──
    if not giderler.empty:
        st.markdown("---")
        st.markdown("#### 📋 Gider Detayı")
        for _, g in giderler.iterrows():
            st.markdown(f"- **{g['kategori']}** — {g['aciklama'] or ''} → **{para(g['tutar'])}**")

    # ── CSV ──
    st.markdown("---")
    csv = goster.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        "📥 Raporu İndir (CSV)",
        data=csv,
        file_name="ideasoft_rapor.csv",
        mime="text/csv",
        use_container_width=True
    )
