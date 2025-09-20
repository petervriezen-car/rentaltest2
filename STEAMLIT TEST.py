import os
import io
import sys
import subprocess
from datetime import datetime

import pandas as pd
import streamlit as st

# =============================================================
# Configuratie
# =============================================================
# Lokale (gesynchroniseerde) Dropbox-map als fallback / lokaal gebruik
LOCAL_DATA_DIR = r"C:\Users\Peterv\LEEUWEN TRUCKS & VAN Dropbox\PRJ Vriezen\Test streamlit"
LOCAL_CSV_PATH = os.path.join(LOCAL_DATA_DIR, "autos.csv")

# Secrets / env toggle
# - In Streamlit (Cloud of lokaal) kun je .streamlit/secrets.toml gebruiken.
USE_DROPBOX = st.secrets.get("USE_DROPBOX", "0") == "1"
DROPBOX_PATH = st.secrets.get("DROPBOX_PATH", "/PRJ Vriezen/Test streamlit/autos.csv")

# Dropbox authenticatie (stel in via Secrets)
# Optie 1 (aanbevolen): refresh token + app key/secret
DBX_APP_KEY = st.secrets.get("DROPBOX_APP_KEY")
DBX_APP_SECRET = st.secrets.get("DROPBOX_APP_SECRET")
DBX_REFRESH_TOKEN = st.secrets.get("DROPBOX_REFRESH_TOKEN")
# Optie 2 (kan, maar kortlopend): access token
DBX_ACCESS_TOKEN = st.secrets.get("DROPBOX_ACCESS_TOKEN")

# Login secrets (stel in via Secrets of env)
APP_USERNAME = st.secrets.get("APP_USERNAME") or os.environ.get("APP_USERNAME")
APP_PASSWORD = st.secrets.get("APP_PASSWORD") or os.environ.get("APP_PASSWORD")

# =============================================================
# Dropbox helpers
# =============================================================
try:
    import dropbox
    from dropbox.files import WriteMode
except Exception:
    dropbox = None


def dbx_client():
    if not USE_DROPBOX:
        raise RuntimeError("Dropbox staat uit (USE_DROPBOX != '1').")
    if dropbox is None:
        raise RuntimeError("Dropbox SDK niet geïnstalleerd. Voeg 'dropbox' toe aan requirements.")

    # Geef voorkeur aan refresh-token flow (auto refresh)
    if DBX_REFRESH_TOKEN and DBX_APP_KEY and DBX_APP_SECRET:
        return dropbox.Dropbox(
            oauth2_refresh_token=DBX_REFRESH_TOKEN,
            app_key=DBX_APP_KEY,
            app_secret=DBX_APP_SECRET,
        )
    # Valt terug op access token (kan verlopen)
    if DBX_ACCESS_TOKEN:
        return dropbox.Dropbox(oauth2_access_token=DBX_ACCESS_TOKEN)

    raise RuntimeError("Dropbox niet geconfigureerd: stel refresh token of access token in.")


def dbx_read_df(csv_path: str) -> pd.DataFrame:
    dbx = dbx_client()
    try:
        _meta, res = dbx.files_download(csv_path)
        return pd.read_csv(io.BytesIO(res.content))
    except Exception:
        return pd.DataFrame(columns=["ID", "Auto naam", "Auto nummer", "Toegevoegd op"])


def dbx_write_df(df: pd.DataFrame, csv_path: str):
    dbx = dbx_client()
    data = df.to_csv(index=False).encode("utf-8")
    dbx.files_upload(data, csv_path, mode=WriteMode("overwrite"))


# =============================================================
# Lokale opslag helpers
# =============================================================

def ensure_local_csv(csv_path: str):
    folder = os.path.dirname(csv_path)
    os.makedirs(folder, exist_ok=True)
    if not os.path.exists(csv_path):
        pd.DataFrame(columns=["ID", "Auto naam", "Auto nummer", "Toegevoegd op"]).to_csv(
            csv_path, index=False, encoding="utf-8"
        )


def local_read_df(csv_path: str) -> pd.DataFrame:
    if not os.path.exists(csv_path):
        return pd.DataFrame(columns=["ID", "Auto naam", "Auto nummer", "Toegevoegd op"])
    try:
        return pd.read_csv(csv_path, dtype={"ID": "Int64"})
    except Exception:
        return pd.DataFrame(columns=["ID", "Auto naam", "Auto nummer", "Toegevoegd op"])


def local_write_df(df: pd.DataFrame, csv_path: str):
    df.to_csv(csv_path, index=False, encoding="utf-8")


# =============================================================
# Opslaglaag (abstractie)
# =============================================================

def storage_init():
    if USE_DROPBOX:
        # Probeer te lezen; indien leeg, initialiseer
        df = dbx_read_df(DROPBOX_PATH)
        if df.empty:
            dbx_write_df(df, DROPBOX_PATH)
    else:
        ensure_local_csv(LOCAL_CSV_PATH)


