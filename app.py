import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import io
from datetime import datetime
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image
from supabase import create_client, Client

# ──────────────────────────────────────────────
# KONFIGURASI HALAMAN
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Buat CV Mu — AI Career Optimizer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ──────────────────────────────────────────────
# LOAD API KEYS (dari Streamlit Secrets)
# ──────────────────────────────────────────────
def load_config():
    gemini_key = None
    supabase_url = None
    supabase_key = None

    if "GEMINI_API_KEY" in st.secrets:
        gemini_key = st.secrets["GEMINI_API_KEY"]
    if "SUPABASE_URL" in st.secrets:
        supabase_url = st.secrets["SUPABASE_URL"]
    if "SUPABASE_KEY" in st.secrets:
        supabase_key = st.secrets["SUPABASE_KEY"]

    return gemini_key, supabase_url, supabase_key

gemini_key, supabase_url, supabase_key = load_config()

# ──────────────────────────────────────────────
# INISIALISASI SUPABASE
# ──────────────────────────────────────────────
@st.cache_resource
def init_supabase(url, key):
    if url and key:
        return create_client(url, key)
    return None

supabase: Client = init_supabase(supabase_url, supabase_key)

# ──────────────────────────────────────────────
# FUNGSI EKSTRAKSI DOKUMEN
# ──────────────────────────────────────────────
def extract_pdf_text(file) -> str:
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text.strip()
    except Exception as e:
        return f"[ERROR membaca PDF: {e}]"

def extract_docx_text(file) -> str:
    try:
        doc = Document(file)
        text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        return text.strip()
    except Exception as e:
        return f"[ERROR membaca DOCX: {e}]"

def extract_cv_text(uploaded_file) -> str:
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        return extract_pdf_text(uploaded_file)
    elif name.endswith(".docx"):
        return extract_docx_text(uploaded_file)
    return "[Format tidak didukung]"

# ──────────────────────────────────────────────
# FUNGSI DATABASE SUPABASE
# ──────────────────────────────────────────────
def save_to_supabase(company: str, position: str, status: str, full_output: str, cover_letter_snippet: str):
    if not supabase:
        return False
    try:
        data = {
            "timestamp": datetime.now().isoformat(),
            "company_name": company,
            "target_position": position,
            "status": status,
            "cover_letter_snippet": cover_letter_snippet[:200],
            "full_output": full_output[:5000]
        }
        supabase.table("cv_applications").insert(data).execute()
        return True
    except Exception as e:
        st.warning(f"Database log gagal: {e}")
        return False

def fetch_history() -> pd.DataFrame:
    if not supabase:
        return pd.DataFrame()
    try:
        response = supabase.table("cv_applications") \
            .select("timestamp, company_name, target_position, status, cover_letter_snippet") \
            .order("timestamp", desc=True) \
            .limit(50) \
            .execute()
        return pd.DataFrame(response.data)
    except Exception:
        return pd.DataFrame()

# ──────────────────────────────────────────────
# CORE: SYSTEM PROMPT "BUAT CV MU"
# ──────────────────────────────────────────────
SYSTEM_PROMPT = """
You are the backend engine of a specialized career optimization application called "Buat CV Mu".
You are an elite corporate recruiter, critical ATS coach, and strict career gatekeeper.

Your job is to process job application materials with the following strict business logic:

═══════════════════════════════════════
STEP 1: GATEKEEPING & MATCHING ANALYSIS
═══════════════════════════════════════

Evaluate compatibility between the CV and the target role STRICTLY and CRITICALLY. Do NOT be a yes-man.

- CASE A (HIGHLY DEVIATED): If qualifications are completely unrelated or impossible to bridge (e.g., fresh graphic design graduate applying for Chief Medical Officer), you MUST output ONLY this and nothing else:
  🚨 [REJECTED BY AI GATEKEEPER]
  [Sharp, professional explanation of why rejected, and what roles they SHOULD target instead.]

- CASE B (SLIGHT MISMATCH / BRIDGEABLE): If there is a gap but transferable skills exist, proceed to Step 2. Emphasize transferable skills and adapt phrasing strategically.

- CASE C (SMOOTH MATCH): Proceed directly to Step 2.

═══════════════════════════════════════
STEP 2: REQUIRED OUTPUT FORMAT
(ONLY for Case B or Case C — never for Case A)
═══════════════════════════════════════

Output EXACTLY using these sections in order. Use the exact headers as written:

### 📝 RECRUITER COMMENTARY
[Honest, concise evaluation of alignment. Note gaps and strengths. Max 150 words.]

---

### 🇬🇧 ATS-OPTIMIZED ENGLISH CV ADJUSTMENTS
[Linear bullet list of rewrite recommendations. Embed job-specific keywords, action verbs, quantifiable metrics. No tables. Structure: Professional Summary → Work Experience → Skills → Education → Achievements]

---

### 🇮🇩 ATS-OPTIMIZED INDONESIAN CV ADJUSTMENTS
[Exact same ATS structure translated and adapted into professional Indonesian syntax. No tables.]

---

### ✉️ CASUAL-PROFESSIONAL COVER LETTER
[Write in INDONESIAN. Tone: profesional tapi santai, modern, persuasif. STRICTLY under 500 characters total including spaces. Count carefully. No greetings like "Dengan Hormat". Start directly with a hook sentence.]

---

### 🤝 HR INTERVIEW ROLEPLAY SIMULATION

**Pertanyaan 1 — Tell me about yourself:**
Rangkaian Jawaban:
- [Strategic bullet point 1]
- [Strategic bullet point 2]
- [Strategic bullet point 3]

**Pertanyaan 2 — [Relevant behavioral question]:**
Rangkaian Jawaban:
- [Framework bullet 1]
- [Framework bullet 2]
- [Framework bullet 3]

**Pertanyaan 3 — [Another behavioral/situational question]:**
Rangkaian Jawaban:
- [Framework bullet 1]
- [Framework bullet 2]
- [Framework bullet 3]

**Pertanyaan 4 — [Technical/role-specific question]:**
Rangkaian Jawaban:
- [Framework bullet 1]
- [Framework bullet 2]
- [Framework bullet 3]

---

### 💾 DATABASE LOG ENTRY

| Timestamp | Company Name | Target Position | Status | Cover Letter Snippet |
|-----------|-------------|-----------------|--------|----------------------|
| {CURRENT_DATETIME} | {COMPANY} | {POSITION} | APPROVED | [First 100 chars of cover letter] |

CRITICAL RULES:
- Never deviate from the output format above.
- The cover letter MUST be under 500 characters. Count again before outputting.
- Always fill the database table row with real values, not placeholders.
- If Case A, output ONLY the rejection block. Nothing else.
"""

