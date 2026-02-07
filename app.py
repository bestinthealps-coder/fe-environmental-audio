import streamlit as st
import pandas as pd
from openai import OpenAI
import random
import os
import time

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="FE Environmental Audio Prep", layout="centered", page_icon="🎧")

# --- API KEY MANAGEMENT (COMMERCIAL MODE) ---
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
    has_valid_key = True
else:
    api_key = st.sidebar.text_input("OpenAI API Key", type="password", help="Enter API Key")
    has_valid_key = bool(api_key)

# --- SIDEBAR: SETTINGS ---
with st.sidebar:
    st.title("⚙️ Engineering Setup")
    
    # --- DARK MODE TOGGLE ---
    dark_mode = st.toggle("🌙 Dark Mode", value=False, help="Enable dark background for eye relief")
    
    st.divider()
    
    if "OPENAI_API_KEY" in st.secrets:
        st.success("✅ Audio License Active")
    
    st.subheader("🗣️ Voice Configuration")
    voice_q = st.selectbox("Question Voice", ["echo", "alloy", "fable", "onyx", "nova", "shimmer"], index=1)
    voice_a = st.selectbox("Answer Voice", ["nova", "alloy", "echo", "fable", "onyx", "shimmer"], index=0)
    
    voice_speed = st.slider("Speech Speed (x)", min_value=0.5, max_value=2.0, value=1.0, step=0.05)
    
    st.divider()
    
    st.subheader("⏱️ Auto-Loop Timings")
    think_time = st.slider("Thinking Time (sec)", min_value=2, max_value=30, value=5)
    review_time = st.slider("Post-Answer Pause (sec)", min_value=2, max_value=15, value=3)

# --- DYNAMIC CSS ---
if dark_mode:
    custom_css = """
    <style>
    /* 1. Sfondo generale scuro */
    .stApp { background-color: #121212; color: #FAFAFA; }
    [data-testid="stSidebar"] { background-color: #1E1E1E; }
    
    /* 2. Container e Input Fields */
    div[data-testid="stVerticalBlockBorderWrapper"] { background-color: #2C2C2C; border-color: #444444; }
    .stTextInput input { background-color: #2C2C2C !important; color: white !important; }
    
    /* 3. Testi generali in bianco */
    h1, h2, h3, p, span, label { color: #FAFAFA !important; }
    
    /* 4. FIX CRITICO PER IL MENU A TENDINA (SELECTBOX) */
    /* Rendiamo il box di selezione scuro */
    .stSelectbox div[data-baseweb="select"] > div {
        background-color: #2C2C2C !important;
        color: white !important;
    }
    /* Rendiamo la LISTA (il menu aperto) scura, così il testo bianco si legge */
    ul[data-testid="stSelectboxVirtualDropdown"] {
        background-color: #2C2C2C !important;
    }
    /* Gestiamo il colore del testo dentro le opzioni */
    li[role="option"] div {
        color: white !important;
    }
    /* Effetto Hover (quando passi il mouse sopra) */
    li[role="option"]:hover {
        background-color: #444444 !important;
    }

    /* 5. Bottoni Standard */
    div[data-testid="stButton"] > button { 
        background-color: #333333 !important; 
        color: #FFFFFF !important; 
        border: 1px solid #555555 !important; 
    }
    div[data-testid="stButton"] > button:hover { 
        border-color: #81c784 !important; 
        color: #FFFFFF !important; 
    }
    
    /* 6. Bottone STOP (Eccezione) */
    div[data-testid="stButton"] > button p:contains("STOP") { color: white !important; }
    </style>
    """
    card_answer_color = "#81c784"
else:
    # --- LIGHT MODE STYLE ---
    custom_css = """
    <style>
    div[data-testid="stButton"] > button { background-color: #FFFFFF; color: #000000; }
    </style>
    """
    card_answer_color = "#2e7d32"

st.markdown(f"""
    <style>
    .stButton>button {{ width: 100%; height: 60px; font-size: 20px; border-radius: 10px; }}
    .big-font {{ font-size: 24px !important; font-weight: bold; line-height: 1.4; }}
    .answer-font {{ font-size: 20px !important; color: {card_answer_color} !important; font-weight: bold; }}
    div[data-testid="stButton"] > button:has(div p:contains("STOP")), 
    div[data-testid="stButton"] > button:has(p:contains("STOP")) {{ background-color: #e57373 !important; color: white !important; border: none !important; }}
    </style>
    {custom_css}
    """, unsafe_allow_html=True)

