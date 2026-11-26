# 📰 GitHub to Blogspot - Auto News Bot & Publisher

Sistem otomatisasi berita pintar yang berjalan 24/7 di **Cloud GitHub Actions**. Sistem ini secara otomatis memindai topik berita viral/hangat di Indonesia, menulis ulang (*rewrite*) menggunakan **Google Gemini 2.5 Flash AI** agar unik dan ramah SEO, lalu menerbitkannya ke **Blogger / Blogspot** secara terjadwal.

---

## 🚀 Fitur Utama

1. **Auto Scanner Berita Viral:** Mengambil berita terkini dari RSS feed terpercaya (Google News Indonesia, CNN Indonesia, Detik, Antara News).
2. **AI Rewriter (Google Gemini 2.5 Flash):**
   - Menghasilkan judul berita baru yang memikat (*click-worthy*).
   - Menulis ulang artikel mendalam 4–6 paragraf dengan format Markdown yang rapi.
   - Menentukan label/kategori artikel secara otomatis.
   - Mencegah penalti plagiarisme & ramah Google AdSense.
3. **Sistem Anti-Duplikat (`published_history.json`):** Mencegah berita yang sama terbit dua kali.
4. **Jadwal Terbit Otomatis (Cron Schedule):**
   - 🌅 **Pagi:** 08:00 WIB
   - ☀️ **Siang:** 13:00 WIB
   - 🌇 **Sore:** 18:00 WIB
   - 🌙 **Malam:** 21:00 WIB
   - *(Bisa juga dipicu manual kapan saja dengan 1 klik via tombol "Run workflow")*
5. **Dual-Method Publisher:**
   - Metode Utama: Google Blogger API v3.
   - Metode Cadangan: Mail-to-Blogger (SMTP Email) dengan *fallback* otomatis.

---

## 📁 Struktur Repositori

```text
├── .github/
│   └── workflows/
│       ├── auto_news.yml      # Workflow bot berita otomatis terjadwal
│       └── publish.yml        # Workflow publikasi manual/push biasa
├── posts/                     # Tempat arsip artikel berita Markdown (.md)
├── scripts/
│   ├── auto_news.py          # Bot pencari berita & pemanggil Gemini AI
│   └── publish.py            # Mesin pengirim artikel ke Blogspot
├── published_history.json     # Catatan riwayat artikel yang sudah terbit
├── requirements.txt
└── README.md
```

---

## ⚙️ Kunci Rahasia (GitHub Repository Secrets)

Sistem ini membutuhkan secrets berikut di **Settings > Secrets and variables > Actions**:
- `GEMINI_API_KEY`: API Key dari Google AI Studio.
- `BLOGGER_SECRET_EMAIL`: Email rahasia Blogspot (`user.kata@blogger.com`).
- `SENDER_EMAIL`: Akun Gmail pengirim artikel.
- `SENDER_APP_PASSWORD`: 16 digit Sandi Aplikasi Google.

---

## 🕹️ Cara Menjalankan Manual Kapan Saja
Jika Anda ingin bot langsung mencari dan memposting berita viral sekarang juga tanpa menunggu jam jadwal:
1. Buka tab **Actions** di repositori GitHub Anda.
2. Pilih workflow **Auto News Bot (Scanner, AI Rewriter & Publisher)** di sebelah kiri.
3. Klik tombol **Run workflow** berwarna hijau.
4. Bot akan langsung bekerja dalam ~15-20 detik dan artikel berita viral baru akan langsung tayang di blog Anda!
