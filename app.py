import os
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from dotenv import load_dotenv
from PyPDF2 import PdfReader

# watsonx boleh gagal, makanya kita import tapi nanti siap fallback
try:
    from ibm_watsonx_ai.foundation_models import ModelInference
except Exception:  # biar container tetap jalan
    ModelInference = None

load_dotenv()

app = Flask(__name__)

# CORS: izinkan frontend prod + semua subdomain Railway + lokal
CORS(
    app,
    resources={
        r"/*": {
            "origins": [
                # production domains
                "https://nafhan.space",
                "https://www.nafhan.space",
                "https://portofolio-nafhan-production.up.railway.app",
                # any Railway preview or custom env under railway.app
                r"https://.*\\.railway\\.app",
                # local dev
                "http://localhost:5500",
                "http://localhost:8080",
                "http://127.0.0.1:8080",
            ],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Type"],
            "vary_header": True,
            "always_send": True,
        }
    },
)

PDF_PATH = "./Nafhan_Profile.pdf"

WATSONX_APIKEY = os.getenv("WATSONX_APIKEY")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
WATSONX_URL = os.getenv("WATSONX_URL", "https://jp-tok.ml.cloud.ibm.com")

PDF_TEXT = ""


def load_pdf_text() -> str:
    if not os.path.exists(PDF_PATH):
        return ""
    reader = PdfReader(PDF_PATH)
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def get_llm():
    # kalau library-nya nggak ke-install, langsung balik None
    if ModelInference is None:
        return None
    if not (WATSONX_APIKEY and WATSONX_PROJECT_ID):
        return None
    return ModelInference(
        model_id="meta-llama/llama-3-3-70b-instruct",
        params={
            "decoding_method": "greedy",
            "max_new_tokens": 350,
        },
        credentials={
            "apikey": WATSONX_APIKEY,
            "url": WATSONX_URL,
        },
        project_id=WATSONX_PROJECT_ID,
    )


def simple_answer_from_pdf(question: str, pdf_text: str) -> str:
    q = question.lower()
    if "siapa" in q or "kenal" in q or "nafhan" in q:
        return "Ini asisten AI dari portfolio Nafhan. Isi PDF dipakai buat jawab hal-hal tentang dia 🙂"
    if pdf_text:
        first = pdf_text.strip().split("\n")[0][:350]
        return (
            "Ini potongan dari PDF kamu, karena model jarak jauh belum aktif:\n\n"
            + first
            + "\n\nAktifkan env WATSONX_xx di Railway biar jawabannya lebih pintar."
        )
    return "Maaf, PDF belum ke-load dan watsonx belum aktif."


# load PDF pas startup
PDF_TEXT = load_pdf_text()
print("📄 PDF loaded, length:", len(PDF_TEXT))


@app.after_request
def add_cors_headers(resp):
    # jaga-jaga kalau proxy di depan (Railway) buang header; jangan overwrite kalau sudah ada
    if "Access-Control-Allow-Origin" not in resp.headers:
        origin = request.headers.get("Origin")
        if origin:
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Vary"] = "Origin"
    if "Access-Control-Allow-Methods" not in resp.headers:
        resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    if "Access-Control-Allow-Headers" not in resp.headers:
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    return resp


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "portfolio chatbot running"}), 200


@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    # handle preflight
    if request.method == "OPTIONS":
        return make_response("", 204)

    data = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()
    if not question:
        return jsonify({"reply": "Pertanyaannya kosong."}), 200

    llm = get_llm()

    prompt = f"""
Kamu adalah asisten yang hanya boleh menjawab dari dokumen berikut.

=== DOKUMEN ===
{PDF_TEXT}
=== AKHIR DOKUMEN ===

Pertanyaan pengguna: "{question}"

Jika di dokumen tidak ada jawabannya, jawab: "Maaf, di PDF saya tidak menemukan info itu."
Jawab dengan bahasa Indonesia, rapi, maksimal 2 paragraf.
""".strip()

    # kalau tidak ada LLM ➜ fallback
    if llm is None:
        fallback = simple_answer_from_pdf(question, PDF_TEXT)
        return jsonify({"reply": fallback}), 200

    try:
        answer = llm.generate_text(prompt)
        return jsonify({"reply": answer}), 200
    except Exception as e:
        fallback = simple_answer_from_pdf(question, PDF_TEXT)
        return jsonify({"reply": f"{fallback}\n\n(catatan: watsonx error: {e})"}), 200


if __name__ == "__main__":
    # jalankan dengan waitress di lokal juga boleh
    from waitress import serve

    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 serving on 0.0.0.0:{port}")
    serve(app, host="0.0.0.0", port=port)
