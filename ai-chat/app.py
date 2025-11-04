import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from PyPDF2 import PdfReader

# watsonx (boleh gagal, kita fallback)
from ibm_watsonx_ai.foundation_models import ModelInference

load_dotenv()

app = Flask(__name__)

# CORS: izinkan domain kamu + localhost
CORS(
    app,
    resources={
        r"/*": {
            "origins": [
                "https://nafhan.space",
                "https://www.nafhan.space",
                "http://localhost:5173",
                "http://localhost:8080",
                "http://127.0.0.1:8080",
            ]
        }
    },
)

# ===== Konfig =====
PDF_PATH = "./Nafhan_Profile.pdf"
WATSONX_APIKEY = os.getenv("WATSONX_APIKEY")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
WATSONX_URL = os.getenv("WATSONX_URL", "https://jp-tok.ml.cloud.ibm.com")

PDF_TEXT = ""


def load_pdf_text() -> str:
    """Baca PDF sekali di startup."""
    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"PDF tidak ditemukan di {PDF_PATH}")
    reader = PdfReader(PDF_PATH)
    pages = [(p.extract_text() or "") for p in reader.pages]
    return "\n".join(pages)


def get_llm():
    """Balikin watsonx kalau env lengkap, kalau nggak None."""
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
    if "sekolah" in q or "kuliah" in q:
        return "Di PDF belum ada info pendidikan. Tambahkan dulu di PDF ya 🙂"

    snippet = pdf_text.strip().split("\n")[0][:280] if pdf_text else ""
    if snippet:
        return f"Aku nemu ini di PDF kamu:\n\n{snippet}\n\n(untuk jawaban lebih spesifik, aktifkan watsonx di Railway)."

    return "Maaf, aku tidak menemukan info itu di PDF dan watsonx belum aktif."


# load pdf di startup
try:
    PDF_TEXT = load_pdf_text()
    print("✅ PDF loaded, length:", len(PDF_TEXT))
except Exception as e:
    print("⚠️ gagal load PDF:", e)
    PDF_TEXT = ""


@app.get("/")
def root():
    return jsonify({"status": "ok", "message": "portfolio chatbot running"})


# penting: bikin /health biar Railway bisa ngecek
@app.get("/health")
def health():
    return jsonify({"status": "healthy"}), 200


@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    # handle preflight
    if request.method == "OPTIONS":
        return "", 204

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

Jika di dokumen tidak ada jawabannya, jawab pakai kalimat ini:
"Maaf, di PDF saya tidak menemukan info itu."

Jawab dalam bahasa Indonesia yang rapi, maksimal 2 paragraf.
""".strip()

    if llm is None:
        # fallback
        return jsonify({"reply": simple_answer_from_pdf(question, PDF_TEXT)}), 200

    try:
        answer = llm.generate_text(prompt)
        return jsonify({"reply": answer}), 200
    except Exception as e:
        fb = simple_answer_from_pdf(question, PDF_TEXT)
        return jsonify(
            {"reply": f"{fb}\n\n(catatan server: watsonx error: {e})"}
        ), 200