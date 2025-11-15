import streamlit as st
import requests

st.title("CSR Upload")

file = st.file_uploader("Upload CSR document", type=["pdf", "xlsx", "csv", "docx"])

if file:
    files = {
        "file": (file.name, file.read(), file.type)
    }

    resp = requests.post(
        "https://nicakdesina.app.n8n.cloud/webhook-test/webhook/csr_upload",
        files=files
    )

    st.write("Response from n8n:")
    st.json(resp.json())
