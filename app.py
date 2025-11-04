import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from PyPDF2 import PdfReader

# =========== CONFIG ============
PDF_PATH = "./Nafhan_Profile.pdf"
PORT = int(os.environ.get("PORT", 8080))

app = Flask(__name__)

# CORS: izinkan semua dulu supaya gampang debug
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=True,
)

# =========== LOAD PDF SEKALI ============
def load_pdf_text() -> str:
    if not os.path.exists(PDF_PATH):
        print(f"⚠️ PDF tidak ditemukan di {PDF_PATH}")
        return ""
    reader = PdfReader(PDF_PATH)
    pages = []
    for p in reader.pages:
        pages.append(p.extract_text() or "")
    full = "\n".join(pages)
    print("✅ PDF loaded, length:", len(full))
    return full


PDF_TEXT = load_pdf_text()


# =========== ROUTES ============
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "portfolio chatbot running"}), 200


@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    # handle preflight
    if request.method == "OPTIONS":
        resp = app.make_response("")
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return resp, 204

    data = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()

    if not question:
        return jsonify({"reply": "Pertanyaannya kosong."}), 200

    # fallback paling sederhana: ambil paragraf awal PDF
    if PDF_TEXT:
        first_lines = PDF_TEXT.strip().split("\n")[0:4]
        snippet = "\n".join(first_lines)
        reply = (
            "Aku baca gini di PDF kamu:\n\n"
            + snippet
            + "\n\n(ini mode fallback, nanti bisa disambung ke watsonx)"
        )
    else:
        reply = "PDF belum kebaca di server."

    return jsonify({"reply": reply}), 200


if __name__ == "__main__":
    # ⚠️ PENTING: pakai waitress supaya proses gak langsung selesai
    from waitress import serve

    print(f"🚀 Serving on 0.0.0.0:{PORT}")
    serve(app, host="0.0.0.0", port=PORT)
