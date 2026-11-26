# 📝 GitHub to Blogspot Auto Publisher

Sistem otomatisasi untuk memposting artikel Markdown (`.md`) dari GitHub langsung ke **Blogger / Blogspot** secara gratis menggunakan **GitHub Actions**.

Sistem ini dirancang dengan **Arsitektur Dual-Method (Fallback Otomatis)**:
1. **Metode Utama (Blogger API v3):** Memposting artikel lengkap dengan format HTML, label/kategori, dan status terbit.
2. **Metode Cadangan (Mail-to-Blogger):** Jika Blogger API bermasalah (token kadaluarsa, kuota habis, atau kendala jaringan), sistem **otomatis beralih** mengirimkan artikel lewat email resmi Blogspot agar postingan tetap terbit!

---

## 📁 Struktur Repositori

```text
├── .github/
│   └── workflows/
│       └── publish.yml       # Workflow GitHub Actions otomatis
├── posts/
│   └── contoh-artikel.md    # Tempat menyimpan artikel Markdown Anda
├── scripts/
│   └── publish.py           # Skrip otomatisasi publikasi & fallback
├── .gitignore
├── requirements.txt
└── README.md
```

---

## ⚙️ Panduan Pengaturan (GitHub Secrets)

Buka repositori ini di GitHub, lalu masuk ke:
**Settings** > **Secrets and variables** > **Actions** > **New repository secret**.

### 1. Pengaturan Metode Cadangan (Mail-to-Blogger) — *Paling Mudah (2 Menit)*
Metode ini sangat disarankan untuk disiapkan terlebih dahulu karena sangat mudah:
1. Buka dashboard [Blogger](https://www.blogger.com) Anda.
2. Masuk ke menu **Setelan (Settings)** > scroll ke bagian **Email** > klik **Memposting menggunakan email**.
3. Pilih **Publikasikan email segera**, lalu tentukan kata rahasia (contoh: `artikelrahasia`).
4. Simpan. Alamat email rahasia Anda akan menjadi `namablog.katasandi@blogger.com`.
5. Masukkan Secrets berikut di GitHub:
   - `BLOGGER_SECRET_EMAIL`: Alamat email rahasia Blogger Anda di atas.
   - `SENDER_EMAIL`: Alamat Gmail Anda.
   - `SENDER_APP_PASSWORD`: 16 digit Sandi Aplikasi (*App Password*) Google Anda (buat di [Google Security > App Passwords](https://myaccount.google.com/apppasswords)).

---

### 2. Pengaturan Metode Utama (Google Blogger API v3) — *Fitur Lengkap*
1. **Blog ID:** Buka dashboard Blogger Anda di browser, lihat angka di akhir URL:
   `https://www.blogger.com/blog/posts/`**`1234567890123456789`** (angka ini adalah Blog ID Anda).
2. **Google Cloud Console:**
   - Buat proyek baru di [Google Cloud Console](https://console.cloud.google.com/).
   - Aktifkan **Blogger API v3** di *APIs & Services > Library*.
   - Buat OAuth Client ID (Web Application atau Desktop App) di *Credentials*.
3. Masukkan Secrets berikut di GitHub:
   - `BLOGGER_BLOG_ID`: ID blog Anda.
   - `BLOGGER_CLIENT_ID`: OAuth Client ID dari Google Cloud.
   - `BLOGGER_CLIENT_SECRET`: OAuth Client Secret.
   - `BLOGGER_REFRESH_TOKEN`: Refresh token OAuth akun Anda.

> **Catatan:** Jika Anda belum mengisi data Blogger API v3, sistem akan langsung dan otomatis menggunakan jalur **Mail-to-Blogger**.

---

## ✍️ Cara Menulis dan Mempublikasikan Artikel

1. Buat berkas baru di dalam folder `posts/`, contoh: `posts/tips-produktif.md`.
2. Format penulisan menggunakan Markdown dengan header (frontmatter) opsional:

```markdown
---
title: "5 Tips Produktif Bekerja dari Rumah"
labels: ["Produktivitas", "Tips", "Kerja"]
status: "publish"
---

# 5 Tips Produktif Bekerja dari Rumah

Berikut adalah beberapa tips yang bisa Anda terapkan...
```

3. Simpan dan lakukan Commit & Push:
```powershell
git add posts/tips-produktif.md
git commit -m "Posting artikel tips produktif"
git push
```

4. **Selesai!** GitHub Actions akan otomatis mendeteksi berkas baru dan mempublikasikannya ke Blogspot Anda dalam hitungan detik.

---

## 🚀 Menjalankan Manual (Workflow Dispatch)
Anda juga bisa memicu publikasi secara manual tanpa push:
1. Masuk ke tab **Actions** di repositori GitHub Anda.
2. Klik workflow **Auto Publish to Blogspot** di sebelah kiri.
3. Klik tombol **Run workflow** (Anda dapat memasukkan path berkas tertentu atau mengosongkannya untuk semua berkas).
