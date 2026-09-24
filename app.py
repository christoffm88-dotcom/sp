from datetime import datetime
from io import BytesIO
import os
import threading
import time
from PIL import Image
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
GITHUB_REPO = "christoffm88-dotcom/sp"
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

def optimaliseer_foto(uploaded_file, max_breedte=600):
    """Verkleint en comprimeert foto's (speciaal geoptimaliseerd voor iPad/telefoon) naar max 600px."""
    try:
        img = Image.open(uploaded_file)
        
        try:
            for orientation in Image.ExifTags.TAGS.keys():
                if Image.ExifTags.TAGS[orientation] == 'Orientation':
                    break
            exif = img._getexif()
            if exif is not None:
                orientation = exif.get(orientation)
                if orientation == 3: img = img.rotate(180, expand=True)
                elif orientation == 6: img = img.rotate(270, expand=True)
                elif orientation == 8: img = img.rotate(90, expand=True)
        except Exception:
            pass

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        breedte, hoogte = img.size
        if breedte > max_breedte:
            nieuwe_hoogte = int(hoogte * (max_breedte / breedte))
            img = img.resize((max_breedte, nieuwe_hoogte), Image.Resampling.LANCZOS)
            
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=75)
        return buffer.getvalue()
    except Exception:
        uploaded_file.seek(0)
        return uploaded_file.read()

def sla_op_naar_github(df_to_save, commit_bericht):
    """Slaat het CSV-bestand direct op in GitHub met foutafhandeling."""
    token = get_github_token()
    df_to_save.to_csv(BESTAND_NAAM, index=False)
    
    if not token:
        return False, "⚠️ Geen GitHub Token gevonden. Data staat lokaal."
    
    try:
        g = Github(token, timeout=15)
        repo = g.get_repo(GITHUB_REPO)
        csv_inhoud = df_to_save.to_csv(index=False)
        
        try:
            file_item = repo.get_contents(BESTAND_NAAM)
            repo.update_file(path=BESTAND_NAAM, message=commit_bericht, content=csv_inhoud, sha=file_item.sha)
        except Exception:
            repo.create_file(path=BESTAND_NAAM, message=commit_bericht, content=csv_inhoud)
        return True, "✅ Opgeslagen en gepusht naar GitHub!"
    except Exception as e:
        return False, f"⚠️ Lokaal opgeslagen (GitHub sync mislukt: {e})"

def sla_foto_op_naar_github(bestands_inhoud, bestands_naam, commit_bericht):
    """Uploadt een foto naar GitHub met ingebouwde hertest (retry) voor betrouwbaarheid."""
    token = get_github_token()
    if not token:
        return False, "Geen token"
    
    for poging in range(3):
        try:
            g = Github(token, timeout=15)
            repo = g.get_repo(GITHUB_REPO)
            pad_in_repo = f"fotos/{bestands_naam}"
            
            try:
                file_item = repo.get_contents(pad_in_repo)
                repo.update_file(path=pad_in_repo, message=commit_bericht, content=bestands_inhoud, sha=file_item.sha)
            except Exception:
                repo.create_file(path=pad_in_repo, message=commit_bericht, content=bestands_inhoud)
            return True, "📸 Foto succesvol geüpload!"
        except Exception:
            if poging == 2:
                return False, "❌ Foto-upload mislukt na 3 pogingen."
            time.sleep(1)
    return False, "Onbekende fout"

def voeg_toe_aan_logboek(actie_type, artikel_nr, omschrijving_tekst, details=""):
    """Voegt een regel toe aan het logboek en pusht naar GitHub op de achtergrond."""
    token = get_github_token()
    huidige_tijd = datetime.now().strftime("%d-%m-%Y %H:%M")
    
    df_log = None
    if os.path.exists(LOG_BESTAND_NAAM):
        try:
            df_log = pd.read_csv(LOG_BESTAND_NAAM, sep=None, engine="python")
        except Exception:
            pass
                
    if df_log is None or df_log.empty:
        df_log = pd.DataFrame(columns=["Tijdstip", "Actie", "Artikel", "Omschrijving", "Details"])
        
    if "Details" not in df_log.columns:
        df_log["Details"] = ""

    nieuwe_log_rij = {
        "Tijdstip": huidige_tijd,
        "Actie": actie_type,
        "Artikel": str(artikel_nr),
        "Omschrijving": str(omschrijving_tekst),
        "Details": str(details)
    }
    
    df_log = pd.concat([df_log, pd.DataFrame([nieuwe_log_rij])], ignore_index=True)
    df_log.to_csv(LOG_BESTAND_NAAM, index=False)
    
    if token:
        try:
            g = Github(token, timeout=10)
            repo = g.get_repo(GITHUB_REPO)
            log_inhoud = df_log.to_csv(index=False)
            try:
                file_item = repo.get_contents(LOG_BESTAND_NAAM)
                repo.update_file(path=LOG_BESTAND_NAAM, message=f"Log: {actie_type}", content=log_inhoud, sha=file_item.sha)
            except Exception:
                repo.create_file(path=LOG_BESTAND_NAAM, message=f"Log aanmaken", content=log_inhoud)
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

