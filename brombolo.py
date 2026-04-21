import streamlit as st
import billboard
import pandas as pd

# --- FUNZIONI DI LOGICA ORIGINALE ---
def pulisci_titolo(riga):
    if " - " not in riga: return None
    grezzo = riga
    for tag in ["NEW✨", "🎵", "🚀", "    "]:
        grezzo = grezzo.replace(tag, "")
    if "#" in grezzo:
        parte_dati = grezzo.split("#")[-1].strip()
        parole = parte_dati.split(" ")
        if parole[0].isdigit(): parole.pop(0)
        grezzo = " ".join(parole).strip()
    return grezzo.lower().strip()

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="Billboard Archiver Pro", page_icon="🎵", layout="wide")

st.title("🎵 Billboard Archiver Pro")

# Inizializziamo il "database" nella sessione (per non perderlo mentre usi l'app)
if 'archivio' not in st.session_state:
    st.session_state.archivio = {}
if 'visti' not in st.session_state:
    st.session_state.visti = set()

# --- SIDEBAR: AGGIUNGI DATA ---
st.sidebar.header("➕ Aggiungi Data")
data_scelta = st.sidebar.date_input("Seleziona una data", value=None)

if st.sidebar.button("Scarica e Archivia"):
    if data_scelta:
        data_str = str(data_scelta)
        with st.spinner(f"Recupero {data_str}..."):
            try:
                chart = billboard.ChartData('hot-100', date=data_str)
                
                # Logica Tag "NEW"
                risultati = {"top10": [], "movers": [], "debutti": []}
                
                def controlla_e_tagga(entry):
                    chiave = f"{entry.title} - {entry.artist}".lower().strip()
                    is_nuovo = chiave not in st.session_state.visti
                    if is_nuovo: st.session_state.visti.add(chiave)
                    return "NEW✨" if is_nuovo else "    "

                # 1. TOP 10
                for e in chart[:10]:
                    tag = controlla_e_tagga(e)
                    risultati["top10"].append(f"{tag} #{e.rank} {e.title} - {e.artist}")

                # 2. MOVERS
                movers = [e for e in chart if e.lastPos > 0 and (e.lastPos - e.rank) >= 10]
                for e in sorted(movers, key=lambda x: (x.lastPos-x.rank), reverse=True):
                    tag = controlla_e_tagga(e)
                    risultati["movers"].append(f"{tag} 🚀 +{e.lastPos - e.rank} pos. - #{e.rank} {e.title}")

                # 3. DEBUTTI
                for e in chart:
                    if e.isNew:
                        tag = controlla_e_tagga(e)
                        risultati["debutti"].append(f"{tag} 🎵 {e.title} - {e.artist}")

                st.session_state.archivio[data_str] = risultati
                st.sidebar.success(f"Data {data_str} salvata!")
            except Exception as e:
                st.sidebar.error(f"Errore: {e}")

# --- CORPO CENTRALE: VISUALIZZAZIONE ---
if not st.session_state.archivio:
    st.info("L'archivio è vuoto. Usa la barra laterale per scaricare una classifica!")
else:
    # Gestione eliminazione
    with st.expander("🗑️ Gestisci Archivio (Elimina date)"):
        date_da_cancellare = st.selectbox("Seleziona data da rimuovere", options=list(st.session_state.archivio.keys()))
        if st.button("Elimina selezionata"):
            del st.session_state.archivio[date_da_cancellare]
            st.rerun()

    # Mostra l'archivio storico
    st.header("=== ARCHIVIO STORICO ===")
    for data, contenuti in reversed(list(st.session_state.archivio.items())):
        with st.container():
            st.subheader(f"📅 Classifica del {data}")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**TOP 10**")
                st.code("\n".join(contenuti["top10"]))
            
            with col2:
                st.markdown("**TOP MOVERS**")
                st.code("\n".join(contenuti["movers"]))
            
            with col3:
                st.markdown("**DEBUTTI**")
                st.code("\n".join(contenuti["debutti"]))
            st.divider()
