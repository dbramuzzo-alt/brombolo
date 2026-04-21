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
        return pd.DataFrame(columns=["Data", "Tag", "Pos", "Canzone", "Artista", "Dettaglio"]), None

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
st.set_page_config(page_title="Billboard Archiver Pro", page_icon="🚀", layout="wide")
st.title("🎵 Billboard Pro Archiver")

df_storico, file_sha = carica_archivio()

st.sidebar.header("➕ Nuova Classifica")
data_scelta = st.sidebar.date_input("Seleziona una data", value=datetime.date.today())

if st.sidebar.button("Scarica e Archivia"):
    data_ottimizzata = correggi_data_billboard(data_scelta)
    with st.spinner(f"Recupero dati per il {data_ottimizzata}..."):
        try:
            chart = billboard.ChartData('hot-100', date=str(data_ottimizzata))
            
            if not chart:
                st.sidebar.error("Nessun dato trovato.")
            else:
                nuove_righe = []
                
                # --- LOGICA NEW: Recuperiamo i titoli già presenti nel file CSV ---
                # Prendiamo solo i titoli dell'ultimo aggiornamento per il confronto
                titoli_gia_in_archivio = set()
                if not df_storico.empty:
                    # Creiamo un set di "Titolo - Artista" di tutto quello che è già salvato nel CSV
                    # per marcare come NEW tutto ciò che entra per la prima volta nel database
                    titoli_gia_in_archivio = set((df_storico['Canzone'].str.lower() + " - " + df_storico['Artista'].str.lower()).unique())

                # Funzione interna per marcare NEW
                def check_new(entry):
                    chiave = f"{entry.title} - {entry.artist}".lower().strip()
                    return "NEW✨ " if chiave not in titoli_gia_in_archivio else ""

                # 1. TOP 10
                for e in chart[:10]:
                    tag_new = check_new(e)
                    nuove_righe.append({
                        "Data": str(chart.date),
                        "Tag": f"{tag_new}TOP 10",
                        "Pos": e.rank,
                        "Canzone": e.title,
                        "Artista": e.artist,
                        "Dettaglio": f"Settimana scorsa: #{e.lastPos}" if e.lastPos > 0 else "Nuova in Top 10"
                    })

                # 2. TOP MOVERS
                movers = [e for e in chart if e.lastPos > 0 and (e.lastPos - e.rank) >= 10]
                for e in sorted(movers, key=lambda x: (x.lastPos - x.rank), reverse=True):
                    tag_new = check_new(e)
                    nuove_righe.append({
                        "Data": str(chart.date),
                        "Pos": e.rank,
                        "Tag": f"{tag_new}🚀 MOVER",
                        "Canzone": e.title,
                        "Artista": e.artist,
                        "Dettaglio": f"Salita di {e.lastPos - e.rank} pos. (da #{e.lastPos})"
                    })

                # 3. DEBUTTI
                for e in chart:
                    if e.isNew:
                        tag_new = check_new(e)
                        nuove_righe.append({
                            "Data": str(chart.date),
                            "Tag": f"{tag_new}🎵 DEBUT",
                            "Pos": e.rank,
                            "Canzone": e.title,
                            "Artista": e.artist,
                            "Dettaglio": "Entrata assoluta in classifica"
                        })
                
                # Salvataggio
                df_nuovo = pd.concat([df_storico, pd.DataFrame(nuove_righe)], ignore_index=True)
                salva_su_github(df_nuovo, file_sha)
                
                st.sidebar.success(f"Archiviato: {chart.date}")
                st.rerun()

        except Exception as e:
            st.sidebar.error(f"Errore: {e}")

# --- VISUALIZZAZIONE ---
if not df_storico.empty:
    df_vista = df_storico.copy()
    df_vista['Data'] = pd.to_datetime(df_vista['Data'])
    df_vista = df_vista.sort_values(by=["Data", "Pos"], ascending=[False, True])
    
    st.dataframe(df_vista, use_container_width=True, hide_index=True)
    
