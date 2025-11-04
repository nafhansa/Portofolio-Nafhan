import os
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# =====================================================
# 1) CORS: buka lebar dulu biar gak 502 gara2 preflight
# =====================================================
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)


# =====================================================
# 2) Import PyPDF2 tapi jangan bikin server mati
# =====================================================
try:
    from PyPDF2 import PdfReader  # type: ignore
    HAS_PYPDF2 = True
except Exception:
    print("⚠️ PyPDF2 tidak tersedia, jalan tanpa baca PDF.")
    HAS_PYPDF2 = False


# =====================================================
# 3) (opsional) watsonx – sementara kita matikan supaya
#    gak bikin crash. Nanti kalau ini sudah hidup baru
#    kita aktifkan lagi.
# =====================================================
HAS_WATSONX = False
PDF_PATH = "./Nafhan_Profile.pdf"
PDF_TEXT = ""


def load_pdf_text() -> str:
    """Baca PDF jadi satu string. Jangan raise apa-apa di sini."""
    if not HAS_PYPDF2:
        return ""
    if not os.path.exists(PDF_PATH):
        print(f"⚠️ PDF {PDF_PATH} tidak ditemukan.")
        return ""
    try:
        reader = PdfReader(PDF_PATH)
        pages = [(p.extract_text() or "") for p in reader.pages]
        return "\n".join(pages)
    except Exception as e:
        print("⚠️ Gagal baca PDF:", e)
        return ""


# muat PDF sekali
PDF_TEXT = load_pdf_text()
print("✅ Flask start. Panjang PDF:", len(PDF_TEXT))


# =====================================================
# 4) helper bikin response OPTIONS
# =====================================================
def cors_ok_response():
    resp = make_response("", 200)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    return resp


@app.after_request
def add_cors_headers(resp):
    # supaya semua response punya header ini
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    return resp


# =====================================================
# 5) routes
# =====================================================

# supaya kalau Railway ngecek "/" gak 502
@app.route("/", methods=["GET", "OPTIONS"])
def home():
    if request.method == "OPTIONS":
        return cors_ok_response()
    return jsonify({"status": "ok", "message": "portfolio chatbot running"})


@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    # preflight dari browser
    if request.method == "OPTIONS":
        return cors_ok_response()

    data = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()

    if not question:
        return jsonify({"reply": "Pertanyaannya kosong."}), 200

    # karena watsonx kita nonaktifkan dulu, jawab dari PDF saja
    if not PDF_TEXT:
        reply = (
            "Server sudah hidup ✅ tapi PDF belum kebaca / library PDF belum ada. "
            "Tambahkan PyPDF2 di requirements atau taruh Nafhan_Profile.pdf di root repo."
        )
        return jsonify({"reply": reply}), 200

    # cari kemunculan kata pertama user di PDF (super simple)
    lowered = PDF_TEXT.lower()
    first_word = question.split()[0].lower()
    pos = lowered.find(first_word)

    if pos == -1:
        reply = "Maaf, di PDF aku belum menemukan info itu. Coba tanya hal lain yang ada di profil 😊"
    else:
        start = max(0, pos - 160)
        end = min(len(PDF_TEXT), pos + 320)
        snippet = PDF_TEXT[start:end]
        reply = f"Aku ambil dari PDF kamu:\n\n{snippet}"

    return jsonify({"reply": reply}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
