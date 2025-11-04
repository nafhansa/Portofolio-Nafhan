import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from PyPDF2 import PdfReader

app = Flask(__name__)

# izinkan semua origin dulu biar gampang tes
CORS(app)

PDF_PATH = "./Nafhan_Profile.pdf"

# load pdf sekali
def load_pdf_text():
    if not os.path.exists(PDF_PATH):
        return ""
    reader = PdfReader(PDF_PATH)
    parts = []
    for p in reader.pages:
        parts.append(p.extract_text() or "")
    return "\n".join(parts)

PDF_TEXT = load_pdf_text()
print("✅ PDF loaded length:", len(PDF_TEXT))

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "portfolio chatbot running"})

@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    # biar preflight ga error
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()
    if not question:
        return jsonify({"reply": "Pertanyaannya kosong."})

    # jawaban super sederhana dari PDF
    snippet = PDF_TEXT[:650] if PDF_TEXT else "PDF-nya kosong atau tidak terbaca."
    reply = (
        f"Kamu nanya: {question}\n\n"
        f"Aku ambil bagian awal dari PDF kamu ya:\n\n{snippet}\n\n"
        f"(Kalau mau jawaban lebih pinter, nanti kita aktifin watsonx.)"
    )
    return jsonify({"reply": reply})

if __name__ == "__main__":
    from waitress import serve
    port = int(os.environ.get("PORT", 8080))
    serve(app, host="0.0.0.0", port=port)
