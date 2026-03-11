import streamlit as st
import pandas as pd
import google.generativeai as genai
from datetime import timedelta, date
import numpy as np
import re

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

            # 🛠 TARİH ARALIĞI DÜZELTİCİ (1 Ocak - 4 Ocak gibi yapıları çözer)
            def tarih_temizle(x):
                x = str(x).split('-')[0].split('–')[0].strip() # Aralıksa ilk tarihi al
                return x

            df['Tarih_Temiz'] = df['Tarih'].apply(tarih_temizle)
            df['Tarih_Formatli'] = pd.to_datetime(df['Tarih_Temiz'], dayfirst=True, errors='coerce')
            
            # Eğer hâlâ NaT varsa, Türkçe ay isimlerini kontrol et (Ocak, Şubat vb.)
            if df['Tarih_Formatli'].isna().all():
                aylar = {"Ocak": "January", "Şubat": "February", "Mart": "March", "Nisan": "April", 
                         "Mayıs": "May", "Haziran": "June", "Temmuz": "July", "Ağustos": "August", 
                         "Eylül": "September", "Ekim": "October", "Kasım": "November", "Aralık": "December"}
                for tr, en in aylar.items():
                    df['Tarih_Temiz'] = df['Tarih_Temiz'].str.replace(tr, en, case=False)
                df['Tarih_Formatli'] = pd.to_datetime(df['Tarih_Temiz'], errors='coerce')

            df = df.dropna(subset=['Tarih_Formatli'])

            # Sayısal sütun temizliği
            for col in df.columns:
                if col not in ['Tarih', 'Tarih_Formatli', 'Tarih_Temiz', 'Ürün Reklam', 'İnf Reklam', 'Cpas Reklam']:
                    temiz = df[col].astype(str).str.replace('₺', '', regex=False).str.replace('.', '', regex=False).str.replace('%', '', regex=False).str.replace('None', '0', regex=False).str.replace(',', '.', regex=False)
                    df[col] = pd.to_numeric(temiz, errors='coerce').fillna(0)

            st.sidebar.markdown("---")
            sekme = st.sidebar.radio("📌 Menü", ["Ana Analiz", "Karşılaştırma"])

            if df.empty:
                st.error("Kiral bu sayfada tarih verisi bulamadım. Hücrede '1 Ocak 2026' gibi bir format olduğundan emin ol.")
            else:
                # --- ANA ANALİZ ---
                if sekme == "Ana Analiz":
                    min_tarih, max_tarih = df['Tarih_Formatli'].min().date(), df['Tarih_Formatli'].max().date()
                    c1, c2 = st.columns(2)
                    with c1: start_date = st.date_input("Başlangıç", min_tarih)
                    with c2: end_date = st.date_input("Bitiş", max_tarih)

                    mask = (df['Tarih_Formatli'].dt.date >= start_date) & (df['Tarih_Formatli'].dt.date <= end_date)
                    filtered_df = df.loc[mask].copy()
                    
                    display_df = filtered_df.drop(columns=['Tarih_Formatli', 'Tarih_Temiz'])
                    toplam = display_df.select_dtypes(include='number').sum()
                    toplam['Tarih'] = 'TOPLAM'
                    display_df = pd.concat([display_df, pd.DataFrame([toplam])], ignore_index=True)

                    st.dataframe(display_df.style.apply(lambda x: ['background-color: #004d40; color: white'] * len(x) if x['Tarih'] == 'TOPLAM' else [''] * len(x), axis=1))

                    # AI SORGUSU
                    st.subheader("🤖 AI Raporu")
                    if st.button("Analiz Et"):
                        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                        model = genai.GenerativeModel('gemini-pro')
                        prompt = f"Şu e-ticaret verilerini yorumla, ciro ve reklam verimliliği hakkında 3 madde yaz: {filtered_df.to_string()}"
                        st.write(model.generate_content(prompt).text)

                # --- KARŞILAŞTIRMA ---
                elif sekme == "Karşılaştırma":
                    st.subheader("⚖️ Dönem Kıyasla")
                    c1, c2 = st.columns(2)
                    with c1: s1 = st.date_input("Dönem 1 Başlangıç", date.today() - timedelta(days=7))
                    with c2: s2 = st.date_input("Dönem 2 Başlangıç", date.today() - timedelta(days=14))
                    
                    # Basit toplam kıyası
                    sum1 = df[df['Tarih_Formatli'].dt.date >= s1].select_dtypes(include='number').sum()
                    sum2 = df[df['Tarih_Formatli'].dt.date >= s2].select_dtypes(include='number').sum()
                    
                    kiyas = pd.DataFrame({'Metrik': sum1.index, 'Önceki': sum2.values, 'Güncel': sum1.values})
                    kiyas['Değişim (%)'] = ((kiyas['Güncel'] - kiyas['Önceki']) / kiyas['Önceki'].replace(0, np.nan) * 100).fillna(0)
                    st.table(kiyas)

        except Exception as e:
            st.error(f"Hata kiral! Detay: {e}")
    else:
        st.info("Sheet ID gir kiral.")
else:
    if sifre: st.warning("Şifre yanlış!")
