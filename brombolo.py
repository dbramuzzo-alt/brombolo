import streamlit as st
import billboard
import pandas as pd
from github import Github
import io
import datetime

# --- CONFIGURAZIONE ---
try:
    TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_NAME = st.secrets["REPO_NAME"]
    FILE_PATH = "archivio_billboard.csv"
except Exception as e:
    st.error("Errore: Secrets non configurati correttamente.")
    st.stop()

g = Github(TOKEN)
repo = g.get_repo(REPO_NAME)

def carica_archivio():
    try:
        file_content = repo.get_contents(FILE_PATH)
        df = pd.read_csv(io.StringIO(file_content.decoded_content.decode()))
        return df, file_content.sha
    except:
        return pd.DataFrame(columns=["Data", "Tag", "Pos", "Canzone", "Artista"]), None

def salva_su_github(df_nuovo, sha):
    csv_content = df_nuovo.to_csv(index=False)
    if sha:
        repo.update_file(FILE_PATH, "Update Billboard Archive", csv_content, sha)
    else:
        repo.create_file(FILE_PATH, "Create Billboard Archive", csv_content)

def correggi_data_billboard(data_input):
    giorno_settimana = data_input.weekday()
    if giorno_settimana == 5:
        return data_input
    else:
        giorni_da_togliere = (giorno_settimana + 2) % 7
        return data_input - datetime.timedelta(days=giorni_da_togliere)

# --- INTERFACCIA ---
st.set_page_config(page_title="Billboard Full Archiver", page_icon="🎵", layout="wide")
st.title("🎵 Billboard Hot 100: Full Archiver")

df_storico, file_sha = carica_archivio()

st.sidebar.header("📥 Scarica Classifica")
data_scelta = st.sidebar.date_input("Data (Sabato)", value=datetime.date.today())

if st.sidebar.button("Scarica Tutte le 100"):
    data_ottimizzata = correggi_data_billboard(data_scelta)
    with st.spinner(f"Scarico 100 brani per il {data_ottimizzata}..."):
        try:
            chart = billboard.ChartData('hot-100', date=str(data_ottimizzata))
            
            if not chart:
                st.sidebar.error("Dati non disponibili.")
            else:
                nuove_righe = []
                
                # Creiamo un set di canzoni già viste per velocità
                canzoni_gia_viste = set()
                if not df_storico.empty:
                    canzoni_gia_viste = set((df_storico['Canzone'].str.lower() + " - " + df_storico['Artista'].str.lower()).unique())

                # Ciclo su tutta la classifica (100 brani)
                for e in chart:
                    chiave = f"{e.title} - {e.artist}".lower().strip()
                    is_new = chiave not in canzoni_gia_viste
                    
                    nuove_righe.append({
                        "Data": str(chart.date),
                        "Tag": "NEW✨" if is_new else "",
                        "Pos": e.rank,
                        "Canzone": e.title,
                        "Artista": e.artist
                    })
                
                # Unione e salvataggio
                df_nuovo = pd.concat([df_storico, pd.DataFrame(nuove_righe)], ignore_index=True)
                salva_su_github(df_nuovo, file_sha)
                
                st.sidebar.success(f"Archiviata classifica del {chart.date}")
                st.rerun()

        except Exception as e:
            st.sidebar.error(f"Errore: {e}")

# --- VISUALIZZAZIONE ---
if not df_storico.empty:
    st.subheader("📊 Database Storico")
    
    # Preparazione vista (mostriamo le ultime scaricate in alto)
    df_vista = df_storico.copy()
    df_vista['Data'] = pd.to_datetime(df_vista['Data'])
    df_vista = df_vista.sort_values(by=["Data", "Pos"], ascending=[False, True])
    
    # Filtro rapido per vedere solo le NEW
    solo_new = st.checkbox("Mostra solo canzoni 'NEW✨'")
    if solo_new:
        df_vista = df_vista[df_vista['Tag'] == "NEW✨"]

    st.dataframe(
        df_vista, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Data": st.column_config.DateColumn("Data"),
            "Pos": st.column_config.NumberColumn("Rank", format="#%d"),
            "Tag": "Novità",
            "Canzone": st.column_config.TextColumn("Titolo"),
            "Artista": st.column_config.TextColumn("Artista")
        }
    )
    
    # Backup
    st.download_button("📥 Scarica CSV", df_storico.to_csv(index=False).encode('utf-8'), "archivio.csv", "text/csv")
    
