import streamlit as st
import pandas as pd
from openai import OpenAI
import random
import os
import time

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="FE Environmental Audio Prep", layout="centered", page_icon="🎧")

# --- SIDEBAR: IMPOSTAZIONI ---
with st.sidebar:
    st.title("⚙️ Setup Ingegnere")
    
    # --- DARK MODE TOGGLE ---
    dark_mode = st.toggle("🌙 Dark Mode", value=False, help="Attiva sfondo scuro per riposare gli occhi")
    
    st.divider()
    
    api_key = st.text_input("OpenAI API Key", type="password", help="Inserisci la tua chiave qui")
    
    st.subheader("🗣️ Configurazione Vocale")
    voice_q = st.selectbox("Voce Domanda", ["echo", "alloy", "fable", "onyx", "nova", "shimmer"], index=1)
    voice_a = st.selectbox("Voce Risposta", ["nova", "alloy", "echo", "fable", "onyx", "shimmer"], index=0)
    
    # Slider Velocità
    voice_speed = st.slider("Velocità Parlato (Speed)", min_value=0.5, max_value=2.0, value=1.0, step=0.05)
    
    st.divider()
    
    st.subheader("⏱️ Tempi Auto-Loop")
    think_time = st.slider("Tempo per pensare (sec)", min_value=2, max_value=30, value=5)
    review_time = st.slider("Pausa post-risposta (sec)", min_value=2, max_value=15, value=3)

# --- CSS DINAMICO (GESTIONE DARK/LIGHT MODE) ---
if dark_mode:
    # --- STILE DARK MODE ---
    custom_css = """
    <style>
    /* 1. Sfondo generale dell'App e Sidebar */
    .stApp {
        background-color: #121212;
        color: #FAFAFA;
    }
    [data-testid="stSidebar"] {
        background-color: #1E1E1E;
    }
    
    /* 2. Container/Card delle Domande */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #2C2C2C;
        border-color: #444444;
    }
    
    /* 3. Testi Generici (Titoli, paragrafi) in bianco */
    h1, h2, h3, p, span, div, label {
        color: #FAFAFA !important;
    }

    /* 4. FIX BOTTONI STANDARD (Audio, Soluzione, ecc.) */
    div[data-testid="stButton"] > button {
        background-color: #333333 !important; /* Sfondo scuro per il bottone */
        color: #FFFFFF !important;             /* Testo bianco */
        border: 1px solid #555555 !important;  /* Bordo sottile */
    }
    div[data-testid="stButton"] > button:hover {
        border-color: #81c784 !important;      /* Bordo verde al passaggio del mouse */
        color: #FFFFFF !important;
    }

    /* 5. Input Fields (Box testo API Key, Selectbox) */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: #2C2C2C !important;
        color: white !important;
        -webkit-text-fill-color: white !important; /* Forza colore su Safari/Chrome */
    }

    /* 6. Bottone STOP (Eccezione Rossa) */
    div[data-testid="stButton"] > button p:contains("STOP") {
        color: white !important;
    }
    /* Cerchiamo il bottone che contiene il testo STOP in modo euristico */
    div[data-testid="stButton"] > button:active {
        color: white !important;
    }
    </style>
    """
    card_answer_color = "#81c784" # Verde chiaro per la risposta
    
    # CSS Extra per colorare di rosso specificamente il tasto STOP in dark mode
    # Streamlit non permette selettori :has() ovunque, quindi usiamo un trucco:
    # coloriamo il background di tutti i bottoni scuri (fatto sopra), 
    # ma il tasto stop lo definiamo nell'interfaccia con un container diverso se possibile
    # Per ora lo lasciamo grigio scuro come gli altri per uniformità, o rosso se riusciamo.
    
else:
    # --- STILE LIGHT MODE (Default) ---
    custom_css = """
    <style>
    /* Evidenzia il bottone Stop in rosso chiaro */
    div[data-testid="stButton"] > button {
        background-color: #FFFFFF;
        color: #000000;
    }
    </style>
    """
    card_answer_color = "#2e7d32" # Verde scuro standard

