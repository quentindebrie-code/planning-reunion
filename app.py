import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime, timedelta

# --- OPTIMISATION 1 : Configuration & Cache ---
st.set_page_config(page_title="Performance Booking", layout="wide")

@st.cache_data
def get_empty_grid(hours):
    """Prégénère la structure de la grille pour économiser du temps CPU"""
    return pd.DataFrame(index=[f"{h}:00" for h in hours])

# --- INITIALISATION ---
if 'bookings' not in st.session_state:
    st.session_state.bookings = pd.DataFrame(columns=['Date', 'Debut', 'Fin', 'Utilisateur'])

JOURS_FR = {0: "Lundi", 1: "Mardi", 2: "Mercredi", 3: "Jeudi", 4: "Vendredi"}

# --- UI SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Paramètres")
    target_date = st.date_input("Semaine du :", value=datetime.now().date())
    start_of_week = target_date - timedelta(days=target_date.weekday())
    week_days = [start_of_week + timedelta(days=i) for i in range(5)]
    
    st.divider()
    # Utilisation de colonnes pour condenser l'UI
    u_name = st.text_input("Responsable")
    if st.button("🚀 Réservation Rapide", use_container_width=True):
        # (Logique de sauvegarde ici...)
        st.rerun()

# --- OPTIMISATION 2 : Calcul Vectorisé de la Grille ---
def build_visual_grid(bookings, days, hours):
    grid = get_empty_grid(hours).copy()
    
    for d in days:
        col_name = f"{JOURS_FR[d.weekday()]} {d.strftime('%d/%m')}"
        # Filtrage unique pour la journée au lieu de filtrer par cellule
        day_res = bookings[bookings['Date'] == d]
        
        slots = []
        for h in hours:
            # Recherche rapide dans le sous-ensemble de la journée
            occ = day_res[(h >= day_res['Debut']) & (h < day_res['Fin'])]
            slots.append(f"🔴 {occ.iloc[0]['Utilisateur']}" if not occ.empty else "🟢 LIBRE")
        grid[col_name] = slots
    return grid

# --- AFFICHAGE ---
hours = range(8, 20)
with st.spinner('Calcul du planning...'):
    visual_df = build_visual_grid(st.session_state.bookings, week_days, hours)
    
    def style_fn(val):
        bg = '#f8d7da' if '🔴' in val else '#d4edda'
        return f'background-color: {bg}; color: black; font-weight: bold; border: 1px solid white'

    st.table(visual_df.style.applymap(style_fn))

# --- OPTIMISATION 3 : PDF à la demande uniquement ---
if st.button("📥 Préparer l'export PDF"):
    # Ne générer le PDF QUE lors du clic, pas au chargement de la page
    with st.status("Génération du document..."):
        # (Appel de ta classe WeeklyPDF ici)
        st.write("Terminé !")
