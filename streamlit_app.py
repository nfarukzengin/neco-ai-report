import streamlit as st
import pandas as pd
import google.generativeai as genai
from datetime import timedelta, date
import numpy as np

st.set_page_config(page_title="Neco AI", layout="wide")
st.title("🚀 Fresh Scarfs AI Analiz Paneli")

# SOL MENÜ - GİRİŞ VE BAĞLANTI
st.sidebar.header("🔑 Sistem Girişi")
sifre = st.sidebar.text_input("Giriş Şifresi:", type="password")
sheet_id_input = st.sidebar.text_input("Google Sheet ID:")

if sifre == "fresh123":
    if sheet_id_input:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id_input}/export?format=xlsx"
        
        try:
            tum_sayfalar = pd.read_excel(url, sheet_name=None)
            sayfa_isimleri = list(tum_sayfalar.keys())
            secilen_sayfa = st.sidebar.selectbox("📂 Sayfa (Sekme) Seç:", sayfa_isimleri)
            
            df = tum_sayfalar[secilen_sayfa].copy()

            # 🛠 TARİH İŞLEME
            def tarih_temizle(x):
                x = str(x).split('-')[0].split('–')[0].strip()
                return x

            df['Tarih_Temiz'] = df['Tarih'].apply(tarih_temizle)
            
            # Türkçe ay desteği
            aylar = {"Ocak": "01", "Şubat": "02", "Mart": "03", "Nisan": "04", "Mayıs": "05", "Haziran": "06", 
                     "Temmuz": "07", "Ağustos": "08", "Eylül": "09", "Ekim": "10", "Kasım": "11", "Aralık": "12"}
            
            for tr, sayi in aylar.items():
                df['Tarih_Temiz'] = df['Tarih_Temiz'].str.replace(tr, sayi, case=False)
            
            df['Tarih_Formatli'] = pd.to_datetime(df['Tarih_Temiz'], dayfirst=True, errors='coerce')
            df = df.dropna(subset=['Tarih_Formatli'])

            # 🛠 SÜTUN TEMİZLİĞİ (METİN VE SAYI AYRIMI)
            for col in df.columns:
                # Ürün Adı, Kampanya gibi metin kalması gerekenleri atla
                if any(x in col.lower() for x in ['ürün', 'adı', 'kampanya', 'tarih']):
                    df[col] = df[col].astype(str).replace('nan', '')
                    continue
                
                # Diğerlerini sayıya çevir ve temizle
                temiz = df[col].astype(str).str.replace('₺', '', regex=False).str.replace('.', '', regex=False).str.replace('%', '', regex=False).str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(temiz, errors='coerce').fillna(0)

            st.sidebar.markdown("---")
            sekme = st.sidebar.radio("📌 Menü", ["Ana Analiz", "Karşılaştırma"])

            if df.empty:
                st.error("Kiral veriler işlenemedi, formatı kontrol et.")
            else:
                if sekme == "Ana Analiz":
                    # TARİH FİLTRESİ
                    min_t, max_t = df['Tarih_Formatli'].min().date(), df['Tarih_Formatli'].max().date()
                    c1, c2 = st.columns(2)
                    with c1: start_d = st.date_input("Başlangıç", min_t)
                    with c2: end_d = st.date_input("Bitiş", max_t)

                    mask = (df['Tarih_Formatli'].dt.date >= start_d) & (df['Tarih_Formatli'].dt.date <= end_d)
                    f_df = df.loc[mask].copy()
                    
                    # Görüntüleme Tablosu
                    d_df = f_df.drop(columns=['Tarih_Formatli', 'Tarih_Temiz'])
                    
                    # Toplam Satırı (Sadece sayısal olanlar için)
                    numeric_cols = d_df.select_dtypes(include=[np.number]).columns
                    toplam = d_df[numeric_cols].sum()
                    toplam_row = {col: '' for col in d_df.columns}
                    for col in numeric_cols: toplam_row[col] = toplam[col]
                    toplam_row['Tarih'] = 'TOPLAM'
                    
                    d_df = pd.concat([d_df, pd.DataFrame([toplam_row])], ignore_index=True)

                    # 💎 ŞIK FORMATLAMA
                    def format_hucre(val, col):
                        if val == '' or val == 'nan': return ''
                        if isinstance(val, (int, float)):
                            if any(x in col.lower() for x in ['revenue', 'cost', 'cpc', 'cpa', 'harcama']):
                                return f"₺{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                            elif any(x in col.lower() for x in ['roas', 'ctr', 'oran']):
                                return f"{val:,.2f}"
                            else:
                                return f"{int(val)}" # Transaction, Imp gibi değerler tam sayı
                        return val

                    for col in d_df.columns:
                        d_df[col] = d_df.apply(lambda row: format_hucre(row[col], col), axis=1)

                    st.subheader("📊 Analiz Tablosu")
                    st.dataframe(d_df.style.apply(lambda x: ['background-color: #004d40; color: white; font-weight: bold'] * len(x) if x['Tarih'] == 'TOPLAM' else [''] * len(x), axis=1))

                    # AI KISMI
                    st.sidebar.markdown("---")
                    if st.sidebar.button("🤖 AI Raporu Al"):
                        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                        model = genai.GenerativeModel('gemini-pro')
                        with st.spinner('Kiral analiz ediyor...'):
                            prompt = f"Şu verileri analiz et: {f_df.drop(columns=['Tarih_Formatli','Tarih_Temiz']).to_string()}"
                            st.info(model.generate_content(prompt).text)

        except Exception as e:
            st.error(f"Hata kiral! Detay: {e}")
    else:
        st.info("Sheet ID gir kiral.")
else:
    if sifre: st.warning("Şifre yanlış!")
