import streamlit as st
import billboard
import pandas as pd
from github import Github
import io
import base64

# --- CONFIGURAZIONE ---
TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = st.secrets["REPO_NAME"]
FILE_PATH = "archivio_billboard.csv"

# Inizializzazione GitHub
g = Github(TOKEN)
repo = g.get_repo(REPO_NAME)

def carica_archivio():
    try:
        file_content = repo.get_contents(FILE_PATH)
        df = pd.read_csv(io.StringIO(file_content.decoded_content.decode()))
        return df, file_content.sha
    except:
        return pd.DataFrame(columns=["Data", "Pos", "Canzone", "Artista", "Tag"]), None

def salva_su_github(df_nuovo, sha):
    csv_content = df_nuovo.to_csv(index=False)
    if sha:
        repo.update_file(FILE_PATH, "Update Billboard Archive", csv_content, sha)
    else:
        repo.create_file(FILE_PATH, "Create Billboard Archive", csv_content)

# --- APP INTERFACCIA ---
st.title("🎵 Billboard GitHub Archiver")

df_storico, file_sha = carica_archivio()

# Sidebar
data_scelta = st.sidebar.date_input("Seleziona un Sabato")

if st.sidebar.button("Scarica e Archivia"):
    with st.spinner("Recupero dati..."):
        chart = billboard.ChartData('hot-100', date=str(data_scelta))
        if chart:
            nuove_righe = []
            for e in chart[:10]:
                # Logica unicità
                chiave = f"{e.title} - {e.artist}".lower().strip()
                gia_presente = chiave in df_storico['Canzone'].str.lower().str.cat(df_storico['Artista'].str.lower(), sep=' - ').values
                
                nuove_righe.append({
                    "Data": str(chart.date),
                    "Pos": e.rank,
                    "Canzone": e.title,
                    "Artista": e.artist,
                    "Tag": "NEW✨" if not gia_presente else ""
                })
            
            df_nuovo = pd.concat([df_storico, pd.DataFrame(nuove_righe)], ignore_index=True)
            salva_su_github(df_nuovo, file_sha)
            st.success(f"Classifica del {chart.date} salvata!")
            st.rerun()

# Visualizzazione
if not df_storico.empty:
    st.write("### Archivio Storico")
    # Mostra le ultime aggiunte in alto
    st.dataframe(df_storico.sort_index(ascending=False), use_container_width=True)
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
