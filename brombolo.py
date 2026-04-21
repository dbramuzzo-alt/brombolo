import streamlit as st
import billboard
import pandas as pd
from github import Github
import io

# --- CONFIGURAZIONE ---
# Recupero credenziali dai Secrets di Streamlit
try:
    TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_NAME = st.secrets["REPO_NAME"]
    FILE_PATH = "archivio_billboard.csv"
except Exception as e:
    st.error("Errore: Secrets non configurati correttamente su Streamlit Cloud.")
    st.stop()

# Inizializzazione connessione GitHub
g = Github(TOKEN)
repo = g.get_repo(REPO_NAME)

def carica_archivio():
    """Scarica il CSV da GitHub o ne crea uno vuoto se non esiste"""
    try:
        file_content = repo.get_contents(FILE_PATH)
        df = pd.read_csv(io.StringIO(file_content.decoded_content.decode()))
        return df, file_content.sha
    except:
        # Se il file non esiste ancora, creiamo un DataFrame con le colonne corrette
        return pd.DataFrame(columns=["Data", "Pos", "Canzone", "Artista", "Tag"]), None

def salva_su_github(df_nuovo, sha):
    """Carica il file aggiornato su GitHub"""
    csv_content = df_nuovo.to_csv(index=False)
    if sha:
        repo.update_file(FILE_PATH, "Aggiornamento Archivio Billboard", csv_content, sha)
    else:
        repo.create_file(FILE_PATH, "Creazione Archivio Billboard", csv_content)

# --- INTERFACCIA UTENTE ---
st.set_page_config(page_title="Billboard Archiver", page_icon="🎵")
st.title("🎵 Billboard GitHub Archiver")

# Carichiamo i dati all'avvio
df_storico, file_sha = carica_archivio()

# Barra laterale per l'input
st.sidebar.header("Nuova Ricerca")
data_scelta = st.sidebar.date_input("Seleziona un Sabato")

if st.sidebar.button("Scarica e Archivia"):
    with st.spinner("Connessione a Billboard..."):
        try:
            chart = billboard.ChartData('hot-100', date=str(data_scelta))
            
            if not chart:
                st.sidebar.error("Nessun dato trovato per questa data.")
            else:
                nuove_righe = []
                # Prendiamo la Top 10
                for e in chart[:10]:
                    # Controlliamo se la canzone è già presente nell'archivio (per il tag NEW)
                    chiave = f"{e.title} - {e.artist}".lower().strip()
                    gia_presente = False
                    if not df_storico.empty:
                        combinati = df_storico['Canzone'].str.lower() + " - " + df_storico['Artista'].str.lower()
                        gia_presente = chiave in combinati.values
                    
                    nuove_righe.append({
                        "Data": str(chart.date),
                        "Pos": e.rank,
                        "Canzone": e.title,
                        "Artista": e.artist,
                        "Tag": "NEW✨" if not gia_presente else ""
                    })
                
                # Uniamo i nuovi dati al vecchio archivio
                df_nuovo = pd.concat([df_storico, pd.DataFrame(nuove_righe)], ignore_index=True)
                
                # Invio a GitHub
                salva_su_github(df_nuovo, file_sha)
                
                st.sidebar.success(f"Classifica del {chart.date} salvata!")
                st.rerun()
                
        except Exception as e:
            st.sidebar.error(f"Errore durante il processo: {e}")

# --- VISUALIZZAZIONE DATI ---
st.subheader("📊 Il tuo Archivio Storico")

if not df_storico.empty:
    # Mostriamo l'archivio ordinato per data (dalla più recente)
    # Convertiamo la colonna Data in formato data per l'ordinamento
    df_visualizzazione = df_storico.copy()
    df_visualizzazione['Data'] = pd.to_datetime(df_visualizzazione['Data'])
    df_visualizzazione = df_visualizzazione.sort_values(by="Data", ascending=False)
    
    st.dataframe(df_visualizzazione, use_container_width=True, hide_index=True)
    
    # Opzione per scaricare il file localmente sul telefono
    csv_download = df_storico.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Scarica Archivio CSV",
        data=csv_download,
        file_name="archivio_billboard_backup.csv",
        mime="text/csv",
    )
else:
    st.info("L'archivio su GitHub è vuoto. Scarica la tua prima classifica dalla barra laterale!")
    
