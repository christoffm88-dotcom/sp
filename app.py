from datetime import datetime
import os
import threading
import time
import requests
import pandas as pd
import streamlit as st
from github import Github, GithubException

# --- ANTI-SLAAPSTAND ACHTERGROND SCRIPT ---
def hou_app_wakker():
    """Stuurt periodiek een verzoek naar de eigen app om te zorgen dat deze wakker blijft."""
    # Haal de app URL op als deze bekend is, of gebruik een standaard mechanisme
    app_url = os.getenv("STREAMLIT_APP_URL", "")
    if not app_url:
        return
    
    while True:
        try:
            requests.get(app_url, timeout=10)
        except Exception:
            pass
        # Elke 10 minuten (600 seconden) een signaal sturen
        time.sleep(600)

# Start de achtergrond-thread eenmalig als deze nog niet draait
if "ping_thread_gestart" not in st.session_state:
    st.session_state["ping_thread_gestart"] = True
    t = threading.Thread(target=hou_app_wakker, daemon=True)
    t.start()


# --- CONFIGURATIE & HULPFUNCTIES VOOR GITHUB ---
GITHUB_REPO = "https://github.com/christoffm88-dotcom/sp"  # <-- Pas dit aan naar jouw GitHub repository (bijv. 'jan/gereedschap-app')
BESTAND_NAAM = "gereedschap.csv"

def sla_op_naar_github(df_to_save, commit_bericht):
    """Slaat het CSV-bestand automatisch op in GitHub met een API-token en haalt altijd de juiste SHA op."""
    token = st.session_state.get("github_token", "") or os.getenv("GITHUB_TOKEN", "")
    if not token:
        df_to_save.to_csv(BESTAND_NAAM, index=False)
        return False, "Geen GitHub Token ingevuld. Data is alleen lokaal opgeslagen."
    
    try:
        g = Github(token)
        repo = g.get_repo(GITHUB_REPO)
        csv_inhoud = df_to_save.to_csv(index=False)
        
        sha = None
        try:
            # Probeer altijd eerst de actuele SHA van het bestand op GitHub op te halen
            file_item = repo.get_contents(BESTAND_NAAM)
            sha = file_item.sha
        except Exception:
            pass # Als het bestand nog niet bestaat, is sha gewoon None
            
        if sha:
            # Als het bestand al bestaat op GitHub, voer een update uit met de SHA
            repo.update_file(
                path=BESTAND_NAAM,
                message=commit_bericht,
                content=csv_inhoud,
                sha=sha
            )
        else:
            # Als het bestand nog helemaal niet bestaat, maak het nieuw aan
            repo.create_file(
                path=BESTAND_NAAM,
                message=commit_bericht,
                content=csv_inhoud
            )
            
        return True, "Succesvol opgeslagen en gepusht naar GitHub!"
    except Exception as e:
        df_to_save.to_csv(BESTAND_NAAM, index=False)
        return False, f"Fout bij verbinden met GitHub: {e}. Data is lokaal opgeslagen."vuld. Data is alleen lokaal opgeslagen. Vul je token in via de zijkant om automatisch naar GitHub te pushen."
    
    try:
        g = Github(token)
        repo = g.get_repo(GITHUB_REPO)
        csv_inhoud = df_to_save.to_csv(index=False)
        
        try:
            # Probeer het bestaande bestand op te halen om de SHA te krijgen (nodig voor update)
            file_item = repo.get_contents(BESTAND_NAAM)
            repo.update_file(
                path=BESTAND_NAAM,
                message=commit_bericht,
                content=csv_inhoud,
                sha=file_item.sha
            )
        except Exception:
            # Als het bestand nog niet bestaat, maak het aan
            repo.create_file(
                path=BESTAND_NAAM,
                message=commit_bericht,
                content=csv_inhoud
            )
        return True, "Succesvol opgeslagen en gepusht naar GitHub!"
    except Exception as e:
        # Fallback naar lokaal opslaan
        df_to_save.to_csv(BESTAND_NAAM, index=False)
        return False, f"Fout bij verbinden met GitHub: {e}. Data is lokaal opgeslagen."


# Pagina instellingen
st.set_page_config(
    page_title="Gereedschap Beheer", page_icon="🛠️", layout="wide"
)

