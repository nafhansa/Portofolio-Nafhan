import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from PyPDF2 import PdfReader
from ibm_watsonx_ai.foundation_models import ModelInference

app = Flask(__name__)

CORS(
    app,
    resources={
        r"/*": {
            "origins": [
                "https://nafhan.space",
                "https://www.nafhan.space",
                "https://portofolio-nafhan-production.up.railway.app",
                "http://localhost:5173",
                "http://localhost:8080",
                "http://127.0.0.1:8080",
            ],
            "allow_headers": ["Content-Type", "Authorization"],
            "methods": ["GET", "POST", "OPTIONS"],
        }
    },
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_PATH = os.path.join(BASE_DIR, "Nafhan_Profile.pdf")

WATSONX_APIKEY = os.environ.get("WATSONX_APIKEY")
WATSONX_PROJECT_ID = os.environ.get("WATSONX_PROJECT_ID")
WATSONX_URL = os.environ.get("WATSONX_URL", "https://jp-tok.ml.cloud.ibm.com")

PDF_TEXT = ""


def load_pdf_text() -> str:
    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"PDF tidak ditemukan di {PDF_PATH}")
    reader = PdfReader(PDF_PATH)
    texts = []
    for page in reader.pages:
        texts.append(page.extract_text() or "")
    return "\n".join(texts)


def get_llm():
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


def fallback_answer(question: str, pdf_text: str) -> str:
    q = question.lower()
    if "sekolah" in q or "kuliah" in q or "kampus" in q:
        return "Di PDF belum ada info pendidikan. Tambahin di PDF kalau mau dijawab detail 🙂"
    first_line = (pdf_text or "").strip().split("\n")[0][:350]
    if first_line:
        return (
            "Ini cuplikan dari PDF kamu:\n\n"
            + first_line
            + "\n\n(Aku pakai fallback karena watsonx belum aktif / error.)"
        )
    return "Maaf, aku nggak nemu jawabannya di PDF dan watsonx belum bisa dipakai."


try:
    PDF_TEXT = load_pdf_text()
    print("✅ PDF loaded, length:", len(PDF_TEXT))
except Exception as e:
    print("⚠️ gagal load PDF:", e)
    PDF_TEXT = ""


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "portfolio chatbot running"}), 200


@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return ("", 204)

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

Jawab dalam bahasa Indonesia yang rapi, maksimal 2 paragraf.
""".strip()

    if llm is None:
        return jsonify({"reply": fallback_answer(question, PDF_TEXT)}), 200

    try:
        answer = llm.generate_text(prompt)
        return jsonify({"reply": answer}), 200
    except Exception as e:
        fb = fallback_answer(question, PDF_TEXT)
        return jsonify({"reply": f"{fb}\n\n(catatan: watsonx error: {e})"}), 200
