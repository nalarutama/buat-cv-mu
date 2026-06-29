import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
from PyPDF2 import PdfReader
from PIL import Image

# 1. Konfigurasi API Key Gemini
if "GEMINI_API_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
elif "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

DB_FILE = "ats_cv_database.csv"

def save_to_database(company, position, status, output):
    new_data = {
        "Timestamp": [pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")],
        "Company Name": [company],
        "Target Position": [position],
        "Status AI": [status],
        "Full AI Output": [output]
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

# 2. Pemrosesan Multimodal dengan Perbaikan Jalur Model (Explicit Model Path)
def process_career_application(cv_content, company_name, position, company_info, job_image):
    # PERBAIKAN: Menggunakan 'models/gemini-1.5-flash' untuk mencegah error NotFound
    model = genai.GenerativeModel('models/gemini-1.5-flash')
    
    contents = []
    
    # Memproses gambar jika diunggah oleh pengguna
    if job_image is not None:
        img = Image.open(job_image)
        contents.append(img)
        image_instruction = "Analisis juga gambar screenshot lowongan kerja yang dilampirkan untuk mengekstrak kualifikasi kunci."
    else:
        image_instruction = "Tidak ada gambar lowongan yang dilampirkan, andalkan teks input manual."

    prompt = f"""
    You are an elite corporate recruiter and critical ATS career coach. 
    Analyze the User's CV and match it against the Target Company and Target Position.

    TARGET COMPANY: {company_name}
    TARGET POSITION: {position}
    MANUAL COMPANY/JOB INFO: {company_info}
    {image_instruction}

    USER CV RAW TEXT:
    {cv_content}

    ------------------
    STEP 1: GATEKEEPING & MATCHING ANALYSIS (CRITICAL)
    Evaluate the compatibility strictly. Do not be a 'yes-man'.
    - CASE A (HIGHLY DEVIATED): If the user's CV qualifications and experience are completely unrelated, impossible, or drastically mismatch the target role, you MUST reject the request. Start your response immediately with [REJECT] followed by a sharp, professional explanation of why it is rejected and what type of roles they should target instead. Do not generate the CV or cover letter.
    - CASE B (SLIGHT MISMATCH / LACK OF EXPERIENCE): If there is a gap but it's bridgeable, study the CV deeply. Highlight transferable skills, adapt phrasing to match the industry keywords, and craft the content to fit the specification.
    - CASE C (SMOOTH MATCH): If it matches well, proceed smoothly to build high-impact assets.

    ------------------
    STEP 2: REQUIRED OUTPUT FORMAT (Only if NOT rejected):
    If the application is feasible (Case B or C), provide:

    [COMMENTARY]
    Provide a brief, honest evaluation regarding the alignment between the CV and the target role.

    [OUTPUT 1: ATS_OPTIMIZED_ENGLISH_CV]
    Linear structured CV adjustments in professional English.

    [OUTPUT 2: ATS_OPTIMIZED_INDONESIAN_CV]
    Linear structured CV adjustments in professional Indonesian.

    [OUTPUT 3: CASUAL_PROFESSIONAL_COVER_LETTER]
    Cover letter in Indonesian, professional yet casual tone, STRICTLY under 500 characters.

    [OUTPUT 4: HR_INTERVIEW_SIMULATION]
    - Point 1: Customized "Tell me about yourself" framework.
    - Points 2-5: General and specific HR screening questions with bullet-pointed response strategies.
    """
    contents.append(prompt)
    
    response = model.generate_content(contents)
    return response.text

# 3. Antarmuka Web App Streamlit
st.set_page_config(page_title="Cloud ATS Smart Optimizer", layout="wide")
st.title("🌐 Smart AI CV & ATS Gatekeeper")
st.caption("Aplikasi cerdas penganalisis kecocokan karir menggunakan berkas CV dan gambar lowongan kerja.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📥 Data Input Application")
    uploaded_file = st.file_uploader("1. Upload CV Lama Anda (PDF)", type=["pdf"])
    uploaded_image = st.file_uploader("2. Upload Foto/Screenshot Lowongan Kerja (Opsional)", type=["png", "jpg", "jpeg"])
    
    st.markdown("---")
    st.caption("Lengkapi detail di bawah jika tidak tertera jelas di gambar lowongan:")
    company_name = st.text_input("Nama Perusahaan Target", value="Belum Diketahui")
    position = st.text_input("Posisi/Role Terperinci", value="Belum Diketahui")
    company_info = st.text_area("Info Tambahan / Catatan Khusus Kerja:")
    
    ui_api_key = st.text_input("Masukkan Gemini API Key Anda (Pintu Darurat Fallback)", type="password")
    if ui_api_key:
        genai.configure(api_key=ui_api_key)

    submit_btn = st.button("Analisis & Optimasi Aplikasi", type="primary")

with col2:
    st.subheader("📤 Hasil Analisis & Generasi Dokumen")
    if submit_btn:
        if not uploaded_file:
            st.warning("Mohon unggah dokumen file CV Anda terlebih dahulu.")
        else:
            with st.spinner("AI sedang menimbang kompetensi dan menganalisis berkas..."):
                cv_text = extract_pdf_text(uploaded_file)
                
                result = process_career_application(cv_text, company_name, position, company_info, uploaded_image)
                
                if result.strip().startswith("[REJECT]"):
                    st.error("🚨 Pengajuan Ditolak oleh Sistem AI (Kualifikasi Tidak Sinkron)")
                    st.write(result)
                    save_to_database(company_name, position, "REJECTED", result)
                else:
                    st.success("✅ Analisis Berhasil! Aset karir Anda telah siap.")
                    st.markdown(result)
                    save_to_database(company_name, position, "APPROVED", result)
                    
                if os.path.exists(DB_FILE):
                    df_download = pd.read_csv(DB_FILE)
                    csv_data = df_download.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Unduh Log Database Karir (.csv)", data=csv_data, file_name="smart_career_database.csv", mime="text/csv")