# Custom CSS voor een strakke weergave
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
beheer_actie = "🔍 Zoeken & Overzicht"

if admin_mode:
  wachtwoord = st.sidebar.text_input("Voer wachtwoord in", type="password")
  if wachtwoord == "gereedschap123":
    bewerk_rechten = True
    st.sidebar.success("✅ Ingelogd als beheerder")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ GitHub Instellingen")
    # Veld om de GitHub Token op te slaan in de sessie
    gh_token_input = st.sidebar.text_input("GitHub Personal Access Token", type="password", value=st.session_state.get("github_token", ""))
    if gh_token_input:
        st.session_state["github_token"] = gh_token_input
        st.sidebar.success("Token opgeslagen voor deze sessie!")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚡ Snelkoppelingen")
    beheer_actie = st.sidebar.radio(
        "Kies een actie:",
        [
            "🔍 Zoeken & Overzicht",
            "➕ Gereedschap toevoegen",
            "✏️ Gereedschap wijzigen",
            "🗑️ Gereedschap verwijderen",
        ],
    )
  else:
    st.sidebar.error("❌ Onjuist wachtwoord")

st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **Tip:** Zonder inlog kun je de lijst direct bekijken en doorzoeken."
)

# --- HOOFDSCHERM ---
st.title("🛠️ Gereedschap & Locatie Beheer")

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

# Probeer het bestand in te lezen (lokaal of direct proberen te downloaden van GitHub als het lokaal mist)
if not os.path.exists(BESTAND_NAAM):
  try:
    # Probeer te downloaden vanuit de publieke github link als fallback
    url_raw = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{BESTAND_NAAM}"
    df = pd.read_csv(url_raw, sep=None, engine="python")
    df.to_csv(BESTAND_NAAM, index=False)
  except Exception:
    df = pd.DataFrame(columns=kolommen_lijst)

