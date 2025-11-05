import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from PyPDF2 import PdfReader

# watsonx (boleh gagal)
from ibm_watsonx_ai.foundation_models import ModelInference

# ====== load env ======
load_dotenv()

app = Flask(__name__)

# ====== CORS longgar ======
# ini udah izinin semua origin
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=False,
)

# kita PAKSA lagi supaya header selalu ada
@app.after_request
def add_cors_headers(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    return resp


# ====== konfig ======
PDF_PATH = "./Nafhan_Profile.pdf"
WATSONX_APIKEY = os.getenv("WATSONX_APIKEY")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
WATSONX_URL = os.getenv("WATSONX_URL", "https://jp-tok.ml.cloud.ibm.com")

PDF_TEXT = ""   # diisi pas startup


# ====== helper baca pdf ======
def load_pdf_text() -> str:
    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"PDF tidak ditemukan di {PDF_PATH}")

    reader = PdfReader(PDF_PATH)
    parts = [(p.extract_text() or "") for p in reader.pages]
    return "\n".join(parts)


# ====== helper watsonx ======
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


# ====== fallback lokal ======
def simple_answer_from_pdf(question: str, pdf_text: str) -> str:
    q = question.lower()

    if "sekolah" in q or "kuliah" in q:
        return "Di PDF belum ada info pendidikan. Tambahin di PDF biar aku bisa jawab ya 🙂"

    first_line = pdf_text.strip().split("\n")[0][:300] if pdf_text else ""
    if first_line:
        return (
            "Aku ambil dari awal PDF kamu ya:\n\n"
            f"{first_line}\n\n"
            "(watsonx lagi nggak ke-cover / belum diset env di Railway)"
        )

    return "Maaf, aku nggak nemu infonya dan layanan AI lagi nggak bisa dipakai."


# ====== startup: baca pdf ======
try:
    PDF_TEXT = load_pdf_text()
    print("✅ PDF loaded, length:", len(PDF_TEXT))
except Exception as e:
    print("⚠️ gagal load PDF:", e)
    PDF_TEXT = ""


# ====== routes ======
@app.route("/health", methods=["GET"])
def health():
    # akses di browser: https://...railway.app/health
    # HARUS balikin header CORS juga
    return jsonify({"status": "ok"}), 200


@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "portfolio chatbot running"}), 200


@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    # browser kirim OPTIONS (preflight)
    if request.method == "OPTIONS":
        # header CORS sudah ditambahin di after_request
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

    # kalau watsonx belum di-set → fallback
    if llm is None:
        fallback = simple_answer_from_pdf(question, PDF_TEXT)
        return jsonify({"reply": fallback}), 200

    # kalau watsonx ada → coba panggil
    try:
        answer = llm.generate_text(prompt)
        return jsonify({"reply": answer}), 200
    except Exception as e:
        fallback = simple_answer_from_pdf(question, PDF_TEXT)
        return jsonify({
            "reply": f"{fallback}\n\n(catatan: watsonx error: {e})"
        }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    # pakai waitress kalau mau: `waitress-serve --host=0.0.0.0 --port=8080 app:app`
    from waitress import serve
    serve(app, host="0.0.0.0", port=port)
