import streamlit as st
import pandas as pd
from datetime import datetime
import os, sys, subprocess

# ---------- Config ----------
# Opslagmap (Windows): gebruik raw string r"..."
DATA_DIR = r"C:\Users\Peterv\LEEUWEN TRUCKS & VAN Dropbox\PRJ Vriezen\Test streamlit"
CSV_PATH = os.path.join(DATA_DIR, "autos.csv")

# Zorg dat de map bestaat
os.makedirs(DATA_DIR, exist_ok=True)

# ---------- Data helpers ----------
def init_csv():
    if not os.path.exists(CSV_PATH):
        df = pd.DataFrame(columns=["Auto naam", "Auto nummer", "Toegevoegd op"])
        df.to_csv(CSV_PATH, index=False, encoding="utf-8")

def add_car(name: str, number: str):
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_row = pd.DataFrame(
        [[name.strip(), number.strip(), created_at]],
        columns=["Auto naam", "Auto nummer", "Toegevoegd op"]
    )
    if os.path.exists(CSV_PATH):
        df = pd.read_csv(CSV_PATH)
        df = pd.concat([df, new_row], ignore_index=True)
    else:
        df = new_row
    df.to_csv(CSV_PATH, index=False, encoding="utf-8")

def get_all_cars() -> pd.DataFrame:
    if os.path.exists(CSV_PATH):
        return pd.read_csv(CSV_PATH)
    return pd.DataFrame(columns=["Auto naam", "Auto nummer", "Toegevoegd op"])

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Auto registratie", page_icon="🚗", layout="centered")
st.title("🚗 Auto registratie")
st.caption(
    "Voer een *auto naam* en *auto nummer* in en sla ze op. "
    f"Data wordt opgeslagen in: {DATA_DIR}"
)

# Init CSV
init_csv()

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
    df = get_all_cars()
    if df.empty:
        st.info("Nog geen auto's opgeslagen. Voeg de eerste toe hierboven.")
    else:
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download als CSV",
            data=csv,
            file_name=f"autos_export_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv",
            mime="text/csv",
        )
except Exception as e:
    st.error(f"Kan gegevens niet laden: {e}")

# ---------- Opties ----------
with st.expander("⚙️ Opties"):
    st.write("Hier kun je desgewenst alle gegevens wissen (onherstelbaar).")
    if st.button("Alles wissen", type="secondary"):
        try:
            df = pd.DataFrame(columns=["Auto naam", "Auto nummer", "Toegevoegd op"])
            df.to_csv(CSV_PATH, index=False, encoding="utf-8")
            st.success("Alle gegevens zijn verwijderd.")
        except Exception as e:
            st.error(f"Verwijderen mislukt: {e}")

# ---- VS Code Play: auto-start Streamlit (optioneel en veilig) ----
# Zet in VS Code bij Run-config een env var LOCAL_PLAY=1 om via 'Play' automatisch te starten.
if __name__ == "__main__" and os.environ.get("LOCAL_PLAY") == "1":
    subprocess.run([sys.executable, "-m", "streamlit", "run", __file__, "--server.port=8501"])
