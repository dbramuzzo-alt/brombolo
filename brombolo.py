import streamlit as st
from streamlit_gsheets import GSheetsConnection
import billboard
import pandas as pd

st.set_page_config(page_title="Billboard Archive", page_icon="🎵")

# --- CONNESSIONE A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("🎵 Billboard Archiver (Google Sheets)")

# Carichiamo i dati esistenti
try:
    df_esistente = conn.read(ttl=0) # ttl=0 forza l'aggiornamento dei dati
except:
    df_esistente = pd.DataFrame(columns=["Data", "Canzone", "Artista"])

# --- SIDEBAR PER SCARICARE ---
st.sidebar.header("Nuova Ricerca")
data_input = st.sidebar.date_input("Scegli un Sabato")

if st.sidebar.button("Scarica e Salva su Sheets"):
    with st.spinner("Connessione a Billboard..."):
        try:
            chart = billboard.ChartData('hot-100', date=str(data_input))
            
            # Creiamo una lista di nuove righe (Top 10)
            nuovi_dati = []
            for e in chart[:10]:
                nuovi_dati.append({
                    "Data": str(chart.date),
                    "Canzone": e.title,
                    "Artista": e.artist
                })
            
            df_nuovo = pd.DataFrame(nuovi_dati)
            
            # Uniamo i nuovi dati ai vecchi
            df_finale = pd.concat([df_esistente, df_nuovo], ignore_index=True)
            
            # SALVATAGGIO FISICO SU GOOGLE SHEETS
            conn.update(data=df_finale)
            
            st.sidebar.success("Dati inviati a Google Sheets! ✅")
            st.rerun()
            
        except Exception as e:
            st.sidebar.error(f"Errore: {e}")

# --- VISUALIZZAZIONE ---
if not df_esistente.empty:
    st.write("### Archivio Storico")
    # Mostriamo i dati raggruppati per data
    st.dataframe(df_esistente, use_container_width=True)
else:
    st.info("L'archivio è vuoto. Scarica la tua prima classifica!")
