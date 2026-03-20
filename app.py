import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime, timedelta
import os

# --- CONFIGURATION ENGINE ---
st.set_page_config(page_title="Planning Turbo", layout="wide")

# Utilisation du cache pour éviter de relire le disque inutilement
@st.cache_data(show_spinner=False)
def get_data(file_path, update_trigger):
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        return df
    return pd.DataFrame(columns=['Date', 'Debut', 'Fin', 'Utilisateur'])

DB_FILE = "reservations_v4.csv"

# --- INITIALISATION ---
if 'update_tick' not in st.session_state:
    st.session_state.update_tick = 0

# Chargement ultra-rapide
data = get_data(DB_FILE, st.session_state.update_tick)

JOURS_FR = {0: "Lundi", 1: "Mardi", 2: "Mercredi", 3: "Jeudi", 4: "Vendredi"}
HEURES_RANGE = range(8, 18)

# --- MOTEUR PDF (STABLE) ---
class WeeklyPDF(FPDF):
    def generate(self, df, days):
        self.set_margins(10, 10, 10)
        self.add_page(orientation='L')
        self.set_auto_page_break(False)
        self.set_font("Arial", 'B', 14)
        title = f"PLANNING : SEMAINE DU {days[0].strftime('%d/%m/%Y')} AU {days[-1].strftime('%d/%m/%Y')}"
        self.cell(0, 10, title.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
        
        col_hour_w, col_day_w, row_h, line_h = 20, 52, 16, 5
        self.set_font("Arial", 'B', 10)
        self.cell(col_hour_w, row_h, "Heure", 1, 0, 'C')
        for d in days:
            label = f"{JOURS_FR[d.weekday()]} {d.strftime('%d/%m')}"
            self.cell(col_day_w, row_h, label.encode('latin-1', 'replace').decode('latin-1'), 1, 0, 'C')
        self.ln()

        self.set_font("Arial", size=8)
        for h in HEURES_RANGE:
            y_s = self.get_y()
            self.cell(col_hour_w, row_h, f"{h}:00", 1, 0, 'C')
            for d in days:
                occ = df[(df['Date'] == d) & (h >= df['Debut']) & (h < df['Fin'])]
                cx = self.get_x()
                self.rect(cx, y_s, col_day_w, row_h)
                if not occ.empty:
                    self.set_fill_color(255, 230, 230)
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

# --- LOGIQUE SIDEBAR ---
with st.sidebar:
    st.header("⚡ Contrôle Rapide")
    t_date = st.date_input("Semaine du", value=datetime.now().date(), key="nav_date")
    start_w = t_date - timedelta(days=t_date.weekday())
    w_days = [start_w + timedelta(days=i) for i in range(5)]
    
    with st.form("res_form", clear_on_submit=True):
        st.write("Nouvelle Entrée")
        d_res = st.date_input("Jour", value=t_date)
        h_s = st.selectbox("Début", HEURES_RANGE)
        h_e = st.selectbox("Fin", range(h_s + 1, 19))
        u_resp = st.text_input("Responsable")
        submit = st.form_submit_button("Ajouter au planning", use_container_width=True)

    if submit and u_resp:
        new_row = pd.DataFrame([[d_res, h_s, h_e, u_resp]], columns=['Date', 'Debut', 'Fin', 'Utilisateur'])
        # Append direct pour éviter de manipuler tout le DF en mémoire
        new_row.to_csv(DB_FILE, mode='a', header=not os.path.exists(DB_FILE), index=False)
        st.session_state.update_tick += 1
        st.rerun()

# --- RENDU DE LA GRILLE (STRATÉGIE DE PERFORMANCE) ---
st.subheader(f"Planning : {start_w.strftime('%d/%m')} au {w_days[-1].strftime('%d/%m')}")

# On filtre les données de la semaine APRES le chargement
mask = (data['Date'] >= w_days[0]) & (data['Date'] <= w_days[-1])
w_data = data[mask]

# Construction de la matrice en pur Python (beaucoup plus rapide que des filtres Pandas successifs)
matrix = []
for h in HEURES_RANGE:
    row = {"Heure": f"{h}:00"}
    for d in w_days:
        col_name = f"{JOURS_FR[d.weekday()]} {d.strftime('%d/%m')}"
        match = w_data[(w_data['Date'] == d) & (h >= w_data['Debut']) & (h < w_data['Fin'])]
        row[col_name] = f"🔴 {match.iloc[0]['Utilisateur']}" if not match.empty else "🟢 LIBRE"
    matrix.append(row)

display_df = pd.DataFrame(matrix).set_index("Heure")

# Utilisation de st.dataframe (moteur Canvas) au lieu de st.table (moteur HTML)
# C'est ce qui fait la plus grosse différence de fluidité
st.dataframe(
    display_df.style.map(lambda v: f"background-color: {'#f8d7da' if '🔴' in v else '#d4edda'}; color: black; font-weight: bold;"),
    use_container_width=True,
    height=420
)

# --- EXPORT ---
st.divider()
if st.button("📥 Générer le PDF (Action unique)", use_container_width=True):
    with st.status("Traitement des données...", expanded=False):
        pdf_content = WeeklyPDF().generate(data, w_days)
    
    st.download_button(
        "Cliquez ici pour télécharger le fichier",
        pdf_content,
        f"planning_{start_w}.pdf",
        "application/pdf",
        use_container_width=True
    )
