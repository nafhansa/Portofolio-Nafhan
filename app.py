import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from PyPDF2 import PdfReader

# =========================================
# coba import watsonx, tapi jangan bikin app mati
# =========================================
try:
    from ibm_watsonx_ai.foundation_models import ModelInference  # type: ignore
    HAS_WATSONX = True
except Exception:
    HAS_WATSONX = False

load_dotenv()

app = Flask(__name__)

# =========================================
# CORS – izinkan domainmu + localhost
# =========================================
ALLOWED_ORIGINS = [
    "https://nafhan.space",
    "https://www.nafhan.space",
    "http://localhost:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

# aktifkan CORS global basic dulu
CORS(app, supports_credentials=True)


@app.after_request
def add_cors_headers(resp):
    origin = request.headers.get("Origin")
    if origin in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
        resp.headers["Access-Control-Allow-Credentials"] = "true"
        resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    return resp


# =========================================
# KONFIG
# =========================================
PDF_PATH = "./Nafhan_Profile.pdf"

WATSONX_APIKEY = os.getenv("WATSONX_APIKEY")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
WATSONX_URL = os.getenv("WATSONX_URL", "https://jp-tok.ml.cloud.ibm.com")

# bakal kita isi di startup
PDF_TEXT = ""


# =========================================
# baca PDF jadi string
# =========================================
def load_pdf_text() -> str:
    if not os.path.exists(PDF_PATH):
        # jangan bikin server mati, balikin string kosong aja
        print(f"⚠️ PDF {PDF_PATH} tidak ditemukan, lanjut tanpa PDF.")
        return ""
    reader = PdfReader(PDF_PATH)
    pages = [(p.extract_text() or "") for p in reader.pages]
    return "\n".join(pages)


# =========================================
# buat LLM watsonx kalau bisa
# =========================================
def get_llm():
    # kalau lib-nya aja gak ada → langsung None
    if not HAS_WATSONX:
        return None
    # kalau env belum diisi → langsung None
    if not (WATSONX_APIKEY and WATSONX_PROJECT_ID):
        return None

    try:
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
    except Exception as e:
        # jangan matikan server
        print("⚠️ gagal init watsonx:", e)
        return None


# =========================================
# fallback jawaban dari PDF
# =========================================
def simple_answer_from_pdf(question: str, pdf_text: str) -> str:
    q = question.lower()
    if "sekolah" in q or "kuliah" in q:
        return "Di PDF-mu belum ada info sekolah/kuliah. Tambahkan di PDF supaya bisa dijawab ya 🙂"

    # ambil 1 paragraf awal PDF
    if pdf_text.strip():
        first = pdf_text.strip().split("\n")[0][:300]
        return f"Aku nemu ini di PDF kamu:\n\n{first}\n\n(Aktifkan watsonx di Railway kalau mau jawaban lebih pinter.)"

    return "PDF-nya kosong atau nggak kebaca, jadi aku belum bisa jawab lebih detail."


# =========================================
# load PDF sekali
# =========================================
PDF_TEXT = load_pdf_text()
print("✅ Server start. PDF length:", len(PDF_TEXT))
print("✅ watsonx available?" , HAS_WATSONX)


# =========================================
# ROUTES
# =========================================
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "portfolio chatbot running"})


@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    # preflight
    if request.method == "OPTIONS":
        return ("", 204)

    data = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()

    if not question:
        return jsonify({"reply": "Pertanyaannya kosong."}), 200

    llm = get_llm()

    # prompt kalau watsonx berhasil
    prompt = f"""
Kamu adalah asisten yang hanya boleh menjawab dari dokumen berikut.

=== DOKUMEN ===
{PDF_TEXT}
=== AKHIR DOKUMEN ===

Pertanyaan pengguna: "{question}"

Jika di dokumen tidak ada jawabannya, jawab:
"Maaf, di PDF saya tidak menemukan info itu."

Jawab dalam bahasa Indonesia yang rapi, maksimal 2 paragraf.
""".strip()

    # kalau gak ada watsonx → fallback saja
    if llm is None:
        reply = simple_answer_from_pdf(question, PDF_TEXT)
        return jsonify({"reply": reply}), 200

    # kalau ada watsonx → coba pakai
    try:
        answer = llm.generate_text(prompt)
        return jsonify({"reply": answer}), 200
    except Exception as e:
        # jangan bikin error 500
        print("⚠️ watsonx error saat generate:", e)
        reply = simple_answer_from_pdf(question, PDF_TEXT)
        return jsonify({"reply": reply + f"\n\n(catatan: watsonx error: {e})"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    # host 0.0.0.0 biar Railway bisa expose
    app.run(host="0.0.0.0", port=port)
