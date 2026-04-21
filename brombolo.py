import streamlit as st
import billboard
import pandas as pd
from github import Github
import io
import datetime

# --- 1. CONFIGURAZIONE E CONNESSIONE ---
try:
    TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_NAME = st.secrets["REPO_NAME"]
    FILE_PATH = "archivio_billboard.csv"
except Exception as e:
    st.error("Errore: Assicurati di aver configurato GITHUB_TOKEN e REPO_NAME nei Secrets.")
    st.stop()

g = Github(TOKEN)
repo = g.get_repo(REPO_NAME)

def carica_archivio():
    """Scarica il database da GitHub o ne crea uno nuovo se vuoto"""
    try:
        file_content = repo.get_contents(FILE_PATH)
        df = pd.read_csv(io.StringIO(file_content.decoded_content.decode()))
        # Pulizia: assicuriamoci che le colonne siano corrette
        if df.empty:
            return pd.DataFrame(columns=["Data", "Tag", "Pos", "Canzone", "Artista"]), file_content.sha
        return df, file_content.sha
    except:
        return pd.DataFrame(columns=["Data", "Tag", "Pos", "Canzone", "Artista"]), None

def salva_su_github(df_nuovo, sha):
    """Sovrascrive il file su GitHub con i nuovi dati"""
    csv_content = df_nuovo.to_csv(index=False)
    if sha:
        repo.update_file(FILE_PATH, "Aggiornamento Archivio Billboard", csv_content, sha)
    else:
        repo.create_file(FILE_PATH, "Creazione Archivio Billboard", csv_content)

def correggi_data_billboard(data_input):
    """Arrotonda la data al sabato corretto per Billboard"""
    giorno_settimana = data_input.weekday() # 5 è Sabato
    if giorno_settimana == 5:
        return data_input
    else:
        giorni_da_togliere = (giorno_settimana + 2) % 7
        return data_input - datetime.timedelta(days=giorni_da_togliere)

# --- 2. INTERFACCIA APP ---
st.set_page_config(page_title="Billboard Full Archiver", page_icon="🎵", layout="wide")
st.title("🎵 Billboard Hot 100: Database Novità")

# Caricamento iniziale dei dati
df_storico, file_sha = carica_archivio()

# Sidebar per il download
st.sidebar.header("📥 Download Classifica")
data_scelta = st.sidebar.date_input("Seleziona Data", value=datetime.date.today())

if st.sidebar.button("Scarica Tutte le 100"):
    data_billboard = correggi_data_billboard(data_scelta)
    
    with st.spinner(f"Scaricando classifica del {data_billboard}..."):
        try:
            chart = billboard.ChartData('hot-100', date=str(data_billboard))
            
            if not chart:
                st.sidebar.error("Classifica non trovata per questa data.")
            else:
                nuove_righe = []
                
                # Creiamo il set delle canzoni GIA' SALVATE nel file per il confronto
                canzoni_gia_nel_file = set()
                if not df_storico.empty:
                    # Uniamo Canzone e Artista per un controllo univoco
                    canzoni_gia_nel_file = set(
                        (df_storico['Canzone'].str.lower() + " - " + df_storico['Artista'].str.lower()).unique()
                    )

                # Elaborazione di tutte le 100 canzoni
                for e in chart:
                    chiave_canzone = f"{e.title} - {e.artist}".lower().strip()
                    # Mettiamo NEW se non è MAI apparsa nel CSV
                    is_new = chiave_canzone not in canzoni_gia_nel_file
                    
                    nuove_righe.append({
                        "Data": str(chart.date),
                        "Tag": "NEW✨" if is_new else "",
                        "Pos": e.rank,
                        "Canzone": e.title,
                        "Artista": e.artist
                    })
                
                # Uniamo al vecchio archivio e salviamo su GitHub
                df_da_salvare = pd.concat([df_storico, pd.DataFrame(nuove_righe)], ignore_index=True)
                salva_su_github(df_da_salvare, file_sha)
                
                st.sidebar.success(f"Classifica {chart.date} salvata con successo!")
                st.rerun() # Ricarica l'app per mostrare i dati

        except Exception as e:
            st.sidebar.error(f"Errore tecnico: {e}")

# --- 3. VISUALIZZAZIONE DATABASE ---
if not df_storico.empty:
    st.subheader(f"📊 Archivio Storico ({len(df_storico)} righe totali)")
    
    # Preparazione dei dati per la tabella
    df_vista = df_storico.copy()
    df_vista['Data'] = pd.to_datetime(df_vista['Data'])
    
    # Opzione: Mostra solo le NEW
    col1, col2 = st.columns([1, 2])
    with col1:
        solo_new = st.checkbox("Mostra solo i brani 'NEW✨'")
    
    if solo_new:
        df_vista = df_vista[df_vista['Tag'] == "NEW✨"]
    
    # Ordiniamo per data (più recente) e poi per posizione
    df_vista = df_vista.sort_values(by=["Data", "Pos"], ascending=[False, True])

    # Visualizzazione Tabella
    st.dataframe(
        df_vista, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Data": st.column_config.DateColumn("Settimana"),
            "Pos": st.column_config.NumberColumn("Posizione", format="#%d"),
            "Tag": "Novità",
            "Canzone": st.column_config.TextColumn("Brano"),
            "Artista": st.column_config.TextColumn("Artista")
        }
    )
    
    # Tasto per backup
    st.download_button(
        "📥 Esporta CSV Backup", 
        df_storico.to_csv(index=False).encode('utf-8'), 
        "archivio_completo.csv", 
        "text/csv"
    )
else:
    st.warning("📭 L'archivio è attualmente vuoto. Scarica una classifica per iniziare!")
    