# --- SLIMME DATA LADEN ---
@st.cache_data(ttl=30)
def laad_data_vanaf_github():
    try:
        url_raw = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{BESTAND_NAAM}?t={time.time()}"
        df_laad = pd.read_csv(url_raw, sep=None, engine="python")
        df_laad.to_csv(BESTAND_NAAM, index=False)
        return df_laad
    except Exception:
        if os.path.exists(BESTAND_NAAM):
            return pd.read_csv(BESTAND_NAAM, sep=None, engine="python")
        return pd.DataFrame(columns=kolommen_lijst)

df = laad_data_vanaf_github()
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

# --- ZIJKBALK & ADMIN LOGIN ---
st.sidebar.title("🔐 Beheer")
st.sidebar.markdown("---")

# DOWNLOAD KNOP NU BOVENAAN IN DE ZIJKBALK
st.sidebar.subheader("📥 Exporteren")
csv_data_sidebar = df.to_csv(index=False).encode('utf-8')
st.sidebar.download_button(
    label="📥 Download volledige lijst",
    data=csv_data_sidebar,
    file_name=f"gereedschap_export_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv",
    mime="text/csv",
    help="Download de inventarislijst direct naar je computer."
)

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
        gh_token_input = st.sidebar.text_input("Token", type="password", value=huidige_opgeslagen_token)
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

# --- SCHERM 1: ZOEKHEID & OVERZICHT ---
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
                lokale_pad = os.path.join("fotos", ruwe_bijlage)
                if os.path.exists(lokale_pad):
                    foto_pad = lokale_pad
                else:
                    foto_pad = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/fotos/{ruwe_bijlage}"

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
                    try:
                        if foto_pad:
                            st.image(foto_pad, use_container_width=True)
                        else:
                            st.markdown("*(Geen foto)*")
                    except Exception:
                        st.markdown("*(Kan foto niet laden)*")
                with c_info:
                    st.markdown(f"📍 **Ligging:** `{ligging_val}`")
                    if datum_val and str(datum_val).lower() != "nan": st.markdown(f"📅 **Datum:** {datum_val}")
                    if opm_val and str(opm_val).lower() != "nan": st.markdown(f"📝 **Opmerking:** {opm_val}")
                st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

# --- SCHERM 2: GEREEDSCHAP TOEVOEGEN ---
elif bewerk_rechten and beheer_actie == "➕ Gereedschap toevoegen":
    st.subheader("➕ Nieuw gereedschap toevoegen")
    st.markdown("---")
    
    foto = st.file_uploader("Bijlage (Foto)", type=["jpg", "png", "jpeg", "heic"], key="add_foto")

    with st.form("gereedschap_form"):
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
                st.error(f"❌ Dit artikelnummer ('{artikel_nummer}') bestaat al in de lijst!")
            else:
                foto_naam = ""
                if foto is not None:
                    foto_naam = f"art_{artikel_nummer.replace('/', '_')}.jpg"
                    geoptimaliseerde_bytes = optimaliseer_foto(foto)
                    
                    os.makedirs("fotos", exist_ok=True)
                    with open(os.path.join("fotos", foto_naam), "wb") as f:
                        f.write(geoptimaliseerde_bytes)
                        
                    f_succes, f_melding = sla_foto_op_naar_github(geoptimaliseerde_bytes, foto_naam, f"Upload foto art {artikel_nummer}")
                    if f_succes:
                        st.success(f_melding)
                    else:
                        st.warning(f_melding)

                huidige_datum = datetime.now().strftime("%d-%m-%Y %H:%M")
                nieuwe_rij = {
                    col_artikel: artikel_nummer,
                    col_omschrijving: omschrijving,
                    col_stock: stock,
                    col_ligging: ligging,
                    col_datum: huidige_datum,
                    col_groep: groep,
                    col_set: set_val_input,
                    col_bijlage: foto_naam,
                    col_opmerkingen: opmerkingen,
                }
                df = pd.concat([df, pd.DataFrame([nieuwe_rij])], ignore_index=True)

                succes, melding = sla_op_naar_github(df, f"Voeg artikel {artikel_nummer} toe")
                if succes:
                    details_str = f"Toegevoegd: {omschrijving} (Ligging: {ligging})"
                    voeg_toe_aan_logboek("Toegevoegd", artikel_nummer, omschrijving, details_str)
                    st.success(f"✨ Artikel '{artikel_nummer}' succesvol toegevoegd!")
                    st.cache_data.clear()
                else:
                    st.warning(melding)

