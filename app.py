import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime, timedelta
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="Planning Salle Réunion", layout="wide")

DB_FILE = "reservations_v4.csv"

# --- FONCTIONS DE DONNÉES ---
def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            # Nettoyage des dates pour éviter les erreurs de comparaison
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            return df
        except:
            return pd.DataFrame(columns=['Date', 'Debut', 'Fin', 'Utilisateur'])
    return pd.DataFrame(columns=['Date', 'Debut', 'Fin', 'Utilisateur'])

if 'bookings' not in st.session_state:
    st.session_state.bookings = load_data()

JOURS_FR = {0: "Lundi", 1: "Mardi", 2: "Mercredi", 3: "Jeudi", 4: "Vendredi"}
HEURES_RANGE = range(8, 18)

# --- CLASSE PDF ---
class WeeklyPDF(FPDF):
    def generate(self, df, days):
        self.set_margins(10, 10, 10)
        self.add_page(orientation='L')
        self.set_auto_page_break(False)
        self.set_font("Arial", 'B', 16)
        title = f"Planning : Réservation salle de réunion - Semaine du {days[0].strftime('%d/%m/%Y')} au {days[-1].strftime('%d/%m/%Y')}"
        self.cell(0, 12, title.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
        
        col_hour_w, col_day_w, row_h, line_h = 20, 52, 16.5, 5
        self.set_font("Arial", 'B', 10)
        self.cell(col_hour_w, row_h, "Heure", 1, 0, 'C')
        for d in days:
            label = f"{JOURS_FR[d.weekday()]} {d.strftime('%d/%m')}"
            self.cell(col_day_w, row_h, label.encode('latin-1', 'replace').decode('latin-1'), 1, 0, 'C')
        self.ln()

        self.set_font("Arial", size=9)
        for h in HEURES_RANGE:
            y_s = self.get_y()
            self.cell(col_hour_w, row_h, f"{h}:00", 1, 0, 'C')
            for d in days:
                occ = df[(df['Date'] == d) & (h >= df['Debut']) & (h < df['Fin'])]
                cx = self.get_x()
                self.rect(cx, y_s, col_day_w, row_h)
                if not occ.empty:
                    self.set_fill_color(255, 225, 225)
                    self.rect(cx, y_s, col_day_w, row_h, style='F')
                    self.rect(cx, y_s, col_day_w, row_h, style='D')
                    txt = str(occ.iloc[0]['Utilisateur']).encode('latin-1', 'replace').decode('latin-1')
                    lines = self.multi_cell(col_day_w, line_h, txt, split_only=True)
                    nb = min(len(lines), 3)
                    m_v = (row_h - (nb * line_h)) / 2
                    self.set_xy(cx, y_s + m_v)
                    self.multi_cell(col_day_w, line_h, "\n".join(lines[:nb]), border=0, align='C')
                    self.set_xy(cx + col_day_w, y_s)
                else:
                    self.set_xy(cx + col_day_w, y_s)
            self.set_y(y_s + row_h)
        return bytes(self.output())

# --- INTERFACE ---
st.title("Gestionnaire de Planning - Salle de réunion")

with st.sidebar:
    st.header("⚙️ Réservation")
    target_date = st.date_input("Semaine du :", value=datetime.now().date())
    start_week = target_date - timedelta(days=target_date.weekday())
    week_days = [start_week + timedelta(days=i) for i in range(5)]
    
    st.divider()
    res_date = st.date_input("Date", value=target_date)
    h_start = st.selectbox("Début", HEURES_RANGE, format_func=lambda x: f"{x}:00")
    h_end = st.selectbox("Fin", range(h_start + 1, 19), format_func=lambda x: f"{x}:00")
    resp = st.text_area("Responsable / Objet")

    if st.button("Enregistrer", use_container_width=True):
        if resp:
            new_data = pd.DataFrame([[res_date, h_start, h_end, resp]], columns=['Date', 'Debut', 'Fin', 'Utilisateur'])
            st.session_state.bookings = pd.concat([st.session_state.bookings, new_data], ignore_index=True)
            st.session_state.bookings.to_csv(DB_FILE, index=False)
            st.rerun()

    # --- NOUVELLE FONCTIONNALITÉ : ANNULATION SÉLECTIVE ---
    st.divider()
    st.header("Annuler un créneau")
    
    if not st.session_state.bookings.empty:
        # On crée une liste textuelle pour que l'utilisateur puisse choisir
        options = st.session_state.bookings.copy()
        options['label'] = options.apply(lambda x: f"{x['Date']} ({x['Debut']}h-{x['Fin']}h) : {x['Utilisateur']}", axis=1)
        
        to_cancel = st.multiselect("Sélectionnez les réservations à supprimer :", options['label'].tolist())
        
        if st.button("Annuler les créneaux sélectionnés", type="primary"):
            if to_cancel:
                # Filtrer pour ne garder que ce qui n'a PAS été sélectionné
                st.session_state.bookings = st.session_state.bookings[~options['label'].isin(to_cancel)]
                st.session_state.bookings.to_csv(DB_FILE, index=False)
                st.success("Annulation effectuée.")
                st.rerun()
            else:
                st.info("Sélectionnez au moins un créneau.")
    else:
        st.write("Aucune réservation à annuler.")

# --- GRILLE D'AFFICHAGE ---
st.subheader(f"Semaine du {start_week.strftime('%d/%m')} au {week_days[-1].strftime('%d/%m')}")

grid_data = {"Heure": [f"{h}:00" for h in HEURES_RANGE]}
for d in week_days:
    col_name = f"{JOURS_FR[d.weekday()]} {d.strftime('%d/%m')}"
    day_slots = []
    for h in HEURES_RANGE:
        match = st.session_state.bookings[(st.session_state.bookings['Date'] == d) & 
                                          (h >= st.session_state.bookings['Debut']) & 
                                          (h < st.session_state.bookings['Fin'])]
        day_slots.append(f"🔴 {match.iloc[0]['Utilisateur']}" if not match.empty else "🟢 LIBRE")
    grid_data[col_name] = day_slots

st.table(pd.DataFrame(grid_data).set_index("Heure").style.applymap(
    lambda v: f"background-color: {'#f8d7da' if '🔴' in v else '#d4edda'}; color: black;"
))

# --- EXPORT PDF ---
st.divider()
if st.button("📥 Préparer le PDF", use_container_width=True):
    pdf_bytes = WeeklyPDF().generate(st.session_state.bookings, week_days)
    st.download_button(
        label="Cliquez ici pour télécharger",
        data=pdf_bytes,
        file_name=f"planning_{start_week}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
