import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime, timedelta

st.set_page_config(page_title="Planning Stratégique Salle", layout="wide")

# --- INITIALISATION ---
if 'bookings' not in st.session_state:
    st.session_state.bookings = pd.DataFrame(columns=['Date', 'Debut', 'Fin', 'Utilisateur'])

JOURS_FR = {0: "Lundi", 1: "Mardi", 2: "Mercredi", 3: "Jeudi", 4: "Vendredi", 5: "Samedi", 6: "Dimanche"}

# --- LOGIQUE DE NAVIGATION ---
st.title("🗓️ Gestionnaire de Planning Hebdomadaire")

with st.sidebar:
    st.header("🔍 Sélection de la période")
    # Choisir un jour dans la semaine cible
    target_date = st.date_input("Afficher la semaine du :", value=datetime.now().date())
    
    # Recalculer le lundi de cette semaine spécifique
    start_of_selected_week = target_date - timedelta(days=target_date.weekday())
    week_days = [start_of_selected_week + timedelta(days=i) for i in range(5)]
    
    st.markdown("---")
    st.header("📝 Nouvelle Réservation")
    res_date = st.date_input("Date de réservation", value=target_date)
    hours = range(8, 20)
    s_hour = st.selectbox("Heure de début", hours, format_func=lambda x: f"{x}:00")
    e_hour = st.selectbox("Heure de fin", range(s_hour + 1, 21), format_func=lambda x: f"{x}:00")
    u_name = st.text_input("Responsable")

    if st.button("Confirmer la réservation", use_container_width=True):
        conflict = st.session_state.bookings[
            (st.session_state.bookings['Date'] == res_date) & 
            (s_hour < st.session_state.bookings['Fin']) & 
            (e_hour > st.session_state.bookings['Debut'])
        ]
        if u_name and conflict.empty:
            new_row = pd.DataFrame([[res_date, s_hour, e_hour, u_name]], columns=['Date', 'Debut', 'Fin', 'Utilisateur'])
            st.session_state.bookings = pd.concat([st.session_state.bookings, new_row], ignore_index=True)
            st.success(f"Réservé pour le {res_date}")
            st.rerun()
        else:
            st.error("Action impossible : Conflit ou nom vide.")

# --- MOTEUR PDF (ADAPTÉ À LA SEMAINE CHOISIE) ---
class WeeklyPDF(FPDF):
    def generate(self, df, days):
        self.add_page(orientation='L')
        self.set_font("Arial", 'B', 16)
        title = f"PLANNING - SEMAINE DU {days[0].strftime('%d/%m/%Y')} AU {days[-1].strftime('%d/%m/%Y')}"
        self.cell(0, 10, title.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
        self.ln(10)
        
        self.set_font("Arial", 'B', 10)
        self.cell(20, 10, "Heure", 1, 0, 'C')
        for d in days:
            label = f"{JOURS_FR[d.weekday()]} {d.strftime('%d/%m')}"
            self.cell(52, 10, label.encode('latin-1', 'replace').decode('latin-1'), 1, 0, 'C')
        self.ln()

        self.set_font("Arial", size=9)
        for h in range(8, 20):
            self.cell(20, 10, f"{h}:00", 1, 0, 'C')
            for d in days:
                occ = df[(df['Date'] == d) & (h >= df['Debut']) & (h < df['Fin'])]
                if not occ.empty:
                    self.set_fill_color(255, 200, 200)
                    txt = str(occ.iloc[0]['Utilisateur']).encode('latin-1', 'replace').decode('latin-1')
                    self.cell(52, 10, txt, 1, 0, 'C', True)
                else:
                    self.cell(52, 10, "", 1, 0, 'C')
            self.ln()
        return self.output(dest='S').encode('latin-1')

# --- AFFICHAGE DE LA GRILLE ---
st.subheader(f"📅 Affichage : {JOURS_FR[0]} {week_days[0].strftime('%d/%m')} au {JOURS_FR[4]} {week_days[4].strftime('%d/%m')}")

grid_df = pd.DataFrame(index=[f"{h}:00" for h in range(8, 20)])

for d in week_days:
    col_name = f"{JOURS_FR[d.weekday()]} {d.strftime('%d/%m')}"
    day_slots = []
    for h in range(8, 20):
        occ = st.session_state.bookings[(st.session_state.bookings['Date'] == d) & 
                                        (h >= st.session_state.bookings['Debut']) & 
                                        (h < st.session_state.bookings['Fin'])]
        day_slots.append(f"🔴 {occ.iloc[0]['Utilisateur']}" if not occ.empty else "🟢 LIBRE")
    grid_df[col_name] = day_slots

def style_fn(val):
    bg = '#f8d7da' if '🔴' in val else '#d4edda'
    return f'background-color: {bg}; color: black; font-weight: bold; border: 1px solid white'

st.table(grid_df.style.applymap(style_fn))

# --- EXPORT ---
if not st.session_state.bookings.empty:
    pdf_gen = WeeklyPDF()
    pdf_bytes = pdf_gen.generate(st.session_state.bookings, week_days)
    st.download_button("📥 Télécharger cette semaine en PDF", pdf_bytes, f"planning_semaine_{start_of_selected_week}.pdf", "application/pdf")
