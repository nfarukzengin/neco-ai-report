import streamlit as st
import pandas as pd
import google.generativeai as genai

st.set_page_config(page_title="Neco AI", layout="wide")
st.title("🚀 Fresh Scarfs AI Analiz Paneli")

if st.sidebar.text_input("Giriş Şifresi:", type="password") == "fresh123":
    
    sheet_id = "1JH3T2ib46IFuT5mnAkQoGQ1V4sZnwHaAUZA9ms1wKXo" 
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
            
        # 3. Seçilen tarihe göre veriyi filtrele
        mask = (df['Tarih'].dt.date >= start_date) & (df['Tarih'].dt.date <= end_date)
        filtered_df = df.loc[mask].copy()
        
        # Tarihleri ekranda tekrar düzgün göstermek için eski haline (String) çevir
        filtered_df['Tarih'] = filtered_df['Tarih'].dt.strftime('%d.%m.%Y')
        
        st.subheader("📊 Seçili Tarihlerin Verisi")
        st.dataframe(filtered_df) 
        
        # 4. AI (Gemini) Bağlantısı
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
       model = genai.GenerativeModel('gemini-pro')
        
        if st.button("Seçili Tarihleri AI ile Yorumla"):
            with st.spinner('Rapor hazırlanıyor kiral...'):
                prompt = f"Sen bir e-ticaret ve CRM uzmanısın. Şu satış verilerine bakarak bana 3 kısa ve net çıkarım yap: {filtered_df.to_string()}"
                response = model.generate_content(prompt)
                st.success(response.text)
                
    except Exception as e:
        st.error(f"Hata kiral! Hata detayı: {e}")
else:
    st.warning("Şifreyi gir kiral!")
