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

st.set_page_config(page_title="Neco AI Komuta Merkezi", layout="wide")

# --- VERİ İNDİRME FONKSİYONU (Hızlı geçişler için Cache'li) ---
@st.cache_data(show_spinner=False)
def veri_indir(sheet_id):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    return pd.read_excel(url, sheet_name=None)

# Menü değişikliklerinde sayfayı sıfırlamak için
def secim_degisti():
    st.session_state.veri_aktif = False

# --- 1. SOL MENÜ (SADECE ŞİFRE VE ARAÇLAR) ---
with st.sidebar:
    st.title("🔐 Panel Girişi")
    sifre = st.text_input("Şifre:", type="password")
    
    st.markdown("---")
    manuel_id = st.text_input("🔗 Manuel Sheet ID (Opsiyonel):", on_change=secim_degisti)
    
    # Slack Test Butonu
    st.markdown("---")
    if st.button("🚀 Slack Test Mesajı Gönder"):
        try:
            webhook_url = st.secrets["SLACK_WEBHOOK"]
            mesaj_paketi = {"text": "🚨 Necocum, butonlu test başarılı, sistem online!", "username": "Fresh AI Bot", "icon_emoji": ":rocket:"}
            cevap = requests.post(webhook_url, data=json.dumps(mesaj_paketi), headers={'Content-type': 'application/json'})
            if cevap.status_code == 200:
                st.success("✅ Mesaj Slack'e uçtu!")
            else:
                st.error(f"❌ Hata: {cevap.status_code}")
        except Exception as e:
            st.error(f"Slack Hatası: {e}")

