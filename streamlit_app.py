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
            
            # 1. TARİH TEMİZLEME (HATAYI ÇÖZEN KISIM)
            df['Tarih_Formatli'] = pd.to_datetime(df['Tarih'], dayfirst=True, errors='coerce')
            # Geçersiz veya boş (NaT) olan tüm satırları uçuruyoruz
            df = df.dropna(subset=['Tarih_Formatli'])
            
            # Sayısal sütunları temizle
            for col in df.columns:
                if col not in ['Tarih', 'Tarih_Formatli', 'Ürün Reklam', 'İnf Reklam', 'Cpas Reklam']:
                    temiz = df[col].astype(str).str.replace('₺', '', regex=False).str.replace('.', '', regex=False).str.replace('%', '', regex=False).str.replace('None', '0', regex=False).str.replace(',', '.', regex=False)
                    df[col] = pd.to_numeric(temiz, errors='coerce').fillna(0)

            st.sidebar.markdown("---")
            sekme = st.sidebar.radio("📌 Menü", ["Ana Analiz", "Karşılaştırma"])

            # ---------------- ANA ANALİZ SEKMESİ ----------------
            if sekme == "Ana Analiz":
                st.subheader(f"📅 Tarih Aralığı Seç ({secilen_sayfa})")
                
                # Eğer veri boşsa uyarı ver
                if df.empty:
                    st.error("Kiral bu sayfada işlenecek tarih verisi bulamadım!")
                else:
                    col1, col2 = st.columns(2)
                    min_tarih = df['Tarih_Formatli'].min().date()
                    max_tarih = df['Tarih_Formatli'].max().date()
                    
                    with col1: start_date = st.date_input("Başlangıç", min_tarih, min_value=min_tarih, max_value=max_tarih)
                    with col2: end_date = st.date_input("Bitiş", max_tarih, min_value=min_tarih, max_value=max_tarih)
                        
                    mask = (df['Tarih_Formatli'].dt.date >= start_date) & (df['Tarih_Formatli'].dt.date <= end_date)
                    filtered_df = df.loc[mask].copy()
                    filtered_df['Tarih'] = filtered_df['Tarih_Formatli'].dt.strftime('%d.%m.%Y')
                    
                    # Gösterim için formatlı tablo hazırlığı
                    display_df = filtered_df.drop(columns=['Tarih_Formatli'])
                    
                    toplam_satiri = display_df.select_dtypes(include='number').sum()
                    toplam_satiri_df = pd.DataFrame([toplam_satiri])
                    toplam_satiri_df['Tarih'] = 'TOPLAM'
                    display_df = pd.concat([display_df, toplam_satiri_df], ignore_index=True)
                    
                    def formatla(val, col_name):
                        if isinstance(val, (int, float)):
                            fmt_val = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                            if any(x in col_name.lower() for x in ['cos', 'katkı', 'gelir']): return f"%{fmt_val}"
                            else: return f"₺{fmt_val}"
                        return val

                    for col in display_df.columns:
                        if col != 'Tarih': display_df[col] = display_df[col].apply(lambda x: formatla(x, col))
                    
                    def satir_boya(row):
                        if row['Tarih'] == 'TOPLAM': return ['background-color: #004d40; color: white; font-weight: bold'] * len(row)
                        return [''] * len(row)

                    st.subheader("📊 Veri Tablosu")
                    st.dataframe(display_df.style.apply(satir_boya, axis=1)) 
                    
                    # AI Kısmı
                    st.subheader("🤖 AI Sorgusu")
                    sorular = ["Reklam verimliliği analizi yap.", "Ciro artışı için öneri ver."]
                    secilen_sorular = st.multiselect("Soruları Seç:", sorular)
                    
                    if st.button("Sorgula"):
                        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                        model = genai.GenerativeModel('gemini-pro')
                        with st.spinner('AI düşünüyor...'):
                            prompt = f"Veriler: {filtered_df.to_string()}\nSorular: {secilen_sorular}"
                            st.success(model.generate_content(prompt).text)

            # ---------------- KARŞILAŞTIRMA SEKMESİ ----------------
            elif sekme == "Karşılaştırma":
                st.subheader(f"⚖️ Karşılaştırma ({secilen_sayfa})")
                bugun = date.today()
                
                # Tarihlerin NaT olmamasını garantiye alıp seçim yaptırıyoruz
                d1_s, d1_e = bugun - timedelta(days=7), bugun
                d2_s, d2_e = bugun - timedelta(days=15), bugun - timedelta(days=8)
                
                c1, c2 = st.columns(2)
                with c1: start1 = st.date_input("Dönem 1 Başlangıç", d1_s)
                with c2: end1 = st.date_input("Dönem 1 Bitiş", d1_e)
                
                c3, c4 = st.columns(2)
                with c3: start2 = st.date_input("Dönem 2 Başlangıç", d2_s)
                with c4: end2 = st.date_input("Dönem 2 Bitiş", d2_e)

                sum1 = df[(df['Tarih_Formatli'].dt.date >= start1) & (df['Tarih_Formatli'].dt.date <= end1)].select_dtypes(include='number').sum()
                sum2 = df[(df['Tarih_Formatli'].dt.date >= start2) & (df['Tarih_Formatli'].dt.date <= end2)].select_dtypes(include='number').sum()
                
                kiyas = pd.DataFrame({'Metrik': sum1.index, 'Önceki': sum2.values, 'Güncel': sum1.values})
                kiyas['Fark'] = kiyas['Güncel'] - kiyas['Önceki']
                kiyas['Değişim (%)'] = np.where(kiyas['Önceki'] == 0, 0, (kiyas['Fark'] / kiyas['Önceki']) * 100)
                
                st.dataframe(kiyas.style.format({'Önceki': '{:,.2f}', 'Güncel': '{:,.2f}', 'Fark': '{:,.2f}', 'Değişim (%)': '%{:.2f}'}))

        except Exception as e:
            st.error(f"Hata kiral! Belki sütun isimleri (Tarih gibi) uymuyordur. Detay: {e}")
    else:
        st.info("Kiral, lütfen sol menüden bir Google Sheet ID gir.")
else:
    if sifre: st.warning("Şifre yanlış kiral!")
