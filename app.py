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
    app_url = os.getenv("STREAMLIT_APP_URL", "")
    if not app_url:
        return
    
    while True:
        try:
            requests.get(app_url, timeout=10)
        except Exception:
            pass
        time.sleep(600)

if "ping_thread_gestart" not in st.session_state:
    st.session_state["ping_thread_gestart"] = True
    t = threading.Thread(target=hou_app_wakker, daemon=True)
    t.start()


# --- CONFIGURATIE & TOKEN BEHEER ---
GITHUB_REPO = "christoffm88-dotcom/sp"  # <-- PAS DIT AAN (bijv. 'jan/gereedschap-app')
BESTAND_NAAM = "gereedschap.csv"
LOG_BESTAND_NAAM = "logboek.csv"

def get_github_token():
    """Haalt de token op uit sessie, Streamlit secrets of omgevingsvariabelen."""
    if "github_token" in st.session_state and st.session_state["github_token"]:
        return st.session_state["github_token"]
    try:
        if "GITHUB_TOKEN" in st.secrets:
            return st.secrets["GITHUB_TOKEN"]
    except Exception:
        pass
    return os.getenv("GITHUB_TOKEN", "")

def sla_op_naar_github(df_to_save, commit_bericht):
    """Slaat het CSV-bestand direct op in GitHub."""
    token = get_github_token()
    df_to_save.to_csv(BESTAND_NAAM, index=False)
    
    if not token:
        return False, "⚠️ Geen GitHub Token gevonden. Voeg hem eenmalig toe via Streamlit Secrets of de zijbalk."
    
    try:
        g = Github(token)
        repo = g.get_repo(GITHUB_REPO)
        csv_inhoud = df_to_save.to_csv(index=False)
        
        try:
            file_item = repo.get_contents(BESTAND_NAAM)
            repo.update_file(path=BESTAND_NAAM, message=commit_bericht, content=csv_inhoud, sha=file_item.sha)
        except Exception:
            repo.create_file(path=BESTAND_NAAM, message=commit_bericht, content=csv_inhoud)
        return True, "✅ Succesvol opgeslagen en veilig vastgelegd in GitHub!"
    except Exception as e:
        return False, f"❌ Fout bij verbinden met GitHub: {e}."

def voeg_toe_aan_logboek(actie_type, artikel_nr, omschrijving_tekst):
    """Voegt een regel toe aan het logboek en slaat dit op naar GitHub."""
    token = get_github_token()
    huidige_tijd = datetime.now().strftime("%d-%m-%Y %H:%M")
    
    # Haal bestaand logboek op of maak een nieuwe
    df_log = None
    try:
        url_log = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{LOG_BESTAND_NAAM}?t={time.time()}"
        df_log = pd.read_csv(url_log, sep=None, engine="python")
    except Exception:
        if os.path.exists(LOG_BESTAND_NAAM):
            try:
                df_log = pd.read_csv(LOG_BESTAND_NAAM, sep=None, engine="python")
            except Exception:
                pass
                
    if df_log is None or df_log.empty:
        df_log = pd.DataFrame(columns=["Tijdstip", "Actie", "Artikel", "Omschrijving"])
        
    nieuwe_log_rij = {
        "Tijdstip": huidige_tijd,
        "Actie": actie_type,
        "Artikel": str(artikel_nr),
        "Omschrijving": str(omschrijving_tekst)
    }
    
    df_log = pd.concat([df_log, pd.DataFrame([nieuwe_log_rij])], ignore_index=True)
    df_log.to_csv(LOG_BESTAND_NAAM, index=False)
    
    if token:
        try:
            g = Github(token)
            repo = g.get_repo(GITHUB_REPO)
            log_inhoud = df_log.to_csv(index=False)
            try:
                file_item = repo.get_contents(LOG_BESTAND_NAAM)
                repo.update_file(path=LOG_BESTAND_NAAM, message=f"Logboek update: {actie_type} - {artikel_nr}", content=log_inhoud, sha=file_item.sha)
            except Exception:
                repo.create_file(path=LOG_BESTAND_NAAM, message=f"Logboek aanmaken: {actie_type} - {artikel_nr}", content=log_inhoud)
        except Exception:
            pass


