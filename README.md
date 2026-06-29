# 📄 Buat CV Mu — AI Career Optimizer

Aplikasi web berbasis **Streamlit** yang mengubah CV biasa menjadi materi lamaran kerja yang outstanding, ditenagai **Google Gemini 2.5 Flash**.

Cukup unggah CV + isi posisi yang dituju, AI akan berperan sebagai **HR Psikolog Senior**, **ATS Specialist**, dan **Personal Branding Strategist** sekaligus untuk menghasilkan analisis mendalam, CV teroptimasi (dwibahasa), cover letter, persiapan interview, dan skor kecocokan ATS.

---

## · Fitur Utama

- **▪ Skor Kecocokan ATS** — meter 0–100 + daftar keyword yang cocok & yang masih kurang.
- **🧠 Analisis HR Psikolog** — pembacaan karakter, kekuatan tersembunyi, gap/red flags, dan verdict strategis.
- **🌐 CV Dwibahasa** — versi Bahasa Inggris (rekruter internasional) & Bahasa Indonesia (JobStreet, Glints, LinkedIn ID), keduanya ATS-optimized.
- **✉️ Cover Letter** — ringkas (<500 karakter), modern, dengan penghitung karakter.
- **🤝 Simulasi Interview** — 5 pertanyaan + kerangka jawaban (termasuk metode STAR).
- **! AI Gatekeeper** — menolak otomatis jika kualifikasi benar-benar tidak relevan.
- **📥 Export PDF & TXT** — unduh CV, cover letter, dan interview prep.
- **🌗 Mode Gelap/Terang** — desain neumorphism dengan ikon 3D glossy, responsif untuk mobile.
- **💾 Riwayat Lamaran** — tersimpan otomatis ke Supabase + export CSV.

---

## 🛠️ Tech Stack

| Komponen | Teknologi |
|----------|-----------|
| Frontend & Backend | Streamlit (Python) |
| AI Model | Google Gemini 2.5 Flash (`google-genai`) |
| Database | Supabase (PostgreSQL) |
| Ekstraksi dokumen | PyPDF2, python-docx |
| Export PDF | fpdf2 |
| Deploy | Streamlit Community Cloud |

---

## → Cara Menjalankan (Lokal)

### 1. Prasyarat
- Python 3.10+
- API Key Google Gemini ([dapatkan di sini](https://aistudio.google.com/apikey))
- Project Supabase (opsional, untuk fitur riwayat)

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Konfigurasi secrets
Buat file `.streamlit/secrets.toml`:
```toml
GEMINI_API_KEY = "isi_api_key_gemini"
SUPABASE_URL   = "https://xxxx.supabase.co"
SUPABASE_KEY   = "isi_anon_atau_service_role_key"
```
> Tanpa secrets pun app tetap jalan — API key bisa dimasukkan manual lewat sidebar.

### 4. Jalankan
```bash
streamlit run app.py
```

---

## 🗄️ Setup Database (Supabase)

Jalankan SQL berikut di **Supabase Dashboard → SQL Editor**:

```sql
CREATE TABLE IF NOT EXISTS public.cv_applications (
    id                   BIGSERIAL PRIMARY KEY,
    timestamp            TIMESTAMPTZ NOT NULL DEFAULT now(),
    company_name         TEXT NOT NULL,
    target_position      TEXT NOT NULL,
    status               TEXT NOT NULL CHECK (status IN ('APPROVED', 'REJECTED')),
    cover_letter_snippet TEXT,
    full_output          TEXT
);

CREATE INDEX IF NOT EXISTS idx_cv_applications_timestamp
    ON public.cv_applications (timestamp DESC);

ALTER TABLE public.cv_applications ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow all for anon" ON public.cv_applications;
CREATE POLICY "Allow all for anon"
    ON public.cv_applications
    FOR ALL TO anon
    USING (true) WITH CHECK (true);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.cv_applications TO anon;
GRANT USAGE, SELECT ON SEQUENCE public.cv_applications_id_seq TO anon;
```

---

## ☁️ Deploy ke Streamlit Cloud

1. Push project ke repository GitHub.
2. Buka [share.streamlit.io](https://share.streamlit.io) → **New app** → pilih repo & `app.py`.
3. Masuk **Settings → Secrets**, isi `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`.
4. Deploy. Jika setelah update library muncul error *module not found*, lakukan **Reboot app**.

---

## 📁 Struktur Project

```
buat-cv-mu/
├── app.py              # Seluruh aplikasi (UI + logika AI + DB)
├── requirements.txt    # Daftar dependencies
├── .gitignore          # Mengabaikan secrets & file lokal
└── README.md           # Dokumentasi ini
```

---

## ⚙️ Konfigurasi AI (di `app.py`)

| Parameter | Nilai | Keterangan |
|-----------|-------|------------|
| `model` | `gemini-2.5-flash` | Model AI |
| `temperature` | `0.5` | Kreativitas output |
| `max_output_tokens` | `32768` | Batas panjang output |
| `thinking_budget` | `8192` | Jatah token "berpikir" model |

> **Catatan biaya:** Gemini menagih per token yang benar-benar dihasilkan, bukan sebesar `max_output_tokens`. Menaikkan batas hanya memberi ruang, bukan otomatis menambah biaya. Untuk lebih hemat/cepat, turunkan `thinking_budget` (mis. `1024`, atau `0` untuk mematikan thinking).

---

## 🔒 Catatan Keamanan

- **Jangan pernah** commit `secrets.toml` (sudah diabaikan via `.gitignore`).
- Policy Supabase saat ini (`Allow all for anon`) cocok untuk pemakaian pribadi. Untuk versi multi-user/produk, ganti dengan RLS berbasis `auth.uid()`.
- Field `full_output` berisi data CV pribadi — perlakukan sebagai data sensitif.

---

## 📌 Status

Proyek personal & bahan showcase. Roadmap potensial: autentikasi multi-user, langganan/billing, dashboard analitik, dan font PDF custom (dukungan emoji penuh).

---

_Dibuat dengan ❤️ menggunakan Streamlit & Gemini._
