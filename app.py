import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime, timedelta
import io
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="Salle de réunion - Planning de réservation", layout="wide")

DB_FILE = "reservations_v5.csv"
JOURS_FR = {0: "Lundi", 1: "Mardi", 2: "Mercredi", 3: "Jeudi", 4: "Vendredi"}
HEURES_RANGE = range(8, 18)

# --- LOGIQUE DE DONNÉES ---
def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            return df
        except Exception as e:
            st.error(f"Erreur lecture DB: {e}")
    return pd.DataFrame(columns=['Date', 'Debut', 'Fin', 'Utilisateur'])

def save_data(df):
    df.to_csv(DB_FILE, index=False)
    st.session_state.bookings = df

if 'bookings' not in st.session_state:
    st.session_state.bookings = load_data()

# --- CLASSE PDF CORRIGÉE ET MATRICIELLE ---
class WeeklyPDF(FPDF):
    def generate_grid(self, start_date, grid_df):
        # Format Paysage pour faire rentrer 6 colonnes
        self.add_page(orientation='L')
        self.set_font("Arial", 'B', 16)
        self.cell(0, 10, f"Planning Semaine du {start_date.strftime('%d/%m/%Y')}", ln=True, align='C')
        self.ln(5)
        
        # Calcul des largeurs de colonnes (Largeur utile A4 Paysage ~ 277mm)
        col_widths = [20] + [51] * 5  # 20mm pour la colonne Heure, 51mm pour les 5 jours
        headers = ["Heure"] + list(grid_df.columns)
        
        # Génération de l'en-tête
        self.set_font("Arial", 'B', 10)
        self.set_fill_color(200, 200, 200) # Gris pour l'en-tête
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 10, header, border=1, align='C', fill=True)
        self.ln()
        
        # Génération de la grille (données)
        self.set_font("Arial", '', 9)
        for heure, row in grid_df.iterrows():
            # Colonne Heure
            self.set_fill_color(240, 240, 240)
            self.cell(col_widths[0], 10, str(heure), border=1, align='C', fill=True)
            
            # Colonnes Jours
            for i, col in enumerate(grid_df.columns):
                valeur = str(row[col])
                
                # Nettoyage obligatoire des emojis pour FPDF + Application du code couleur
                if "🔴" in valeur:
                    self.set_fill_color(248, 215, 218) # Rouge pastel (occupé)
                    texte = valeur.replace("🔴 ", "")[:25] # Nettoyage et limitation
                else:
                    self.set_fill_color(212, 237, 218) # Vert pastel (libre)
                    texte = "LIBRE"
                
                self.cell(col_widths[i+1], 10, texte, border=1, align='C', fill=True)
            self.ln()
            
        return self.output()

# --- INTERFACE SIDEBAR ---
with st.sidebar:
    st.header("🎯 Gestion des Flux")
    
    st.subheader("📥 Importer")
    uploaded_file = st.file_uploader("Fichier Excel (.xlsx)", type=["xlsx"])
    if uploaded_file:
        try:
            imported_df = pd.read_excel(uploaded_file)
            imported_df['Date'] = pd.to_datetime(imported_df['Date']).dt.date
            if st.button("Fusionner l'import"):
                combined = pd.concat([st.session_state.bookings, imported_df]).drop_duplicates().reset_index(drop=True)
                save_data(combined)
                st.success("Données synchronisées.")
                st.rerun()
        except Exception as e:
            st.error(f"Format invalide : {e}")

    st.divider()

    st.subheader("📅 Nouveau Créneau")
    res_date = st.date_input("Date", value=datetime.now().date())
    h_start = st.selectbox("Début", HEURES_RANGE, format_func=lambda x: f"{x}:00")
    h_end = st.selectbox("Fin", range(h_start + 1, 19), format_func=lambda x: f"{x}:00")
    resp = st.text_input("Responsable / Objet")

    if st.button("Enregistrer", use_container_width=True):
        if resp:
            new_line = pd.DataFrame([[res_date, h_start, h_end, resp]], columns=['Date', 'Debut', 'Fin', 'Utilisateur'])
            save_data(pd.concat([st.session_state.bookings, new_line], ignore_index=True))
            st.rerun()

    st.divider()

    st.subheader("🗑️ Annuler")
    if not st.session_state.bookings.empty:
        options = st.session_state.bookings.copy()
        options['label'] = options.apply(lambda x: f"{x['Date']} | {x['Debut']}h-{x['Fin']}h | {x['Utilisateur']}", axis=1)
        to_cancel = st.multiselect("Sélectionner :", options['label'].tolist())
        if st.button("Supprimer", type="primary"):
            new_df = st.session_state.bookings[~options['label'].isin(to_cancel)]
            save_data(new_df)
            st.rerun()

# --- CORPS PRINCIPAL ---
st.title("Salle de réunion - Planning de réservation")

view_date = st.date_input("Afficher la semaine du :", value=datetime.now().date())
start_week = view_date - timedelta(days=view_date.weekday())
week_days = [start_week + timedelta(days=i) for i in range(5)]

grid_data = {"Heure": [f"{h}:00" for h in HEURES_RANGE]}
for d in week_days:
    col_name = f"{JOURS_FR[d.weekday()]} {d.strftime('%d/%m')}"
    day_slots = []
    for h in HEURES_RANGE:
        match = st.session_state.bookings[
            (st.session_state.bookings['Date'] == d) & 
            (h >= st.session_state.bookings['Debut']) & 
            (h < st.session_state.bookings['Fin'])
        ]
        day_slots.append(f"🔴 {match.iloc[0]['Utilisateur']}" if not match.empty else "🟢 LIBRE")
    grid_data[col_name] = day_slots

df_display = pd.DataFrame(grid_data).set_index("Heure")

# On utilise map au lieu de applymap (déprécié dans les versions récentes de pandas)
st.table(df_display.style.map(lambda v: f"background-color: {'#f8d7da' if '🔴' in v else '#d4edda'}; color: black;"))

# --- EXPORTS ---
st.divider()
col1, col2 = st.columns(2)

with col1:
    output_excel = io.BytesIO()
    with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
        st.session_state.bookings.to_excel(writer, index=False, sheet_name='Reservations')
    
    st.download_button(
        label="📥 Exporter la base en Excel",
        data=output_excel.getvalue(),
        file_name=f"Réservation salle de réunion - semaine du {start_week.strftime('%Y%m%d')}.pdf",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

with col2:
    if st.button("📄 Préparer le PDF", use_container_width=True):
        pdf = WeeklyPDF()
        # On passe directement df_display à la génération du PDF
        pdf_output = pdf.generate_grid(start_week, df_display)
        
        st.download_button(
            label="Cliquez pour télécharger le PDF",
            data=bytes(pdf_output),
            file_name=f"Réservation salle de réunion - semaine du {start_week.strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
