import os
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from dotenv import load_dotenv
from PyPDF2 import PdfReader

load_dotenv()

app = Flask(__name__)

# 1. buka CORS lebar dulu supaya preflight nggak ditolak
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# 2. lokasi PDF kamu di repo Railway
PDF_PATH = "./Nafhan_Profile.pdf"

# kita isi setelah startup
PDF_TEXT = ""


def load_pdf_text() -> str:
    """Baca PDF jadi satu string, tapi JANGAN bikin app mati kalau gagal."""
    if not os.path.exists(PDF_PATH):
        print(f"⚠️ PDF tidak ditemukan di {PDF_PATH}, lanjut tanpa PDF.")
        return ""
    reader = PdfReader(PDF_PATH)
    pages = [(p.extract_text() or "") for p in reader.pages]
    return "\n".join(pages)


# muat PDF sekali
PDF_TEXT = load_pdf_text()
print("✅ Flask up. PDF length:", len(PDF_TEXT))


@app.after_request
def add_headers(resp):
    # pastikan semua respons punya header CORS yang lengkap
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    return resp


# 3. catch-all OPTIONS — ini yang sering bikin 502 kalau nggak ada
@app.route("/", methods=["OPTIONS"])
@app.route("/chat", methods=["OPTIONS"])
def options_only():
    resp = make_response("", 200)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    return resp


@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "portfolio chatbot running"})


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()

    if not question:
        return jsonify({"reply": "Pertanyaannya kosong."}), 200

    # jawaban super sederhana dari PDF
    if not PDF_TEXT:
        return jsonify(
            {"reply": "PDF di server belum ada atau kosong, jadi aku belum bisa jawab 🙏"}
        )

    # cari kalimat yang mengandung kata dari pertanyaan (sangat sederhana)
    lowered = PDF_TEXT.lower()
    key = question.split()[0].lower()  # ambil kata pertama aja
    idx = lowered.find(key)

    if idx == -1:
        reply = "Maaf, di PDF aku tidak menemukan info itu. Coba tanya hal lain yang ada di profil 😊"
    else:
        start = max(0, idx - 150)
        end = min(len(PDF_TEXT), idx + 300)
        snippet = PDF_TEXT[start:end]
        reply = f"Aku ambil dari PDF kamu:\n\n{snippet}"

    return jsonify({"reply": reply}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
