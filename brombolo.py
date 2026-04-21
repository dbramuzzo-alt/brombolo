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
    st.error("Errore: Secrets non configurati correttamente su Streamlit Cloud.")
    st.stop()

# Connessione GitHub
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
    """Arrotonda la data al sabato precedente per evitare classifiche vuote"""
    giorno_settimana = data_input.weekday() # 5 è Sabato
    if giorno_settimana == 5:
        return data_input
    else:
        giorni_da_togliere = (giorno_settimana + 2) % 7
        return data_input - datetime.timedelta(days=giorni_da_togliere)

# --- INTERFACCIA ---
st.set_page_config(page_title="Billboard Archiver Pro", page_icon="🚀", layout="wide")
st.title("🎵 Billboard Pro Archiver (GitHub Storage)")

df_storico, file_sha = carica_archivio()

# Sidebar
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
                
                # 1. TOP 10
                for e in chart[:10]:
                    chiave = f"{e.title} - {e.artist}".lower().strip()
                    gia_visto = False
                    if not df_storico.empty:
                        # Controllo se la canzone è mai apparsa nell'archivio (colonne Canzone + Artista)
                        gia_visto = chiave in (df_storico['Canzone'].str.lower() + " - " + df_storico['Artista'].str.lower()).values
                    
                    nuove_righe.append({
                        "Data": str(chart.date),
                        "Tag": "NEW✨" if not gia_visto else "TOP 10",
                        "Pos": e.rank,
                        "Canzone": e.title,
                        "Artista": e.artist,
                        "Dettaglio": "Stabile/Discesa" if e.lastPos <= e.rank and e.lastPos != 0 else f"Ex #{e.lastPos}"
                    })

                # 2. TOP MOVERS (Salite >= 10 posizioni)
                movers = [e for e in chart if e.lastPos > 0 and (e.lastPos - e.rank) >= 10]
                for e in sorted(movers, key=lambda x: (x.lastPos - x.rank), reverse=True):
                    nuove_righe.append({
                        "Data": str(chart.date),
                        "Tag": "🚀 MOVER",
                        "Pos": e.rank,
                        "Canzone": e.title,
                        "Artista": e.artist,
                        "Dettaglio": f"Salita di {e.lastPos - e.rank} pos."
                    })

                # 3. DEBUTTI
                for e in chart:
                    if e.isNew:
                        nuove_righe.append({
                            "Data": str(chart.date),
                            "Tag": "🎵 DEBUT",
                            "Pos": e.rank,
                            "Canzone": e.title,
                            "Artista": e.artist,
                            "Dettaglio": "Nuova entrata"
                        })
                
                # Unione e salvataggio
                df_nuovo = pd.concat([df_storico, pd.DataFrame(nuove_righe)], ignore_index=True)
                salva_su_github(df_nuovo, file_sha)
                
                st.sidebar.success(f"Archivio aggiornato: {chart.date}")
                st.rerun()

        except Exception as e:
            st.sidebar.error(f"Errore: {e}")

# --- VISUALIZZAZIONE ---
st.subheader("📊 Archivio Storico")

if not df_storico.empty:
    # Preparazione tabella per la vista
    df_vista = df_storico.copy()
    # Ordiniamo per data decrescente e poi per posizione
    df_vista['Data'] = pd.to_datetime(df_vista['Data'])
    df_vista = df_vista.sort_values(by=["Data", "Pos"], ascending=[False, True])
    
    # Mostriamo la tabella con i filtri
    filtro_tag = st.multiselect("Filtra per Tag", options=df_vista['Tag'].unique(), default=df_vista['Tag'].unique())
    df_filtrato = df_vista[df_vista['Tag'].isin(filtro_tag)]
    
    st.dataframe(
        df_filtrato, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Data": st.column_config.DateColumn("Settimana"),
            "Pos": st.column_config.NumberColumn("Pos.", format="#%d"),
            "Tag": "Tipo",
            "Dettaglio": st.column_config.TextColumn("Info Extra")
        }
    )
    
    # Tasto Download per backup locale
    st.download_button(
        "📥 Scarica CSV Completo",
        df_storico.to_csv(index=False).encode('utf-8'),
        "billboard_archive.csv",
        "text/csv"
    )
else:
    st.info("L'archivio è ancora vuoto. Seleziona una data e clicca su scarica!")
    
