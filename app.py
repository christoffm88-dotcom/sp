from datetime import datetime
import os
from io import BytesIO
import pandas as pd
import streamlit as st

# Pagina instellingen
st.set_page_config(
    page_title="Gereedschap Beheer", page_icon="🛠️", layout="wide"
)

# Custom CSS voor een strakke mobiele weergave
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
    .tool-card {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        border-left: 5px solid #ff4b4b;
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
st.markdown("Welkom! Zoek hieronder direct in de inventaris.")

# Automatisch het bestand inlezen
bestand_naam = "gereedschap.csv"

# Verwachte kolommen uit jouw Excel
kolommen_lijst = [
    "Artikel Nu",
    "Omschrijving",
    "Stock",
    "Ligging",
    "Datum",
    "Groep",
    "Set",
    "Bijlage",
    "Opmerkingen",
]

if os.path.exists(bestand_naam):
  try:
    df = pd.read_csv(bestand_naam, sep=None, engine="python")
  except Exception as e:
    df = pd.DataFrame(columns=kolommen_lijst)

  # Zorg dat alle kolommen altijd bestaan
  for col in kolommen_lijst:
    if col not in df.columns:
      df[col] = ""

  # --- ZOEKBALK EN OVERZICHT ---
  st.markdown("---")
  st.subheader("🔍 Zoeken in de inventaris")

  zoekterm = st.text_input(
      "Zoek op artikelnummer, omschrijving, ligging, groep of set...",
      placeholder="Bijv. C511 of Accuboormachine...",
  )

  # Filter logica toepassen over meerdere kolommen
  df_gefilterd = df.copy()

  if zoekterm:
    mask = (
        df_gefilterd["Artikel Nu"].astype(str).str.contains(zoekterm, case=False, na=False)
        | df_gefilterd["Omschrijving"].astype(str).str.contains(zoekterm, case=False, na=False)
        | df_gefilterd["Ligging"].astype(str).str.contains(zoekterm, case=False, na=False)
        | df_gefilterd["Groep"].astype(str).str.contains(zoekterm, case=False, na=False)
        | df_gefilterd["Set"].astype(str).str.contains(zoekterm, case=False, na=False)
        | df_gefilterd["Opmerkingen"].astype(str).str.contains(zoekterm, case=False, na=False)
    )
    df_gefilterd = df_gefilterd[mask]

  st.markdown(f"**Aantal resultaten gevonden:** {len(df_gefilterd)}")
  st.markdown("---")

  # --- KAARTWEERGAVE VOOR SMARTPHONE ---
  if len(df_gefilterd) == 0:
    st.info("Geen gereedschap gevonden dat aan je zoekopdracht voldoet.")
  else:
    for i, row in df_gefilterd.iterrows():
      with st.container():
        st.markdown(
            f"""
                <div class="tool-card">
                    <span style="background-color: #ff4b4b; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">Art: {row['Artikel Nu']}</span>
                    <h3 style="margin: 8px 0 0 0; color: #31333F;">{row['Omschrijving']}</h3>
                    <p style="margin: 5px 0 0 0; color: #6c757d; font-size: 13px;">
                        <b>Groep:</b> {row.get('Groep', '-')} | <b>Set:</b> {row.get('Set', '-')} | <b>Stock:</b> {row.get('Stock', '-')}
                    </p>
                </div>
                """,
            unsafe_allow_html=True,
        )

        c_img, c_info = st.columns([1, 2])
        with c_img:
          foto_pad = str(row.get("Bijlage", ""))
          if foto_pad and os.path.exists(foto_pad):
            st.image(foto_pad, use_container_width=True)
          else:
            st.markdown("*(Geen foto)*")

        with c_info:
          st.markdown(f"📍 **Ligging:** `{row['Ligging']}`")
          if row.get("Datum"):
            st.markdown(f"📅 **Datum:** {row['Datum']}")
          if row.get("Opmerkingen"):
            st.markdown(f"📝 **Opmerking:** {row['Opmerkingen']}")

        st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

  # --- ADMIN GEDEELTE (Alleen zichtbaar na inloggen) ---
  if bewerk_rechten:
    st.markdown("---")
    st.header("➕ Beheerderspaneel")

    tab1, tab2 = st.tabs(
        ["➕ Gereedschap toevoegen", "🗑️ Gereedschap verwijderen"]
    )

    with tab1:
      with st.form("gereedschap_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
          artikel_nu = st.text_input("Artikel Nu *")
          stock = st.text_input("Stock", value="1")
          groep = st.text_input("Groep")
        with c2:
          omschrijving = st.text_input("Omschrijving *")
          ligging = st.text_input("Ligging *", placeholder="Bijv. SCA 10")
          set_val = st.text_input("Set")

        opmerkingen = st.text_area("Opmerkingen")
        foto = st.file_uploader(
            "Bijlage (Foto)", type=["jpg", "png", "jpeg"]
        )

        submit_button = st.form_submit_button(label="💾 Opslaan in inventaris")

        if submit_button:
          if not artikel_nu or not omschrijving or not ligging:
            st.error("⚠️ Vul ten minste Artikel Nu, Omschrijving en Ligging in!")
          else:
            foto_pad = ""
            if foto is not None:
              foto_pad = os.path.join("fotos", foto.name)
              with open(foto_pad, "wb") as f:
                f.write(foto.getbuffer())

            huidige_datum = datetime.now().strftime("%d-%m-%Y %H:%M")

            nieuwe_rij = {
                "Artikel Nu": artikel_nu,
                "Omschrijving": omschrijving,
                "Stock": stock,
                "Ligging": ligging,
                "Datum": huidige_datum,
                "Groep": groep,
                "Set": set_val,
                "Bijlage": foto_pad,
                "Opmerkingen": opmerkingen,
            }
            df = pd.concat([df, pd.DataFrame([nieuwe_rij])], ignore_index=True)

            df.to_csv(bestand_naam, index=False)
            st.success(
                f"✨ Artikel '{artikel_nu} - {omschrijving}' is toegevoegd!"
                " Download hieronder het bestand en zet het in GitHub."
            )

    with tab2:
      st.subheader("Verwijder een item uit de lijst")
      if len(df) > 0:
        items_lijst = [
            f"Art: {row['Artikel Nu']} - {row['Omschrijving']} (Ligging: {row['Ligging']}) - Rijnr: {i}"
            for i, row in df.iterrows()
        ]
        te_verwijderen_item = st.selectbox(
            "Selecteer het gereedschap om te wissen", items_lijst
        )

        if st.button(
            "❌ Verwijder geselecteerd gereedschap", type="primary"
        ):
          rij_index = int(te_verwijderen_item.split(" - Rijnr: ")[1])
          verwijderde_omschrijving = df.loc[rij_index, "Omschrijving"]
          df = df.drop(rij_index).reset_index(drop=True)

          df.to_csv(bestand_naam, index=False)
          st.success(
              f"🗑️ '{verwijderde_omschrijving}' is verwijderd! Download het"
              " bijgewerkte bestand hieronder om het vast te leggen op GitHub."
          )
          st.rerun()
      else:
        st.info("De lijst is momenteel leeg.")

    # --- DOWNLOAD KNOP VOOR ADMIN ---
    st.markdown("---")
    st.subheader("📥 Bestand bijwerken op GitHub")
    st.markdown(
        "Nadat je hebt toegevoegd of verwijderd, kun je hier de nieuwe versie"
        " downloaden en slepen naar je GitHub repository ter vervanging van de"
        " oude."
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
        "🔒 *Wil je gereedschap toevoegen of verwijderen? Log dan in via de"
        " zijbalk met het beheerderswachtwoord.*"
    )

else:
  st.error(
      "⚠️ Het bestand 'gereedschap.csv' is nog niet gevonden in de GitHub map."
      " Zorg dat je jouw CSV-bestand met deze exacte kolommen uploadt naar je"
      " repository."
  )
