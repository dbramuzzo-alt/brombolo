import streamlit as st
import random
import pandas as pd

# Configurazione Pagina
st.set_page_config(page_title="Gestione Orari Negozio", layout="wide", page_icon="📅")

# --- ISTRUZIONI ---
st.title("📅 Gestore Orari Settimanale")
with st.expander("📖 CLICCA QUI PER LE ISTRUZIONI"):
    st.write("""
    1. **Target**: Imposta gli incassi previsti nella barra laterale.
    2. **Algoritmo**: L'app cercherà di incastrare le ore (Margherita 40h, Giorgia 34h, Vanessa 18h, Hilary 18h).
    3. **Sicurezza**: Se l'app non riesce a trovare una soluzione valida dopo 1000 tentativi, si fermerà per evitare errori.
    """)

# --- SIDEBAR: INPUT TARGET ---
st.sidebar.header("🎯 Imposta i Target")
target_utente = {}
giorni = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
default_vals = [1700, 1200, 900, 2300, 2400, 2000, 1500]

for giorno, def_val in zip(giorni, default_vals):
    target_utente[giorno] = st.sidebar.number_input(f"{giorno} (€)", value=def_val, step=50)

# --- FUNZIONE LOGICA OTTIMIZZATA ---
def genera_orario_logica(target):
    contratti = {"Margherita": 40, "Giorgia": 34, "Vanessa": 18, "Hilary": 18}
    
    # Limite massimo di tentativi globali per evitare il crash del browser
    for tentativo_globale in range(2000):
        schedule = {g: [] for g in giorni}
        ore_fatte = {n: 0 for n in contratti}
        
        # 1. Assegnazione Turni Base (Apertura e Chiusura)
        for g in giorni:
            candidati = [n for n in contratti if not (n == "Margherita" and g == "Domenica")]
            random.shuffle(candidati)
            apre, chiude = candidati[0], candidati[1]
            
            # Regola Target Alto: Turno Spezzato
            if target[g] >= 2000 and apre in ["Margherita", "Giorgia"]:
                schedule[g].append({"n": apre, "i": 9, "f": 13})
                schedule[g].append({"n": apre, "i": 17, "f": 20})
                ore_fatte[apre] += 7
            else:
                schedule[g].append({"n": apre, "i": 9, "f": 15})
                ore_fatte[apre] += 6
            
            # Chiusura (evita sovrapposizione se lo stesso dipendente fa tutto)
            if not any(t['n'] == chiude for t in schedule[g]):
                schedule[g].append({"n": chiude, "i": 14, "f": 20})
                ore_fatte[chiude] += 6

        # 2. Riempimento Ore Mancanti
        giorni_top = sorted(giorni, key=lambda x: target[x], reverse=True)
        for g in giorni_top:
            for n in contratti:
                if ore_fatte[n] < contratti[n]:
                    if n == "Margherita" and g == "Domenica": continue
                    if not any(t['n'] == n for t in schedule[g]):
                        mancanti = contratti[n] - ore_fatte[n]
                        durata = min(mancanti, 8 if target[g] >= 2000 else 5)
                        if durata >= 3:
                            inizio = 10 if target[g] >= 2000 else 11
                            schedule[g].append({"n": n, "i": inizio, "f": inizio + durata})
                            ore_fatte[n] += durata

        # 3. Bilanciamento Fine (Aggiustamento puntuale)
        for n, t_ore in contratti.items():
            tentativi_locali = 0
            while ore_fatte[n] != t_ore and tentativi_locali < 200:
                tentativi_locali += 1
                g = random.choice(giorni)
                if n == "Margherita" and g == "Domenica": continue
                
                turni_del_giorno = [t for t in schedule[g] if t["n"] == n]
                if not turni_del_giorno: continue
                t = random.choice(turni_del_giorno)
                
                if ore_fatte[n] < t_ore:
                    # Prova ad allungare il turno esistente se non sbatte contro altri turni
                    if t["f"] < 20: 
                        t["f"] += 1
                        ore_fatte[n] += 1
                elif ore_fatte[n] > t_ore:
                    if (t["f"] - t["i"] > 3): 
                        t["f"] -= 1
                        ore_fatte[n] -= 1

        # 4. Validazione Finale
        successo = True
        if not all(ore_fatte[n] == contratti[n] for n in contratti):
            successo = False
        
        for g in giorni:
            copertura = [0] * 24
            for t in schedule[g]:
                for h in range(t["i"], t["f"]): copertura[h] += 1
            # Controllo copertura minima (nessun buco tra le 9 e le 20)
            if sum(1 for h in copertura[9:20] if h >= 1) < 11: successo = False
            # Se target alto, servono almeno 3 persone contemporaneamente in qualche momento
            if target[g] >= 2300 and max(copertura) < 3: successo = False

        if successo:
            return schedule, ore_fatte
            
    return None, None

# --- INTERFACCIA DI OUTPUT ---
st.write("---")
if st.button('🚀 GENERA NUOVO ORARIO'):
    res_sch, res_ore = genera_orario_logica(target_utente)
    
    if res_sch:
        rows = []
        for g in giorni:
            diario = {}
            for t in res_sch[g]:
                if t["n"] not in diario: diario[t["n"]] = []
                diario[t["n"]].append(f"{t['i']:02d}:00-{t['f']:02d}:00")
            
            turni_str = "  \n ".join([f"**{n}**: {', '.join(sorted(set(f)))}" for n, f in diario.items()])
            icona = "🔥" if target_utente[g] >= 2000 else "☕"
            rows.append({"Giorno": f"{icona} {g}", "Target": f"{target_utente[g]}€", "Turni": turni_str})
        
        st.table(pd.DataFrame(rows))

        st.subheader("✅ Riepilogo ore contrattuali")
        cols = st.columns(4)
        for i, (nome, ore) in enumerate(res_ore.items()):
            cols[i].metric(nome, f"{ore}h")
    else:
        st.error("❌ Impossibile generare un orario perfetto con questi target. Riprova o cambia i valori!")
else:
    st.info("Configura i target a sinistra e premi il tasto per iniziare.")
            
