import requests

url = "https://nicakdesina.app.n8n.cloud/webhook/csr_upload"
file_path = r"C:\Users\nicka\Downloads\disney_csr.pdf"

with open(file_path, "rb") as f:
    resp = requests.post(url, files={"file": ("disney_csr.pdf", f, "application/pdf")})

print(resp.status_code)
print(resp.text)
