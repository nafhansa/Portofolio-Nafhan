import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from PyPDF2 import PdfReader

# watsonx optional
try:
    from ibm_watsonx_ai.foundation_models import ModelInference
except Exception:
    ModelInference = None

load_dotenv()

app = Flask(__name__)

# CORS longgar dulu aja biar gampang debug
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
)

PDF_PATH = "./Nafhan_Profile.pdf"

WATSONX_APIKEY = os.getenv("WATSONX_APIKEY")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
WATSONX_URL = os.getenv("WATSONX_URL", "https://jp-tok.ml.cloud.ibm.com")

PDF_TEXT = ""


def load_pdf_text() -> str:
    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"PDF tidak ditemukan di {PDF_PATH}")
    reader = PdfReader(PDF_PATH)
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def get_llm():
    """balikin watsonx kalau env-nya ada, kalau gak ada balikin None"""
    if not (WATSONX_APIKEY and WATSONX_PROJECT_ID):
        return None
    if ModelInference is None:
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
        return "Di PDF belum ada info sekolah/kuliah. Tambahkan ke PDF ya 🙂"

    snippet = pdf_text[:400] if pdf_text else ""
    if snippet:
        return f"Aku nemu ini di PDF kamu:\n\n{snippet}\n\n(ini fallback lokal karena watsonx nggak jalan)."
    return "Maaf, aku nggak nemu di PDF dan watsonx nggak aktif."


# load pdf pas start container
try:
    PDF_TEXT = load_pdf_text()
    print("✅ PDF loaded, length:", len(PDF_TEXT))
except Exception as e:
    print("⚠️ gagal load PDF:", e)
    PDF_TEXT = ""


@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "portfolio chatbot running"})


@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()

    if not question:
        return jsonify({"reply": "Pertanyaannya kosong."}), 200

    prompt = f"""
Kamu adalah asisten yang hanya boleh menjawab dari dokumen berikut.

=== DOKUMEN ===
{PDF_TEXT}
=== AKHIR DOKUMEN ===

Pertanyaan pengguna: "{question}"

Jika di dokumen tidak ada jawabannya, jawab:
"Maaf, di PDF saya tidak menemukan info itu."

Jawab rapi pakai bahasa Indonesia, maksimal 2 paragraf.
""".strip()

    llm = get_llm()
    if llm is None:
        # fallback lokal
        return jsonify({"reply": simple_answer_from_pdf(question, PDF_TEXT)}), 200

    try:
        answer = llm.generate_text(prompt)
        return jsonify({"reply": answer}), 200
    except Exception as e:
        fallback = simple_answer_from_pdf(question, PDF_TEXT)
        return jsonify({"reply": f"{fallback}\n\n(catatan: watsonx error: {e})"}), 200


if __name__ == "__main__":
    # kalau kamu jalanin lokal: python app.py
    port = int(os.environ.get("PORT", 8080))
    # jalankan pakai waitress di docker (di Dockerfile kita override juga)
    from waitress import serve
    serve(app, host="0.0.0.0", port=port)