# --- ANA SİSTEM ---
if sifre == "fresh123":
    
    if 'marka' not in st.session_state:
        st.session_state.marka = None
    if 'veri_aktif' not in st.session_state:
        st.session_state.veri_aktif = False

    # --- 2. MARKA SEÇİMİ ---
    if st.session_state.marka is None:
        st.title("Lütfen Marka Seçiniz")
        c1, c2 = st.columns(2)
        if c1.button("🏢 MANUKA", use_container_width=True):
            st.session_state.marka = "MANUKA"
            st.rerun()
        if c2.button("🌿 FRESH SCARFS", use_container_width=True):
            st.session_state.marka = "FRESH SCARFS"
            st.rerun()
            
    else:
        st.subheader(f"📍 {st.session_state.marka} Paneli")
        if st.button("⬅️ Marka Değiştir"):
            st.session_state.marka = None
            st.session_state.veri_aktif = False
            st.rerun()
        
        st.divider()

        # --- VERİTABANI AĞACI ---
        veri_agaci = {
            "FRESH SCARFS": {
                "Reklam Verileri": {
                    "Fresh Scarfs Reklam COS | Trendyol": "1JH3T2ib46IFuT5mnAkQoGQ1V4sZnwHaAUZA9ms1wKXo",
                    "Aylık Özet": "FRESH_AYLIK_ID_BURAYA",
                    "📊 GA4 Verileri": "GA4_SHEET_ID_BURAYA" # GA4 buraya eklendi
                }
            },
            "MANUKA": {
                "Reklam Verileri": {
                    "Manuka Estimate Mart": "11BsMe68YenKhK4UDddwBeaEJgz4zJA9ZRBAxNIAIaIY",
                    "Manuka Reklam COS | Trendyol": "1cnxOLFg3qzggWIL7gPaTrsTa63uywmISroC8lbz2V7o"
                }
            }
        }

        # --- 3. KLASÖR VE DOSYA SEÇİMİ ---
        col_klasor, col_dosya, col_sayfa = st.columns(3)
        
        with col_klasor:
            klasor_listesi = list(veri_agaci[st.session_state.marka].keys())
            secilen_klasor = st.selectbox("📁 Klasör Seç", klasor_listesi, on_change=secim_degisti)
            
        with col_dosya:
            dosya_listesi = list(veri_agaci[st.session_state.marka][secilen_klasor].keys())
            secilen_dosya = st.selectbox("📄 Dosya Seç", dosya_listesi, on_change=secim_degisti)
            
        # Geçerli ID Belirleme (Manuel ID varsa ezer)
        sheet_id_input = manuel_id.strip() if manuel_id.strip() != "" else veri_agaci[st.session_state.marka][secilen_klasor][secilen_dosya]
        
        # Sayfaları Çekme ve Seçme
        with col_sayfa:
            gecersiz_idler = ["", "FRESH_ID_BURAYA", "FRESH_AYLIK_ID_BURAYA", "MANUKA_ID_BURAYA", "GA4_SHEET_ID_BURAYA"]
            if sheet_id_input and sheet_id_input not in gecersiz_idler:
                try:
                    tum_sayfalar = veri_indir(sheet_id_input)
                    sayfa_isimleri = list(tum_sayfalar.keys())
                    secilen_sayfa = st.selectbox("📑 Sayfa Seç", sayfa_isimleri, on_change=secim_degisti)
                    veri_hazir = True
                except Exception as e:
                    st.error("Dosya okunamadı! Sheet ID yanlış veya erişim yetkisi yok.")
                    veri_hazir = False
            else:
                st.warning("Bu dosya için geçerli bir Sheet ID tanımlanmamış.")
                veri_hazir = False

        st.divider()

        # --- 4. TARİH, MOD VE ÇALIŞTIR BUTONLARI ---
        if veri_hazir:
            # Ön Filtre İçin DF'i Hızlıca Hazırla
            df_ham = tum_sayfalar[secilen_sayfa].copy()
            df_ham['Tarih_Formatli'] = pd.to_datetime(df_ham['Tarih'], format='%d.%m.%Y', errors='coerce')
            df_gecerli = df_ham.dropna(subset=['Tarih_Formatli'])
            
            min_tarih = df_gecerli['Tarih_Formatli'].min().date() if not df_gecerli.empty else date.today() - timedelta(days=7)
            max_tarih = df_gecerli['Tarih_Formatli'].max().date() if not df_gecerli.empty else date.today()

            t1, t2, t3, b1, b2 = st.columns([1.5, 1.5, 2, 1.5, 1.5])
            
            baslangic = t1.date_input("Başlangıç Tarihi", min_tarih, on_change=secim_degisti)
            bitis = t2.date_input("Bitiş Tarihi", max_tarih, on_change=secim_degisti)
            sekme = t3.radio("📌 Analiz Modu", ["Ana Analiz", "Karşılaştırma"], horizontal=True, on_change=secim_degisti)
            
            # Çalıştır ve Yenile
            if b1.button("🚀 VERİYİ GETİR", use_container_width=True):
                st.session_state.veri_aktif = True
                
            if b2.button("🔄 GÜNCELLE", use_container_width=True):
                st.cache_data.clear()
                st.session_state.veri_aktif = True
                st.rerun()

            # --- 5. VERİ GÖSTERİMİ VE ANALİZ (BUTONA BASILDIYSA) ---
            if st.session_state.veri_aktif:
                st.success(f"✅ Veriler getirildi: {secilen_dosya} -> {secilen_sayfa}")
                st.markdown("---")
                
                # Veri Temizleme İşlemi (Sadece aktifken yapar, sistemi yormaz)
                df = df_gecerli.copy()
                for col in df.columns:
                    if col not in ['Tarih', 'Tarih_Formatli', 'Ürün Reklam', 'İnf Reklam', 'Cpas Reklam', 'Ürün Adı', 'Kampanya']:
                        def temizle(x):
                            if isinstance(x, str):
                                x = x.replace('₺', '').replace('%', '').replace('None', '0').strip()
                                if '.' in x and ',' in x: x = x.replace('.', '').replace(',', '.')
                                elif ',' in x: x = x.replace(',', '.')
                            return x 
                        df[col] = df[col].apply(temizle)
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

                # TARİH FİLTRESİ
                mask = (df['Tarih_Formatli'].dt.date >= baslangic) & (df['Tarih_Formatli'].dt.date <= bitis)
                filtered_df = df.loc[mask].copy()

                # ---- ANA ANALİZ MODU ----
                if sekme == "Ana Analiz":
                    # --- OTOMATİK ANORMALLİK DEDEKTÖRÜ ---
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
                                    anormallikler.append(f"**{col}**: Dün ({son_deger:,.2f} ₺), son 7 gün ortalamasından ({ortalama_deger:,.2f} ₺) **%{artis_orani:.1f}** daha yüksek!")
                        
                        if anormallikler:
                            st.error("🚨 **DİKKAT KİRAL! MALİYETLERDE ANORMALLİK VAR:**")
                            slack_mesaj_metni = "🚨 *DİKKAT KİRAL! MALİYETLERDE ANORMALLİK VAR:*\n\n"
                            
                            for mesaj in anormallikler:
                                st.warning(f"⚠️ {mesaj}")
                                slack_mesaj_metni += f"⚠️ {mesaj.replace('**', '*')}\n"
                            
                            if "slack_anormallik_tarihi" not in st.session_state or st.session_state.slack_anormallik_tarihi != son_gun:
                                try:
                                    requests.post(st.secrets["SLACK_WEBHOOK"], data=json.dumps({"text": slack_mesaj_metni, "username": "Fresh AI Dedektör", "icon_emoji": ":rotating_light:"}), headers={'Content-type': 'application/json'})
                                    st.session_state.slack_anormallik_tarihi = son_gun
                                except Exception: pass
                        else:
                            st.success("✅ Kiral, son gün verilerinde göze çarpan bir maliyet patlaması yok. Her şey stabil.")
                    except Exception: pass

                    # --- GRAFİK ALANI ---
                    st.subheader("📈 Trend Grafiği")
                    grafik_df = filtered_df.copy().sort_values('Tarih_Formatli')
                    sayisal_sutunlar_gr = grafik_df.select_dtypes(include=np.number).columns.tolist()
                    varsayilan_secim = [col for col in sayisal_sutunlar_gr if any(x in col.lower() for x in ['revenue', 'cost', 'ciro', 'harcama'])]
                    if not varsayilan_secim and sayisal_sutunlar_gr: varsayilan_secim = [sayisal_sutunlar_gr[0]]

                    secilen_metrikler = st.multiselect("Grafikte Gösterilecek Metrikleri Seç:", sayisal_sutunlar_gr, default=varsayilan_secim)
                    
                    if secilen_metrikler:
                        aylar_tr = {1: 'Ocak', 2: 'Şubat', 3: 'Mart', 4: 'Nisan', 5: 'Mayıs', 6: 'Haziran', 7: 'Temmuz', 8: 'Ağustos', 9: 'Eylül', 10: 'Ekim', 11: 'Kasım', 12: 'Aralık'}
                        grafik_df['Grafik_Tarihi'] = grafik_df['Tarih_Formatli'].dt.day.astype(str) + ' ' + grafik_df['Tarih_Formatli'].dt.month.map(aylar_tr)
                        erimis_df = grafik_df.melt(id_vars=['Tarih_Formatli', 'Grafik_Tarihi'], value_vars=secilen_metrikler, var_name='Metrik', value_name='Değer')
                        cizgi_grafik = alt.Chart(erimis_df).mark_line(point=True).encode(x=alt.X('Grafik_Tarihi:N', sort=alt.EncodingSortField(field='Tarih_Formatli', order='ascending'), title='Tarih'), y=alt.Y('Değer:Q', title='Tutar'), color='Metrik:N', tooltip=['Grafik_Tarihi', 'Metrik', 'Değer']).interactive()
                        st.altair_chart(cizgi_grafik, use_container_width=True)

                    # --- TABLO ALANI ---
                    filtered_df['Tarih'] = filtered_df['Tarih_Formatli'].dt.strftime('%d.%m.%Y')
                    filtered_df = filtered_df.drop(columns=['Tarih_Formatli'])
                    toplam_satiri = filtered_df.select_dtypes(include='number').sum()
                    toplam_satiri_df = pd.DataFrame([toplam_satiri])
                    toplam_satiri_df['Tarih'] = 'TOPLAM'
                    filtered_df = pd.concat([filtered_df, toplam_satiri_df], ignore_index=True)
                    
                    def formatla(val, col_name):
                        if isinstance(val, (int, float)):
                            c_lower = col_name.lower()
                            if any(x in c_lower for x in ['cos', 'katkı', 'gelir', 'cr']) and 'cost' not in c_lower:
                                if val < 10 and val > -10: val = val * 100 
                                return f"%{f'{val:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')}"
                            elif any(x in c_lower for x in ['revenue', 'cost', 'cpc', 'cpa', 'harcama', 'aov', 'cps', 'rps']):
                                return f"₺{f'{val:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')}"
                            else:
                                fmt_val = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                                if fmt_val.endswith(",00"): fmt_val = fmt_val[:-3]
                                return fmt_val
                        return val

                    for col in filtered_df.columns:
                        if col != 'Tarih': filtered_df[col] = filtered_df[col].apply(lambda x: formatla(x, col))
                    
                    def satir_boya(row): return ['background-color: #004d40; color: white; font-weight: bold'] * len(row) if row['Tarih'] == 'TOPLAM' else [''] * len(row)

                    st.subheader("📊 Filtrelenmiş Veri ve Toplamlar")
                    st.dataframe(filtered_df.style.apply(satir_boya, axis=1), use_container_width=True) 
                    
                    # --- AI SORGULAMA ---
                    st.subheader("🤖 AI'a Ne Sormak İstersin?")
                    sorular = ["CPA ve COS oranlarına göre reklam verimliliğini değerlendir.", "En yüksek ve en düşük ciro yapılan günleri kıyasla, sence neden?", "Reklam harcamalarının ciroya katkısını analiz et, kârlı mıyız?", "Bu verilere göre yarınki reklam bütçesini artırmalı mıyım, kısmalı mıyım?", "Sadık müşteri kazanımı (CRM) için bu tabloya göre nasıl bir aksiyon almalıyım?"]
                    secilen_sorular = st.multiselect("Soruları Seç:", sorular)
                    
                    if st.button("Sorgula"):
                        if not secilen_sorular: st.warning("Soru seç kiral!")
                        else:
                            with st.spinner('AI düşünüyor...'):
                                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                                model = genai.GenerativeModel([m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods][0])
                                prompt = f"Şu verilere bakarak kısa cevap ver:\nSorular: {secilen_sorular}\nVeri:\n{filtered_df.to_string()}"
                                st.success(model.generate_content(prompt).text)

                # ---- KARŞILAŞTIRMA MODU ----
                elif sekme == "Karşılaştırma":
                    st.subheader(f"⚖️ Dönem Karşılaştırması ({secilen_sayfa})")
                    hizli_secim = st.selectbox("Hızlı Seçim", ["Özel Tarih Seç", "Bugün", "Dün", "Son 7 Gün", "Son 15 Gün", "Son 30 Gün"])
                    
                    bugun = date.today()
                    if hizli_secim == "Son 7 Gün": d1_end=bugun; d1_start=bugun-timedelta(days=6); d2_end=d1_start-timedelta(days=1); d2_start=d2_end-timedelta(days=6)
                    elif hizli_secim == "Son 15 Gün": d1_end=bugun; d1_start=bugun-timedelta(days=14); d2_end=d1_start-timedelta(days=1); d2_start=d2_end-timedelta(days=14)
                    elif hizli_secim == "Son 30 Gün": d1_end=bugun; d1_start=bugun-timedelta(days=29); d2_end=d1_start-timedelta(days=1); d2_start=d2_end-timedelta(days=29)
                    elif hizli_secim == "Dün": d1_end=d1_start=bugun-timedelta(days=1); d2_end=d2_start=bugun-timedelta(days=2)
                    elif hizli_secim == "Bugün": d1_end=d1_start=bugun; d2_end=d2_start=bugun-timedelta(days=1)
                    else:
                        c1, c2 = st.columns(2); c3, c4 = st.columns(2)
                        with c1: d1_start = st.date_input("1. Dönem Başlangıç", bugun - timedelta(days=7))
                        with c2: d1_end = st.date_input("1. Dönem Bitiş", bugun)
                        with c3: d2_start = st.date_input("2. Dönem Başlangıç", bugun - timedelta(days=15))
                        with c4: d2_end = st.date_input("2. Dönem Bitiş", bugun - timedelta(days=8))

                    st.write(f"**Güncel:** {d1_start.strftime('%d.%m.%Y')} - {d1_end.strftime('%d.%m.%Y')} | **Önceki:** {d2_start.strftime('%d.%m.%Y')} - {d2_end.strftime('%d.%m.%Y')}")

                    mask1 = (df['Tarih_Formatli'].dt.date >= d1_start) & (df['Tarih_Formatli'].dt.date <= d1_end)
                    mask2 = (df['Tarih_Formatli'].dt.date >= d2_start) & (df['Tarih_Formatli'].dt.date <= d2_end)
                    
                    sum1 = df.loc[mask1].select_dtypes(include='number').sum()
                    sum2 = df.loc[mask2].select_dtypes(include='number').sum()
                    
                    kiyas_df = pd.DataFrame({'Metrik': sum1.index, 'Önceki Dönem': sum2.values, 'Güncel Dönem': sum1.values})
                    kiyas_df['Fark'] = kiyas_df['Güncel Dönem'] - kiyas_df['Önceki Dönem']
                    kiyas_df['Değişim (%)'] = np.where(kiyas_df['Önceki Dönem'] == 0, 0, (kiyas_df['Fark'] / kiyas_df['Önceki Dönem']) * 100)
                    
                    def renk_ver(val): return 'color: #00c853; font-weight: bold' if val > 0 else ('color: #d50000; font-weight: bold' if val < 0 else '')
                    try: st.dataframe(kiyas_df.style.map(renk_ver, subset=['Değişim (%)']).format({'Önceki Dönem': '{:,.2f}', 'Güncel Dönem': '{:,.2f}', 'Fark': '{:,.2f}', 'Değişim (%)': '%{:.2f}'}), use_container_width=True)
                    except AttributeError: st.dataframe(kiyas_df.style.applymap(renk_ver, subset=['Değişim (%)']).format({'Önceki Dönem': '{:,.2f}', 'Güncel Dönem': '{:,.2f}', 'Fark': '{:,.2f}', 'Değişim (%)': '%{:.2f}'}), use_container_width=True)

                    st.subheader("🤖 Karşılaştırma Analizi için AI'a Sor")
                    kiyas_sorular = ["Geçen döneme göre cirodaki değişimi ve karlılığı (COS/ROAS) değerlendir.", "CPA ve reklam harcamalarındaki artış/azalış ciroya nasıl yansımış? Yorumla.", "En çok artış ve düşüş gösteren metrikleri bulup, önümüzdeki dönem için 2 stratejik öneri ver.", "Bu iki dönemi kıyasladığında reklam bütçesini nasıl optimize etmeliyim?"]
                    secilen_kiyas_sorular = st.multiselect("Soruları Seç:", kiyas_sorular)
                    
                    if st.button("Karşılaştırmayı Sorgula"):
                        if not secilen_kiyas_sorular: st.warning("Soru seç kiral!")
                        else:
                            with st.spinner('Kıyaslama yapılıyor...'):
                                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                                model = genai.GenerativeModel([m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods][0])
                                prompt = f"Sen bir e-ticaret ve CRM uzmanısın. Şu verilere bakıp kısa, net cevap ver:\nSorular: {secilen_kiyas_sorular}\nVeri:\n{kiyas_df.to_string()}"
                                st.success(model.generate_content(prompt).text)

else:
    if sifre: st.warning("Şifre yanlış kiral, bir daha dene.")
    else: st.info("Başlamak için sol taraftan şifreyi gir.")
