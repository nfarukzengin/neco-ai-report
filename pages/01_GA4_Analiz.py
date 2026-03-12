import streamlit as st
import pandas as pd

st.set_page_config(page_title="GA4 Dashboard", layout="wide")
st.title("📈 GA4 Veri Analiz Merkezi")

# 1. VERİ TEMİZLEME FONKSİYONU (EĞİTİM KISMI)
def ga4_veriyi_isle(df):
    # Eklenti veriye 15. satırda başlar (ilk 14 satırı atla)
    clean_df = df.iloc[14:].copy()
    clean_df.columns = df.iloc[14] # Başlıkları belirle
    clean_df = clean_df.iloc[1:] # Başlık satırını datadan sil
    
    # Tarihi düzelt (YYYYMMDD -> Tarih formatı)
    clean_df['tarih'] = pd.to_datetime(clean_df['tarih'], format='%Y%m%d').dt.date
    
    # Sayıları temizle (O devasa noktaları/virgülleri sayıya çevir)
    numeric_cols = ['sessions', 'purchaseRevenue', 'keyEvents', 'transactions', 'advertiserAdCost']
    for col in numeric_cols:
        if col in clean_df.columns:
            clean_df[col] = pd.to_numeric(clean_df[col], errors='coerce').fillna(0)
    
    return clean_df

# 2. VERİ ÇEKME VE GÖSTERME
if "tum_sayfalar" in st.session_state:
    try:
        raw_data = st.session_state["tum_sayfalar"]["GA4Genel"]
        df = ga4_veriyi_isle(raw_data)
        
        # Dashboard Görünümü
        st.success("Veriler başarıyla çekildi!")
        
        # Özet Kartları
        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Ciro", f"{df['purchaseRevenue'].sum():,.0f} TL")
        c2.metric("Oturum (Sessions)", f"{df['sessions'].sum():,.0f}")
        c3.metric("Reklam Maliyeti", f"{df['advertiserAdCost'].sum():,.0f} TL")

        # Grafik
        st.subheader("Günlük Ciro Trendi")
        st.line_chart(df.set_index('tarih')['purchaseRevenue'])

    except KeyError:
        st.warning("Henüz 'GA4Genel' sayfası okunmadı. Lütfen ana sayfadan Sheets bağlantısını yap.")
else:
    st.info("Ana sayfadaki Sheets bağlantısı bekleniyor...")