# ──────────────────────────────────────────────
# FUNGSI ANALISIS UTAMA
# ──────────────────────────────────────────────
def analyze_application(
    cv_text: str,
    company_name: str,
    position: str,
    extra_info: str,
    job_image=None,
    api_key: str = None
) -> str:

    key_to_use = api_key or gemini_key
    if not key_to_use:
        return "[ERROR] Gemini API Key tidak ditemukan. Masukkan via sidebar atau Streamlit Secrets."

    genai.configure(api_key=key_to_use)

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=SYSTEM_PROMPT
    )

    user_prompt = f"""
CURRENT DATETIME: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
TARGET COMPANY: {company_name}
TARGET POSITION: {position}
ADDITIONAL INFO / NOTES: {extra_info if extra_info else "Tidak ada catatan tambahan."}

USER CV (RAW TEXT):
{cv_text}
"""

    contents = []

    if job_image is not None:
        img = Image.open(job_image)
        contents.append(img)
        contents.append("Analisis gambar screenshot lowongan kerja di atas untuk mengekstrak kualifikasi, requirement, dan keyword penting dari posisi ini.")

    contents.append(user_prompt)

    try:
        response = model.generate_content(
            contents,
            generation_config=genai.GenerationConfig(
                temperature=0.4,
                max_output_tokens=4096,
            )
        )
        return response.text
    except Exception as e:
        return f"[ERROR dari Gemini API]: {str(e)}"

# ──────────────────────────────────────────────
# HELPER: EKSTRAK STATUS DAN SNIPPET
# ──────────────────────────────────────────────
def parse_result(result: str):
    result_upper = result.strip()
    if result_upper.startswith("🚨") or "[REJECTED BY AI GATEKEEPER]" in result:
        status = "REJECTED"
    else:
        status = "APPROVED"

    snippet = ""
    if "✉️" in result and "COVER LETTER" in result.upper():
        parts = result.split("###")
        for part in parts:
            if "COVER LETTER" in part.upper():
                lines = [l.strip() for l in part.split("\n") if l.strip() and not l.strip().startswith("#")]
                if lines:
                    snippet = lines[0][:200]
                break

    return status, snippet