# --- FUNCTIONS ---
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
        print(f"Audio Error: {e}")
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

# --- MAIN APP LOGIC ---
df = load_data()
if df.empty:
    st.error("Error: 'flashcards.csv' not found.")
    st.stop()

if 'index' not in st.session_state: st.session_state.index = 0
if 'shuffled_indices' not in st.session_state: st.session_state.shuffled_indices = list(range(len(df)))
if 'is_looping' not in st.session_state: st.session_state.is_looping = False
if 'loop_phase' not in st.session_state: st.session_state.loop_phase = 'question'

categories = ["All"] + list(df['category'].unique()) if 'category' in df.columns else []
if categories:
    selected_cat = st.selectbox("Filter by Subject:", categories, disabled=st.session_state.is_looping)
    if selected_cat != "All":
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

if st.session_state.is_looping:
    st.markdown("### 🔴 LOOP ACTIVE")
    if st.button("⏹️ STOP LOOP"):
        st.session_state.is_looping = False
        st.session_state.loop_phase = 'question'
        st.rerun()

if not st.session_state.shuffled_indices:
    st.error("No questions available.")
    st.stop()
if st.session_state.index >= len(st.session_state.shuffled_indices): st.session_state.index = 0
current_idx = st.session_state.shuffled_indices[st.session_state.index]
card = df.iloc[current_idx]

st.progress((st.session_state.index + 1) / len(st.session_state.shuffled_indices))
st.caption(f"Question {st.session_state.index + 1} of {len(st.session_state.shuffled_indices)}")

with st.container(border=True):
    st.markdown(f"<p class='big-font'>{card['question']}</p>", unsafe_allow_html=True)
    if st.session_state.is_looping and st.session_state.loop_phase == 'question':
        if has_valid_key:
            client = OpenAI(api_key=api_key)
            audio_q = get_audio(client, card['question'], voice_q, voice_speed)
            if audio_q:
                st.audio(audio_q, format="audio/mp3", autoplay=True)
                time.sleep(think_time + 2) 
                st.session_state.loop_phase = 'answer'
                st.rerun()
        else:
            st.warning("Audio License Missing")
            st.session_state.is_looping = False

    show_ans_manual = st.session_state.get('show_answer_manual', False)
    if show_ans_manual or (st.session_state.is_looping and st.session_state.loop_phase == 'answer'):
        st.divider()
        st.markdown(f"**Answer:**")
        st.markdown(f"<p class='answer-font'>{card['answer']}</p>", unsafe_allow_html=True)
        if st.session_state.is_looping and st.session_state.loop_phase == 'answer':
            if has_valid_key:
                client = OpenAI(api_key=api_key)
                audio_a = get_audio(client, card['answer'], voice_a, voice_speed)
                if audio_a:
                    st.audio(audio_a, format="audio/mp3", autoplay=True)
                    time.sleep(review_time + 2)
                    st.session_state.index += 1
                    st.session_state.loop_phase = 'question'
                    st.rerun()

if not st.session_state.is_looping:
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    if has_valid_key:
         with c1:
            if st.button("🔊 Audio"):
                client = OpenAI(api_key=api_key)
                aud = get_audio(client, card['question'], voice_q, voice_speed)
                st.audio(aud, format="audio/mp3", autoplay=True)
    with c2:
        if st.button("👁️ Reveal Answer"):
            st.session_state.show_answer_manual = not st.session_state.get('show_answer_manual', False)
            st.rerun()
    with c3:
        if st.button("Next ➡️"):
            st.session_state.index += 1
            st.session_state.show_answer_manual = False
            st.rerun()
    st.markdown("---")
    if st.button("▶️ START AUTO-LOOP MODE"):
        st.session_state.is_looping = True
        st.session_state.loop_phase = 'question'
        st.session_state.show_answer_manual = False
        st.rerun()
    if st.button("🔀 Shuffle Deck"):
        random.shuffle(st.session_state.shuffled_indices)
        st.session_state.index = 0
        st.rerun()
