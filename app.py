import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
from PyPDF2 import PdfReader

# 1. Konfigurasi API Key Gemini
if "GEMINI_API_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
elif "GEMINI_API_KEY" in st.secrets:
    # Digunakan jika Anda dideploy di Streamlit Community Cloud
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.warning("Catatan: Pastikan Anda telah memasukkan GEMINI_API_KEY di pengaturan Cloud Environment Anda.")

# 2. Database Lokal/Cloud kompatibel Excel
DB_FILE = "ats_cv_database.csv"

def save_to_database(company, position, cl_output, raw_result):
    new_data = {
        "Timestamp": [pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")],
        "Company Name": [company],
        "Target Position": [position],
        "Generated Cover Letter": [cl_output],
        "Full AI Output": [raw_result]
    }
    df_new = pd.DataFrame(new_data)
    if not os.path.isfile(DB_FILE):
        df_new.to_csv(DB_FILE, index=False)
    else:
        df_new.to_csv(DB_FILE, mode='a', header=False, index=False)

def extract_pdf_text(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

# 3. Prompt Engineering Teroptimasi ATS
def generate_ats_career_assets(cv_content, company_name, position, company_info=""):
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are an expert ATS (Applicant Tracking System) Optimization Engineer and Corporate Recruiter. 
    Analyze the provided User CV and tailor it perfectly to pass parsing algorithms for the target company and position.

    TARGET COMPANY: {company_name}
    TARGET POSITION: {position}
    COMPANY RESEARCH CONTEXT: {company_info}
    USER CV RAW TEXT:
    {cv_content}

    ------------------
    CRITICAL INSTRUCTIONS FOR ATS COMPLIANCE:
    1. ATS systems require clear, standard section headings ("Work Experience", "Skills", "Education", "Summary"). Do not use creative titles.
    2. ATS systems scan for specific keywords. Identify high-frequency keywords related to {position} and embed them naturally.
    3. No multi-column layouts, tables, images, or progress bars should be recommended. Output must be purely linear text structured top-to-bottom.

    REQUIRED OUTPUTS:

    [OUTPUT 1: ATS_OPTIMIZED_ENGLISH_CV]
    Rewrite the core sections of the user's CV in professional, high-impact ENGLISH. Optimize the "Summary", "Core Competencies/Skills", and "Professional Experience" using action verbs and quantifiable metrics (e.g., increased efficiency by X%, managed Y projects). Format this as clean, copy-pasteable text that an ATS scanner can read flawlessly.

    [OUTPUT 2: ATS_OPTIMIZED_INDONESIAN_CV]
    Translate and adapt the exact same ATS-optimized structure into professional INDONESIAN, adhering to modern professional syntax.

    [OUTPUT 3: CASUAL_PROFESSIONAL_COVER_LETTER]
    Write a short cover letter in INDONESIAN.
    - Tone: Professional but casual/approachable (tidak terlalu kaku, gunakan gaya bahasa modern yang persuasif).
    - CONSTRAINT: It MUST be under 500 characters total. Keep it brief, high-impact, and conversational.

    [OUTPUT 4: HR_INTERVIEW_SIMULATION]
    Generate an interactive HR Interview prep block based on this tailored CV:
    - Point 1: "Tell me about yourself" question customized to frame the user as the perfect match for {company_name}. Provide bullet-point answer framework.
    - Point 2 to 5: Four general HR screening questions with actionable bullet-point talking points for the user to develop.
    """
    
    response = model.generate_content(prompt)
    return response.text

# 4. Antarmuka Web App (Streamlit Layout)
st.set_page_config(page_title="Cloud ATS Optimizer", layout="wide")
st.title("🌐 Cloud AI CV & ATS Optimizer")
st.caption("Aplikasi berbasis web untuk transformasi CV standar menjadi ATS-friendly dan pembuatan Cover Letter.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📥 Data Input (Tanpa Instalasi)")
    uploaded_file = st.file_uploader("Upload CV Lama Anda (PDF)", type=["pdf"])
    company_name = st.text_input("Nama Perusahaan Target (Contoh: GoTo, Telkom)")
    position = st.text_input("Posisi/Role Terperinci")
    
    manual_mode = st.checkbox("Saya ingin menambahkan data riset perusahaan secara manual")
    company_info = ""
    if manual_mode:
        company_info = st.text_area("Tulis info tambahan produk/budaya kerja perusahaan di sini:")

    # Input API Key opsional di UI jika tidak di-set di environment cloud
    ui_api_key = st.text_input("Masukkan Gemini API Key Anda (Jika belum dikonfigurasi di cloud system)", type="password")
    if ui_api_key:
        genai.configure(api_key=ui_api_key)

    submit_btn = st.button("Generate & Optimasi ATS", type="primary")

with col2:
    st.subheader("📤 Hasil Optimasi ATS & Database")
    if submit_btn:
        if not uploaded_file or not company_name or not position:
            st.warning("Harap isi file CV, Nama Perusahaan, dan Posisi Target.")
        else:
            with st.spinner("Sistem sedang memproses data teks untuk ramah ATS..."):
                cv_text = extract_pdf_text(uploaded_file)
                output_content = generate_ats_career_assets(cv_text, company_name, position, company_info)
                
                # Ekstrak perkiraan cover letter untuk disimpan ke database
                save_to_database(company_name, position, "Lihat detail output", output_content)
                
                st.success("Sukses! Data Anda telah ditambahkan ke database cloud lokal (`ats_cv_database.csv`).")
                st.markdown(output_content)
                
                # Fitur tambahan cloud untuk download file database langsung dari website
                if os.path.exists(DB_FILE):
                    df_download = pd.read_csv(DB_FILE)
                    csv_data = df_download.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Unduh Database Excel/CSV Anda", data=csv_data, file_name="my_career_database.csv", mime="text/csv")
