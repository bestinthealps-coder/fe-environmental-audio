import streamlit as st
import pandas as pd
from openai import OpenAI
import random
import streamlit as st
import pandas as pd
import os # <--- Assicurati che questo sia importato

# --- DEBUGGING AREA (DA RIMUOVERE DOPO) ---
st.error("--- INIZIO DIAGNOSTICA ---")
st.write("Il server sta eseguendo il codice in questa cartella:", os.getcwd())
st.write("Ecco TUTTI i file che il server vede qui:", os.listdir())
st.error("--- FINE DIAGNOSTICA ---")
# ------------------------------------------
# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="FE Environmental Audio Prep", layout="centered", page_icon="🎧")

# --- CSS PER STILE MOBILE-FRIENDLY ---
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        height: 60px;
        font-size: 20px;
    }
    .big-font {
        font-size: 22px !important;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: IMPOSTAZIONI ---
with st.sidebar:
    st.title("⚙️ Setup")
    api_key = st.text_input("OpenAI API Key", type="password", help="Inserisci la tua chiave qui per attivare l'audio")
    
    st.divider()
    
    voice_q = st.selectbox("Voce Domanda", ["echo", "alloy", "fable", "onyx", "nova", "shimmer"], index=1)
    voice_a = st.selectbox("Voce Risposta", ["nova", "alloy", "echo", "fable", "onyx", "shimmer"], index=0)
    
    st.info("💡 Consiglio: Usa voci diverse per domanda e risposta per mantenere l'attenzione.")

# --- FUNZIONI ---
def get_audio(client, text, voice):
    """Genera l'audio tramite API OpenAI"""
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )
        return response.content
    except Exception as e:
        st.error(f"Errore audio: {e}")
        return None

@st.cache_data
def load_data():
    # Carica il CSV. Assicurati che il separatore sia punto e virgola
    try:
        df = pd.read_csv('flashcards.csv', sep=';')
        return df
    except:
        return pd.DataFrame()

# --- CARICAMENTO DATI ---
df = load_data()

if df.empty:
    st.error("File 'flashcards.csv' non trovato o vuoto. Caricalo nella repository GitHub.")
    st.stop()

# --- STATO DELLA SESSIONE ---
if 'index' not in st.session_state:
    st.session_state.index = 0
if 'shuffled_indices' not in st.session_state:
    st.session_state.shuffled_indices = list(range(len(df)))
if 'show_answer' not in st.session_state:
    st.session_state.show_answer = False
if 'study_mode' not in st.session_state:
    st.session_state.study_mode = "Sequenziale"

# --- FILTRI (OPZIONALE) ---
categories = ["Tutti"] + list(df['category'].unique()) if 'category' in df.columns else []
if categories:
    selected_cat = st.selectbox("Filtra per materia:", categories)
    if selected_cat != "Tutti":
        # Filtra gli indici basandosi sulla categoria
        filtered_indices = df[df['category'] == selected_cat].index.tolist()
        # Se cambiamo categoria, resettiamo il mazzo
        if len(filtered_indices) > 0:
             st.session_state.shuffled_indices = filtered_indices
             st.session_state.index = 0

# --- LOGICA NAVIGAZIONE ---
current_idx = st.session_state.shuffled_indices[st.session_state.index] if st.session_state.shuffled_indices else 0
card = df.iloc[current_idx]

# --- INTERFACCIA UTENTE ---
st.title("🎧 FE Environmental Flashcards")
st.markdown(f"**Card {st.session_state.index + 1} di {len(st.session_state.shuffled_indices)}**")

# Container Domanda
with st.container(border=True):
    st.markdown(f"<p class='big-font'>{card['question']}</p>", unsafe_allow_html=True)
    
    if api_key:
        client = OpenAI(api_key=api_key)
        if st.button("▶️ Ascolta Domanda", use_container_width=True):
            audio = get_audio(client, card['question'], voice_q)
            if audio: st.audio(audio, format="audio/mp3", autoplay=True)
    else:
        st.warning("Inserisci API Key per l'audio")

# Container Risposta
if st.session_state.show_answer:
    st.markdown("---")
    st.success(f"**Risposta:** {card['answer']}")
    
    if api_key:
        if st.button("▶️ Ascolta Risposta", use_container_width=True):
            audio = get_audio(client, card['answer'], voice_a)
            if audio: st.audio(audio, format="audio/mp3", autoplay=True)

st.markdown("---")

# Pulsanti Controllo
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("⬅️ Prev"):
        if st.session_state.index > 0:
            st.session_state.index -= 1
            st.session_state.show_answer = False
            st.rerun()

with col2:
    if st.button("👁️ Vedi Risposta"):
        st.session_state.show_answer = not st.session_state.show_answer
        st.rerun()

with col3:
    if st.button("Next ➡️"):
        if st.session_state.index < len(st.session_state.shuffled_indices) - 1:
            st.session_state.index += 1
            st.session_state.show_answer = False
            st.rerun()

# Bottone Shuffle
if st.button("🔀 Mescola Mazzo (Shuffle)"):
    random.shuffle(st.session_state.shuffled_indices)
    st.session_state.index = 0
    st.session_state.show_answer = False

    st.rerun()
