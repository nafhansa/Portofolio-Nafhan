import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from ibm_watsonx_ai.foundation_models import ModelInference

load_dotenv()

app = Flask(__name__)

# ===================== CORS =========================
# list origin yang boleh
ALLOWED_ORIGINS = [
    "https://nafhan.space",
    "https://www.nafhan.space",
    "http://localhost:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

# aktifkan CORS global dulu
CORS(app, supports_credentials=True)


@app.after_request
def add_cors_headers(resp):
    """
    Ditambahin ke SEMUA response, termasuk OPTIONS.
    Ini yang bikin browser berhenti komplain.
    """
    origin = request.headers.get("Origin")
    if origin in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
        resp.headers["Access-Control-Allow-Credentials"] = "true"
        resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    return resp


# ===================== CONFIG =======================
PDF_PATH = "./Nafhan_Profile.pdf"

WATSONX_APIKEY = os.getenv("WATSONX_APIKEY")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
WATSONX_URL = os.getenv("WATSONX_URL", "https://jp-tok.ml.cloud.ibm.com")

PDF_TEXT = ""  # diisi pas startup


def load_pdf_text() -> str:
    """Baca isi PDF jadi 1 string panjang."""
    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"PDF tidak ditemukan di {PDF_PATH}")
    reader = PdfReader(PDF_PATH)
    pages = [(p.extract_text() or "") for p in reader.pages]
    return "\n".join(pages)


def get_llm() -> ModelInference | None:
    """Balikin watsonx kalau env ada, kalau nggak ya None."""
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
    """Fallback kalau watsonx nggak bisa dipakai."""
    q = question.lower()

    if "sekolah" in q or "kuliah" in q:
        return "Di PDF belum ada bagian sekolah/kuliah. Tambahkan di PDF biar AI bisa jawab ya 🙂"

    snippet = pdf_text.strip().split("\n")[0][:300] if pdf_text else ""
    if snippet:
        return (
            "Aku baca dari PDF kamu:\n\n"
            f"{snippet}\n\n"
            "(kalau mau jawaban lebih detail, aktifkan kredensial watsonx di Railway.)"
        )

    return "Maaf, aku nggak nemu jawabannya di PDF dan watsonx belum aktif."


# =============== LOAD PDF DI STARTUP =================
try:
    PDF_TEXT = load_pdf_text()
    print("✅ PDF loaded, length:", len(PDF_TEXT))
except Exception as e:
    print("⚠️ gagal load PDF:", e)
    PDF_TEXT = ""


# ====================== ROUTES =======================
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "portfolio chatbot running"})


@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    # browser kirim ini dulu
    if request.method == "OPTIONS":
        # header CORS sudah ditambahin di after_request
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

Jika di dokumen tidak ada jawabannya, jawab pakai kalimat ini:
"Maaf, di PDF saya tidak menemukan info itu."

Jawab dalam bahasa Indonesia yang rapi, maksimal 2 paragraf.
""".strip()

    # kalau watsonx belum diset → fallback
    if llm is None:
        reply = simple_answer_from_pdf(question, PDF_TEXT)
        return jsonify({"reply": reply}), 200

    try:
        answer = llm.generate_text(prompt)
        return jsonify({"reply": answer}), 200
    except Exception as e:
        fallback = simple_answer_from_pdf(question, PDF_TEXT)
        return jsonify({
            "reply": f"{fallback}\n\n(catatan server: watsonx error: {e})"
        }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
