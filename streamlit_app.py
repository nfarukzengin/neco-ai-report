import streamlit as st
import pandas as pd
import google.generativeai as genai
from datetime import timedelta, date
import numpy as np

st.set_page_config(page_title="Neco AI", layout="wide")
st.title("🚀 Fresh Scarfs AI Analiz Paneli")

if st.sidebar.text_input("Giriş Şifresi:", type="password") == "fresh123":
    
    sheet_id = "1JH3T2ib46IFuT5mnAkQoGQ1V4sZnwHaAUZA9ms1wKXo" 
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    try:
        df = pd.read_csv(url)
        df['Tarih_Formatli'] = pd.to_datetime(df['Tarih'], format='%d.%m.%Y', errors='coerce')
        df = df.dropna(subset=['Tarih_Formatli'])
        
        for col in df.columns:
            if col not in ['Tarih', 'Tarih_Formatli', 'Ürün Reklam', 'İnf Reklam', 'Cpas Reklam']:
                temiz = df[col].astype(str).str.replace('₺', '', regex=False).str.replace('.', '', regex=False).str.replace('%', '', regex=False).str.replace('None', '0', regex=False).str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(temiz, errors='coerce').fillna(0)

        st.sidebar.markdown("---")
        sekme = st.sidebar.radio("📌 Menü", ["Ana Analiz", "Karşılaştırma"])

        # ---------------- ANA ANALİZ SEKMESİ ----------------
        if sekme == "Ana Analiz":
            st.subheader("📅 Tarih Aralığı Seç")
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Başlangıç", df['Tarih_Formatli'].min().date())
            with col2:
                end_date = st.date_input("Bitiş", df['Tarih_Formatli'].max().date())
                
            mask = (df['Tarih_Formatli'].dt.date >= start_date) & (df['Tarih_Formatli'].dt.date <= end_date)
            filtered_df = df.loc[mask].copy()
            filtered_df['Tarih'] = filtered_df['Tarih_Formatli'].dt.strftime('%d.%m.%Y')
            filtered_df = filtered_df.drop(columns=['Tarih_Formatli'])
            
            toplam_satiri = filtered_df.select_dtypes(include='number').sum()
            toplam_satiri_df = pd.DataFrame([toplam_satiri])
            toplam_satiri_df['Tarih'] = 'TOPLAM'
            filtered_df = pd.concat([filtered_df, toplam_satiri_df], ignore_index=True)
            
            def formatla(val, col_name):
                if isinstance(val, (int, float)):
                    fmt_val = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    if any(x in col_name.lower() for x in ['cos', 'katkı', 'gelir']): return f"%{fmt_val}"
                    else: return f"₺{fmt_val}"
                return val

            for col in filtered_df.columns:
                if col != 'Tarih': filtered_df[col] = filtered_df[col].apply(lambda x: formatla(x, col))
            
            def satir_boya(row):
                if row['Tarih'] == 'TOPLAM': return ['background-color: #004d40; color: white; font-weight: bold'] * len(row)
                return [''] * len(row)

            st.subheader("📊 Seçili Tarihler ve Kesin Toplam")
            st.dataframe(filtered_df.style.apply(satir_boya, axis=1)) 
            
            st.subheader("🤖 AI'a Ne Sormak İstersin?")
            sorular = [
                "CPA ve COS oranlarına göre reklam verimliliğini değerlendir.",
                "En yüksek ve en düşük ciro yapılan günleri kıyasla, sence neden?",
                "Reklam harcamalarının ciroya katkısını analiz et, kârlı mıyız?",
                "Bu verilere göre yarınki reklam bütçesini artırmalı mıyım, kısmalı mıyım?",
                "Sadık müşteri kazanımı (CRM) için bu tabloya göre nasıl bir aksiyon almalıyım?"
            ]
            secilen_sorular = st.multiselect("Soruları Seç:", sorular)
            
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            uygun_modeller = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            model = genai.GenerativeModel(uygun_modeller[0])
            
            if st.button("Sorgula"):
                if not secilen_sorular: st.warning("Soru seç kiral!")
                else:
                    with st.spinner('Hazırlanıyor...'):
                        prompt = f"Şu verilere bakarak kısa cevap ver:\nSorular: {secilen_sorular}\nVeri:\n{filtered_df.to_string()}"
                        st.success(model.generate_content(prompt).text)

        # ---------------- KARŞILAŞTIRMA SEKMESİ ----------------
        elif sekme == "Karşılaştırma":
            st.subheader("⚖️ Dönem Karşılaştırması")
            
            bugun = date.today()
            
            hizli_secim = st.selectbox("Hızlı Seçim (Otomatik Önceki Dönemle Kıyaslar)", 
                                       ["Özel Tarih Seç", "Bugün", "Dün", "Son 7 Gün", "Son 15 Gün", "Son 30 Gün"])
            
            if hizli_secim == "Son 7 Gün":
                d1_end = bugun
                d1_start = bugun - timedelta(days=6)
                d2_end = d1_start - timedelta(days=1)
                d2_start = d2_end - timedelta(days=6)
            elif hizli_secim == "Son 15 Gün":
                d1_end = bugun
                d1_start = bugun - timedelta(days=14)
                d2_end = d1_start - timedelta(days=1)
                d2_start = d2_end - timedelta(days=14)
            elif hizli_secim == "Son 30 Gün":
                d1_end = bugun
                d1_start = bugun - timedelta(days=29)
                d2_end = d1_start - timedelta(days=1)
                d2_start = d2_end - timedelta(days=29)
            elif hizli_secim == "Dün":
                d1_end = d1_start = bugun - timedelta(days=1)
                d2_end = d2_start = bugun - timedelta(days=2)
            elif hizli_secim == "Bugün":
                d1_end = d1_start = bugun
                d2_end = d2_start = bugun - timedelta(days=1)
            else:
                st.info("Aşağıdan özel tarihlerinizi seçin.")
                
                # Tarihleri yan yana iki sütuna böldük
                c1, c2 = st.columns(2)
                with c1: d1_start = st.date_input("1. Dönem Başlangıç", bugun - timedelta(days=7))
                with c2: d1_end = st.date_input("1. Dönem Bitiş", bugun)
                
                c3, c4 = st.columns(2)
                with c3: d2_start = st.date_input("2. Dönem Başlangıç", bugun - timedelta(days=15))
                with c4: d2_end = st.date_input("2. Dönem Bitiş", bugun - timedelta(days=8))

            st.write(f"**Güncel Dönem:** {d1_start.strftime('%d.%m.%Y')} - {d1_end.strftime('%d.%m.%Y')}")
            st.write(f"**Önceki Dönem:** {d2_start.strftime('%d.%m.%Y')} - {d2_end.strftime('%d.%m.%Y')}")

            mask1 = (df['Tarih_Formatli'].dt.date >= d1_start) & (df['Tarih_Formatli'].dt.date <= d1_end)
            mask2 = (df['Tarih_Formatli'].dt.date >= d2_start) & (df['Tarih_Formatli'].dt.date <= d2_end)
            
            sum1 = df.loc[mask1].select_dtypes(include='number').sum()
            sum2 = df.loc[mask2].select_dtypes(include='number').sum()
            
            kiyas_df = pd.DataFrame({'Metrik': sum1.index, 'Önceki Dönem': sum2.values, 'Güncel Dönem': sum1.values})
            kiyas_df['Fark'] = kiyas_df['Güncel Dönem'] - kiyas_df['Önceki Dönem']
            
            # Yüzdelik Değişim Hesaplama
            kiyas_df['Değişim (%)'] = np.where(kiyas_df['Önceki Dönem'] == 0, 0, (kiyas_df['Fark'] / kiyas_df['Önceki Dönem']) * 100)
            
            # Renklendirme Fonksiyonu (Yeşil / Kırmızı)
            def renk_ver(val):
                if val > 0: return 'color: #00c853; font-weight: bold' # Yeşil
                elif val < 0: return 'color: #d50000; font-weight: bold' # Kırmızı
                return ''

            # Versiyon uyumluluğu için try-except
            try:
                st.dataframe(kiyas_df.style.map(renk_ver, subset=['Değişim (%)']).format({'Önceki Dönem': '{:,.2f}', 'Güncel Dönem': '{:,.2f}', 'Fark': '{:,.2f}', 'Değişim (%)': '%{:.2f}'}))
            except AttributeError:
                st.dataframe(kiyas_df.style.applymap(renk_ver, subset=['Değişim (%)']).format({'Önceki Dönem': '{:,.2f}', 'Güncel Dönem': '{:,.2f}', 'Fark': '{:,.2f}', 'Değişim (%)': '%{:.2f}'}))

    except Exception as e:
        st.error(f"Hata kiral! Detay: {e}")
else:
    st.warning("Şifreyi gir kiral!")
