import os
from io import BytesIO
import pandas as pd
import streamlit as st

# Pagina instellingen (breed scherm, mooie titel)
st.set_page_config(
    page_title="Gereedschap Beheer", page_icon="🛠️", layout="wide"
)

# Custom CSS voor een nettere visuele stijl
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Map aanmaken om foto's op te slaan
if not os.path.exists("fotos"):
    os.makedirs("fotos")

# --- ZIJKBALK & ADMIN LOGIN ---
st.sidebar.title("🔐 Beheer")
st.sidebar.markdown("---")
admin_mode = st.sidebar.checkbox("Inloggen als Beheerder")

bewerk_rechten = False
if admin_mode:
    wachtwoord = st.sidebar.text_input("Voer wachtwoord in", type="password")
    # Pas hieronder je wachtwoord aan:
    if wachtwoord == "gereedschap123":
        bewerk_rechten = True
        st.sidebar.success("✅ Ingelogd als beheerder")
    else:
        st.sidebar.error("❌ Onjuist wachtwoord")

st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **Tip:** Zonder inlog kun je de lijst alleen bekijken en doorzoeken."
)

# --- HOOFDSCHERM ---
st.title("🛠️ Gereedschap & Locatie Beheer")
st.markdown(
    "Welkom! Zoek snel naar gereedschap en zie direct waar het ligt."
)

# 1. Bestaande data inlezen
uploaded_file = st.file_uploader(
    "📂 Upload hier je huidige Excel- of CSV-bestand", type=["xlsx", "csv"]
)

if uploaded_file is not None:
    # Inlezen
    if uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
    else:
        df = pd.read_csv(uploaded_file)

    # Zorg dat de basiskolommen bestaan
    for col in ["Naam", "Categorie", "Ligging", "Foto"]:
        if col not in df.columns:
            df[col] = ""

    # --- ZOEKBALK EN OVERZICHT (Voor iedereen zichtbaar) ---
    st.markdown("---")
    st.subheader("🔍 Zoeken in de inventaris")
    
    col_zoek, col_filter = st.columns([2, 1])
    with col_zoek:
        zoekterm = st.text_input(
            "Zoek op naam, categorie of ligging...",
            placeholder="Bijv. Accuboormachine of Stelling 2...",
        )
    with col_filter:
        # Filter op categorie als optie
        unieke_cat = ["Alle"] + list(df["Categorie"].dropna().unique())
        geselecteerde_cat = st.selectbox("Filter op categorie", unieke_cat)

    # Filter logica toepassen
    df_gefilterd = df.copy()
    
    if zoekterm:
        mask = (
            df_gefilterd["Naam"].astype(str).str.contains(zoekterm, case=False, na=False)
            | df_gefilterd["Categorie"].astype(str).str.contains(zoekterm, case=False, na=False)
            | df_gefilterd["Ligging"].astype(str).str.contains(zoekterm, case=False, na=False)
        )
        df_gefilterd = df_gefilterd[mask]

    if geselecteerde_cat != "Alle":
        df_gefilterd = df_gefilterd[df_gefilterd["Categorie"] == geselecteerde_cat]

    # Visuele weergave van de tabel
    st.markdown(f"**Aantal resultaten gevonden:** {len(df_gefilterd)}")
    st.dataframe(df_gefilterd, use_container_width=True, height=350)

    # --- ADMIN GEDEELTE (Alleen zichtbaar na inloggen) ---
    if bewerk_rechten:
        st.markdown("---")
        st.header("➕ Beheerderspaneel: Nieuw gereedschap toevoegen")

        with st.form("gereedschap_form", clear_on_submit=True):
            c1, c2 = st.columns(2)

            with c1:
                naam = st.text_input("Naam gereedschap *")
                categorie = st.selectbox(
                    "Categorie",
                    [
                        "Handgereedschap",
                        "Elektrisch gereedschap",
                        "Meetgereedschap",
                        "Luchtgereedschap",
                        "Overig",
                    ],
                )

            with c2:
                ligging = st.text_input(
                    "Ligging (Waar ligt het?) *",
                    placeholder="Bijv. Bus 3, Kast B, Plank 1",
                )
                foto = st.file_uploader(
                    "Maak of upload foto", type=["jpg", "png", "jpeg"]
                )

            submit_button = st.form_submit_button(
                label="💾 Gereedschap opslaan"
            )

            if submit_button:
                if not naam or not ligging:
                    st.error("⚠️ Vul ten minste de naam en de ligging in!")
                else:
                    foto_pad = ""
                    if foto is not None:
                        foto_pad = os.path.join("fotos", foto.name)
                        with open(foto_pad, "wb") as f:
                            f.write(foto.getbuffer())

                    # Rij toevoegen
                    nieuwe_rij = {
                        "Naam": naam,
                        "Categorie": categorie,
                        "Ligging": ligging,
                        "Foto": foto_pad,
                    }
                    df = pd.concat([df, pd.DataFrame([nieuwe_rij])], ignore_index=True)
                    st.success(f"✨ '{naam}' is succesvol toegevoegd!")

        # --- DOWNLOAD KNOPPEN VOOR ADMIN ---
        st.markdown("---")
        st.subheader("📥 Gegevens exporteren")
        st.markdown("Download het bijgewerkte bestand om je wijzigingen te bewaren.")

        d1, d2 = st.columns(2)
        with d1:
            csv_data = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download als CSV",
                data=csv_data,
                file_name="gereedschap_lijst.csv",
                mime="text/csv",
            )

        with d2:
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Gereedschap")
            excel_data = output.getvalue()

            st.download_button(
                label="📥 Download als Excel (.xlsx)",
                data=excel_data,
                file_name="gereedschap_lijst.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    else:
        st.markdown("---")
        st.info("🔒 *Wil je gereedschap toevoegen of de lijst downloaden? Log dan in via de zijbalk.*")

else:
    st.warning("👉 Upload om te beginnen je Excel- of CSV-bestand hierboven in de app.")
