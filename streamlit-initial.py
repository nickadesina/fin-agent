import streamlit as st
import pandas as pd
import requests
import json
import tempfile
from streamlit_lottie import st_lottie
from PyPDF2 import PdfReader
from openai import OpenAI  # <<–– OpenAI SDK

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------
# CONFIG
# -------------------------

st.set_page_config(page_title="Altrua AI", page_icon="📊", layout="wide")

OPENAI_API_KEY = "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"  # <-- put your key here (or use env var)
client = OpenAI(api_key=OPENAI_API_KEY)

# -------------------------
# HELPERS
# -------------------------


def load_lottie(url: str):
    try:
        r = requests.get(url)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None


def extract_pdf_text(file) -> str:
    """Extract plaintext from uploaded PDF."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(file.read())
        tmp_path = tmp.name

    reader = PdfReader(tmp_path)
    text = "\n".join([page.extract_text() or "" for page in reader.pages])
    return text


def run_llm_extraction(text: str):
    """
    Send CSR text to OpenAI and return a Python list of
    {section, gri_code, confidence} items.
    """
    system_prompt = (
        "You are an ESG analyst. Given CSR text, identify disclosures and map "
        "each to GRI codes. Return ONLY valid JSON: a JSON array where each "
        "item has fields: section (string), gri_code (string), confidence (0–1)."
    )

    user_prompt = f"CSR TEXT (truncated):\n{text[:6000]}"

    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw = resp.choices[0].message.content.strip()

    # First try direct JSON parse
    try:
        return json.loads(raw)
    except Exception:
        # Fallback: grab array between first `[` and last `]`
        start = raw.find("[")
        end = raw.rfind("]")
        if start == -1 or end == -1:
            raise ValueError("Model response did not contain JSON array.")
        return json.loads(raw[start : end + 1])


def enrich_rows(rows):
    """Business-logic enrichment layer."""
    enriched = []
    for r in rows:
        section = r.get("section")
        gri = r.get("gri_code")
        conf = r.get("confidence")

        new = {
            "section": section,
            "gri_code": gri,
            "confidence": conf,
            "extracted_at": pd.Timestamp.utcnow().isoformat(),
            "is_energy_related": gri.startswith("302") if gri else False,
            "is_water_related": gri.startswith("303") if gri else False,
            "is_emissions_related": gri.startswith("305") if gri else False,
            "low_confidence": conf is not None and conf < 0.65,
        }
        enriched.append(new)
    return enriched


def aggregate(enriched_rows):
    """Build dashboard-friendly summary payload."""
    breakdown = {}
    for r in enriched_rows:
        if not r["gri_code"]:
            continue
        prefix = r["gri_code"].split("-")[0]
        breakdown[prefix] = breakdown.get(prefix, 0) + 1

    low_conf = [r for r in enriched_rows if r["low_confidence"]]

    return {
        "organization": "Demo Corp",
        "gri_breakdown": breakdown,
        "low_confidence": low_conf,
        "full_extraction": enriched_rows,
    }


# -------------------------
# UI START
# -------------------------

lottie_ai = load_lottie("https://assets9.lottiefiles.com/packages/lf20_3rwasyjy.json")

col1, col2 = st.columns([1, 2])
with col1:
    if lottie_ai:
        st_lottie(lottie_ai, height=180)
with col2:
    st.markdown(
        """
        <h1 style='font-size:52px;margin-bottom:-10px;'>Altrua AI</h1>
        <p style='font-size:20px;color:#aaa;'>
        Upload CSR/Sustainability reports. Our AI automatically extracts GRI metrics.
        </p>
        """,
        unsafe_allow_html=True,
    )

uploaded = st.file_uploader("Upload CSR Report (PDF)", type=["pdf"])

if uploaded:
    try:
        with st.spinner("Extracting text..."):
            text = extract_pdf_text(uploaded)

        with st.spinner("Running AI extraction..."):
            llm_output = run_llm_extraction(text)

        with st.spinner("Enriching and generating dashboard data..."):
            enriched = enrich_rows(llm_output)
            data = aggregate(enriched)

        st.success("Analysis complete!")

        # -------------------------
        # METRICS
        # -------------------------
        colA, colB, colC = st.columns(3)
        colA.metric("Total Extracted Sections", len(data["full_extraction"]))
        colB.metric("Distinct GRI Categories", len(data["gri_breakdown"]))
        colC.metric("Low Confidence Flags", len(data["low_confidence"]))

        # -------------------------
        # TABS
        # -------------------------
        tab1, tab2, tab3 = st.tabs(
            ["📊 GRI Breakdown", "⚠️ Low Confidence", "📄 Full Extraction"]
        )

        with tab1:
            if data["gri_breakdown"]:
                df_bd = pd.DataFrame.from_dict(
                    data["gri_breakdown"], orient="index", columns=["Count"]
                )
                st.bar_chart(df_bd)
            else:
                st.info("No GRI codes detected.")

        with tab2:
            if not data["low_confidence"]:
                st.success("No low-confidence fields found.")
            else:
                st.warning("These items need human review:")
                st.table(pd.DataFrame(data["low_confidence"]))

        with tab3:
            df_full = pd.DataFrame(data["full_extraction"])
            st.dataframe(df_full, use_container_width=True)
            st.download_button(
                "Download CSV",
                df_full.to_csv(index=False),
                file_name="csr_extraction.csv",
                mime="text/csv",
            )

    except Exception as e:
        logger.exception("Pipeline failed")
        st.error(f"Something went wrong: {e}")