# --- SCHERM 3: GEREEDSCHAP WIJZIGEN ---
elif bewerk_rechten and beheer_actie == "✏️ Gereedschap wijzigen":
    st.subheader("✏️ Bestaand gereedschap aanpassen")
    st.markdown("Typ hieronder een stukje van het artikelnummer of de omschrijving.")
    st.markdown("---")
    
    if len(df) > 0:
        zoek_bewerk = st.text_input("🔍 Zoek artikel om te wijzigen", key="zoek_bewerk_input")
        
        if zoek_bewerk:
            mask_b = False
            for c in df.columns:
                mask_b = mask_b | df[c].astype(str).str.contains(zoek_bewerk, case=False, na=False)
            df_bewerk_gevonden = df[mask_b]
            
            if len(df_bewerk_gevonden) > 0:
                bewerk_items_lijst = [
                    f"Art: {row.get(col_artikel, '')} - {row.get(col_omschrijving, '')} (Ligging: {row.get(col_ligging, '')}) - Rijnr: {i}"
                    for i, row in df_bewerk_gevonden.iterrows()
                ]
                gekozen_item_str = st.selectbox("Selecteer item", bewerk_items_lijst)
                rij_index = int(gekozen_item_str.split(" - Rijnr: ")[1])
                huidige_rij = df.loc[rij_index]

                b_nieuwe_foto = st.file_uploader("Nieuwe Foto (optioneel)", type=["jpg", "png", "jpeg", "heic"], key="edit_foto")

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
                    b_bijlage = st.text_input("Huidige Bijlage", value=str(huidige_rij.get(col_bijlage, "")))

                    bewerk_submit = st.form_submit_button(label="💾 Wijzigingen opslaan")

                    if bewerk_submit:
                        b_ligging = b_extra_ligging if b_ligging_keuze == "➕ Nieuwe ligging opgeven..." else (b_ligging_keuze if b_ligging_keuze != "-- Kies bestaande of typ hieronder --" else "")
                        
                        final_bijlage = b_bijlage
                        if b_nieuwe_foto is not None:
                            foto_naam = f"art_{b_artikel.replace('/', '_')}.jpg"
                            geoptimaliseerde_bytes = optimaliseer_foto(b_nieuwe_foto)
                            
                            os.makedirs("fotos", exist_ok=True)
                            with open(os.path.join("fotos", foto_naam), "wb") as f:
                                f.write(geoptimaliseerde_bytes)
                                
                            f_succes, f_melding = sla_foto_op_naar_github(geoptimaliseerde_bytes, foto_naam, f"Update foto art {b_artikel}")
                            if f_succes:
                                st.success(f_melding)
                            final_bijlage = foto_naam

                        wijzigingen_lijst = []
                        oud_oud = huidige_rij.to_dict()
                        nieuw_nieuw = {
                            col_artikel: b_artikel, col_omschrijving: b_omschrijving, col_stock: b_stock,
                            col_ligging: b_ligging, col_groep: b_groep, col_set: b_set, col_bijlage: final_bijlage, col_opmerkingen: b_opmerkingen
                        }
                        for k in nieuw_nieuw:
                            if str(oud_oud.get(k, "")) != str(nieuw_nieuw[k]):
                                wijzigingen_lijst.append(f"{k}: '{oud_oud.get(k, '')}' ➡️ '{nieuw_nieuw[k]}'")

                        df.loc[rij_index, col_artikel] = b_artikel
                        df.loc[rij_index, col_omschrijving] = b_omschrijving
                        df.loc[rij_index, col_stock] = b_stock
                        df.loc[rij_index, col_ligging] = b_ligging
                        df.loc[rij_index, col_datum] = datetime.now().strftime("%d-%m-%Y %H:%M")
                        df.loc[rij_index, col_groep] = b_groep
                        df.loc[rij_index, col_set] = b_set
                        df.loc[rij_index, col_bijlage] = final_bijlage
                        df.loc[rij_index, col_opmerkingen] = b_opmerkingen

                        succes, melding = sla_op_naar_github(df, f"Wijzig artikel {b_artikel}")
                        if succes:
                            details_str = " | ".join(wijzigingen_lijst) if wijzigingen_lijst else "Geen wijzigingen"
                            voeg_toe_aan_logboek("Gewijzigd", b_artikel, b_omschrijving, details_str)
                            st.success("✅ Wijzigingen opgeslagen!")
                            st.cache_data.clear()
                        else:
                            st.warning(melding)
    else:
        st.info("De lijst is leeg.")

