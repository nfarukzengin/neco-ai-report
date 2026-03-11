import streamlit as st
import pandas as pd
import google.generativeai as genai

st.set_page_config(page_title="Neco AI", layout="wide")
st.title("🚀 Fresh Scarfs AI Analiz Paneli")

if st.sidebar.text_input("Giriş Şifresi:", type="password") == "fresh123":
    
    sheet_id = "SENİN_SHEET_ID_BURAYA_GELECEK" # <-- BURAYI DEĞİŞTİRMEYİ UNUTMA KİRAL
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    try:
        df = pd.read_csv(url)
        
        # 1. Tarihleri formata sok ve "Toplam" gibi hatalı satırları yoksay
        df['Tarih'] = pd.to_datetime(df['Tarih'], format='%d.%m.%Y', errors='coerce')
        df = df.dropna(subset=['Tarih']) 
        
        # 2. Takvim (Tarih Seçici)
        st.subheader("📅 Tarih Aralığı Seç")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Başlangıç Tarihi", df['Tarih'].min())
        with col2:
            end_date = st.date_input("Bitiş Tarihi", df['Tarih'].max())
            
        # 3. Veriyi Filtrele, Temizle ve Toplam Satırı Ekle
        mask = (df['Tarih'].dt.date >= start_date) & (df['Tarih'].dt.date <= end_date)
        filtered_df = df.loc[mask].copy()
        
        # Tüm sütunları (Tarih hariç) temizleyip sayıya çeviriyoruz
        for col in filtered_df.columns:
            if col != 'Tarih':
                temiz = filtered_df[col].astype(str).str.replace('₺', '', regex=False).str.replace('.', '', regex=False).str.replace('%', '', regex=False).str.replace('None', '0', regex=False).str.replace(',', '.', regex=False)
                filtered_df[col] = pd.to_numeric(temiz, errors='coerce').fillna(0)
        
        filtered_df['Tarih'] = filtered_df['Tarih'].dt.strftime('%d.%m.%Y')
        
        # Gerçek matematiği yap ve en alta 'TOPLAM' satırı olarak ekle
        toplam_satiri = filtered_df.select_dtypes(include='number').sum()
        toplam_satiri_df = pd.DataFrame([toplam_satiri])
        toplam_satiri_df['Tarih'] = 'TOPLAM'
        filtered_df = pd.concat([filtered_df, toplam_satiri_df], ignore_index=True)
        
        # Makyaj: Sayıları şık formata çevir
        def formatla(val, col_name):
            if isinstance(val, (int, float)):
                fmt_val = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                if any(x in col_name.lower() for x in ['cos', 'katkı', 'gelir']): 
                    return f"%{fmt_val}"
                else:
                    return f"₺{fmt_val}"
            return val

        for col in filtered_df.columns:
            if col != 'Tarih':
                filtered_df[col] = filtered_df[col].apply(lambda x: formatla(x, col))
        
        # Satır boyama kuralı
        def satir_boya(row):
            if row['Tarih'] == 'TOPLAM':
                return ['background-color: #004d40; color: white; font-weight: bold'] * len(row)
            return [''] * len(row)

        st.subheader("📊 Seçili Tarihler ve Kesin Toplam")
        st.dataframe(filtered_df.style.apply(satir_boya, axis=1)) 
        
        # 4. Hazır Sorular ve AI Bağlantısı
        st.subheader("🤖 AI'a Ne Sormak İstersin?")
        sorular = [
            "CPA ve COS oranlarına göre reklam verimliliğini değerlendir.",
            "En yüksek ve en düşük ciro yapılan günleri kıyasla, sence neden?",
            "Reklam harcamalarının ciroya katkısını analiz et, kârlı mıyız?",
            "Bu verilere göre yarınki reklam bütçesini artırmalı mıyım, kısmalı mıyım?",
            "Sadık müşteri kazanımı (CRM) için bu tabloya göre nasıl bir aksiyon almalıyım?"
        ]
        secilen_sorular = st.multiselect("Soruları Seç (Birden fazla seçebilirsin):", sorular)
        
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        uygun_modeller = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        model = genai.GenerativeModel(uygun_modeller[0])
        
        if st.button("Sorgula"):
            if not secilen_sorular:
                st.warning("Kiral, önce yukarıdan en az bir soru seçmelisin!")
            else:
                with st.spinner('Cevaplar hazırlanıyor kiral...'):
                    soru_metni = "\n- ".join(secilen_sorular)
                    prompt = f"Sen bir e-ticaret ve CRM uzmanısın. Şu satış verilerine bakarak sadece aşağıdaki soruları net ve kısa cevapla:\n\nSorular:\n- {soru_metni}\n\nVeri:\n{filtered_df.to_string()}"
                    response = model.generate_content(prompt)
                    st.success(response.text)
                    
    except Exception as e:
        st.error(f"Hata kiral! Hata detayı: {e}")
else:
    st.warning("Şifreyi gir kiral!")
