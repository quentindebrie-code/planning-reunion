import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import date

# --- CONFIGURATION ---
st.set_page_config(page_title="Visual Booking System", layout="wide")

if 'bookings' not in st.session_state:
    st.session_state.bookings = pd.DataFrame(columns=['Date', 'Debut', 'Fin', 'Utilisateur'])

# --- MOTEUR DE GÉNÉRATION PDF VISUEL ---
class VisualCalendarPDF(FPDF):
    def draw_calendar(self, selected_date, daily_data):
        self.add_page()
        self.set_font("Arial", 'B', 16)
        self.cell(0, 15, f"PLANNING DE LA SALLE - {selected_date}", ln=True, align='C')
        self.ln(5)
        
        # En-têtes
        self.set_font("Arial", 'B', 11)
        self.set_fill_color(230, 230, 230)
        self.cell(30, 10, "Heure", 1, 0, 'C', True)
        self.cell(160, 10, "Occupation / Responsable", 1, 1, 'C', True)
        
        self.set_font("Arial", size=10)
        
        # Dessin de la grille (8h à 20h)
        for h in range(8, 21):
            hour_str = f"{h}:00"
            
            # Vérifier si l'heure est occupée
            occ = daily_data[(h >= daily_data['Debut']) & (h < daily_data['Fin'])]
            
            if not occ.empty:
                # Cellule occupée (Rouge léger)
                self.set_fill_color(255, 200, 200) 
                user_info = f"OCCUPE - {occ.iloc[0]['Utilisateur']}"
                self.cell(30, 10, hour_str, 1, 0, 'C', True)
                self.cell(160, 10, user_info, 1, 1, 'L', True)
            else:
                # Cellule libre (Vert léger)
                self.set_fill_color(220, 255, 220)
                self.cell(30, 10, hour_str, 1, 0, 'C', True)
                self.cell(160, 10, "LIBRE", 1, 1, 'L', True)

def export_visual_pdf(df, selected_date):
    pdf = VisualCalendarPDF()
    pdf.draw_calendar(selected_date, df)
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACE UTILISATEUR ---
st.title("🛡️ Booking Expert : Interface Visuelle")

col_left, col_right = st.columns([1, 2])

with col_left:
    st.subheader("📝 Réservation")
    res_date = st.date_input("Date", value=date.today())
    s_hour = st.selectbox("Début", range(8, 20), format_func=lambda x: f"{x}:00")
    e_hour = st.selectbox("Fin", range(s_hour + 1, 21), format_func=lambda x: f"{x}:00")
    u_name = st.text_input("Nom de l'organisateur")

    if st.button("Valider la réservation", use_container_width=True):
        conflict = st.session_state.bookings[
            (st.session_state.bookings['Date'] == res_date) & 
            (s_hour < st.session_state.bookings['Fin']) & 
            (e_hour > st.session_state.bookings['Debut'])
        ]
        if not u_name:
            st.warning("Merci de saisir un nom.")
        elif not conflict.empty:
            st.error("Collision détectée sur ce créneau !")
        else:
            new_entry = pd.DataFrame([[res_date, s_hour, e_hour, u_name]], 
                                    columns=['Date', 'Debut', 'Fin', 'Utilisateur'])
            st.session_state.bookings = pd.concat([st.session_state.bookings, new_entry], ignore_index=True)
            st.rerun()

with col_right:
    st.subheader(f"Aperçu du {res_date}")
    
    # Création de la vue visuelle à l'écran
    view_list = []
    current_day = st.session_state.bookings[st.session_state.bookings['Date'] == res_date]
    
    for h in range(8, 21):
        occ = current_day[(h >= current_day['Debut']) & (h < current_day['Fin'])]
        status = f"🔴 {occ.iloc[0]['Utilisateur']}" if not occ.empty else "🟢 LIBRE"
        view_list.append({"Heure": f"{h}:00", "Statut": status})
    
    df_view = pd.DataFrame(view_list)
    
    # CSS pour l'affichage écran
    def color_rows(row):
        color = "#f8d7da" if "🔴" in row['Statut'] else "#d4edda"
        return [f'background-color: {color}; color: black; border: 1px solid #ddd'] * len(row)

    st.table(df_view.style.apply(color_rows, axis=1))

    # Export PDF
    if st.button("🖨️ Générer le calendrier PDF visuel", use_container_width=True):
        pdf_data = export_visual_pdf(current_day, res_date)
        st.download_button("Cliquez ici pour télécharger", pdf_data, f"planning_{res_date}.pdf", "application/pdf")