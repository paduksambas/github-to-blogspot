import os
import sys
import json
import time
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime

# Import helper publikasi dari publish.py
try:
    from publish import publish_post
except ImportError:
    import sys
    sys.path.append(os.path.dirname(__file__))
    from publish import publish_post

HISTORY_FILE = "published_history.json"

# Sumber RSS berita Indonesia terpercaya & terupdate
RSS_FEEDS = [
    "https://news.google.com/rss?hl=id&gl=ID&ceid=ID:id",
    "https://www.cnnindonesia.com/nasional/rss",
    "https://news.detik.com/rss",
    "https://www.antaranews.com/rss/terkini.xml"
]


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def fetch_news_from_rss(feed_url):
    articles = []
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        req = urllib.request.Request(feed_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
            root = ET.fromstring(content)
            
            # Cari item di channel RSS
            items = root.findall(".//item")
            for item in items[:15]:
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                description = item.findtext("description", "").strip()
                pub_date = item.findtext("pubDate", "").strip()
                
                # Bersihkan tag HTML sederhana dari deskripsi jika ada
                clean_desc = re.sub(r"<[^>]+>", "", description).strip()
                
                if title and link:
                    articles.append({
                        "title": title,
                        "link": link,
                        "description": clean_desc,
                        "pub_date": pub_date
                    })
    except Exception as e:
        print(f"[!] Gagal mengambil RSS dari {feed_url}: {e}")
    return articles


def get_fresh_article(history):
    """
    Mengambil 1 artikel berita terbaru yang belum pernah diposting sebelumnya.
    """
    for feed in RSS_FEEDS:
        print(f"[*] Memeriksa sumber berita: {feed}")
        items = fetch_news_from_rss(feed)
        for it in items:
            title_key = it["title"].lower().strip()
            # Cek apakah judul atau URL sudah ada di history
            if title_key not in history and it["link"] not in history:
                return it
    return None


def rewrite_with_gemini(api_key, original_news):
    """
    Menulis ulang berita menggunakan Google Gemini Flash
    agar unik, ramah SEO, berbobot, dan menghindari penalti duplikat konten.
    """
    candidate_models = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-flash-latest"]
    
    prompt = f"""
Anda adalah jurnalis dan editor berita profesional Indonesia untuk portal berita terkemuka.
Tugas Anda adalah menulis ulang (rewrite) topik berita berikut menjadi artikel blog berita yang lengkap, menarik, mendalam, dan ramah SEO (Search Engine Optimization).

Data Berita Asli:
- Judul: {original_news['title']}
- Ringkasan/Fakta: {original_news['description']}
- Sumber Asal: {original_news['link']}

Ketentuan Penulisan:
1. Buat judul baru yang memikat (click-worthy), bernada informatif dan viral, tanpa hoax.
2. Tulis isi artikel secara komprehensif, minimal 4 hingga 6 paragraf dengan alur cerita yang runtut:
   - Paragraf Pembuka: Bahas mengapa peristiwa ini sedang ramai dibicarakan publik dan poin utamanya.
   - Paragraf Isi (Gunakan sub-heading Markdown ##): Paparkan rincian fakta, kronologi, atau konteks kejadian secara runtut.
   - Paragraf Dampak/Tanggapan: Berikan sudut pandang dampak peristiwa atau tanggapan masyarakat.
   - Paragraf Penutup: Rangkuman dan ajakan interaktif untuk pembaca di kolom komentar.
   - Cantumkan catatan referensi sumber resmi di akhir tulisan.
3. Tentukan 3 sampai 5 label/kategori artikel yang relevan (misal: ["Berita", "Viral", "Nasional", "Tren"]).
4. Format output WAJIB HANYA berupa JSON murni tanpa markdown fence backticks (```json ... ```):

{{
  "title": "Judul Baru Artikel yang Menarik",
  "labels": ["Kategori1", "Kategori2", "Kategori3"],
  "content": "Isi artikel dalam format Markdown lengkap dengan heading ##, paragraf, dan list jika relevan..."
}}
"""

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2048
        }
    }

    last_error = None
    for model in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        print(f"[*] Mencoba rewrite dengan model: {model}...")
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=45) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                candidate = res_data["candidates"][0]["content"]["parts"][0]["text"]
                
                # Bersihkan format jika ada pembungkus ```json
                cleaned = candidate.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()

                return json.loads(cleaned)
        except Exception as e:
            last_error = e
            print(f"[!] Gagal dengan {model}: {e}. Mencoba model alternatif...")

    raise last_error


def slugify(text):
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:50].strip("-")


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY tidak ditemukan di environment.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("🤖 MEMULAI AUTO NEWS SCANNER & AI REWRITER")
    print("=" * 60)

    history = load_history()
    print(f"[*] Riwayat postingan tersimpan: {len(history)} artikel.")

    news_item = get_fresh_article(history)
    if not news_item:
        print("[INFO] Belum ada berita baru yang belum diposting saat ini.")
        sys.exit(0)

    print(f"\n[+] Berita hangat ditemukan: '{news_item['title']}'")
    print(f"[+] Sumber: {news_item['link']}")
    print("[*] Menulis ulang dengan Google Gemini AI...")

    try:
        rewritten = rewrite_with_gemini(api_key, news_item)
    except Exception as e:
        print(f"[ERROR] Gagal menulis ulang dengan Gemini: {e}")
        sys.exit(1)

    title = rewritten.get("title", news_item["title"])
    labels = rewritten.get("labels", ["Berita", "Viral", "Trending"])
    content = rewritten.get("content", "")

    today_str = datetime.now().strftime("%Y-%m-%d")
    slug = slugify(title)
    file_name = f"{today_str}-{slug}.md"
    file_path = os.path.join("posts", file_name)

    os.makedirs("posts", exist_ok=True)

    # Susun file Markdown dengan Frontmatter
    md_post = f"""---
title: "{title}"
labels: {json.dumps(labels, ensure_ascii=False)}
status: "publish"
date: "{today_str}"
original_source: "{news_item['link']}"
---

{content}
"""

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(md_post)

    print(f"[+] Artikel baru berhasil dibuat: {file_path}")
    print(f"[+] Judul Baru: {title}")

    # Terbitkan artikel ke Blogspot
    print("\n[*] Menerbitkan ke Blogspot via skrip publish...")
    success = publish_post(file_path)

    if success:
        # Catat ke history
        history[news_item["title"].lower().strip()] = {
            "date": datetime.now().isoformat(),
            "published_title": title,
            "file": file_path,
            "original_url": news_item["link"]
        }
        save_history(history)
        print(f"\n🎉 Berita viral '{title}' berhasil dipublikasikan ke Blogspot dan disimpan di history!")
    else:
        print("\n[!] Gagal menerbitkan artikel ke Blogspot.")
        sys.exit(1)


if __name__ == "__main__":
    main()
