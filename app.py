import streamlit as st
import pandas as pd
from openai import OpenAI
import random
import os

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
    file_path = 'flashcards.csv'
    
    # Tentativo 1: Formato Excel Italiano (Punto e virgola, encoding Windows)
    try:
        df = pd.read_csv(file_path, sep=';', encoding='latin-1')
        if not df.empty and 'question' in df.columns:
            return df
    except:
        pass

    # Tentativo 2: Formato Standard (Virgola, encoding UTF-8)
    try:
        df = pd.read_csv(file_path, sep=',')
        if not df.empty and 'question' in df.columns:
            return df
    except:
        pass

    # Tentativo 3: Formato Misto (Virgola, encoding Windows)
    try:
        df = pd.read_csv(file_path, sep=',', encoding='latin-1')
        if not df.empty and 'question' in df.columns:
            return df
    except Exception as e:
        st.error(f"ERRORE DI LETTURA: {e}")
        return pd.DataFrame()
    
    return pd.DataFrame()

# --- CARICAMENTO DATI ---
df = load_data()

if df.empty:
    st.error("File 'flashcards.csv' non trovato o impossibile da leggere. Controlla che il file esista su GitHub e abbia le colonne: id,category,question,answer")
    # Debug info
    st.write("File nella cartella:", os.listdir())
    st.stop()

# --- STATO DELLA SESSIONE ---
if 'index' not in st.session_state:
    st.session_state.index = 0
if 'shuffled_indices' not in st.session_state:
    st.session_state.shuffled_indices = list(range(len(df)))
if 'show_answer' not in st.session_state:
    st.session_state.show_answer = False

# --- FILTRI (OPZIONALE) ---
categories = ["Tutti"] + list(df['category'].unique()) if 'category' in df.columns else []
if categories:
    selected_cat = st.selectbox("Filtra per materia:", categories)
    if selected_cat != "Tutti":
        # Filtra gli indici basandosi sulla categoria
        filtered_indices = df[df['category'] == selected_cat].index.tolist()
        # Se cambiamo categoria, resettiamo il mazzo se necessario
        # (Qui semplifico per evitare bug di reset continuo: ricalcolo solo se la lista corrente non matcha)
        current_selection_set = set(filtered_indices)
        current_shuffled_set = set(st.session_state.shuffled_indices)
        
        # Logica base: se l'utente filtra, mostriamo solo quelle
        # Nota: per semplicità, se filtriamo, ricreiamo la lista filtrata
        # Per evitare loop infiniti in Streamlit, facciamo il reset solo se l'utente cambia filtro attivamente
        # Ma per ora, forziamo il filtraggio semplice:
        if len(st.session_state.shuffled_indices) != len(filtered_indices) or not set(st.session_state.shuffled_indices).issubset(set(df[df['category'] == selected_cat].index)):
             st.session_state.shuffled_indices = filtered_indices
             st.session_state.index = 0
    else:
        # Se torna a "Tutti" e non ha tutti gli indici, resetta
        if len(st.session_state.shuffled_indices) != len(df):
            st.session_state.shuffled_indices = list(range(len(df)))
            st.session_state.index = 0

# --- LOGICA NAVIGAZIONE ---
# Protezione caso indici vuoti
if not st.session_state.shuffled_indices:
    st.warning("Nessuna domanda trovata per questa categoria.")
    st.stop()

# Assicuriamoci che l'indice non vada fuori range
if st.session_state.index >= len(st.session_state.shuffled_indices):
    st.session_state.index = 0

current_idx = st.session_state.shuffled_indices[st.session_state.index]
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
