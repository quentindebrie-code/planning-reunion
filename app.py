import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime, timedelta
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="Planning Ultra-Fast", layout="wide")

# --- PERSISTENCE OPTIMISÉE ---
DB_FILE = "reservations_v4.csv"

@st.cache_data
def load_data_cached(file_path, timestamp):
    """Charge les données seulement si le fichier a été modifié"""
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            return df
        except:
            return pd.DataFrame(columns=['Date', 'Debut', 'Fin', 'Utilisateur'])
    return pd.DataFrame(columns=['Date', 'Debut', 'Fin', 'Utilisateur'])

# Gestion de l'état sans recalcul inutile
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now().timestamp()

bookings = load_data_cached(DB_FILE, st.session_state.last_update)

JOURS_FR = {0: "Lundi", 1: "Mardi", 2: "Mercredi", 3: "Jeudi", 4: "Vendredi"}
HEURES_RANGE = range(8, 18)

# --- MOTEUR PDF (INCHANGÉ MAIS FIABLE) ---
class WeeklyPDF(FPDF):
    def generate(self, df, days):
        self.set_margins(10, 10, 10)
        self.add_page(orientation='L')
        self.set_auto_page_break(False)
        self.set_font("Arial", 'B', 16)
        title = f"PLANNING : SEMAINE DU {days[0].strftime('%d/%m/%Y')} AU {days[-1].strftime('%d/%m/%Y')}"
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
                    self.set_fill_color(255, 215, 215)
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
        return self.output(dest='S').encode('latin-1')

# --- INTERFACE ---
st.title("⚡ Planning Haute Performance (8h-18h)")

with st.sidebar:
    target_date = st.date_input("Semaine du :", value=datetime.now().date())
    start_week = target_date - timedelta(days=target_date.weekday())
    week_days = [start_week + timedelta(days=i) for i in range(5)]
    
    st.divider()
    res_date = st.date_input("Date", value=target_date)
    h_start = st.selectbox("Début", HEURES_RANGE)
    h_end = st.selectbox("Fin", range(h_start + 1, 19))
    resp = st.text_area("Responsable")

    if st.button("Enregistrer", use_container_width=True):
        if resp:
            new_data = pd.DataFrame([[res_date, h_start, h_end, resp]], columns=['Date', 'Debut', 'Fin', 'Utilisateur'])
            # On écrit directement dans le CSV pour la persistence
            updated_df = pd.concat([bookings, new_data], ignore_index=True)
            updated_df.to_csv(DB_FILE, index=False)
            # On force le rafraîchissement du cache
            st.session_state.last_update = datetime.now().timestamp()
            st.rerun()

# --- OPTIMISATION DU RENDU DE LA GRILLE ---
st.subheader(f"Semaine du {start_week.strftime('%d/%m')} au {week_days[-1].strftime('%d/%m')}")

# Filtrer les bookings de la semaine UNE SEULE FOIS au lieu de filtrer par cellule
week_bookings = bookings[bookings['Date'].isin(week_days)]

grid_df = pd.DataFrame(index=[f"{h}:00" for h in HEURES_RANGE])
for d in week_days:
    col_name = f"{JOURS_FR[d.weekday()]} {d.strftime('%d/%m')}"
    day_res = week_bookings[week_bookings['Date'] == d] # Filtre par jour
    
    day_col = []
    for h in HEURES_RANGE:
        occ = day_res[(h >= day_res['Debut']) & (h < day_res['Fin'])]
        day_col.append(f"🔴 {occ.iloc[0]['Utilisateur']}" if not occ.empty else "🟢 LIBRE")
    grid_df[col_name] = day_col

st.table(grid_df.style.applymap(lambda v: f"background-color: {'#f8d7da' if '🔴' in v else '#d4edda'}; color: black; font-weight: bold;"))

# --- EXPORT ---
if st.button("📥 Télécharger le PDF One-Page"):
    pdf_content = WeeklyPDF().generate(bookings, week_days)
    st.download_button("Confirmer", pdf_content, f"planning_{start_week}.pdf", "application/pdf")