# ──────────────────────────────────────────────
# CUSTOM CSS
# ──────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .main-header h1 { color: #e94560; margin: 0; font-size: 2.2rem; }
    .main-header p { color: #a8b2d8; margin: 0.5rem 0 0 0; font-size: 1rem; }
    .status-approved {
        background: #0d3b2e; border-left: 4px solid #00d4aa;
        padding: 1rem; border-radius: 8px; margin: 1rem 0;
    }
    .status-rejected {
        background: #3b0d0d; border-left: 4px solid #e94560;
        padding: 1rem; border-radius: 8px; margin: 1rem 0;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #e94560, #c23152);
        border: none; border-radius: 8px;
        padding: 0.75rem 2rem; font-size: 1rem;
        font-weight: 700; width: 100%;
        transition: transform 0.2s;
    }
    .stButton > button[kind="primary"]:hover { transform: translateY(-2px); }
    div[data-testid="stExpander"] { border: 1px solid #2d3561; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>📄 Buat CV Mu</h1>
    <p>AI-Powered Career Optimizer · ATS Gatekeeper · Interview Coach</p>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# SIDEBAR: API KEY FALLBACK
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Konfigurasi")
    manual_api_key = st.text_input(
        "Gemini API Key (Fallback)",
        type="password",
        help="Isi jika key belum dikonfigurasi di Streamlit Secrets"
    )
    st.markdown("---")
    st.caption("v1.0.0 · Powered by Gemini 1.5 Pro + Supabase")

    if supabase:
        st.success("✅ Supabase terhubung")
    else:
        st.warning("⚠️ Supabase tidak terhubung")

# ──────────────────────────────────────────────
# MAIN LAYOUT: DUA KOLOM
# ──────────────────────────────────────────────
col_input, col_output = st.columns([1, 1.2], gap="large")

with col_input:
    st.markdown("### 📥 Input Lamaran")

    uploaded_cv = st.file_uploader(
        "1. Upload CV Anda",
        type=["pdf", "docx"],
        help="Format yang diterima: PDF atau DOCX"
    )

    uploaded_jd_image = st.file_uploader(
        "2. Screenshot Lowongan Kerja (Opsional)",
        type=["png", "jpg", "jpeg"],
        help="Upload foto/screenshot dari LinkedIn, Jobstreet, dll."
    )

    st.markdown("---")
    st.caption("📝 Lengkapi detail di bawah ini:")

    company_name = st.text_input(
        "Nama Perusahaan",
        placeholder="Contoh: PT Tokopedia, Google Indonesia",
        value=""
    )
    position = st.text_input(
        "Posisi yang Dilamar",
        placeholder="Contoh: Senior Account Manager, Business Development Manager",
        value=""
    )
    extra_info = st.text_area(
        "Info Tambahan / Catatan Khusus",
        placeholder="Tempel teks deskripsi pekerjaan di sini jika tidak ada gambar, atau tambahkan catatan khusus...",
        height=150
    )

    st.markdown("---")
    analyze_btn = st.button("🚀 Analisis & Optimasi Sekarang", type="primary")

# ──────────────────────────────────────────────
# OUTPUT KOLOM KANAN
# ──────────────────────────────────────────────
with col_output:
    st.markdown("### 📤 Hasil Analisis")

    if analyze_btn:
        # Validasi input
        if not uploaded_cv:
            st.error("❌ Mohon upload file CV terlebih dahulu.")
            st.stop()

        if not company_name.strip() or not position.strip():
            st.error("❌ Nama perusahaan dan posisi wajib diisi.")
            st.stop()

        key_used = manual_api_key or gemini_key
        if not key_used:
            st.error("❌ Gemini API Key tidak ditemukan. Masukkan via sidebar.")
            st.stop()

        with st.spinner("🤖 AI sedang menganalisis profil dan lowongan Anda..."):
            cv_text = extract_cv_text(uploaded_cv)

            if cv_text.startswith("[ERROR"):
                st.error(cv_text)
                st.stop()

            result = analyze_application(
                cv_text=cv_text,
                company_name=company_name,
                position=position,
                extra_info=extra_info,
                job_image=uploaded_jd_image if uploaded_jd_image is not None else None,
                api_key=manual_api_key if manual_api_key else None
            )

        status, snippet = parse_result(result)

        if status == "REJECTED":
            st.markdown('<div class="status-rejected">', unsafe_allow_html=True)
            st.error("🚨 DITOLAK OLEH AI GATEKEEPER")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-approved">', unsafe_allow_html=True)
            st.success("✅ Analisis Selesai — Aset karir Anda siap!")
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(result)

        # Simpan ke Supabase
        saved = save_to_supabase(company_name, position, status, result, snippet)
        if saved:
            st.caption("💾 Log tersimpan ke database.")

        # Download hasil sebagai TXT
        st.download_button(
            label="📥 Download Hasil (.txt)",
            data=result.encode("utf-8"),
            file_name=f"buat_cv_mu_{company_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain"
        )

    else:
        st.info("⬅️ Isi form di sebelah kiri dan klik **Analisis & Optimasi Sekarang** untuk memulai.")

# ──────────────────────────────────────────────
# RIWAYAT LAMARAN (BAWAH)
# ──────────────────────────────────────────────
st.markdown("---")
st.markdown("### 📊 Riwayat Lamaran")

if supabase:
    with st.expander("Lihat Riwayat dari Database", expanded=False):
        df_history = fetch_history()
        if not df_history.empty:
            df_history.columns = ["Waktu", "Perusahaan", "Posisi", "Status", "Cuplikan Cover Letter"]
            st.dataframe(df_history, use_container_width=True)

            csv_export = df_history.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Export Riwayat (.csv)",
                data=csv_export,
                file_name=f"riwayat_lamaran_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("Belum ada riwayat lamaran.")
else:
    st.caption("⚠️ Hubungkan Supabase untuk melihat riwayat lamaran.")
