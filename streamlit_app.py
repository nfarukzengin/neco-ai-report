import streamlit as st
import pandas as pd
import google.generativeai as genai
from datetime import timedelta, date
import numpy as np
import urllib.request
import re

st.set_page_config(page_title="Neco AI", layout="wide")
st.title("🚀 Fresh Scarfs AI Analiz Paneli")

# SOL MENÜ - GİRİŞ
st.sidebar.header("🔑 Sistem Girişi")
sifre = st.sidebar.text_input("Giriş Şifresi:", type="password")

if sifre == "fresh123":
    st.sidebar.markdown("---")
    st.sidebar.subheader("📁 Dosya Yöneticisi")
    
    klasorler = {
        "Manuel Giriş (ID Yaz)": {
            "Yeni Bağlantı": ""
        },
        "Fresh Scarfs": {

            "Fresh Scarfs Reklam COS | Trendyol": "1JH3T2ib46IFuT5mnAkQoGQ1V4sZnwHaAUZA9ms1wKXo",

            "Aylık Özet": "FRESH_AYLIK_ID_BURAYA"

        },

        "Manuka": {

            "Manuka Estimate Mart": "11BsMe68YenKhK4UDddwBeaEJgz4zJA9ZRBAxNIAIaIY",

            "Manuka Reklam COS | Trendyol": "1cnxOLFg3qzggWIL7gPaTrsTa63uywmISroC8lbz2V7o"
        }
    }
    
    secilen_klasor = st.sidebar.selectbox("Klasör Seç:", list(klasorler.keys()))
    secilen_dosya = st.sidebar.selectbox("Dosya Seç:", list(klasorler[secilen_klasor].keys()))
    
    if secilen_klasor == "Manuel Giriş (ID Yaz)":
        sheet_id_input = st.sidebar.text_input("Google Sheet ID Girin:")
    else:
        sheet_id_input = klasorler[secilen_klasor][secilen_dosya]
        
    gecersiz_idler = ["", "FRESH_ID_BURAYA", "FRESH_AYLIK_ID_BURAYA", "MANUKA_ID_BURAYA"]

    if sheet_id_input and sheet_id_input not in gecersiz_idler:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id_input}/export?format=xlsx"
        
        try:
            # --- DOSYA ADINI ÇEKME ---
            try:
                html = urllib.request.urlopen(f"https://docs.google.com/spreadsheets/d/{sheet_id_input}/edit").read().decode('utf-8')
                dosya_adi = re.search(r'<title>(.*?)</title>', html).group(1).replace(" - Google Tablolar", "").replace(" - Google Sheets", "")
            except:
                dosya_adi = "Rapor"
            
            st.success(f"📂 Çalışılan Dosya: **{dosya_adi}**")

            tum_sayfalar = pd.read_excel(url, sheet_name=None)
            sayfa_isimleri = list(tum_sayfalar.keys())
            secilen_sayfa = st.sidebar.selectbox("📂 Sayfa (Sekme) Seç:", sayfa_isimleri)
            
            df = tum_sayfalar[secilen_sayfa].copy()
            
            df['Tarih_Formatli'] = pd.to_datetime(df['Tarih'], format='%d.%m.%Y', errors='coerce')
            df = df.dropna(subset=['Tarih_Formatli'])
            
            # --- KRİTİK DÜZELTME: SADECE METİNSE TEMİZLE, SAYIYSA DOKUNMA! ---
            for col in df.columns:
                if col not in ['Tarih', 'Tarih_Formatli', 'Ürün Reklam', 'İnf Reklam', 'Cpas Reklam', 'Ürün Adı', 'Kampanya']:
                    def temizle(x):
                        if isinstance(x, str): # Eğer hücre metinse özel karakterleri sil
                            x = x.replace('₺', '').replace('%', '').replace('None', '0').strip()
                            # Türk tipi (1.234,56) formatını koda uygun (1234.56) yap
                            if '.' in x and ',' in x:
                                x = x.replace('.', '').replace(',', '.')
                            elif ',' in x:
                                x = x.replace(',', '.')
                        return x # Zaten sayıysa (float/int) hiç dokunmadan geri ver
                    
                    df[col] = df[col].apply(temizle)
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            st.sidebar.markdown("---")
            sekme = st.sidebar.radio("📌 Menü", ["Ana Analiz", "Karşılaştırma"])

            if sekme == "Ana Analiz":
                st.subheader(f"📅 Tarih Aralığı Seç ({secilen_sayfa})")
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
                
                # --- FORMATLAMA DÜZELTİLDİ ---
                def formatla(val, col_name):
                    if isinstance(val, (int, float)):
                        c_lower = col_name.lower()
                        
                        # 1. Yüzdelikler (CR, COS vb.)
                        if any(x in c_lower for x in ['cos', 'katkı', 'gelir', 'cr']) and 'cost' not in c_lower:
                            # Excel 0.02 veriyorsa %2 yapmak için 100 ile çarpıyoruz
                            if val < 10 and val > -10: val = val * 100 
                            fmt_val = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                            return f"%{fmt_val}"
                            
                        # 2. Para Birimleri (Revenue, Cost, AOV vb.)
                        elif any(x in c_lower for x in ['revenue', 'cost', 'cpc', 'cpa', 'harcama', 'aov', 'cps', 'rps']):
                            fmt_val = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                            return f"₺{fmt_val}"
                            
                        # 3. Düz Sayılar (Session, Trx vb.) - İşaretsiz kalsın
                        else:
                            fmt_val = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                            # Sonu tam sayıysa (,00) gereksiz sıfırları at
                            if fmt_val.endswith(",00"): fmt_val = fmt_val[:-3]
                            return fmt_val
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
                    "Bu Estimate raporda güncel olarak bütçe arttırmalı mıyım? hedef: cironun %3'ü.?",
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

            elif sekme == "Karşılaştırma":
                st.subheader(f"⚖️ Dönem Karşılaştırması ({secilen_sayfa})")
                
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
                
                kiyas_df['Değişim (%)'] = np.where(kiyas_df['Önceki Dönem'] == 0, 0, (kiyas_df['Fark'] / kiyas_df['Önceki Dönem']) * 100)
                
                def renk_ver(val):
                    if val > 0: return 'color: #00c853; font-weight: bold'
                    elif val < 0: return 'color: #d50000; font-weight: bold'
                    return ''

                try:
                    st.dataframe(kiyas_df.style.map(renk_ver, subset=['Değişim (%)']).format({'Önceki Dönem': '{:,.2f}', 'Güncel Dönem': '{:,.2f}', 'Fark': '{:,.2f}', 'Değişim (%)': '%{:.2f}'}))
                except AttributeError:
                    st.dataframe(kiyas_df.style.applymap(renk_ver, subset=['Değişim (%)']).format({'Önceki Dönem': '{:,.2f}', 'Güncel Dönem': '{:,.2f}', 'Fark': '{:,.2f}', 'Değişim (%)': '%{:.2f}'}))

                st.subheader("🤖 Karşılaştırma Analizi için AI'a Sor")
                kiyas_sorular = [
                    "Geçen döneme göre cirodaki değişimi ve karlılığı (COS/ROAS) değerlendir.",
                    "CPA ve reklam harcamalarındaki artış/azalış ciroya nasıl yansımış? Yorumla.",
                    "En çok artış ve düşüş gösteren metrikleri bulup, önümüzdeki dönem için 2 stratejik öneri ver.",
                    "Bu iki dönemi kıyasladığında reklam bütçesini nasıl optimize etmeliyim?"
                ]
                secilen_kiyas_sorular = st.multiselect("Soruları Seç (Karşılaştırma):", kiyas_sorular)
                
                if st.button("Karşılaştırmayı Sorgula"):
                    if not secilen_kiyas_sorular: 
                        st.warning("Soru seç kiral!")
                    else:
                        with st.spinner('Karşılaştırma raporu hazırlanıyor kiral...'):
                            prompt = f"Sen bir e-ticaret ve CRM uzmanısın. Şu iki dönemin karşılaştırma verilerine bakarak seçtiğim sorulara kısa, net ve aksiyon odaklı cevap ver:\n\nSorular:\n{secilen_kiyas_sorular}\n\nKarşılaştırma Verisi:\n{kiyas_df.to_string()}"
                            st.success(model.generate_content(prompt).text)

        except Exception as e:
            st.error(f"Hata kiral! Belki sekme formatları farklıdır. Detay: {e}")
    else:
        st.info("Kiral, başlamak için lütfen klasörden bir dosya seç veya manuel ID gir.")
else:
    if sifre:
        st.warning("Şifre yanlış kiral!")
