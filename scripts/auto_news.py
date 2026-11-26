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
            
            items = root.findall(".//item")
            for item in items[:15]:
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                description = item.findtext("description", "").strip()
                pub_date = item.findtext("pubDate", "").strip()
                
                # Deteksi gambar jika tersedia di RSS (enclosure / media / img tag)
                image_url = ""
                enclosure = item.find("enclosure")
                if enclosure is not None and "image" in enclosure.get("type", ""):
                    image_url = enclosure.get("url", "")
                
                if not image_url:
                    img_match = re.search(r'src=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']', description, re.IGNORECASE)
                    if img_match:
                        image_url = img_match.group(1)

                clean_desc = re.sub(r"<[^>]+>", "", description).strip()
                
                if title and link:
                    articles.append({
                        "title": title,
                        "link": link,
                        "description": clean_desc,
                        "pub_date": pub_date,
                        "rss_image": image_url
                    })
    except Exception as e:
        print(f"[!] Gagal mengambil RSS dari {feed_url}: {e}")
    return articles


def get_fresh_article(history):
    for feed in RSS_FEEDS:
        print(f"[*] Memeriksa sumber berita: {feed}")
        items = fetch_news_from_rss(feed)
        for it in items:
            title_key = it["title"].lower().strip()
            if title_key not in history and it["link"] not in history:
                return it
    return None


