import streamlit as st
import billboard
import pandas as pd
from github import Github, Auth  # Aggiunto Auth qui
import io
import datetime

# --- 1. CONFIGURAZIONE E CONNESSIONE ---
try:
    TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_NAME = st.secrets["REPO_NAME"]
    FILE_PATH = "archivio_billboard.csv"
except Exception as e:
    st.error("❌ Configura GITHUB_TOKEN e REPO_NAME nei Secrets.")
    st.stop()

# NUOVO METODO DI AUTENTICAZIONE (Risolve il tuo errore)
auth = Auth.Token(TOKEN)
g = Github(auth=auth)

def carica_archivio():
    try:
        # Usiamo get_repo in modo esplicito
        repo = g.get_repo(REPO_NAME.strip())
        try:
            file_content = repo.get_contents(FILE_PATH)
            df = pd.read_csv(io.StringIO(file_content.decoded_content.decode()))
            return df, file_content.sha
        except:
            # Se il file non esiste ancora nel repo
            return pd.DataFrame(columns=["Data", "Tag", "Pos", "Canzone", "Artista"]), None
    except Exception as e:
        st.error(f"Errore connessione Repo: {e}")
        return pd.DataFrame(), None

def salva_su_github(df_nuovo, sha):
    repo = g.get_repo(REPO_NAME.strip())
    csv_content = df_nuovo.to_csv(index=False)
    if sha:
        repo.update_file(FILE_PATH, "Update Billboard", csv_content, sha)
    else:
        repo.create_file(FILE_PATH, "Create Billboard", csv_content)

def correggi_data(data_in):
    giorno = data_in.weekday()
    return data_in if giorno == 5 else data_in - datetime.timedelta(days=(giorno + 2) % 7)

# --- 2. INTERFACCIA ---
st.set_page_config(page_title="Billboard Full Archiver", layout="wide")
st.title("🎵 Billboard Hot 100 Archiver")

df_storico, file_sha = carica_archivio()

st.sidebar.header("📥 Download")
data_scelta = st.sidebar.date_input("Data (Sabato)", value=datetime.date.today())

if st.sidebar.button("Scarica Tutte le 100"):
    data_ok = correggi_data(data_scelta)
    with st.spinner("Scaricamento in corso..."):
        try:
            chart = billboard.ChartData('hot-100', date=str(data_ok))
            if chart:
                # Logica controllo brani già salvati
                gia_visti = set()
                if not df_storico.empty:
                    gia_visti = set((df_storico['Canzone'].str.lower() + " - " + df_storico['Artista'].str.lower()).unique())

                nuove_righe = []
                for e in chart:
                    chiave = f"{e.title} - {e.artist}".lower().strip()
                    nuove_righe.append({
                        "Data": str(chart.date),
                        "Tag": "NEW✨" if chiave not in gia_visti else "",
                        "Pos": e.rank,
                        "Canzone": e.title,
                        "Artista": e.artist
                    })
                
                df_finale = pd.concat([df_storico, pd.DataFrame(nuove_righe)], ignore_index=True)
                salva_su_github(df_finale, file_sha)
                st.sidebar.success("✅ Salvato!")
                st.rerun()
        except Exception as e:
            st.sidebar.error(f"Errore: {e}")

# --- 3. TABELLA ---
if df_storico is not None and not df_storico.empty:
    st.subheader(f"📊 Archivio ({len(df_storico)} righe)")
    
    df_vista = df_storico.copy()
    df_vista['Data'] = pd.to_datetime(df_vista['Data'])
    
    solo_new = st.checkbox("Mostra solo 'NEW✨'")
    if solo_new:
        df_vista = df_vista[df_vista['Tag'] == "NEW✨"]
    
    st.dataframe(
        df_vista.sort_values(by=["Data", "Pos"], ascending=[False, True]),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("L'archivio è vuoto. Scarica una classifica!")
    
