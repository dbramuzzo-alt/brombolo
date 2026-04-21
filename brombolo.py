import streamlit as st
import billboard
import pandas as pd
from github import Github
import io
import datetime

# --- 1. CONFIGURAZIONE E CONNESSIONE ---
# Recupero i segreti impostati su Streamlit Cloud
try:
    TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_NAME = st.secrets["REPO_NAME"]
    FILE_PATH = "archivio_billboard.csv"
except Exception as e:
    st.error("❌ ERRORE: Configura GITHUB_TOKEN e REPO_NAME nei Secrets di Streamlit.")
    st.stop()

# Inizializzazione GitHub
g = Github(TOKEN)

def carica_archivio():
    """Scarica il database da GitHub o ne crea uno vuoto se non esiste"""
    try:
        repo = g.get_repo(REPO_NAME)
        file_content = repo.get_contents(FILE_PATH)
        df = pd.read_csv(io.StringIO(file_content.decoded_content.decode()))
        return df, file_content.sha
    except Exception:
        # Se il file non esiste, restituiamo un DataFrame vuoto e sha None
        return pd.DataFrame(columns=["Data", "Tag", "Pos", "Canzone", "Artista"]), None

def salva_su_github(df_nuovo, sha):
    """Salva il file aggiornato su GitHub"""
    repo = g.get_repo(REPO_NAME)
    csv_content = df_nuovo.to_csv(index=False)
    if sha:
        repo.update_file(FILE_PATH, "Update Billboard Data", csv_content, sha)
    else:
        repo.create_file(FILE_PATH, "Create Billboard Data", csv_content)

def correggi_data_billboard(data_input):
    """Trova il sabato corretto per Billboard"""
    giorno_settimana = data_input.weekday() # 5 è Sabato
    if giorno_settimana == 5:
        return data_input
    else:
        giorni_da_togliere = (giorno_settimana + 2) % 7
        return data_input - datetime.timedelta(days=giorni_da_togliere)

# --- 2. INTERFACCIA APP ---
st.set_page_config(page_title="Billboard Full Archiver", page_icon="🎵", layout="wide")
st.title("🎵 Billboard Hot 100: Database Personale")

# Caricamento dati
df_storico, file_sha = carica_archivio()

# Sidebar
st.sidebar.header("📥 Gestione Dati")
data_scelta = st.sidebar.date_input("Scegli una data", value=datetime.date.today())

if st.sidebar.button("Scarica Tutte le 100"):
    data_billboard = correggi_data_billboard(data_scelta)
    
    with st.spinner(f"Scaricando i 100 brani del {data_billboard}..."):
        try:
            chart = billboard.ChartData('hot-100', date=str(data_billboard))
            
            if not chart:
                st.sidebar.error("❌ Nessun dato trovato per questa data.")
            else:
                nuove_righe = []
                
                # Creiamo il set di canzoni GIA' SALVATE per il controllo NEW
                canzoni_gia_salvate = set()
                if not df_storico.empty:
                    canzoni_gia_salvate = set(
                        (df_storico['Canzone'].str.lower() + " - " + df_storico['Artista'].str.lower()).unique()
                    )

                for e in chart:
                    chiave = f"{e.title} - {e.artist}".lower().strip()
                    # Mette NEW solo se non l'abbiamo MAI vista nel CSV
                    is_new = chiave not in canzoni_gia_salvate
                    
                    nuove_righe.append({
                        "Data": str(chart.date),
                        "Tag": "NEW✨" if is_new else "",
                        "Pos": e.rank,
                        "Canzone": e.title,
                        "Artista": e.artist
                    })
                
                # Uniamo i nuovi dati allo storico
                df_finale = pd.concat([df_storico, pd.DataFrame(nuove_righe)], ignore_index=True)
                
                # Salvataggio
                salva_su_github(df_finale, file_sha)
                
                st.sidebar.success(f"✅ Salvato con successo!")
                st.rerun()

        except Exception as e:
            st.sidebar.error(f"❌ Errore durante il salvataggio: {e}")

# --- 3. VISUALIZZAZIONE ---
if not df_storico.empty:
    st.subheader(f"📊 Archivio ({len(df_storico)} voci)")
    
    df_vista = df_storico.copy()
    df_vista['Data'] = pd.to_datetime(df_vista['Data'])
    
    # Filtro NEW
    solo_new = st.checkbox("Mostra solo i brani 'NEW✨'")
    if solo_new:
        df_vista = df_vista[df_vista['Tag'] == "NEW✨"]
    
    # Ordiniamo: Ultima data inserita in alto, posizione dalla 1 alla 100
    df_vista = df_vista.sort_values(by=["Data", "Pos"], ascending=[False, True])

    st.dataframe(
        df_vista, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Data": st.column_config.DateColumn("Data Classifica"),
            "Pos": st.column_config.NumberColumn("Rank", format="#%d"),
            "Tag": "Novità",
            "Canzone": "Titolo",
            "Artista": "Artista"
        }
    )
    
    st.download_button(
        "📥 Esporta CSV", 
        df_storico.to_csv(index=False).encode('utf-8'), 
        "archivio_billboard.csv", 
        "text/csv"
    )
else:
    st.info("💡 L'archivio è vuoto. Scarica la tua prima classifica dalla barra laterale!")
    