# Pagina instellingen
st.set_page_config(page_title="Gereedschap Beheer", page_icon="🛠️", layout="wide")

st.markdown(
    """
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; font-weight: bold; }
    .tool-card {
        background-color: white; padding: 15px; border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 15px;
        border-left: 5px solid #ff4b4b;
    }
    </style>
""",
    unsafe_allow_html=True,
)

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
        st.sidebar.markdown("### ⚙️ GitHub Token")
        huidige_opgeslagen_token = get_github_token()
        gh_token_input = st.sidebar.text_input("Token (optioneel als Secrets ingesteld)", type="password", value=huidige_opgeslagen_token)
        if gh_token_input:
            st.session_state["github_token"] = gh_token_input

        st.sidebar.markdown("---")
        st.sidebar.markdown("### ⚡ Snelkoppelingen")
        beheer_actie = st.sidebar.radio(
            "Kies een actie:",
            [
                "🔍 Zoeken & Overzicht",
                "➕ Gereedschap toevoegen",
                "✏️ Gereedschap wijzigen",
                "🗑️ Gereedschap verwijderen",
                "📋 Logboek bekijken",
            ],
        )
    else:
        st.sidebar.error("❌ Onjuist wachtwoord")

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Zonder inlog kun je de lijst direct bekijken.")

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

# --- ROBUUSTE DATA LADEN ---
df = None
try:
    url_raw = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{BESTAND_NAAM}?t={time.time()}"
    df = pd.read_csv(url_raw, sep=None, engine="python")
    df.to_csv(BESTAND_NAAM, index=False)
except Exception:
    if os.path.exists(BESTAND_NAAM):
        try:
            df = pd.read_csv(BESTAND_NAAM, sep=None, engine="python")
        except Exception:
            pass

if df is None or df.empty:
    df = pd.DataFrame(columns=kolommen_lijst)

df.columns = df.columns.str.strip()

kolommen = list(df.columns)
col_artikel = "Artikel Nummer" if "Artikel Nummer" in kolommen else kolommen[0]
col_omschrijving = "Omschrijving" if "Omschrijving" in kolommen else kolommen[1]
col_stock = "Stock" if "Stock" in kolommen else kolommen[2]
col_ligging = "Ligging" if "Ligging" in kolommen else kolommen[3]
col_datum = "Datum" if "Datum" in kolommen else kolommen[4]
col_groep = "Groep" if "Groep" in kolommen else kolommen[5]
col_set = "Set" if "Set" in kolommen else kolommen[6]
col_bijlage = "Bijlage" if "Bijlage" in kolommen else kolommen[7]
col_opmerkingen = "Opmerkingen" if "Opmerkingen" in kolommen else kolommen[8]

for c in [col_artikel, col_omschrijving, col_stock, col_ligging, col_datum, col_groep, col_set, col_bijlage, col_opmerkingen]:
    if c not in df.columns:
        df[c] = ""

bestaane_liggingen_lijst = sorted(df[col_ligging].dropna().astype(str).unique().tolist())
bestaane_liggingen_lijst = [l for l in bestaane_liggingen_lijst if l.strip() and l.lower() != "nan"]
opties_ligging = ["-- Kies bestaande of typ hieronder --"] + bestaane_liggingen_lijst + ["➕ Nieuwe ligging opgeven..."]

# --- SCHERM 1: ZOEKHEID & OVERZICHT ---
# --- DOWNLOAD KNOP VOOR DE LIJST ---
    st.markdown("---")
    st.subheader("📥 Lijst exporteren")
    
    # Converteer de huidige dataframe naar CSV formaat
    csv_data = df_gefilterd.to_csv(index=False).encode('utf-8')
    
    st.download_button(
        label="📥 Download huidige lijst als CSV",
        data=csv_data,
        file_name=f"gereedschap_export_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv",
        mime="text/csv",
        help="Download de getoonde lijst direct naar je computer."
    )
