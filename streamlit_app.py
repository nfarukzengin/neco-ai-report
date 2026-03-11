import streamlit as st
import pandas as pd

st.title("🚀 Fresh Scarfs Satış Dashboard")

# Sheets URL'ni buraya yapıştıracaksın kiral
# URL'nin sonundaki /edit... kısmını silip /export?format=csv eklemeyi unutma!
sheet_id = "BURAYA_SHEET_ID_GELECEK"
url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

try:
    df = pd.read_csv(url)
    st.subheader("📊 Güncel Tablo")
    st.dataframe(df) # Veriyi ekrana basar
except:
    st.error("Veri çekilemedi. Sheets linkini 'Bağlantıya sahip herkes' olarak ayarladın mı?")
