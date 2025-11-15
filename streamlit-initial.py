import streamlit as st
import pandas as pd
import requests
import json
import tempfile
from streamlit_lottie import st_lottie
from PyPDF2 import PdfReader
from anthropic import Anthropic

# -------------------------
# CONFIG
# -------------------------

st.set_page_config(page_title="Altrua AI", page_icon="📊", layout="wide")

ANTHROPIC_API_KEY = st.secrets.get("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", None)
client = Anthropic(api_key=ANTHROPIC_API_KEY)

# -------------------------
# HELPERS
# -------------------------

def load_lottie(url):
    try:
        r = requests.get(url)
        if r.status_code == 200:
            return r.json()
    except:
        return None

def extract_pdf_text(file):
    """Extract plaintext from uploaded PDF."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(file.read())
        tmp_path = tmp.name

    reader = PdfReader(tmp_path)
    text = "\n".join([page.extract_text() or "" for page in reader.pages])
    return text

def run_llm_extraction(text):
    """Send CSR text to Claude and return JSON list of extracted items."""

    prompt = f"""
You are an ESG analyst. Given the CSR text below, identify disclosures and map each
to GRI codes. Return ONLY a JSON array of objects with:

[
  {{
    "section": "...",
    "gri_code": "...",
    "confidence": 0.0
  }},
  ...
]

CSR TEXT:
{text[:6000]}
"""

    resp = client.messages.create(
        model="claude-4-5-sonnet",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}]
    )

    # Parse JSON out of LLM output
    raw = resp.content[0].text.strip()

    # try pure JSON
    try:
        return json.loads(raw)
    except:
        # fallback: extract JSON between brackets
        start = raw.find("[")
        end = raw.rfind("]")
        return json.loads(raw[start:end+1])

def enrich_rows(rows):
    """Replicate the same JavaScript enrichment logic."""
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
    """Build same summary JSON as your n8n Python node."""
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
        "full_extraction": enriched_rows
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
    st.markdown("""
        <h1 style='font-size:52px;margin-bottom:-10px;'>Altrua AI</h1>
        <p style='font-size:20px;color:#aaa;'>Upload CSR/Sustainability reports. Our AI automatically extracts GRI metrics.</p>
    """, unsafe_allow_html=True)

uploaded = st.file_uploader("Upload CSR Report (PDF)", type=["pdf"])

if uploaded:
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
    tab1, tab2, tab3 = st.tabs(["📊 GRI Breakdown", "⚠️ Low Confidence", "📄 Full Extraction"])

    with tab1:
        df_bd = pd.DataFrame.from_dict(data["gri_breakdown"], orient="index")
        df_bd.columns = ["Count"]
        st.bar_chart(df_bd)

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
            mime="text/csv"
        )
