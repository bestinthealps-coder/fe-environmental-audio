import streamlit as st
import pandas as pd
from openai import OpenAI
import random
import os
import time

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="FE Environmental Audio Prep", layout="centered", page_icon="🎧")

# --- CSS E STILE ---
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        height: 60px;
        font-size: 20px;
        border-radius: 10px;
    }
    .big-font {
        font-size: 24px !important;
        font-weight: bold;
        line-height: 1.4;
    }
    .answer-font {
        font-size: 20px !important;
        color: #2e7d32;
    }
    /* Evidenzia il bottone Stop in rosso */
    div[data-testid="stButton"] > button:contains("Stop") {
        background-color: #ffcdd2;
        color: #b71c1c;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: IMPOSTAZIONI ---
with st.sidebar:
    st.title("⚙️ Setup")
    api_key = st.text_input("OpenAI API Key", type="password", help="Inserisci la tua chiave qui")
    
    st.divider()
    
    st.subheader("🗣️ Voci")
    voice_q = st.selectbox("Voce Domanda", ["echo", "alloy", "fable", "onyx", "nova", "shimmer"], index=1)
    voice_a = st.selectbox("Voce Risposta", ["nova", "alloy", "echo", "fable", "onyx", "shimmer"], index=0)
    
    st.divider()
    
    st.subheader("⏱️ Tempi Auto-Loop")
    # Slider per controllare la velocità del loop
    think_time = st.slider("Tempo per pensare (sec)", min_value=2, max_value=15, value=5, help="Pausa tra domanda e risposta")
    review_time = st.slider("Pausa post-risposta (sec)", min_value=2, max_value=10, value=3, help="Pausa prima della prossima domanda")

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
        # Non mostriamo errore in loop per non bloccare flusso, solo console
        print(f"Errore audio: {e}")
        return None

@st.cache_data
def load_data():
    file_path = 'flashcards.csv'
    # Tentativo 1: Formato Excel Italiano
    try:
        df = pd.read_csv(file_path, sep=';', encoding='latin-1')
        if not df.empty and 'question' in df.columns: return df
    except: pass
    # Tentativo 2: Formato Standard
    try:
        df = pd.read_csv(file_path, sep=',')
        if not df.empty and 'question' in df.columns: return df
    except: pass
    # Tentativo 3: Misto
    try:
        df = pd.read_csv(file_path, sep=',', encoding='latin-1')
        if not df.empty and 'question' in df.columns: return df
    except: return pd.DataFrame()
    return pd.DataFrame()

# --- INIT STATO ---
df = load_data()
if df.empty:
    st.error("Errore: File 'flashcards.csv' non valido o assente.")
    st.stop()

if 'index' not in st.session_state: st.session_state.index = 0
if 'shuffled_indices' not in st.session_state: st.session_state.shuffled_indices = list(range(len(df)))
if 'is_looping' not in st.session_state: st.session_state.is_looping = False
if 'loop_phase' not in st.session_state: st.session_state.loop_phase = 'question' # stati: question, answer, next

# --- GESTIONE CATEGORIE ---
categories = ["Tutti"] + list(df['category'].unique()) if 'category' in df.columns else []
if categories:
    selected_cat = st.selectbox("Filtra per materia:", categories, disabled=st.session_state.is_looping)
    if selected_cat != "Tutti":
        filtered_indices = df[df['category'] == selected_cat].index.tolist()
        # Aggiorna solo se non stiamo già loopando per evitare reset improvvisi
        if not st.session_state.is_looping:
            current_subset = set(st.session_state.shuffled_indices)
            target_subset = set(filtered_indices)
            if not current_subset.issubset(target_subset) or len(current_subset) != len(target_subset):
                st.session_state.shuffled_indices = filtered_indices
                st.session_state.index = 0
    elif not st.session_state.is_looping and len(st.session_state.shuffled_indices) != len(df):
        st.session_state.shuffled_indices = list(range(len(df)))
        st.session_state.index = 0

# --- LOGICA LOOP ---
if st.session_state.is_looping:
    st.markdown("### 🔴 LOOP ATTIVO")
    if st.button("⏹️ STOP LOOP"):
        st.session_state.is_looping = False
        st.session_state.loop_phase = 'question'
        st.rerun()

# Recupera card corrente
if not st.session_state.shuffled_indices:
    st.error("Nessuna domanda disponibile.")
    st.stop()
    
# Controllo overflow indice
if st.session_state.index >= len(st.session_state.shuffled_indices):
    st.session_state.index = 0 # Ricomincia il giro

current_idx = st.session_state.shuffled_indices[st.session_state.index]
card = df.iloc[current_idx]

# --- UI VISUALE ---
st.progress((st.session_state.index + 1) / len(st.session_state.shuffled_indices))
st.caption(f"Domanda {st.session_state.index + 1} / {len(st.session_state.shuffled_indices)}")

# CARD CONTAINER
with st.container(border=True):
    # Mostra Domanda
    st.markdown(f"<p class='big-font'>{card['question']}</p>", unsafe_allow_html=True)
    
    # Logica Audio Domanda (Solo se in loop e fase domanda, o manuale)
    if st.session_state.is_looping and st.session_state.loop_phase == 'question':
        if api_key:
            client = OpenAI(api_key=api_key)
            audio_q = get_audio(client, card['question'], voice_q)
            if audio_q:
                st.audio(audio_q, format="audio/mp3", autoplay=True)
                # Aspettiamo la durata dell'audio (stimata) + tempo per pensare
                time.sleep(think_time + 2) 
                st.session_state.loop_phase = 'answer'
                st.rerun()
        else:
            st.warning("Manca API Key per il loop")
            st.session_state.is_looping = False

    # Mostra Risposta (se richiesta o fase answer del loop)
    show_ans_manual = st.session_state.get('show_answer_manual', False)
    if show_ans_manual or (st.session_state.is_looping and st.session_state.loop_phase == 'answer'):
        st.divider()
        st.markdown(f"<p class='answer-font'>{card['answer']}</p>", unsafe_allow_html=True)
        
        # Logica Audio Risposta
        if st.session_state.is_looping and st.session_state.loop_phase == 'answer':
            if api_key:
                client = OpenAI(api_key=api_key)
                audio_a = get_audio(client, card['answer'], voice_a)
                if audio_a:
                    st.audio(audio_a, format="audio/mp3", autoplay=True)
                    time.sleep(review_time + 2) # Tempo per metabolizzare la risposta
                    
                    # Passa alla prossima
                    st.session_state.index += 1
                    st.session_state.loop_phase = 'question'
                    st.rerun()

# --- CONTROLLI MANUALI (Nascosti se in loop) ---
if not st.session_state.is_looping:
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    
    # Audio Manuale Domanda
    if api_key:
         with c1:
            if st.button("🔊 Audio"):
                client = OpenAI(api_key=api_key)
                aud = get_audio(client, card['question'], voice_q)
                st.audio(aud, format="audio/mp3", autoplay=True)

    with c2:
        if st.button("👁️ Soluzione"):
            st.session_state.show_answer_manual = not st.session_state.get('show_answer_manual', False)
            st.rerun()
            
    with c3:
        if st.button("Prossima ➡️"):
            st.session_state.index += 1
            st.session_state.show_answer_manual = False
            st.rerun()
            
    st.markdown("---")
    # TASTO AVVIO LOOP
    if st.button("▶️ AVVIA STUDIO LOOP (AUTOMATICO)"):
        st.session_state.is_looping = True
        st.session_state.loop_phase = 'question'
        st.session_state.show_answer_manual = False
        st.rerun()

    if st.button("🔀 Shuffle Mazzo"):
        random.shuffle(st.session_state.shuffled_indices)
        st.session_state.index = 0
        st.rerun()