if not bewerk_rechten or beheer_actie == "🔍 Zoeken & Overzicht":
    st.markdown("Welkom! Zoek en filter hieronder in de inventaris.")
    st.markdown("---")
    st.subheader("🔍 Zoeken & Filteren")

    zoekterm = st.text_input("Vrij zoeken (artikelnummer, omschrijving, opmerking...)")

    with st.expander("🎯 Geavanceerde filters (Groep, Set, Ligging)"):
        f_col1, f_col2, f_col3 = st.columns(3)
        unieke_groepen = ["Alle"] + sorted([str(x) for x in df[col_groep].dropna().unique() if str(x).strip() and str(x).lower() != "nan"])
        unieke_sets = ["Alle"] + sorted([str(x) for x in df[col_set].dropna().unique() if str(x).strip() and str(x).lower() != "nan"])
        unieke_liggingen = ["Alle"] + sorted([str(x) for x in df[col_ligging].dropna().unique() if str(x).strip() and str(x).lower() != "nan"])

        with f_col1: gekozen_groep = st.selectbox("Filter op Groep", unieke_groepen)
        with f_col2: gekozen_set = st.selectbox("Filter op Set", unieke_sets)
        with f_col3: gekozen_ligging = st.selectbox("Filter op Ligging", unieke_liggingen)

    df_gefilterd = df.copy()
    if zoekterm:
        mask = False
        for c in df_gefilterd.columns:
            mask = mask | df_gefilterd[c].astype(str).str.contains(zoekterm, case=False, na=False)
        df_gefilterd = df_gefilterd[mask]

    if gekozen_groep != "Alle": df_gefilterd = df_gefilterd[df_gefilterd[col_groep].astype(str) == gekozen_groep]
    if gekozen_set != "Alle": df_gefilterd = df_gefilterd[df_gefilterd[col_set].astype(str) == gekozen_set]
    if gekozen_ligging != "Alle": df_gefilterd = df_gefilterd[df_gefilterd[col_ligging].astype(str) == gekozen_ligging]

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
                for p in [ruwe_bijlage, os.path.join("fotos", ruwe_bijlage), os.path.join("fotos", os.path.basename(ruwe_bijlage))]:
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
                        st.markdown("*(Geen foto)*")
                with c_info:
                    st.markdown(f"📍 **Ligging:** `{ligging_val}`")
                    if datum_val and str(datum_val).lower() != "nan": st.markdown(f"📅 **Datum:** {datum_val}")
                    if opm_val and str(opm_val).lower() != "nan": st.markdown(f"📝 **Opmerking:** {opm_val}")
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
        foto = st.file_uploader("Bijlage (Foto)", type=["jpg", "png", "jpeg"], key="add_foto")

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
            elif artikel_nummer in df[col_artikel].astype(str).values:
                st.error(f"❌ Dit artikelnummer ('{artikel_nummer}') bestaat al in de lijst! Dubbele records zijn niet toegestaan.")
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

                succes, melding = sla_op_naar_github(df, f"Voeg artikel {artikel_nummer} toe")
                if succes:
                    voeg_toe_aan_logboek("Toegevoegd", artikel_nummer, omschrijving)
                    st.success(f"✨ Artikel '{artikel_nummer} - {omschrijving}' is toegevoegd en opgeslagen op GitHub!")
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
        gekozen_item_str = st.selectbox("Selecteer het gereedschap om te wijzigen", bewerk_items_lijst)
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
                "Ligging selecteren *", opties_ligging, 
                index=opties_ligging.index(huidige_ligging_val) if huidige_ligging_val in opties_ligging else 0,
                key="edit_ligging"
            )
            b_extra_ligging = ""
            if b_ligging_keuze == "➕ Nieuwe ligging opgeven...":
                b_extra_ligging = st.text_input("Geef de nieuwe ligging op *", key="edit_new_lig")

            b_opmerkingen = st.text_area("Opmerkingen", value=str(huidige_rij.get(col_opmerkingen, "")))
            b_bijlage = st.text_input("Huidige Bijlage / Foto", value=str(huidige_rij.get(col_bijlage, "")))
            b_nieuwe_foto = st.file_uploader("Nieuwe Bijlage (Foto uploaden ter vervanging)", type=["jpg", "png", "jpeg"], key="edit_foto")

            bewerk_submit = st.form_submit_button(label="💾 Wijzigingen opslaan naar GitHub")

            if bewerk_submit:
                if b_ligging_keuze == "➕ Nieuwe ligging opgeven...":
                    b_ligging = b_extra_ligging
                elif b_ligging_keuze == "-- Kies bestaande of typ hieronder --":
                    b_ligging = ""
                else:
                    b_ligging = b_ligging_keuze

                ander_df = df.drop(rij_index)
                if not b_artikel or not b_omschrijving or not b_ligging:
                    st.error("⚠️ Artikel Nummer, Omschrijving en Ligging mogen niet leeg zijn!")
                elif b_artikel in ander_df[col_artikel].astype(str).values:
                    st.error(f"❌ Artikelnummer '{b_artikel}' bestaat al bij een ander item!")
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
                        voeg_toe_aan_logboek("Gewijzigd", b_artikel, b_omschrijving)
                        st.success("✅ Wijzigingen opgeslagen en gepusht naar GitHub!")
                    else:
                        st.warning(melding)
    else:
        st.info("De lijst is leeg.")

