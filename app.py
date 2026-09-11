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
st.markdown("Welkom! Zoek hieronder direct naar gereedschap en zie waar het ligt.")

# Automatisch het bestand inlezen
bestand_naam = "gereedschap.csv"

if os.path.exists(bestand_naam):
  try:
    df = pd.read_csv(bestand_naam, sep=None, engine="python")
  except Exception as e:
    df = pd.DataFrame(columns=["Naam", "Ligging", "Datum toegevoegd", "Foto"])

  # Zorg dat de basiskolommen altijd bestaan (zonder categorie)
  for col in ["Naam", "Ligging", "Datum toegevoegd", "Foto"]:
    if col not in df.columns:
      df[col] = ""

  # --- ZOEKBALK EN OVERZICHT ---
  st.markdown("---")
  st.subheader("🔍 Zoeken in de inventaris")

  zoekterm = st.text_input(
      "Zoek op naam of ligging...",
      placeholder="Bijv. Accuboormachine of Kast 1...",
  )

  # Filter logica toepassen
  df_gefilterd = df.copy()

  if zoekterm:
    mask = df_gefilterd["Naam"].astype(str).str.contains(
        zoekterm, case=False, na=False
    ) | df_gefilterd["Ligging"].astype(str).str.contains(
        zoekterm, case=False, na=False
    )
    df_gefilterd = df_gefilterd[mask]

  st.markdown(f"**Aantal resultaten gevonden:** {len(df_gefilterd)}")
  st.markdown("---")

  # --- MOBIELAAGTROUWE KAARTWEERGAVE ---
  if len(df_gefilterd) == 0:
    st.info("Geen gereedschap gevonden dat aan je zoekopdracht voldoet.")
  else:
    for i, row in df_gefilterd.iterrows():
      with st.container():
        st.markdown(
            f"""
                <div class="tool-card">
                    <h3 style="margin: 0; color: #31333F;">{row['Naam']}</h3>
                    <p style="margin: 5px 0 0 0; color: #6c757d; font-size: 14px;"><b>Toegevoegd:</b> {row.get('Datum toegevoegd', 'Onbekend')}</p>
                </div>
                """,
            unsafe_allow_html=True,
        )

        c_img, c_info = st.columns([1, 2])
        with c_img:
          foto_pad = str(row.get("Foto", ""))
          if foto_pad and os.path.exists(foto_pad):
            st.image(foto_pad, use_container_width=True)
          else:
            st.markdown("*(Geen foto)*")

        with c_info:
          st.markdown(f"📍 **Ligging:** `{row['Ligging']}`")

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
        naam = st.text_input("Naam gereedschap *")
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

            huidige_datum = datetime.now().strftime("%d-%m-%Y %H:%M")

            nieuwe_rij = {
                "Naam": naam,
                "Ligging": ligging,
                "Datum toegevoegd": huidige_datum,
                "Foto": foto_pad,
            }
            df = pd.concat([df, pd.DataFrame([nieuwe_rij])], ignore_index=True)

            df.to_csv(bestand_naam, index=False)
            st.success(
                f"✨ '{naam}' is toegevoegd! Download hieronder het bestand en"
                " zet het in GitHub."
            )

    with tab2:
      st.subheader("Verwijder een item uit de lijst")
      if len(df) > 0:
        items_lijst = [
            f"{row['Naam']} (Ligging: {row['Ligging']}) - Rijnr: {i}"
            for i, row in df.iterrows()
        ]
        te_verwijderen_item = st.selectbox(
            "Selecteer het gereedschap om te wissen", items_lijst
        )

        if st.button(
            "❌ Verwijder geselecteerd gereedschap", type="primary"
        ):
          rij_index = int(te_verwijderen_item.split(" - Rijnr: ")[1])
          verwijderde_naam = df.loc[rij_index, "Naam"]
          df = df.drop(rij_index).reset_index(drop=True)

          df.to_csv(bestand_naam, index=False)
          st.success(
              f"🗑️ '{verwijderde_naam}' is verwijderd! Download het"
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
      " Upload het bestand in je repository om de lijst te laden."
  )
