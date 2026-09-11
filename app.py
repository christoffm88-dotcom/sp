from datetime import datetime
import os
from io import BytesIO
import pandas as pd
import streamlit as st

# Pagina instellingen
st.set_page_config(
    page_title="Gereedschap Beheer", page_icon="🛠️", layout="wide"
)

# Custom CSS voor een nettere visuele stijl
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

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
  if wachtwoord == "gereedschap123":
    bewerk_rechten = True
    st.sidebar.success("✅ Ingelogd als beheerder")
  else:
    st.sidebar.error("❌ Onjuist wachtwoord")

st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **Tip:** Zonder inlog kun je de lijst direct bekijken en doorzoeken."
)

# --- HOOFDSCHERM ---
st.title("🛠️ Gereedschap & Locatie Beheer")
st.markdown("Welkom! Zoek hieronder direct naar gereedschap en zie waar het ligt.")

# Automatisch het bestand inlezen dat in GitHub staat
bestand_naam = "gereedschap.csv"

if os.path.exists(bestand_naam):
  df = pd.read_csv(bestand_naam)

  # Zorg dat de basiskolommen bestaan (inclusief Datum toegevoegd)
  for col in ["Naam", "Categorie", "Ligging", "Datum toegevoegd", "Foto"]:
    if col not in df.columns:
      df[col] = ""

  # --- ZOEKBALK EN OVERZICHT ---
  st.markdown("---")
  st.subheader("🔍 Zoeken in de inventaris")

  col_zoek, col_filter = st.columns([2, 1])
  with col_zoek:
    zoekterm = st.text_input(
        "Zoek op naam, categorie of ligging...",
        placeholder="Bijv. Accuboormachine of Stelling 2...",
    )
  with col_filter:
    unieke_cat = ["Alle"] + list(df["Categorie"].dropna().unique())
    geselecteerde_cat = st.selectbox("Filter op categorie", unieke_cat)

  # Filter logica toepassen
  df_gefilterd = df.copy()

  if zoekterm:
    mask = (
        df_gefilterd["Naam"]
        .astype(str)
        .str.contains(zoekterm, case=False, na=False)
        | df_gefilterd["Categorie"]
        .astype(str)
        .str.contains(zoekterm, case=False, na=False)
        | df_gefilterd["Ligging"]
        .astype(str)
        .str.contains(zoekterm, case=False, na=False)
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

      submit_button = st.form_submit_button(label="💾 Gereedschap opslaan")

      if submit_button:
        if not naam or not ligging:
          st.error("⚠️ Vul ten minste de naam en de ligging in!")
        else:
          foto_pad = ""
          if foto is not None:
            foto_pad = os.path.join("fotos", foto.name)
            with open(foto_pad, "wb") as f:
              f.write(foto.getbuffer())

          # Huidige datum en tijd ophalen
          huidige_datum = datetime.now().strftime("%d-%m-%Y %H:%M")

          nieuwe_rij = {
              "Naam": naam,
              "Categorie": categorie,
              "Ligging": ligging,
              "Datum toegevoegd": huidige_datum,
              "Foto": foto_pad,
          }
          df = pd.concat([df, pd.DataFrame([nieuwe_rij])], ignore_index=True)

          # Sla het direct op in de map
          df.to_csv(bestand_naam, index=False)
          st.success(
              f"✨ '{naam}' is toegevoegd op {huidige_datum}! Download hieronder"
              " het bestand en zet het in GitHub om het online te bewaren."
          )

    # --- DOWNLOAD KNOP VOOR ADMIN ---
    st.markdown("---")
    st.subheader("📥 Bestand bijwerken op GitHub")
    st.markdown(
        "Omdat je wijzigingen hebt gemaakt, kun je hier de nieuwe versie"
        " downloaden en even slepen naar je GitHub repository ter vervanging"
        " van de oude."
    )

    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download bijgewerkte gereedschap.csv",
        data=csv_data,
        file_name="gereedschap.csv",
        mime="text/csv",
    )
  else:
    st.markdown("---")
    st.info(
        "🔒 *Wil je gereedschap toevoegen? Log dan in via de zijbalk met het"
        " beheerderswachtwoord.*"
    )

else:
  st.error(
      "⚠️ Het bestand 'gereedschap.csv' is nog niet gevonden in de GitHub map."
      " Upload dit bestand in je repository om de lijst te laden."
  )