# --- SCHERM 4: GEREEDSCHAP VERWIJDEREN ---
elif bewerk_rechten and beheer_actie == "🗑️ Gereedschap verwijderen":
    st.subheader("🗑️ Verwijder een item uit de lijst")
    st.markdown("---")
    
    if len(df) > 0:
        items_lijst = [
            f"Art: {row.get(col_artikel, '')} - {row.get(col_omschrijving, '')} (Ligging: {row.get(col_ligging, '')}) - Rijnr: {i}"
            for i, row in df.iterrows()
        ]
        te_verwijderen_item = st.selectbox("Selecteer het gereedschap om te wissen", items_lijst, key="del_sel")

        if st.button("❌ Verwijder geselecteerd gereedschap", type="primary"):
            rij_index = int(te_verwijderen_item.split(" - Rijnr: ")[1])
            verwijderd_art = df.loc[rij_index, col_artikel]
            verwijderde_omschrijving = df.loc[rij_index, col_omschrijving]
            df = df.drop(rij_index).reset_index(drop=True)

            succes, melding = sla_op_naar_github(df, f"Verwijder item {verwijderde_omschrijving}")
            if succes:
                voeg_toe_aan_logboek("Verwijderd", verwijderd_art, verwijderde_omschrijving)
                st.success(f"🗑️ '{verwijderde_omschrijving}' is verwijderd en verwerkt op GitHub!")
            else:
                st.warning(melding)
            st.rerun()
    else:
        st.info("De lijst is momenteel leeg.")

# --- SCHERM 5: LOGBOEK BEKIJKEN ---
elif bewerk_rechten and beheer_actie == "📋 Logboek bekijken":
    st.subheader("📋 Wijzigingenlogboek")
    st.markdown("Hier zie je een overzicht van alle handelingen die zijn verricht (toegevoegd, gewijzigd, verwijderd).")
    st.markdown("---")
    
    df_log_weergave = None
    try:
        url_log_get = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{LOG_BESTAND_NAAM}?t={time.time()}"
        df_log_weergave = pd.read_csv(url_log_get, sep=None, engine="python")
    except Exception:
        if os.path.exists(LOG_BESTAND_NAAM):
            df_log_weergave = pd.read_csv(LOG_BESTAND_NAAM, sep=None, engine="python")
            
    if df_log_weergave is not None and not df_log_weergave.empty:
        # Omgekeerde volgorde zodat de meest recente actie bovenaan staat
        df_log_weergave = df_log_weergave.iloc[::-1].reset_index(drop=True)
        st.dataframe(df_log_weergave, use_container_width=True)
    else:
        st.info("Er is nog geen logboekhistorie beschikbaar.")
