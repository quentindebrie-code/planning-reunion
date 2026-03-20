import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime, timedelta
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="Planning 8h-18h One-Page", layout="wide")

# --- PERSISTENCE ---
DB_FILE = "reservations_v4.csv"

def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            return df
        except:
            return pd.DataFrame(columns=['Date', 'Debut', 'Fin', 'Utilisateur'])
    return pd.DataFrame(columns=['Date', 'Debut', 'Fin', 'Utilisateur'])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

if 'bookings' not in st.session_state:
    st.session_state.bookings = load_data()

JOURS_FR = {0: "Lundi", 1: "Mardi", 2: "Mercredi", 3: "Jeudi", 4: "Vendredi"}
HEURES_RANGE = range(8, 18) # 8h à 18h (18h étant l'heure de fin du dernier créneau)

# --- MOTEUR PDF (OPTIMISÉ 8H-18H UNE SEULE PAGE) ---
class WeeklyPDF(FPDF):
    def generate(self, df, days):
        self.set_margins(10, 10, 10)
        self.add_page(orientation='L')
        self.set_auto_page_break(False)
        
        # Titre
        self.set_font("Arial", 'B', 16)
        title = f"Planning - Réservation salle de réunion du {days[0].strftime('%d/%m/%Y')} au {days[-1].strftime('%d/%m/%Y')}"
        self.cell(0, 12, title.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
        self.ln(2)
        
        # Dimensions pour 8h-18h (10 lignes + 1 en-tête)
        # On a plus d'espace vertical par cellule car il y a moins de créneaux
        col_hour_w = 20
        col_day_w = 52 
        row_h = 16.5 # Hauteur augmentée pour un meilleur confort visuel
        line_height = 5 

        # En-tête
        self.set_font("Arial", 'B', 10)
        self.cell(col_hour_w, row_h, "Heure", 1, 0, 'C')
        for d in days:
            label = f"{JOURS_FR[d.weekday()]} {d.strftime('%d/%m')}"
            self.cell(col_day_w, row_h, label.encode('latin-1', 'replace').decode('latin-1'), 1, 0, 'C')
        self.ln()

        # Corps
        self.set_font("Arial", size=9)
        for h in HEURES_RANGE:
            y_start = self.get_y()
            # Cellule Heure
            self.cell(col_hour_w, row_h, f"{h}:00", 1, 0, 'C')
            
            for d in days:
                occ = df[(df['Date'] == d) & (h >= df['Debut']) & (h < df['Fin'])]
                curr_x = self.get_x()
                
                # Cadre de base
                self.rect(curr_x, y_start, col_day_w, row_h)
                
                if not occ.empty:
                    # Remplissage intégral
                    self.set_fill_color(240, 240, 240) # Gris très clair pour économiser l'encre
                    if '🔴' in str(occ.iloc[0]['Utilisateur']): # Optionnel : gestion si emoji présent
                        self.set_fill_color(255, 210, 210)
                    else:
                        self.set_fill_color(255, 225, 225) # Rouge pastel constant
                        
                    self.rect(curr_x, y_start, col_day_w, row_h, style='F')
                    self.rect(curr_x, y_start, col_day_w, row_h, style='D')
                    
                    txt = str(occ.iloc[0]['Utilisateur']).encode('latin-1', 'replace').decode('latin-1')
                    
                    # Centrage vertical dynamique
                    lines = self.multi_cell(col_day_w, line_height, txt, split_only=True)
                    nb_lignes = min(len(lines), 3) # Max 3 lignes
                    txt_final = "\n".join(lines[:nb_lignes])
                    
                    h_totale = nb_lignes * line_height
                    margin_v = (row_h - h_totale) / 2
                    
                    self.set_xy(curr_x, y_start + margin_v)
                    self.multi_cell(col_day_w, line_height, txt_final, border=0, align='C')
                    self.set_xy(curr_x + col_day_w, y_start)
                else:
                    self.set_xy(curr_x + col_day_w, y_start)
            
            self.set_y(y_start + row_h)
            
        return self.output()

# --- INTERFACE ---
st.title("Planning - Réservation salle de réunion")

with st.sidebar:
    st.header("⚙️ Configuration")
    target_date = st.date_input("Semaine du :", value=datetime.now().date())
    start_week = target_date - timedelta(days=target_date.weekday())
    week_days = [start_week + timedelta(days=i) for i in range(5)]
    
    st.divider()
    res_date = st.date_input("Date de l'événement", value=target_date)
    h_start = st.selectbox("Heure de début", HEURES_RANGE, format_func=lambda x: f"{x}:00")
    h_end = st.selectbox("Heure de fin", range(h_start + 1, 19), format_func=lambda x: f"{x}:00")
    resp = st.text_area("Responsable & Détails", placeholder="Apparaîtra centré dans le PDF")

    if st.button("Enregistrer la réservation", use_container_width=True):
        conflict = st.session_state.bookings[
            (st.session_state.bookings['Date'] == res_date) & 
            (h_start < st.session_state.bookings['Fin']) & 
            (h_end > st.session_state.bookings['Debut'])
        ]
        if resp and conflict.empty:
            new_data = pd.DataFrame([[res_date, h_start, h_end, resp]], columns=['Date', 'Debut', 'Fin', 'Utilisateur'])
            st.session_state.bookings = pd.concat([st.session_state.bookings, new_data], ignore_index=True)
            save_data(st.session_state.bookings)
            st.success("Réservation effectuée.")
            st.rerun()
        else:
            st.error("Action impossible : Champ vide ou conflit d'horaire.")

# --- AFFICHAGE GRILLE ---
st.subheader(f"Période : {start_week.strftime('%d/%m')} au {week_days[-1].strftime('%d/%m')}")

grid_df = pd.DataFrame(index=[f"{h}:00" for h in HEURES_RANGE])
for d in week_days:
    col_name = f"{JOURS_FR[d.weekday()]} {d.strftime('%d/%m')}"
    day_data = []
    for h in HEURES_RANGE:
        occ = st.session_state.bookings[(st.session_state.bookings['Date'] == d) & 
                                        (h >= st.session_state.bookings['Debut']) & 
                                        (h < st.session_state.bookings['Fin'])]
        day_data.append(f"🔴 {occ.iloc[0]['Utilisateur']}" if not occ.empty else "🟢 LIBRE")
    grid_df[col_name] = day_data

st.table(grid_df.style.applymap(lambda v: f"background-color: {'#f8d7da' if '🔴' in v else '#d4edda'}; color: black; font-weight: bold; border: 1px solid white;"))

# --- EXPORT FINAL ---
st.divider()
if st.button("📥 Télécharger le Planning Hebdo PDF", use_container_width=True):
    filename = f"planning_{start_week.strftime('%d-%m')}_au_{week_days[-1].strftime('%d-%m')}.pdf"
    pdf_bytes = WeeklyPDF().generate(st.session_state.bookings, week_days)
    st.download_button("Finaliser le téléchargement", pdf_bytes, filename, "application/pdf")
