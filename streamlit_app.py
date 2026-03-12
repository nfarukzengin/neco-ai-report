import streamlit as st
import pandas as pd
import google.generativeai as genai
from datetime import timedelta, date
import numpy as np
import urllib.request
import re
import altair as alt
import requests
import json

st.set_page_config(page_title="Neco AI", layout="wide")
st.title("🚀 AI Analiz Paneli")

# SOL MENÜ - GİRİŞ
st.sidebar.header("🔑 Sistem Girişi")
sifre = st.sidebar.text_input("Giriş Şifresi:", type="password")

if sifre == "fresh123":
    st.sidebar.markdown("---")
    st.sidebar.subheader("📁 Dosya Yöneticisi")

    # --- SLACK TEST BUTONU ---
    if st.sidebar.button("🚀 Slack Test Mesajı Gönder"):
        try:
            webhook_url = st.secrets["SLACK_WEBHOOK"]
            mesaj_paketi = {
                "text": "🚨 Necocum, butonlu test başarılı, sistem online!",
                "username": "Fresh AI Bot",
                "icon_emoji": ":rocket:"
            }
            headers = {'Content-type': 'application/json'}
            cevap = requests.post(webhook_url, data=json.dumps(mesaj_paketi), headers=headers)
            if cevap.status_code == 200:
                st.sidebar.success("✅ Mesaj Slack'e uçtu!")
            else:
                st.sidebar.error(f"❌ Hata: {cevap.status_code}")
        except Exception as e:
            st.sidebar.error(f"Bağlantı hatası: {e}")

    # --- DOSYA YÖNETİMİ ---
    manuel_id = st.sidebar.text_input("🔗 Manuel Google Sheet ID (Öncelikli):")
    
    klasorler = {
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
    
    sheet_id_input = manuel_id.strip() if manuel_id.strip() != "" else klasorler[secilen_klasor][secilen_dosya]
    gecersiz_idler = ["", "FRESH_ID_BURAYA", "FRESH_AYLIK_ID_BURAYA", "MANUKA_ID_BURAYA"]

    if sheet_id_input and sheet_id_input not in gecersiz_idler:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id_input}/export?format=xlsx"
        
        try:
            # Dosya adını çekme
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
            
            # Veri Temizleme
            for col in df.columns:
                if col not in ['Tarih', 'Tarih_Formatli', 'Ürün Adı', 'Kampanya']:
                    def temizle(x):
                        if isinstance(x, str):
                            x = x.replace('₺', '').replace('%', '').replace('None', '0').strip()
                            if '.' in x and ',' in x: x = x.replace('.', '').replace(',', '.')
                            elif ',' in x: x = x.replace(',', '.')
                        return x 
                    df[col] = df[col].apply(temizle)
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            st.sidebar.markdown("---")
            sekme = st.sidebar.radio("📌 Menü", ["Ana Analiz", "Karşılaştırma"])

            if sekme == "Ana Analiz":
                st.subheader(f"📅 Tarih Aralığı Seç ({secilen_sayfa})")
                c1, c2 = st.columns(2)
                with c1: start_date = st.date_input("Başlangıç", df['Tarih_Formatli'].min().date())
                with c2: end_date = st.date_input("Bitiş", df['Tarih_Formatli'].max().date())
                
                mask = (df['Tarih_Formatli'].dt.date >= start_date) & (df['Tarih_Formatli'].dt.date <= end_date)
                filtered_df = df.loc[mask].copy()

                # --- ANORMALLİK DEDEKTÖRÜ ---
                st.markdown("---")
                try:
                    son_gun = filtered_df['Tarih_Formatli'].max()
                    gecmis_7_gun = son_gun - timedelta(days=7)
                    son_gun_verisi = filtered_df[filtered_df['Tarih_Formatli'] == son_gun]
                    gecmis_veriler = filtered_df[(filtered_df['Tarih_Formatli'] >= gecmis_7_gun) & (filtered_df['Tarih_Formatli'] < son_gun)]
                    
                    sayisal_sutunlar = son_gun_verisi.select_dtypes(include=np.number).columns
                    anormallikler = []
                    
                    for col in sayisal_sutunlar:
                        if any(x in col.lower() for x in ['cpa', 'maliyet', 'cost', 'harcama']):
                            son_deger = son_gun_verisi[col].sum()
                            ortalama_deger = gecmis_veriler[col].mean()
                            if ortalama_deger > 0 and son_deger > (ortalama_deger * 1.3):
                                artis_orani = ((son_deger - ortalama_deger) / ortalama_deger) * 100
                                anormallikler.append(f"*{col}*: Dün ({son_deger:,.2f} ₺), Ortalamadan ({ortalama_deger:,.2f} ₺) *%{artis_orani:.1f}* yüksek!")

                    if anormallikler:
                        st.error("🚨 **DİKKAT NECO! MALİYETLERDE ANORMALLİK VAR:**")
                        slack_metni = "🚨 *DİKKAT NECO! MALİYETLERDE ANORMALLİK VAR:*\n\n"
                        for m in anormallikler:
                            st.warning(f"⚠️ {m.replace('*', '**')}")
                            slack_metni += f"⚠️ {m}\n"
                        
                        if "slack_notif_date" not in st.session_state or st.session_state.slack_notif_date != son_gun:
                            webhook_url = st.secrets["SLACK_WEBHOOK"]
                            requests.post(webhook_url, data=json.dumps({"text": slack_metni, "username": "Fresh AI", "icon_emoji": ":rotating_light:"}), headers={'Content-type': 'application/json'})
                            st.session_state.slack_notif_date = son_gun
                    else:
                        st.success("✅ Veriler stabil, maliyet patlaması yok.")
                except: pass

                # --- GRAFİK ---
                st.subheader("📈 Trend Grafiği")
                grafik_df = filtered_df.copy().sort_values('Tarih_Formatli')
                sayisal = grafik_df.select_dtypes(include=np.number).columns.tolist()
                secilen_metrik = st.multiselect("Metrikler:", sayisal, default=[sayisal[0]] if sayisal else [])
                if secilen_metrik:
                    aylar = {1:'Ocak',2:'Şubat',3:'Mart',4:'Nisan',5:'Mayıs',6:'Haziran',7:'Temmuz',8:'Ağustos',9:'Eylül',10:'Ekim',11:'Kasım',12:'Aralık'}
                    grafik_df['Eksen'] = grafik_df['Tarih_Formatli'].dt.day.astype(str) + ' ' + grafik_df['Tarih_Formatli'].dt.month.map(aylar)
                    erimis = grafik_df.melt(id_vars=['Tarih_Formatli', 'Eksen'], value_vars=secilen_metrik)
                    chart = alt.Chart(erimis).mark_line(point=True).encode(x=alt.X('Eksen:N', sort=alt.EncodingSortField(field='Tarih_Formatli')), y='value:Q', color='variable:N').interactive()
                    st.altair_chart(chart, use_container_width=True)

                # --- TABLO VE AI ---
                st.markdown("---")
                display_df = filtered_df.copy()
                display_df['Tarih'] = display_df['Tarih_Formatli'].dt.strftime('%d.%m.%Y')
                st.dataframe(display_df.drop(columns=['Tarih_Formatli']))
                
                st.subheader("🤖 AI Analizi")
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel('gemini-1.5-flash')
                soru = st.text_input("Veriler hakkında ne sormak istersin?")
                if st.button("Sor"):
                    with st.spinner('Analiz ediliyor...'):
                        res = model.generate_content(f"Verileri analiz et ve kısa cevap ver: {soru}\nVeri:\n{display_df.to_string()}")
                        st.info(res.text)

            elif sekme == "Karşılaştırma":
                st.subheader(f"⚖️ Dönem Karşılaştırması ({secilen_sayfa})")
                bugun = date.today()
                c1, c2 = st.columns(2)
                d1_start = c1.date_input("1. Dönem Başlangıç", bugun - timedelta(days=7))
                d1_end = c2.date_input("1. Dönem Bitiş", bugun)
                
                mask1 = (df['Tarih_Formatli'].dt.date >= d1_start) & (df['Tarih_Formatli'].dt.date <= d1_end)
                sum1 = df.loc[mask1].select_dtypes(include='number').sum()
                st.write("**Seçili Dönem Toplamları:**")
                st.table(sum1)

        except Exception as e:
            st.error(f"Sistemsel Hata: {e}")
    else:
        st.info("Lütfen sol menüden bir dosya seçin.")
else:
    if sifre: st.warning("Şifre yanlış Necocum!")
