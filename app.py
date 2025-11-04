import os
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# =========================================================
# 1. CORS: buka lebar dulu biar preflight nggak 502
# =========================================================
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=True,
)

# =========================================================
# 2. Try-import semua yang berat
# =========================================================
# PDF
try:
    from PyPDF2 import PdfReader  # type: ignore
    HAS_PDF = True
except Exception:
    print("⚠️ PyPDF2 tidak tersedia di environment, jalan tanpa baca PDF.")
    HAS_PDF = False

# watsonx
try:
    from ibm_watsonx_ai.foundation_models import ModelInference  # type: ignore
    HAS_WATSONX = True
except Exception:
    print("⚠️ ibm-watsonx-ai tidak tersedia, jalan tanpa LLM.")
    HAS_WATSONX = False

# =========================================================
# 3. config
# =========================================================
PDF_PATH = "./Nafhan_Profile.pdf"
WATSONX_APIKEY = os.getenv("WATSONX_APIKEY")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
WATSONX_URL = os.getenv("WATSONX_URL", "https://jp-tok.ml.cloud.ibm.com")

PDF_TEXT = ""  # akan diisi di startup


# =========================================================
# 4. helper
# =========================================================
def load_pdf_text() -> str:
    """Baca PDF jadi string, tapi jangan bikin server mati."""
    if not HAS_PDF:
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


def get_watsonx():
    """Balikin instance watsonx kalau semua env & libnya ada, kalau nggak ya None."""
    if not HAS_WATSONX:
        return None
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
        print("⚠️ gagal inisiasi watsonx:", e)
        return None


def cors_response_empty():
    """Supaya OPTIONS selalu 200 dan ada header-nya."""
    resp = make_response("", 200)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    return resp


@app.after_request
def add_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    return resp


# =========================================================
# 5. muat PDF sekali
# =========================================================
PDF_TEXT = load_pdf_text()
print("✅ Flask running. Panjang teks PDF:", len(PDF_TEXT))


# =========================================================
# 6. routes
# =========================================================
@app.route("/", methods=["GET", "OPTIONS"])
def index():
    if request.method == "OPTIONS":
        return cors_response_empty()
    return jsonify({"status": "ok", "message": "portfolio chatbot running"})


@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    # preflight
    if request.method == "OPTIONS":
        return cors_response_empty()

    data = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()

    if not question:
        return jsonify({"reply": "Pertanyaannya kosong."}), 200

    # 1) kalau PDF kosong, langsung balas
    if not PDF_TEXT:
        return jsonify(
            {
                "reply": (
                    "Server sudah jalan ✅ tapi PDF belum bisa dibaca atau library PDF belum terinstall. "
                    "Pastikan file Nafhan_Profile.pdf ikut ke Railway dan tambahkan PyPDF2 ke requirements."
                )
            }
        ), 200

    # 2) coba pakai watsonx kalau ada
    llm = get_watsonx()
    if llm is not None:
        prompt = f"""
Kamu adalah asisten yang hanya boleh menjawab dari dokumen berikut.

=== DOKUMEN ===
{PDF_TEXT}
=== AKHIR DOKUMEN ===

Pertanyaan: {question}

Jika tidak ada di dokumen, katakan: "Maaf, di PDF saya tidak menemukan info itu."
Jawab bahasa Indonesia rapi, maks 2 paragraf.
""".strip()
        try:
            answer = llm.generate_text(prompt)
            return jsonify({"reply": answer}), 200
        except Exception as e:
            print("⚠️ watsonx error:", e)
            # lanjut ke fallback di bawah

    # 3) fallback super sederhana: cari kata dari pertanyaan di PDF
    lower_pdf = PDF_TEXT.lower()
    first_token = question.split()[0].lower()
    pos = lower_pdf.find(first_token)

    if pos == -1:
        reply = "Maaf, di PDF aku nggak nemu itu. Tambahin aja di PDF kamu biar bisa dijawab 🙂"
    else:
        start = max(0, pos - 160)
        end = min(len(PDF_TEXT), pos + 320)
        snippet = PDF_TEXT[start:end]
        reply = f"Aku ambil dari PDF kamu:\n\n{snippet}"

    return jsonify({"reply": reply}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