# --- SCHERM 4: GEREEDSCHAP VERWIJDEREN ---
elif bewerk_rechten and beheer_actie == "🗑️ Gereedschap verwijderen":
    st.subheader("🗑️ Verwijder een item uit de lijst")
    st.markdown("---")
    
    if len(df) > 0:
        zoek_verwijder = st.text_input("🔍 Zoek artikel om te verwijderen", key="zoek_verwijder_input")
        
        if zoek_verwijder:
            mask_v = False
            for c in df.columns:
                mask_v = mask_v | df[c].astype(str).str.contains(zoek_verwijder, case=False, na=False)
            df_verwijder_gevonden = df[mask_v]
            
            if len(df_verwijder_gevonden) > 0:
                items_lijst = [
                    f"Art: {row.get(col_artikel, '')} - {row.get(col_omschrijving, '')} (Ligging: {row.get(col_ligging, '')}) - Rijnr: {i}"
                    for i, row in df_verwijder_gevonden.iterrows()
                ]
                te_verwijderen_item = st.selectbox("Selecteer item om te wissen", items_lijst, key="del_sel")
                
                rij_index = int(te_verwijderen_item.split(" - Rijnr: ")[1])
                verwijderd_art = str(df.loc[rij_index, col_artikel])
                verwijdeerde_omschrijving = str(df.loc[rij_index, col_omschrijving])

                with st.form("verwijder_form"):
                    st.warning(f"⚠️ Verwijderen: **{verwijderd_art} - {verwijdeerde_omschrijving}**")
                    bevestiging_tekst = st.text_input(f"Typ artikelnummer ter bevestiging ({verwijderd_art}):")
                    bevestig_verwijder = st.form_submit_button("❌ Definitief verwijderen", type="primary")

                    if bevestig_verwijder:
                        if bevestiging_tekst.strip() != verwijderd_art.strip():
                            st.error("❌ Artikelnummer komt niet overeen.")
                        else:
                            df = df.drop(rij_index).reset_index(drop=True)
                            succes, melding = sla_op_naar_github(df, f"Verwijder item {verwijdeerde_omschrijving}")
                            if succes:
                                voeg_toe_aan_logboek("Verwijderd", verwijderd_art, verwijdeerde_omschrijving, "Item gewist")
                                st.success("🗑️ Artikel verwijderd!")
                                st.cache_data.clear()
                            else:
                                st.warning(melding)
    else:
        st.info("De lijst is leeg.")

# --- SCHERM 5: LOGBOEK BEKIJKEN ---
elif bewerk_rechten and beheer_actie == "📋 Logboek bekijken":
    st.subheader("📋 Wijzigingenlogboek")
    st.markdown("---")
    
    try:
        url_log_get = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{LOG_BESTAND_NAAM}?t={time.time()}"
        df_log_weergave = pd.read_csv(url_log_get, sep=None, engine="python")
    except Exception:
        df_log_weergave = pd.read_csv(LOG_BESTAND_NAAM, sep=None, engine="python") if os.path.exists(LOG_BESTAND_NAAM) else None
            
    if df_log_weergave is not None and not df_log_weergave.empty:
        st.dataframe(df_log_weergave.iloc[::-1].reset_index(drop=True), use_container_width=True)
    else:
        st.info("Geen logboekhistorie beschikbaar.")
     
