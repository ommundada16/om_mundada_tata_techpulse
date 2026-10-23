import os

import streamlit as st
import requests

API_URL = os.getenv("TARA_API_URL", "http://localhost:8000")


@st.cache_resource(show_spinner="Starting TARA backend (first load takes ~1 minute)...")
def ensure_backend():
    """Hosted mode (Streamlit Community Cloud runs a single process): start the FastAPI backend in a background
    thread. Locally the backend is started separately with uvicorn, so this just detects it and returns."""
    import threading
    import time

    def alive():
        try:
            return requests.get(f"{API_URL}/", timeout=2).ok
        except requests.exceptions.RequestException:
            return False

    if not alive():
        import uvicorn
        from app.main import app as fastapi_app

        config = uvicorn.Config(fastapi_app, host="127.0.0.1", port=8000, log_level="warning")
        threading.Thread(target=uvicorn.Server(config).run, daemon=True).start()
        for _ in range(180):
            if alive():
                break
            time.sleep(1)
    return True


ensure_backend()

st.set_page_config(page_title="TARA Assistant", layout="wide")
st.title("Automotive Cybersecurity TARA Assistant")
st.caption("Case Study 3 - Threat Analysis and Risk Assessment, powered by RAG + a local LLM")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["1. Assets", "2. Threats", "3. Risk Assessment", "4. Mitigations", "5. Traceability Report"]
)

# ---------------- Tab 1: Assets ----------------
with tab1:
    st.subheader("Step 1: Extract Assets from the Architecture Document")
    if st.button("Extract Assets"):
        response = requests.post(f"{API_URL}/assets/extract")
        if response.ok:
            st.success(f"Extracted {len(response.json())} assets")
        else:
            st.error(response.text)

    assets_data = requests.get(f"{API_URL}/assets/").json()
    if assets_data:
        st.table(assets_data)
    else:
        st.info("No assets yet. Click 'Extract Assets' above.")

# ---------------- Tab 2: Threats ----------------
with tab2:
    st.subheader("Step 2: Generate Threat Scenarios for an Asset")
    assets_data = requests.get(f"{API_URL}/assets/").json()

    if assets_data:
        asset_options = {f"{a['id']} - {a['name']}": a["id"] for a in assets_data}
        selected = st.selectbox("Select an asset", list(asset_options.keys()))
        asset_id = asset_options[selected]

        if st.button("Generate Threats"):
            response = requests.post(f"{API_URL}/threats/generate/{asset_id}")
            if response.ok:
                st.success(f"Generated {len(response.json())} threats")
            else:
                st.error(response.text)

        threats_data = requests.get(f"{API_URL}/threats/by-asset/{asset_id}").json()
        if threats_data:
            st.table(threats_data)
    else:
        st.info("Extract assets first (Tab 1).")

# ---------------- Tab 3: Risk Assessment ----------------
with tab3:
    st.subheader("Step 3: Rate Impact and Feasibility -> Get a Risk Level")
    threat_id = st.number_input("Threat Scenario ID", min_value=1, step=1)
    impact = st.selectbox("Impact", ["LOW", "MEDIUM", "HIGH"])
    feasibility = st.selectbox("Attack Feasibility", ["LOW", "MEDIUM", "HIGH"])
    assessed_by = st.text_input("Your name", value="engineer")

    if st.button("Submit Risk Assessment"):
        payload = {
            "threat_scenario_id": int(threat_id),
            "impact": impact,
            "feasibility": feasibility,
            "assessed_by": assessed_by,
        }
        response = requests.post(f"{API_URL}/risk/assess", json=payload)
        if response.ok:
            result = response.json()
            st.success(f"Risk Level: {result['risk_level']}")
        else:
            st.error(response.text)

# ---------------- Tab 4: Mitigations ----------------
with tab4:
    st.subheader("Step 4: Suggest and Approve a Mitigation")
    threat_id_m = st.number_input(
        "Threat Scenario ID for Mitigation", min_value=1, step=1, key="mitigation_threat_id"
    )

    if st.button("Suggest Mitigation"):
        response = requests.post(f"{API_URL}/mitigations/suggest/{int(threat_id_m)}")
        if response.ok:
            st.session_state["last_mitigation"] = response.json()
            st.success("Mitigation drafted")
        else:
            st.error(response.text)

    if "last_mitigation" in st.session_state:
        mitigation = st.session_state["last_mitigation"]
        st.write(mitigation)
        approved_by = st.text_input("Approve as", value="reviewer")
        if st.button("Approve Mitigation"):
            response = requests.post(
                f"{API_URL}/mitigations/{mitigation['id']}/approve",
                json={"approved_by": approved_by},
            )
            if response.ok:
                st.success("Mitigation approved")

# ---------------- Tab 5: Traceability Report ----------------
with tab5:
    st.subheader("Step 5: Full Traceability Report")
    if st.button("Generate Report"):
        response = requests.get(f"{API_URL}/report/traceability")
        st.table(response.json())
