import streamlit as st
import pandas as pd
import google.generativeai as genai

st.set_page_config(page_title="Neco AI", layout="wide")
st.title("🚀 Fresh Scarfs AI Analiz Paneli")

# Şifre Koruması
if st.sidebar.text_input("Giriş Şifresi:", type="password") == "fresh123":
    
    # 1. Veriyi Çek (Sheets'ten)
    sheet_id = "1JH3T2ib46IFuT5mnAkQoGQ1V4sZnwHaAUZA9ms1wKXo" 
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    try:
        df = pd.read_csv(url)
        st.subheader("📊 Son Satış Verileri")
        st.dataframe(df.tail(5)) 
        
        # 2. AI (Gemini) Bağlantısı - Şifreyi ayarlardan çeker
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        if st.button("AI ile Yorumla"):
            with st.spinner('Rapor hazırlanıyor kral...'):
                prompt = f"Sen bir e-ticaret ve CRM uzmanısın. Şu satış verilerine bakarak bana 3 kısa ve net çıkarım yap: {df.tail(5).to_string()}"
                response = model.generate_content(prompt)
                st.success(response.text)
                
    except Exception as e:
        st.error("Hata be gözüm! Sheet ID veya API Key kısmını kontrol et.")
else:
    st.warning("Şifreyi gir başkan!")
