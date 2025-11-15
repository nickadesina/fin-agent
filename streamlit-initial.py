import streamlit as st
import requests
import json
from streamlit_lottie import st_lottie
import pandas as pd

st.set_page_config(page_title="Altrua AI", page_icon="📊", layout="wide")

# ---- Load Lottie Animation ----
def load_lottie(url):
    try:
        r = requests.get(url)
        if r.status_code == 200:
            return r.json()
    except:
        return None

lottie_ai = load_lottie("https://assets9.lottiefiles.com/packages/lf20_3rwasyjy.json")


# ---- HEADER ----
col1, col2 = st.columns([1, 2])

with col1:
    if lottie_ai:
        st_lottie(lottie_ai, height=180, key="ai_anim")

with col2:
    st.markdown("""
        <h1 style='font-size: 52px; margin-bottom:-10px;'> Altrua AI</h1>
        <p style='font-size: 20px; color:#aaa;'>Upload CSR/Sustainability reports. Our AI automatically extracts GRI metrics.</p>
    """, unsafe_allow_html=True)


# ---- FILE UPLOADER ----
uploaded = st.file_uploader(
    "Upload CSR Report (PDF, XLSX, CSV, DOCX)",
    type=["pdf", "xlsx", "csv", "docx"]
)

if uploaded:
    with st.spinner("Analyzing report… typically 3–6 seconds..."):
        files = {"file": (uploaded.name, uploaded.read(), uploaded.type)}
        resp = requests.post(
            "https://nicakdesina.app.n8n.cloud/webhook/webhook/csr_upload",
            files=files
        )

    if resp.status_code != 200:
        st.error("Something went wrong with the server.")
        st.text(resp.text)
        st.stop()

    data = resp.json()
    st.success("Analysis complete!")


    # ---- TOP SUMMARY METRICS ----
    colA, colB, colC = st.columns(3)

    with colA:
        st.metric("Total Extracted Sections", len(data["full_extraction"]))

    with colB:
        st.metric("Distinct GRI Categories", len(data["gri_breakdown"]))

    with colC:
        st.metric("Low Confidence Flags", len(data["low_confidence"]))


    # ---- TABS ----
    tab1, tab2, tab3 = st.tabs(["📊 GRI Breakdown", "⚠️ Low Confidence", "📄 Full Extraction"])


    # --- TAB 1: BAR CHART ---
    with tab1:
        df_breakdown = pd.DataFrame.from_dict(data["gri_breakdown"], orient="index")
        df_breakdown.columns = ["Count"]
        st.bar_chart(df_breakdown)


    # --- TAB 2: LOW CONFIDENCE ---
    with tab2:
        if len(data["low_confidence"]) == 0:
            st.success("No low-confidence fields found. Great extraction quality.")
        else:
            st.warning("These items need human review:")
            st.table(pd.DataFrame(data["low_confidence"]))


    # --- TAB 3: FULL EXTRACTION ---
    with tab3:
        df_full = pd.DataFrame(data["full_extraction"])
        st.dataframe(df_full, use_container_width=True)

        st.download_button(
            "Download CSV",
            data=df_full.to_csv(index=False),
            file_name="csr_extraction.csv",
            mime="text/csv"
        )
