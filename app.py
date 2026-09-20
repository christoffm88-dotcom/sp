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

kolommen_lijst = [
    "Artikel Nummer",
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
    df.columns = df.columns.str.strip()
  except Exception as e:
    df = pd.DataFrame(columns=kolommen_lijst)

  kolommen = list(df.columns)
  col_artikel = "Artikel Nummer" if "Artikel Nummer" in kolommen else (kolommen[0] if len(kolommen) > 0 else "Artikel Nummer")
  col_omschrijving = "Omschrijving" if "Omschrijving" in kolommen else (kolommen[1] if len(kolommen) > 1 else "Omschrijving")
  col_stock = "Stock" if "Stock" in kolommen else (kolommen[2] if len(kolommen) > 2 else "Stock")
  col_ligging = "Ligging" if "Ligging" in kolommen else (kolommen[3] if len(kolommen) > 3 else "Ligging")
  col_datum = "Datum" if "Datum" in kolommen else (kolommen[4] if len(kolommen) > 4 else "Datum")
  col_groep = "Groep" if "Groep" in kolommen else (kolommen[5] if len(kolommen) > 5 else "Groep")
  col_set = "Set" if "Set" in kolommen else (kolommen[6] if len(kolommen) > 6 else "Set")
  col_bijlage = "Bijlage" if "Bijlage" in kolommen else (kolommen[7] if len(kolommen) > 7 else "Bijlage")
  col_opmerkingen = "Opmerkingen" if "Opmerkingen" in kolommen else (kolommen[8] if len(kolommen) > 8 else "Opmerkingen")

  for c in [col_artikel, col_omschrijving, col_stock, col_ligging, col_datum, col_groep, col_set, col_bijlage, col_opmerkingen]:
    if c not in df.columns:
      df[c] = ""

  # --- ZOEKBALK EN OVERZICHT ---
  st.markdown("---")
  st.subheader("🔍 Zoeken in de inventaris")

  zoekterm = st.text_input(
      "Zoek op artikelnummer, omschrijving, ligging, groep of set...",
      placeholder="Bijv. C511 of Accuboormachine...",
  )

  df_gefilterd = df.copy()

  if zoekterm:
    mask = False
    for c in df_gefilterd.columns:
      mask = mask | df_gefilterd[c].astype(str).str.contains(zoekterm, case=False, na=False)
    df_gefilterd = df_gefilterd[mask]

  st.markdown(f"**Aantal resultaten gevonden:** {len(df_gefilterd)}")
  st.markdown("---")

  # --- KAARTWEERGAVE VOOR SMARTPHONE ---
  if len(df_gefilterd) == 0:
    st.info("Geen gereedschap gevonden dat aan je zoekopdracht voldoet.")
  else:
    for i, row in df_gefilterd.iterrows():
      art_val = row.get(col_artikel, "-")
      oms_val = row.get(col_omschrijving, "-")
      groep_val = row.get(col_groep, "-")
      set_val = row.get(col_set, "-")
      stock_val = row.get(col_stock, "-")
      ligging_val = row.get(col_ligging, "-")
      datum_val = row.get(col_datum, "")
      opm_val = row.get(col_opmerkingen, "")
      
      ruwe_bijlage = str(row.get(col_bijlage, "")).strip()
      foto_pad = ""
      if ruwe_bijlage and ruwe_bijlage.lower() != "nan":
        mogelijke_paden = [
            ruwe_bijlage,
            os.path.join("fotos", ruwe_bijlage),
            os.path.join("fotos", os.path.basename(ruwe_bijlage))
        ]
        for p in mogelijke_paden:
          if os.path.exists(p):
            foto_pad = p
            break

      with st.container():
        st.markdown(
            f"""
                <div class="tool-card">
                    <span style="background-color: #ff4b4b; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">Art: {art_val}</span>
                    <h3 style="margin: 8px 0 0 0; color: #31333F;">{oms_val}</h3>
                    <p style="margin: 5px 0 0 0; color: #6c757d; font-size: 13px;">
                        <b>Groep:</b> {groep_val} | <b>Set:</b> {set_val} | <b>Stock:</b> {stock_val}
                    </p>
                </div>
                """,
            unsafe_allow_html=True,
        )

        c_img, c_info = st.columns([1, 2])
        with c_img:
          if foto_pad and os.path.exists(foto_pad):
            st.image(foto_pad, use_container_width=True)
          else:
            st.markdown(f"*(Geen foto gevonden)*")

        with c_info:
          st.markdown(f"📍 **Ligging:** `{ligging_val}`")
          if datum_val and str(datum_val).lower() != "nan":
            st.markdown(f"📅 **Datum:** {datum_val}")
          if opm_val and str(opm_val).lower() != "nan":
            st.markdown(f"📝 **Opmerking:** {opm_val}")

        st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

  # --- ADMIN GEDEELTE (Alleen zichtbaar na inloggen) ---
  if bewerk_rechten:
    st.markdown("---")
    st.header("➕ Beheerderspaneel")

    tab1, tab2 = st.tabs(
        ["➕ Gereedschap toevoegen", "🗑️ Gereedschap verwijderen"]
    )

    with tab1:
      # Bepaal unieke, gesorteerde lijst van bestaande liggingen voor de keuzelijst (+ optie voor een nieuwe)
      bestaande_liggingen = sorted(df[col_ligging].dropna().astype(str).unique().tolist())
      bestaande_liggingen = [l for l in bestaande_liggingen if l.strip() and l.lower() != "nan"]
      
      opties_ligging = ["-- Kies bestaande of typ hieronder --"] + bestaande_liggingen + ["➕ Nieuwe ligging opgeven..."]

      with st.form("gereedschap_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
          artikel_nummer = st.text_input("Artikel Nummer *")
          stock = st.text_input("Stock", value="1")
          groep = st.text_input("Groep")
        with c2:
          omschrijving = st.text_input("Omschrijving *")
          set_val_input = st.text_input("Set")

        # Keuzelijst voor liggingen
        keuze_ligging = st.selectbox("Ligging selecteren *", opties_ligging)
        
        # Als de gebruiker kiest om een nieuwe ligging op te geven, tonen we een extra invoerveld
        extra_nieuwe_ligging = ""
        if keuze_ligging == "➕ Nieuwe ligging opgeven...":
          extra_nieuwe_ligging = st.text_input("Geef de nieuwe ligging op *")

        opmerkingen = st.text_area("Opmerkingen")
        foto = st.file_uploader(
            "Bijlage (Foto)", type=["jpg", "png", "jpeg"]
        )

        submit_button = st.form_submit_button(label="💾 Opslaan in inventaris")

        if submit_button:
          # Bepaal de definitieve ligging op basis van de geselecteerde optie
          if keuze_ligging == "➕ Nieuwe ligging opgeven...":
            ligging = extra_nieuwe_ligging
          elif keuze_ligging == "-- Kies bestaande of typ hieronder --":
            ligging = ""
          else:
            ligging = keuze_ligging

          if not artikel_nummer or not omschrijving or not ligging:
            st.error("⚠️ Vul ten minste Artikel Nummer, Omschrijving en een geldige Ligging in!")
          else:
            foto_pad = ""
            if foto is not None:
              foto_pad = os.path.join("fotos", foto.name)
              with open(foto_pad, "wb") as f:
                f.write(foto.getbuffer())

            huidige_datum = datetime.now().strftime("%d-%m-%Y %H:%M")

            nieuwe_rij = {
                col_artikel: artikel_nummer,
                col_omschrijving: omschrijving,
                col_stock: stock,
                col_ligging: ligging,
                col_datum: huidige_datum,
                col_groep: groep,
                col_set: set_val_input,
                col_bijlage: foto.name if foto else "",
                col_opmerkingen: opmerkingen,
            }
            df = pd.concat([df, pd.DataFrame([nieuwe_rij])], ignore_index=True)

            df.to_csv(bestand_naam, index=False)
            st.success(
                f"✨ Artikel '{artikel_nummer} - {omschrijving}' is toegevoegd!"
                " Download hieronder het bestand en zet het in GitHub."
            )

    with tab2:
      st.subheader("Verwijder een item uit de lijst")
      if len(df) > 0:
        items_lijst = [
            f"Art: {row.get(col_artikel, '')} - {row.get(col_omschrijving, '')} (Ligging: {row.get(col_ligging, '')}) - Rijnr: {i}"
            for i, row in df.iterrows()
        ]
        te_verwijderen_item = st.selectbox(
            "Selecteer het gereedschap om te wissen", items_lijst
        )

        if st.button(
            "❌ Verwijder geselecteerd gereedschap", type="primary"
        ):
          rij_index = int(te_verwijderen_item.split(" - Rijnr: ")[1])
          verwijderde_omschrijving = df.loc[rij_index, col_omschrijving]
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
      " Zorg dat je jouw CSV-bestand uploadt naar je repository."
  )
