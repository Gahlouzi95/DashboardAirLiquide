import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import numpy as np

# --- 1. CONFIGURATION & DESIGN "GLASSMORPHISM" (Le fond dégradé) ---
st.set_page_config(page_title="Air Liquide | Ultimate Terminal", layout="wide", page_icon="💎")

st.markdown("""
<style>
    /* 1. LE FOND DÉGRADÉ (Mesh Gradient) */
    .stApp {
        background-color: #f3f4f6;
        background-image: 
            radial-gradient(at 0% 0%, hsla(213,100%,85%,1) 0, transparent 50%), 
            radial-gradient(at 50% 0%, hsla(205,100%,92%,1) 0, transparent 50%), 
            radial-gradient(at 100% 0%, hsla(200,100%,89%,1) 0, transparent 50%);
        background-attachment: fixed;
    }

    /* 2. SIDEBAR : Semi-transparente */
    [data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.5);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255,255,255,0.6);
    }

    /* 3. CARTES KPI : Effet Verre (Glassmorphism) */
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.65); /* Blanc transparent */
        backdrop-filter: blur(12px); /* Flou */
        padding: 15px;
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.4);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.05);
        transition: transform 0.2s;
    }
    
    div[data-testid="stMetric"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 40px 0 rgba(31, 38, 135, 0.1);
    }
    
    div[data-testid="stMetricLabel"] { color: #475569; font-weight: 600; font-size: 0.9rem; }
    div[data-testid="stMetricValue"] { color: #0f172a; font-weight: 800; }

    /* 4. TITRES : Style Moderne */
    h1 {
        background: -webkit-linear-gradient(45deg, #0f172a, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Segoe UI', sans-serif;
        font-weight: 800;
    }
    h2, h3 { color: #1e293b !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. CHARGEMENT DONNÉES ---
@st.cache_data
def load_and_process_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    possible_files = ["data.txt", "data.txt.txt"]
    file_path = None
    for f in possible_files:
        temp_path = os.path.join(current_dir, f)
        if os.path.exists(temp_path):
            file_path = temp_path
            break
    if not file_path: return None

    try:
        df = pd.read_csv(file_path, sep='\t')
        df.columns = df.columns.str.strip()
        df['date'] = pd.to_datetime(df['date'], dayfirst=True)
        df.set_index('date', inplace=True)
        
        # Calculs Indicateurs
        df['SMA20'] = df['clot'].rolling(window=20).mean()
        df['SMA50'] = df['clot'].rolling(window=50).mean()
        df['STD20'] = df['clot'].rolling(window=20).std()
        df['Upper_BB'] = df['SMA20'] + (df['STD20'] * 2)
        df['Lower_BB'] = df['SMA20'] - (df['STD20'] * 2)
        
        delta = df['clot'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp12 = df['clot'].ewm(span=12, adjust=False).mean()
        exp26 = df['clot'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp12 - exp26
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

        df['Returns'] = df['clot'].pct_change() * 100
        return df
    except: return None

df = load_and_process_data()
if df is None: st.stop()

# --- 3. SIDEBAR (Fonctionnalités) ---
st.sidebar.title("💎 Réglages")
st.sidebar.markdown("---")

st.sidebar.subheader("Visuel Graphique")
chart_type = st.sidebar.selectbox("Style", ["Bougies (Candles)", "Ligne", "Montagne"])

# --- LA FONCTIONNALITÉ VOLUME ---
show_vol = st.sidebar.checkbox("Afficher le Volume", value=True) 

show_ma = st.sidebar.checkbox("Moyennes Mobiles", value=True)
show_bb = st.sidebar.checkbox("Bandes de Bollinger", value=True)

st.sidebar.markdown("---")
st.sidebar.info("Mode : Ultimate Glass\nDonnées Locales")

# --- 4. HEADER & KPI (Les 5 cartes) ---
st.title(f"Air Liquide (AI.PA)")
st.markdown("**Analyse Technique & Stratégique**")

last = df['clot'].iloc[-1]
prev = df['clot'].iloc[-2]
var_pct = ((last - prev) / prev) * 100
vol = df['Returns'].std() * (252**0.5)
max_drawdown = ((df['clot'] / df['clot'].cummax()) - 1).min() * 100

# Tes 5 indicateurs clés :
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Prix de Clôture", f"{last:.2f} €", f"{var_pct:.2f}%")
k2.metric("Plus Haut (1 an)", f"{df['haut'].max():.2f} €")
k3.metric("Volume Moyen", f"{df['vol'].mean()/1000:.1f} K")
k4.metric("Volatilité (An)", f"{vol:.2f}%")
k5.metric("Max Drawdown", f"{max_drawdown:.2f}%", delta_color="inverse")

st.markdown("---")

# --- 5. GRAPHIQUE PRINCIPAL (Adaptatif) ---
st.subheader("📊 Dynamique de Marché")

# Logique d'affichage : 3 lignes si volume, 2 lignes sinon
if show_vol:
    fig = make_subplots(
        rows=3, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.06, 
        row_heights=[0.6, 0.2, 0.2],
        specs=[[{"secondary_y": False}], [{"secondary_y": False}], [{"secondary_y": False}]],
        subplot_titles=("", "Volume", "RSI (14)")
    )
    rsi_row = 3
else:
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.06, 
        row_heights=[0.75, 0.25],
        specs=[[{"secondary_y": False}], [{"secondary_y": False}]],
        subplot_titles=("", "RSI (14)")
    )
    rsi_row = 2

# A. PRIX
if chart_type == "Bougies (Candles)":
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['ouv'], high=df['haut'], low=df['bas'], close=df['clot'],
        name='Prix', increasing_line_color='#10b981', decreasing_line_color='#ef4444'
    ), row=1, col=1)
elif chart_type == "Montagne":
    fig.add_trace(go.Scatter(
        x=df.index, y=df['clot'], mode='lines', fill='tozeroy', name='Prix', 
        line=dict(color='#0f172a', width=2), fillcolor='rgba(15, 23, 42, 0.1)'
    ), row=1, col=1)
else: 
    fig.add_trace(go.Scatter(
        x=df.index, y=df['clot'], mode='lines', name='Prix', line=dict(color='#0f172a', width=2.5)
    ), row=1, col=1)

if show_ma:
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA20'], line=dict(color='#f59e0b', width=1.5), name='Moyenne 20j'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], line=dict(color='#3b82f6', width=1.5), name='Moyenne 50j'), row=1, col=1)

if show_bb:
    fig.add_trace(go.Scatter(x=df.index, y=df['Upper_BB'], line=dict(color='rgba(100, 116, 139, 0.5)', width=1), showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Lower_BB'], line=dict(color='rgba(100, 116, 139, 0.5)', width=1), fill='tonexty', fillcolor='rgba(203, 213, 225, 0.2)', name='Bollinger'), row=1, col=1)

# B. VOLUME (Si coché)
if show_vol:
    colors_vol = ['#f87171' if row['ouv'] > row['clot'] else '#34d399' for index, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['vol'], marker_color=colors_vol, name='Volume'), row=2, col=1)

# C. RSI
fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#6366f1', width=2), name='RSI'), row=rsi_row, col=1)
fig.add_hline(y=70, line_dash="dash", line_color="#ef4444", row=rsi_row, col=1)
fig.add_hline(y=30, line_dash="dash", line_color="#10b981", row=rsi_row, col=1)

# LAYOUT TRANSPARENT (Pour laisser voir le dégradé)
fig.update_layout(
    height=850,
    template="plotly_white",
    paper_bgcolor='rgba(0,0,0,0)', 
    plot_bgcolor='rgba(255,255,255,0.5)', # Légèrement blanc
    xaxis_rangeslider_visible=False,
    margin=dict(l=20, r=20, t=30, b=20),
    legend=dict(orientation="h", y=1.01, x=0.5, xanchor="center"),
    hovermode="x unified"
)
fig.update_xaxes(showgrid=True, gridcolor='rgba(0,0,0,0.05)')
fig.update_yaxes(showgrid=True, gridcolor='rgba(0,0,0,0.05)')

st.plotly_chart(fig, use_container_width=True)

# --- 6. ANALYSE (Bas de page) ---
st.markdown("---")
col_b1, col_b2 = st.columns(2)
with col_b1:
    st.subheader("📉 Distribution")
    fig_hist = go.Figure(data=[go.Histogram(x=df['Returns'], nbinsx=45, marker_color='#3b82f6', opacity=0.8)])
    fig_hist.update_layout(template="plotly_white", height=300, margin=dict(l=20, r=20, t=40, b=20), 
                           paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(255,255,255,0.5)')
    st.plotly_chart(fig_hist, use_container_width=True)

with col_b2:
    st.subheader("🔄 Momentum (MACD)")
    fig_macd = go.Figure()
    fig_macd.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='#10b981'), name='MACD'))
    fig_macd.add_trace(go.Scatter(x=df.index, y=df['Signal_Line'], line=dict(color='#ef4444'), name='Signal'))
    fig_macd.update_layout(template="plotly_white", height=300, margin=dict(l=20, r=20, t=40, b=20), 
                           paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(255,255,255,0.5)')
    st.plotly_chart(fig_macd, use_container_width=True)

# --- 7. DONNÉES (Cachées + Corrigées) ---
with st.expander("📋 Voir le tableau de données brutes (Cliquez pour ouvrir)"):
    # Protection contre l'erreur de formatage
    numeric_cols = df.select_dtypes(include=['float', 'int']).columns
    st.dataframe(df.sort_index(ascending=False).style.format("{:.2f}", subset=numeric_cols))