def rewrite_with_gemini(api_key, original_news):
    """
    Menulis ulang berita dengan gaya jurnalisme manusia profesional (Anti-Bot Standard)
    dan menghasilkan prompt thumbnail visual.
    """
    candidate_models = [
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.8-flash",
        "gemini-3.6-flash",
        "gemini-3.7-flash",
        "gemini-3.5-flash",
        "gemini-3-flash-preview"
    ]
    
    prompt = f"""
Anda adalah jurnalis dan editor berita investigasi profesional untuk portal berita 'Paduka Sambas'.
Tugas Anda adalah menulis ulang topik berita berikut menjadi artikel berita yang berbobot, mendalam, dan 100% lolos deteksi algoritma bot/AI Google (mengikuti standar Google Helpful Content E-E-A-T).

Data Berita Asli:
- Judul Asal: {original_news['title']}
- Fakta Peristiwa: {original_news['description']}
- Sumber Asal: {original_news['link']}

PEDOMAN GAYA BAHASA ANTI-BOT (WAJIB DIIKUTI):
1. RITME KALIMAT ALAMI (Burstiness): Variasikan panjang kalimat. Gunakan kalimat pendek yang lugas, diselingi kalimat majemuk. Hindari kalimat monoton yang seragam.
2. DILARANG KERAS MENGGUNAKAN KATA KLISE AI:
   - JANGAN PERNAH gunakan: "Di era digital ini...", "Kesimpulannya...", "Penting untuk diingat bahwa...", "Tentu saja...", "Mari kita telusuri...".
   - GUNAKAN kosakata jurnalistik hidup: "Usut punya usut...", "Fakta di lapangan mengungkap...", "Sorotan publik tertuju pada...", "Tak butuh waktu lama hingga...", "Menanggapi hal tersebut...".
3. STRUKTUR ARTIKEL LENGKAP:
   - Paragraf Pembuka: Langsung sorot inti berita paling mengejutkan/hangat dalam 2-3 kalimat tajam.
   - Sub-heading 1 (## Fakta dan Kronologi Kejadian): Paparkan rincian fakta secara runtut.
   - Sisipkan setidaknya satu kutipan narasumber dalam format blockquote Markdown:
     > *"Pernyataan atau kutipan penting narasumber di sini,"* tegas pihak terkait.
   - Sub-heading 2 (## Catatan Redaksi: Dampak bagi Masyarakat): Tulis analisis sudut pandang mendalam mengapa isu ini penting bagi publik.
   - Paragraf Penutup & Diskusi: Pertanyaan interaktif memancing komentar pembaca blog.
   - Cantumkan referensi sumber di baris paling akhir.
4. TENTUKAN THUMBNAIL VISUAL:
   - Buat `image_prompt`: Deskripsi gambar jurnalistik realistis dalam bahasa Inggris (15-20 kata) yang menggambarkan peristiwa tersebut secara visual dan dramatis (contoh: "indonesian news journalism photography of government press conference, realistic high resolution, 8k").
5. TENTUKAN 3-4 LABEL: (contoh: ["Berita", "Viral", "Nasional", "Politik"]).

FORMAT OUTPUT HANYA JSON MURNI TANPA BACKTICKS (```json ... ```):
{{
  "title": "Judul Baru yang Menggugah dan Berbobot",
  "labels": ["Kategori1", "Kategori2", "Kategori3"],
  "image_prompt": "English descriptive prompt for realistic news photo thumbnail...",
  "content": "Isi artikel lengkap dalam format Markdown..."
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
        
        for attempt in range(2):
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
                err_str = str(e)
                if "503" in err_str and attempt == 0:
                    print(f"    [!] {model} 503 (antrian sibuk), menunggu 3 detik...")
                    time.sleep(3)
                    continue
                else:
                    print(f"    [!] Gagal dengan {model}: {e}")
                    break

    raise last_error


def generate_thumbnail_url(image_prompt, title, rss_image=""):
    """
    Menghasilkan URL thumbnail gambar:
    1. Menggunakan gambar asli dari RSS jika tersedia.
    2. Jika tidak ada, membuat gambar ilustrasi editorial resolusi tinggi via Pollinations AI.
    """
    if rss_image and rss_image.startswith("http"):
        return rss_image
    
    # Gunakan Pollinations AI untuk generate gambar editorial berita (1200x675)
    prompt = image_prompt or f"indonesian news editorial photo about {title}, photojournalism, realistic"
    encoded_prompt = urllib.parse.quote(prompt[:120])
    return f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1200&height=675&nologo=true"


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
    print("🤖 MEMULAI AUTO NEWS SCANNER DENGAN AUTO-THUMBNAIL")
    print("=" * 60)

    history = load_history()
    print(f"[*] Riwayat postingan tersimpan: {len(history)} artikel.")

    news_item = get_fresh_article(history)
    if not news_item:
        print("[INFO] Belum ada berita baru yang belum diposting saat ini.")
        sys.exit(0)

    print(f"\n[+] Berita hangat ditemukan: '{news_item['title']}'")
    print(f"[+] Sumber: {news_item['link']}")
    print("[*] Menulis ulang dengan Google Gemini AI (Gaya Anti-Bot)...")

    try:
        rewritten = rewrite_with_gemini(api_key, news_item)
    except Exception as e:
        print(f"[ERROR] Gagal menulis ulang dengan Gemini: {e}")
        sys.exit(1)

    title = rewritten.get("title", news_item["title"])
    labels = rewritten.get("labels", ["Berita", "Viral", "Trending"])
    content = rewritten.get("content", "")
    image_prompt = rewritten.get("image_prompt", "")

    # Dapatkan URL thumbnail otomatis
    thumbnail_url = generate_thumbnail_url(image_prompt, title, news_item.get("rss_image", ""))
    print(f"[+] Thumbnail Otomatis: {thumbnail_url}")

    today_str = datetime.now().strftime("%Y-%m-%d")
    slug = slugify(title)
    file_name = f"{today_str}-{slug}.md"
    file_path = os.path.join("posts", file_name)

    os.makedirs("posts", exist_ok=True)

    # Masukkan thumbnail di bagian paling atas konten agar Blogger otomatis
    # mendeteksinya sebagai featured image / thumbnail postingan
    header_image_md = f"""<p style="text-align: center;">
  <img src="{thumbnail_url}" alt="{title}" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.15);" />
  <br/><em>Ilustrasi: {title}</em>
</p>

"""

    full_body_markdown = header_image_md + content

    # Susun file Markdown dengan Frontmatter
    md_post = f"""---
title: "{title}"
labels: {json.dumps(labels, ensure_ascii=False)}
status: "publish"
date: "{today_str}"
thumbnail: "{thumbnail_url}"
original_source: "{news_item['link']}"
---

{full_body_markdown}
"""

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(md_post)

    print(f"[+] Artikel baru berhasil dibuat: {file_path}")
    print(f"[+] Judul Baru: {title}")

    # Terbitkan artikel ke Blogspot
    print("\n[*] Menerbitkan ke Blogspot via skrip publish...")
    success = publish_post(file_path)

    if success:
        history[news_item["title"].lower().strip()] = {
            "date": datetime.now().isoformat(),
            "published_title": title,
            "file": file_path,
            "thumbnail": thumbnail_url,
            "original_url": news_item["link"]
        }
        save_history(history)
        print(f"\n🎉 Berita viral '{title}' dengan THUMBNAIL OTOMATIS berhasil dipublikasikan ke Blogspot!")
    else:
        print("\n[!] Gagal menerbitkan artikel ke Blogspot.")
        sys.exit(1)


if __name__ == "__main__":
    main()