# --- INIEZIONE CSS GLOBALE ---
st.markdown(f"""
    <style>
    /* Stile comune a entrambe le modalità */
    .stButton>button {{
        width: 100%;
        height: 60px;
        font-size: 20px;
        border-radius: 10px;
    }}
    .big-font {{
        font-size: 24px !important;
        font-weight: bold;
        line-height: 1.4;
    }}
    .answer-font {{
        font-size: 20px !important;
        color: {card_answer_color} !important; /* Importante per sovrascrivere il bianco globale */
        font-weight: bold;
    }}
    /* Tasto STOP specifico (selettore avanzato CSS) */
    div[data-testid="stButton"] > button:has(div p:contains("STOP")), 
    div[data-testid="stButton"] > button:has(p:contains("STOP")) {{
        background-color: #e57373 !important;
        color: white !important;
        border: none !important;
    }}
    </style>
    {custom_css}
    """, unsafe_allow_html=True)

# --- FUNZIONI ---
def get_audio(client, text, voice, speed_val):
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text,
            speed=speed_val
        )
        return response.content
    except Exception as e:
        print(f"Errore audio: {e}")
        return None

@st.cache_data
def load_data():
    file_path = 'flashcards.csv'
    try:
        df = pd.read_csv(file_path, sep=';', encoding='latin-1')
        if not df.empty and 'question' in df.columns: return df
    except: pass
    try:
        df = pd.read_csv(file_path, sep=',')
        if not df.empty and 'question' in df.columns: return df
    except: pass
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
if 'loop_phase' not in st.session_state: st.session_state.loop_phase = 'question'

# --- GESTIONE CATEGORIE ---
categories = ["Tutti"] + list(df['category'].unique()) if 'category' in df.columns else []
if categories:
    selected_cat = st.selectbox("Filtra per materia:", categories, disabled=st.session_state.is_looping)
    if selected_cat != "Tutti":
        filtered_indices = df[df['category'] == selected_cat].index.tolist()
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

if not st.session_state.shuffled_indices:
    st.error("Nessuna domanda disponibile.")
    st.stop()
    
if st.session_state.index >= len(st.session_state.shuffled_indices):
    st.session_state.index = 0

current_idx = st.session_state.shuffled_indices[st.session_state.index]
card = df.iloc[current_idx]

# --- UI VISUALE ---
st.progress((st.session_state.index + 1) / len(st.session_state.shuffled_indices))
st.caption(f"Domanda {st.session_state.index + 1} / {len(st.session_state.shuffled_indices)}")

with st.container(border=True):
    # Domanda
    st.markdown(f"<p class='big-font'>{card['question']}</p>", unsafe_allow_html=True)
    
    # Audio Loop Domanda
    if st.session_state.is_looping and st.session_state.loop_phase == 'question':
        if api_key:
            client = OpenAI(api_key=api_key)
            audio_q = get_audio(client, card['question'], voice_q, voice_speed)
            if audio_q:
                st.audio(audio_q, format="audio/mp3", autoplay=True)
                time.sleep(think_time + 2) 
                st.session_state.loop_phase = 'answer'
                st.rerun()
        else:
            st.warning("Manca API Key")
            st.session_state.is_looping = False

    # Risposta
    show_ans_manual = st.session_state.get('show_answer_manual', False)
    if show_ans_manual or (st.session_state.is_looping and st.session_state.loop_phase == 'answer'):
        st.divider()
        st.markdown(f"<p class='answer-font'>{card['answer']}</p>", unsafe_allow_html=True)
        
        # Audio Loop Risposta
        if st.session_state.is_looping and st.session_state.loop_phase == 'answer':
            if api_key:
                client = OpenAI(api_key=api_key)
                audio_a = get_audio(client, card['answer'], voice_a, voice_speed)
                if audio_a:
                    st.audio(audio_a, format="audio/mp3", autoplay=True)
                    time.sleep(review_time + 2)
                    st.session_state.index += 1
                    st.session_state.loop_phase = 'question'
                    st.rerun()

# --- CONTROLLI MANUALI ---
if not st.session_state.is_looping:
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    
    if api_key:
         with c1:
            if st.button("🔊 Audio"):
                client = OpenAI(api_key=api_key)
                aud = get_audio(client, card['question'], voice_q, voice_speed)
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
    if st.button("▶️ AVVIA STUDIO LOOP (AUTOMATICO)"):
        st.session_state.is_looping = True
        st.session_state.loop_phase = 'question'
        st.session_state.show_answer_manual = False
        st.rerun()

    if st.button("🔀 Shuffle Mazzo"):
        random.shuffle(st.session_state.shuffled_indices)
        st.session_state.index = 0
        st.rerun()