def storage_read() -> pd.DataFrame:
    if USE_DROPBOX:
        return dbx_read_df(DROPBOX_PATH)
    return local_read_df(LOCAL_CSV_PATH)


def storage_write(df: pd.DataFrame):
    if USE_DROPBOX:
        dbx_write_df(df, DROPBOX_PATH)
    else:
        local_write_df(df, LOCAL_CSV_PATH)


# =============================================================
# Data logica
# =============================================================

def add_car(name: str, number: str):
    df = storage_read()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_id = int(df["ID"].max() + 1) if not df.empty else 1
    row = pd.DataFrame([[new_id, name.strip(), number.strip(), ts]],
                       columns=["ID", "Auto naam", "Auto nummer", "Toegevoegd op"])
    df = pd.concat([df, row], ignore_index=True)
    storage_write(df)


# =============================================================
# UI: Login scherm
# =============================================================

def login_gate() -> bool:
    if st.session_state.get("authed"):
        return True

    st.title("🔒 Inloggen")
    with st.form("login_form"):
        u = st.text_input("Gebruiker")
        p = st.text_input("Wachtwoord", type="password")
        submit = st.form_submit_button("Log in")

    if submit:
        if not APP_USERNAME or not APP_PASSWORD:
            st.error("Login is niet geconfigureerd. Stel APP_USERNAME en APP_PASSWORD in via Secrets/omgeving.")
            return False
        if u == APP_USERNAME and p == APP_PASSWORD:
            st.session_state["authed"] = True
            return True
        st.error("Onjuiste inloggegevens.")
    st.stop()


# =============================================================
# Streamlit App
# =============================================================

st.set_page_config(page_title="Auto registratie", page_icon="🚗", layout="centered")

# Login eerst
if not login_gate():
    st.stop()

# Hoofdscherm
st.title("🚗 Auto registratie")

# Opslagstatus tonen
with st.expander("ℹ️ Opslag-instellingen"):
    if USE_DROPBOX:
        st.success("Opslag: Dropbox")
        st.code(f"Pad: {DROPBOX_PATH}")
        if not (DBX_REFRESH_TOKEN and DBX_APP_KEY and DBX_APP_SECRET) and not DBX_ACCESS_TOKEN:
            st.warning("Dropbox-credentials ontbreken of zijn incompleet.")
    else:
        st.info("Opslag: Lokaal (CSV)")
        st.code(f"Bestand: {LOCAL_CSV_PATH}")

# Init storage
try:
    storage_init()
except Exception as e:
    st.error(f"Opslag initialiseren mislukt: {e}")

# Formulier
with st.form("add_car_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Auto naam", placeholder="Bijv. Volvo FH16")
    with col2:
        number = st.text_input("Auto nummer", placeholder="Bijv. 12345 of kenteken")
    submitted = st.form_submit_button("Opslaan")

    if submitted:
        errors = []
        if not name or not name.strip():
            errors.append("Vul een geldige *auto naam* in.")
        if not number or not number.strip():
            errors.append("Vul een geldig *auto nummer* in.")
        if errors:
            for e in errors:
                st.error(e)
        else:
            try:
                add_car(name, number)
                st.success("Opgeslagen ✅")
            except Exception as e:
                st.error(f"Er ging iets mis bij opslaan: {e}")

st.subheader("📋 Overzicht")
try:
    df = storage_read()
    if df.empty:
        st.info("Nog geen auto's opgeslagen. Voeg de eerste toe hierboven.")
    else:
        st.dataframe(df, use_container_width=True)
        csv_copy = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download als CSV (kopie)",
            data=csv_copy,
            file_name=f"autos_export_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv",
            mime="text/csv",
        )
except Exception as e:
    st.error(f"Kan gegevens niet laden: {e}")

# Opties
with st.expander("⚙️ Opties"):
    st.write("Hier kun je desgewenst alle gegevens wissen (onherstelbaar).")
    if st.button("Alles wissen", type="secondary"):
        try:
            empty = pd.DataFrame(columns=["ID", "Auto naam", "Auto nummer", "Toegevoegd op"])
            storage_write(empty)
            st.success("Alle gegevens zijn verwijderd.")
        except Exception as e:
            st.error(f"Verwijderen mislukt: {e}")

# Uitloggen
st.sidebar.button("Uitloggen", on_click=lambda: st.session_state.pop("authed", None))

# ---- VS Code Play: auto-start Streamlit (optioneel, veilig) ----
if __name__ == "__main__" and os.environ.get("LOCAL_PLAY") == "1":
    subprocess.run([sys.executable, "-m", "streamlit", "run", __file__, "--server.port=8501"])
