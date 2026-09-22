import streamlit as st
import pandas as pd
import os
from github import Github

# --- CONFIGURATIE ---
GITHUB_REPO = "christoffm88-dotcom/sp"  # Jouw GitHub repository
BESTAND_NAAM = "gereedschap.csv"       # Naam van het CSV-bestand in GitHub

st.set_page_config(page_title="Gereedschapsbeheer", layout="wide")

# --- FUNCTIE VOOR GITHUB SYNCHRONISATIE ---
def laad_data_van_github():
    """Laadt het CSV-bestand direct vanuit GitHub, of lokaal als fallback."""
    token = st.session_state.get("github_token", "") or os.getenv("GITHUB_TOKEN", "")
    try:
        if token:
            g = Github(token)
            repo = g.get_repo(GITHUB_REPO)
            file_content = repo.get_contents(BESTAND_NAAM)
            decoded_content = file_content.decoded_content.decode("utf-8")
            from io import StringIO
            return pd.read_csv(StringIO(decoded_content))
        else:
            # Probeer lokaal te laden als er geen token is
            if os.path.exists(BESTAND_NAAM):
                return pd.read_csv(BESTAND_NAAM)
    except Exception:
        pass
    
    # Fallback: standaard DataFrame als er niets is
    if os.path.exists(BESTAND_NAAM):
        return pd.read_csv(BESTAND_NAAM)
    else:
        # Maak een leeg basisbestand aan als het helemaal niet bestaat
        df_init = pd.DataFrame(columns=["ID", "Naam", "Categorie", "Aantal", "Locatie"])
        df_init.to_csv(BESTAND_NAAM, index=False)
        return df_init

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
        return False, f"Fout bij verbinden met GitHub: {e}. Data is lokaal opgeslagen."

# --- ZIJKANT (SIDEBAR) VOOR BEHEER & TOKEN ---
st.sidebar.title("Instellingen & Login")

if "ingelogd" not in st.session_state:
    st.session_state["ingelogd"] = False

if not st.session_state["ingelogd"]:
    wachtwoord = st.sidebar.text_input("Beheerderswachtwoord", type="password")
    if st.sidebar.button("Inloggen"):
        if wachtwoord == "Gereedschap123vanmossel":  # Pas dit aan naar wens
            st.session_state["ingelogd"] = True
            st.sidebar.success("Ingelogd als beheerder!")
            st.rerun()
        else:
            st.sidebar.error("Onjuist wachtwoord")
else:
    st.sidebar.success("Je bent ingelogd als beheerder.")
    
    # Veld voor GitHub Token
    huidige_token = st.session_state.get("github_token", "")
    ingevoerde_token = st.sidebar.text_input("GitHub Personal Access Token", value=huidige_token, type="password")
    if ingevoerde_token:
        st.session_state["github_token"] = ingevoerde_token
        st.sidebar.info("Token opgeslagen voor deze sessie.")

    if st.sidebar.button("Uitloggen"):
        st.session_state["ingelogd"] = False
        st.rerun()

# --- HOOFDSCHERM APP ---
st.title("🛠️ Gereedschapsbeheer Werkplaats")

# Data inladen
df = laad_data_van_github()

# Weergave van de tabel
st.subheader("Huidige Gereedschapsvoorraad")
st.dataframe(df, use_container_width=True)

# Alleen beheerders mogen toevoegen/wijzigen/verwijderen
if st.session_state["ingelogd"]:
    st.markdown("---")
    st.subheader("Beheer: Gereedschap Toevoegen of Bewerken")
    
    tab1, tab2 = st.tabs(["Nieuw toevoegen", "Bestaand bewerken/verwijderen"])
    
    with tab1:
        with st.form("nieuw_formulier"):
            nieuwe_naam = st.text_input("Naam gereedschap")
            nieuwe_cat = st.text_input("Categorie")
            nieuw_aantal = st.number_input("Aantal", min_value=1, value=1, step=1)
            nieuwe_loc = st.text_input("Locatie in werkplaats")
            
            submit_nieuw = st.form_submit_button("Toevoegen aan systeem")
            
            if submit_nieuw:
                if nieuwe_naam:
                    nieuw_id = int(df["ID"].max() + 1) if not df.empty and "ID" in df.columns and pd.notna(df["ID"].max()) else 1
                    nieuw_item = pd.DataFrame([{"ID": nieuw_id, "Naam": nieuwe_naam, "Categorie": nieuwe_cat, "Aantal": nieuw_aantal, "Locatie": nieuwe_loc}])
                    df = pd.concat([df, nieuw_item], ignore_index=True)
                    
                    succes, melding = sla_op_naar_github(df, f"Nieuw item toegevoegd: {nieuwe_naam}")
                    if succes:
                        st.success(melding)
                    else:
                        st.warning(melding)
                    st.rerun()
                else:
                    st.error("Vul ten minste de naam van het gereedschap in.")

    with tab2:
        if not df.empty:
            geselecteerd_item = st.selectbox("Kies gereedschap om te bewerken of verwijderen", df["Naam"].tolist())
            item_rij = df[df["Naam"] == geselecteerd_item].iloc[0]
            
            with st.form("bewerk_formulier"):
                bewerk_naam = st.text_input("Naam", value=item_rij["Naam"])
                bewerk_cat = st.text_input("Categorie", value=item_rij["Categorie"])
                bewerk_aantal = st.number_input("Aantal", min_value=0, value=int(item_rij["Aantal"]), step=1)
                bewerk_loc = st.text_input("Locatie", value=item_rij["Locatie"])
                
                col1, col2 = st.columns(2)
                with col1:
                    submit_wijzig = st.form_submit_button("Wijzigingen opslaan")
                with col2:
                    submit_verwijder = st.form_submit_button("Item verwijderen")
                
                if submit_wijzig:
                    df.loc[df["Naam"] == geselecteerd_item, ["Naam", "Categorie", "Aantal", "Locatie"]] = [bewerk_naam, bewerk_cat, bewerk_aantal, bewerk_loc]
                    succes, melding = sla_op_naar_github(df, f"Item gewijzigd: {bewerk_naam}")
                    if succes:
                        st.success(melding)
                    else:
                        st.warning(melding)
                    st.rerun()
                
                if submit_verwijder:
                    df = df[df["Naam"] != geselecteerd_item]
                    succes, melding = sla_op_naar_github(df, f"Item verwijderd: {geselecteerd_item}")
                    if succes:
                        st.success(melding)
                    else:
                        st.warning(melding)
                    st.rerun()
        else:
            st.info("Geen items beschikbaar om te bewerken.")
else:
    st.info("💡 Log in via de zijkant met het beheerderswachtwoord om gereedschap toe te voegen, te wijzigen of te verwijderen.")
