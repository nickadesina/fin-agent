import streamlit as st
import requests
import json

st.set_page_config(
    page_title="CSR Analyzer",
    page_icon="📊",
    layout="wide"
)

# --- HEADER ---
st.markdown("""
    <style>
    .main-title {
        font-size: 48px;
        font-weight: 700;
        margin-bottom: -10px;
    }
    .subtitle {
        font-size: 20px;
        color: #666;
        margin-bottom: 40px;
    }
    .upload-box {
        padding: 40px;
        border-radius: 10px;
        border: 2px dashed #444;
        background-color: #1E1E1E20;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">📄 CSR Document Analyzer</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Upload your CSR/Sustainability report. Our AI extracts GRI metrics automatically.</p>', unsafe_allow_html=True)

# --- FILE UPLOADER ---
uploaded = st.file_uploader(
    "Upload CSR Report (PDF, XLSX, CSV, DOCX)",
    type=["pdf", "xlsx", "csv", "docx"]
)

if uploaded:
    with st.spinner("Analyzing report… this usually takes 3–6 seconds..."):
        files = {"file": (uploaded.name, uploaded.read(), uploaded.type)}

        resp = requests.post(
            "YOUR_N8N_WEBHOOK_URL",
            files=files
        )

    st.success("Done! Here's what we found:")

    data = resp.json()

    # --- DISPLAY JSON RESULT ---
    st.json(data, expanded=False)

    # --- OPTIONAL PRETTY SUMMARY ---
    if "gri_breakdown" in data:
        st.subheader("GRI Category Coverage")
        st.bar_chart(data["gri_breakdown"])