if os.path.exists(BESTAND_NAAM):
  try:
    df = pd.read_csv(BESTAND_NAAM, sep=None, engine="python")
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

  bestaane_liggingen_lijst = sorted(df[col_ligging].dropna().astype(str).unique().tolist())
  bestaane_liggingen_lijst = [l for l in bestaane_liggingen_lijst if l.strip() and l.lower() != "nan"]
  opties_ligging = ["-- Kies bestaande of typ hieronder --"] + bestaane_liggingen_lijst + ["➕ Nieuwe ligging opgeven..."]

  # --- SCHERM 1: ZOEKHEID & OVERZICHT ---
  if not bewerk_rechten or beheer_actie == "🔍 Zoeken & Overzicht":
    st.markdown("Welkom! Zoek en filter hieronder in de inventaris.")
    st.markdown("---")
    st.subheader("🔍 Zoeken & Filteren")

    zoekterm = st.text_input(
        "Vrij zoeken (artikelnummer, omschrijving, opmerking...)",
        placeholder="Bijv. C511 of Accuboormachine...",
    )

    with st.expander("🎯 Geavanceerde filters (Groep, Set, Ligging)"):
      f_col1, f_col2, f_col3 = st.columns(3)
      
      unieke_groepen = ["Alle"] + sorted([str(x) for x in df[col_groep].dropna().unique() if str(x).strip() and str(x).lower() != "nan"])
      unieke_sets = ["Alle"] + sorted([str(x) for x in df[col_set].dropna().unique() if str(x).strip() and str(x).lower() != "nan"])
      unieke_liggingen = ["Alle"] + sorted([str(x) for x in df[col_ligging].dropna().unique() if str(x).strip() and str(x).lower() != "nan"])

      with f_col1:
        gekozen_groep = st.selectbox("Filter op Groep", unieke_groepen)
      with f_col2:
        gekozen_set = st.selectbox("Filter op Set", unieke_sets)
      with f_col3:
        gekozen_ligging = st.selectbox("Filter op Ligging", unieke_liggingen)

    df_gefilterd = df.copy()

    if zoekterm:
      mask = False
      for c in df_gefilterd.columns:
        mask = mask | df_gefilterd[c].astype(str).str.contains(zoekterm, case=False, na=False)
      df_gefilterd = df_gefilterd[mask]

    if gekozen_groep != "Alle":
      df_gefilterd = df_gefilterd[df_gefilterd[col_groep].astype(str) == gekozen_groep]

    if gekozen_set != "Alle":
      df_gefilterd = df_gefilterd[df_gefilterd[col_set].astype(str) == gekozen_set]

    if gekozen_ligging != "Alle":
      df_gefilterd = df_gefilterd[df_gefilterd[col_ligging].astype(str) == gekozen_ligging]

    st.markdown(f"**Aantal resultaten gevonden:** {len(df_gefilterd)}")
    st.markdown("---")

    if len(df_gefilterd) == 0:
      st.info("Geen gereedschap gevonden dat aan je zoekopdracht/filters voldoet.")
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

  # --- SCHERM 2: GEREEDSCHAP TOEVOEGEN ---
  elif bewerk_rechten and beheer_actie == "➕ Gereedschap toevoegen":
    st.subheader("➕ Nieuw gereedschap toevoegen")
    st.markdown("---")
    
    with st.form("gereedschap_form", clear_on_submit=True):
      c1, c2 = st.columns(2)
      with c1:
        artikel_nummer = st.text_input("Artikel Nummer *")
        stock = st.text_input("Stock", value="1")
        groep = st.text_input("Groep")
      with c2:
        omschrijving = st.text_input("Omschrijving *")
        set_val_input = st.text_input("Set")

      keuze_ligging = st.selectbox("Ligging selecteren *", opties_ligging, key="add_ligging")
      extra_nieuwe_ligging = ""
      if keuze_ligging == "➕ Nieuwe ligging opgeven...":
        extra_nieuwe_ligging = st.text_input("Geef de nieuwe ligging op *", key="add_new_lig")

      opmerkingen = st.text_area("Opmerkingen")
      foto = st.file_uploader(
          "Bijlage (Foto)", type=["jpg", "png", "jpeg"], key="add_foto"
      )

      submit_button = st.form_submit_button(label="💾 Opslaan en direct naar GitHub")

      if submit_button:
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

          # Opslaan en automatisch naar GitHub pushen
          succes, melding = sla_op_naar_github(df, f"Voeg artikel {artikel_nummer} toe")
          if succes:
              st.success(f"✨ Artikel '{artikel_nummer} - {omschrijving}' is toegevoegd en automatisch opgeslagen op GitHub!")
          else:
              st.warning(melding)

  # --- SCHERM 3: GEREEDSCHAP WIJZIGEN ---
  elif bewerk_rechten and beheer_actie == "✏️ Gereedschap wijzigen":
    st.subheader("✏️ Bestaand gereedschap aanpassen")
    st.markdown("---")
    
    if len(df) > 0:
      bewerk_items_lijst = [
          f"Art: {row.get(col_artikel, '')} - {row.get(col_omschrijving, '')} (Ligging: {row.get(col_ligging, '')}) - Rijnr: {i}"
          for i, row in df.iterrows()
      ]
      gekozen_item_str = st.selectbox(
          "Selecteer het gereedschap om te wijzigen", bewerk_items_lijst
      )
      rij_index = int(gekozen_item_str.split(" - Rijnr: ")[1])
      huidige_rij = df.loc[rij_index]

      with st.form("bewerk_form"):
        bc1, bc2 = st.columns(2)
        with bc1:
          b_artikel = st.text_input("Artikel Nummer *", value=str(huidige_rij.get(col_artikel, "")))
          b_stock = st.text_input("Stock", value=str(huidige_rij.get(col_stock, "")))
          b_groep = st.text_input("Groep", value=str(huidige_rij.get(col_groep, "")))
        with bc2:
          b_omschrijving = st.text_input("Omschrijving *", value=str(huidige_rij.get(col_omschrijving, "")))
          b_set = st.text_input("Set", value=str(huidige_rij.get(col_set, "")))

        huidige_ligging_val = str(huidige_rij.get(col_ligging, ""))
        b_ligging_keuze = st.selectbox(
            "Ligging selecteren *", 
            opties_ligging, 
            index=opties_ligging.index(huidige_ligging_val) if huidige_ligging_val in opties_ligging else 0,
            key="edit_ligging"
        )
        b_extra_ligging = ""
        if b_ligging_keuze == "➕ Nieuwe ligging opgeven...":
          b_extra_ligging = st.text_input("Geef de nieuwe ligging op *", key="edit_new_lig")

        b_opmerkingen = st.text_area("Opmerkingen", value=str(huidige_rij.get(col_opmerkingen, "")))
        b_bijlage = st.text_input("Huidige Bijlage / Foto", value=str(huidige_rij.get(col_bijlage, "")))
        
        b_nieuwe_foto = st.file_uploader(
            "Nieuwe Bijlage (Foto uploaden ter vervanging)", type=["jpg", "png", "jpeg"], key="edit_foto"
        )

        bewerk_submit = st.form_submit_button(label="💾 Wijzigingen opslaan naar GitHub")

        if bewerk_submit:
          if b_ligging_keuze == "➕ Nieuwe ligging opgeven...":
            b_ligging = b_extra_ligging
          elif b_ligging_keuze == "-- Kies bestaande of typ hieronder --":
            b_ligging = ""
          else:
            b_ligging = b_ligging_keuze

          if not b_artikel or not b_omschrijving or not b_ligging:
            st.error("⚠️ Artikel Nummer, Omschrijving en Ligging mogen niet leeg zijn!")
          else:
            final_bijlage = b_bijlage
            if b_nieuwe_foto is not None:
              foto_pad = os.path.join("fotos", b_nieuwe_foto.name)
              with open(foto_pad, "wb") as f:
                f.write(b_nieuwe_foto.getbuffer())
              final_bijlage = b_nieuwe_foto.name

            wijzig_datum = datetime.now().strftime("%d-%m-%Y %H:%M")

            df.loc[rij_index, col_artikel] = b_artikel
            df.loc[rij_index, col_omschrijving] = b_omschrijving
            df.loc[rij_index, col_stock] = b_stock
            df.loc[rij_index, col_ligging] = b_ligging
            df.loc[rij_index, col_datum] = wijzig_datum
            df.loc[rij_index, col_groep] = b_groep
            df.loc[rij_index, col_set] = b_set
            df.loc[rij_index, col_bijlage] = final_bijlage
            df.loc[rij_index, col_opmerkingen] = b_opmerkingen

            succes, melding = sla_op_naar_github(df, f"Wijzig artikel {b_artikel}")
            if succes:
                st.success(f"✅ Wijzigingen opgeslagen en automatisch gepusht naar GitHub!")
            else:
                st.warning(melding)
    else:
      st.info("De lijst is leeg, er valt niets te wijzigen.")

  # --- SCHERM 4: GEREEDSCHAP VERWIJDEREN ---
  elif bewerk_rechten and beheer_actie == "🗑️ Gereedschap verwijderen":
    st.subheader("🗑️ Verwijder een item uit de lijst")
    st.markdown("---")
    
    if len(df) > 0:
      items_lijst = [
          f"Art: {row.get(col_artikel, '')} - {row.get(col_omschrijving, '')} (Ligging: {row.get(col_ligging, '')}) - Rijnr: {i}"
          for i, row in df.iterrows()
      ]
      te_verwijderen_item = st.selectbox(
          "Selecteer het gereedschap om te wissen", items_lijst, key="del_sel"
      )

      if st.button("❌ Verwijder geselecteerd gereedschap", type="primary"):
        rij_index = int(te_verwijderen_item.split(" - Rijnr: ")[1])
        verwijderde_omschrijving = df.loc[rij_index, col_omschrijving]
        df = df.drop(rij_index).reset_index(drop=True)

        succes, melding = sla_op_naar_github(df, f"Verwijder item {verwijderde_omschrijving}")
        if succes:
            st.success(f"🗑️ '{verwijderde_omschrijving}' is verwijderd en de wijziging is op GitHub verwerkt!")
        else:
            st.warning(melding)
        st.rerun()
    else:
      st.info("De lijst is momenteel leeg.")

else:
  st.error(
      "⚠️ Het bestand 'gereedschap.csv' kon niet worden gevonden. "
      "Zorg dat je repository gekoppeld is en dat de naam van de repository klopt in de code."
  )
