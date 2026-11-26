import os
import sys
import json
import time
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
import io
from PIL import Image, ImageDraw, ImageFont, ImageOps

# Import helper publikasi dari publish.py
try:
    from publish import publish_post
except ImportError:
    import sys
    sys.path.append(os.path.dirname(__file__))
    from publish import publish_post

HISTORY_FILE = "published_history.json"

# Sumber RSS berita Indonesia terpercaya & terupdate (Disinkronkan dengan acuan MD-V14 Paduka Sambas)
RSS_FEEDS = [
    "https://news.google.com/rss?hl=id&gl=ID&ceid=ID:id",
    "https://www.antaranews.com/rss/terkini.xml",
    "https://www.antaranews.com/rss/ekonomi.xml",
    "https://www.antaranews.com/rss/sepak-bola.xml",
    "https://www.cnnindonesia.com/nasional/rss",
    "https://www.cnnindonesia.com/ekonomi/rss",
    "https://news.detik.com/rss",
    "https://finance.detik.com/rss",
    "https://sepakbola.detik.com/rss",
    "https://www.cna.id/api/v1/rss-outbound-feed?_format=xml"
]


def get_existing_blog_articles():
    """
    Mengambil katalog artikel yang sudah terbit di blog Paduka Sambas
    untuk dijadikan target internal linking yang benar-benar kontekstual & relevan.
    """
    feed_url = "https://padukasambas.blogspot.com/feeds/posts/default?alt=json&max-results=30"
    articles = []
    try:
        req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for entry in data.get("feed", {}).get("entry", []):
                title = entry.get("title", {}).get("$t", "").strip()
                links = [l.get("href") for l in entry.get("link", []) if l.get("rel") == "alternate"]
                url = links[0] if links else ""
                
                # Jika title kosong di feed, ekstrak dari slug URL
                if not title and url:
                    slug = url.split("/")[-1].replace(".html", "")
                    title = slug.replace("-", " ").title()
                
                if url and title and "selamat-datang" not in url:
                    articles.append({"title": title, "url": url})
    except Exception as e:
        print(f"[!] Gagal mengambil katalog artikel blog: {e}")
    return articles


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

                # Ekstraksi nama sumber media (misal: detikNews, CNN Indonesia, Kompas)
                source_elem = item.find("source")
                source_name = "Media Nasional"
                source_url = ""
                if source_elem is not None:
                    source_name = source_elem.text or "Media Nasional"
                    source_url = source_elem.get("url", "")
                
                if source_name == "Media Nasional" and " - " in title:
                    source_name = title.split(" - ")[-1].strip()

                clean_desc = re.sub(r"<[^>]+>", "", description).strip()
                
                if title and link:
                    articles.append({
                        "title": title,
                        "link": link,
                        "description": clean_desc,
                        "pub_date": pub_date,
                        "rss_image": image_url,
                        "source_name": source_name,
                        "source_url": source_url
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


def rewrite_with_gemini(api_key, original_news, existing_articles=None):
    """
    Menulis ulang berita dengan gaya jurnalisme manusia profesional (Anti-Bot Standard),
    menghasilkan thumbnail visual, dan menyisipkan Internal Link yang benar-benar kontekstual.
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
    
    source_label = original_news.get('source_name', 'Media Nasional')

    # Siapkan daftar artikel internal blog untuk internal linking kontekstual
    internal_links_context = ""
    if existing_articles:
        sample_links = "\n".join([f"- Judul: \"{a['title']}\" | URL: {a['url']}" for a in existing_articles[:15]])
        internal_links_context = f"""
DAFTAR ARTIKEL YANG SUDAH TERBIT DI BLOG PADUKA SAMBAS:
{sample_links}

ATURAN WAJIB INTERNAL LINKING KONTEKSTUAL (SEO TINGGI):
- Pilih 1 artikel dari daftar di atas yang PALING MEMILIKI KETERKAITAN TEMA (benang merah nyata) dengan berita yang sedang Anda tulis (misal: sama-sama isu politik, sama-sama ekonomi/bisnis, sama-sama bola, atau sama-sama tragedi/peristiwa).
- SISIPKAN LINK TERSEBUT SECARA ALAMI & ORGANIK di dalam alur cerita kalimat (DILARANG menggunakan format 'Baca juga:' kaku di akhir paragraf).
- WAJIB MENYALIN ALAMAT URL LENGKAP PERSIS DARI DAFTAR DI ATAS ke dalam tanda kurung `(https://padukasambas.blogspot.com/...)`. JANGAN PERNAH mengosongkan tanda kurung `()`!
- Contoh penulisan yang benar:
  "...peristiwa nahas ini mengingatkan publik pada [kasus maut di tambang Pongkor](https://padukasambas.blogspot.com/2026/11/tragedi-lubang-maut-pongkor-13-gurandil.html) yang sempat menyita perhatian nasional."
- Tautan internal ini HARUS BENAR-BENAR NYAMBUNG DENGAN KONTEKS PEMBICARAAN.
"""

    prompt = f"""
Anda adalah jurnalis dan editor intelijen berita profesional untuk portal 'Paduka Sambas' (mengikuti standar jurnalisme MD-V14: "DETECT THE TREND. VERIFY THE FACT. CREATE THE IMPACT.").
Tugas Anda adalah menulis ulang topik berita berikut menjadi artikel berita yang berbobot, mendalam, orisinal, dan 100% lolos deteksi algoritma bot/AI Google (mengikuti standar Google Helpful Content E-E-A-T).

Data Berita Asli:
- Judul Asal: {original_news['title']}
- Fakta Peristiwa: {original_news['description']}
- Sumber Media: {source_label}

{internal_links_context}

PEDOMAN GAYA PENULISAN & STRUKTUR:
1. SUB-HEADING DINAMIS & SESUAI TOPIK CERITA (SANGAT PENTING):
   - JANGAN PERNAH gunakan sub-heading template yang seragam dan kaku seperti "Fakta dan Kronologi Kejadian" atau "Catatan Redaksi: Dampak bagi Masyarakat".
   - SUB-HEADING (##) HARUS DINAMIS, KREATIF, DAN LANGSUNG MERUJUK PADA SUB-TOPIK BERITA YANG SEDANG DIBAHAS.
   - Contoh untuk berita hukum/politik:
     ## Menanti Putusan Majelis di Meja Hijau
     ## Konstelasi Baru dan Implikasi Terhadap Publik
   - Contoh untuk berita ekonomi/bisnis:
     ## Lonjakan Harga dan Dampaknya Terhadap Konsumsi Rumah Tangga
     ## Respon Pelaku Usaha Menghadapi Kebijakan Moneter Baru
   - Contoh untuk berita bola:
     ## Taktik Serangan Balik dan Evaluasi Lini Belakang
     ## Peluang Menembus Putaran Final

2. RITME KALIMAT ALAMI (Burstiness & Human Flow):
   - Variasikan panjang kalimat. Gunakan kalimat pendek yang lugas, diselingi kalimat majemuk. Hindari kalimat monoton yang seragam.
   - DILARANG KERAS MENGGUNAKAN KATA KLISE AI: JANGAN gunakan "Di era digital ini...", "Kesimpulannya...", "Penting untuk diingat bahwa...", "Tentu saja...", "Mari kita telusuri...".
   - Gunakan gaya bahasa jurnalisme investigatif yang hidup dan mengalir alami.

3. KUTIPAN NARASUMBER:
   - Sisipkan setidaknya satu kutipan narasumber/pernyataan resmi dalam format blockquote Markdown:
     > *"Pernyataan atau kutipan penting narasumber di sini,"* tegas pihak terkait.

4. LABEL RESMI (PILIH HANYA DARI DAFTAR BERIKUT):
   - "Berita" : Berita umum, nasional, politik, hukum, peristiwa, kriminal.
   - "Bisnis" : Ekonomi, keuangan, perbankan, pasar modal, industri, UMKM.
   - "Bola"   : Sepak bola, liga dunia, timnas Indonesia, olahraga.
   - "Hot"    : Topik viral yang sedang hangat dibicarakan di media sosial.
   - "Travel" : Wisata, daerah, budaya, perjalanan.
   *Pilih 1 sampai 3 label yang paling relevan dari daftar di atas.*

5. DESKRIPSI PENELUSURAN (Search Description SEO):
   - Buat `description`: Ringkasan padat dan menarik sepanjang 130-150 karakter untuk kolom Deskripsi Penelusuran Blogger (SEO Google).

6. THUMBNAIL VISUAL REALISTIS:
   - Buat `image_prompt`: Deskripsi gambar jurnalistik realistis dalam bahasa Inggris (15-20 kata) yang menggambarkan momen spesifik berita tersebut (photojournalism, realistic lighting, 8k).

7. PENUTUP & SUMBER:
   - Akhiri artikel dengan satu pertanyaan reflektif atau diskusi untuk memancing komentar pembaca.
   - Di baris paling bawah, cantumkan kredit sumber rapi:
     *Referensi: Dirangkum dari liputan berita resmi {source_label}.*

FORMAT OUTPUT HANYA JSON MURNI TANPA BACKTICKS (```json ... ```):
{{
  "title": "Judul Baru yang Menggugah dan Berbobot",
  "labels": ["Kategori1", "Kategori2"],
  "description": "Ringkasan padat 130-150 karakter untuk deskripsi penelusuran...",
  "image_prompt": "English descriptive prompt for realistic news photo thumbnail...",
  "content": "Isi artikel lengkap dalam format Markdown dengan heading ## yang dinamis dan relevan..."
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


DEFAULT_UNSPLASH_MAP = {
    "Berita": "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=1200&q=80",
    "Bisnis": "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=1200&q=80",
    "Bola": "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?w=1200&q=80",
    "Hot": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1200&q=80",
    "Travel": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1200&q=80"
}


def create_branded_thumbnail(title, category, rss_image="", output_path="posts/images/thumb.jpg"):
    """
    Membuat Kartu Berita (Branded News Banner 16:9) beresolusi tinggi dengan:
    1. Foto jurnalistik asli dari RSS atau foto editorial jernih (tanpa kecacatan AI).
    2. Badge merek resmi 'PADUKA SAMBAS'.
    3. Badge kategori berita [BERITA / BOLA / BISNIS].
    4. Tipografi judul berita tebal dengan gradien gelap elegan.
    5. Watermark identitas domain 'padukasambas.blogspot.com'.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    target_w, target_h = 1200, 675
    
    bg_img = None
    candidate_urls = []
    if rss_image and rss_image.startswith("http"):
        candidate_urls.append(rss_image)
    
    candidate_urls.append(DEFAULT_UNSPLASH_MAP.get(category, DEFAULT_UNSPLASH_MAP["Berita"]))

    for u in candidate_urls:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            req = urllib.request.Request(u, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as r:
                raw_data = r.read()
                bg_img = Image.open(io.BytesIO(raw_data)).convert("RGBA")
                break
        except Exception as e:
            print(f"[!] Gagal download foto latar {u}: {e}")

    if not bg_img:
        bg_img = Image.new("RGBA", (target_w, target_h), (20, 24, 33, 255))

    # Resize dan crop proporsional 16:9
    bg_img = ImageOps.fit(bg_img, (target_w, target_h), method=Image.Resampling.LANCZOS)

    # Layer gradien gelap
    overlay = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)

    # Gradien bawah untuk judul
    for y in range(240, target_h):
        alpha = int(((y - 240) / (target_h - 240)) ** 1.4 * 230)
        draw_ov.line([(0, y), (target_w, y)], fill=(8, 12, 20, alpha))

    # Gradien atas untuk badge
    for y in range(0, 130):
        alpha = int((1 - (y / 130)) * 140)
        draw_ov.line([(0, y), (target_w, y)], fill=(5, 5, 10, alpha))

    final_img = Image.alpha_composite(bg_img, overlay).convert("RGB")
    draw = ImageDraw.Draw(final_img)

    # Muat Font
    font_brand = None
    font_title = None
    font_wm = None

    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeui.ttf"
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                font_brand = ImageFont.truetype(p, 26)
                font_title = ImageFont.truetype(p, 36)
                font_wm = ImageFont.truetype(p, 20)
                break
            except Exception:
                pass

    if not font_brand:
        font_brand = ImageFont.load_default()
        font_title = font_brand
        font_wm = font_brand

    # 1. Badge Merah 'PADUKA SAMBAS'
    draw.rounded_rectangle([40, 35, 290, 82], radius=8, fill=(225, 29, 72))
    draw.text((55, 43), "PADUKA SAMBAS", font=font_brand, fill=(255, 255, 255))

    # 2. Badge Kategori '[ BERITA / BOLA / BISNIS ]'
    cat_text = category.upper() if category else "BERITA"
    draw.rounded_rectangle([305, 35, 440, 82], radius=8, fill=(15, 23, 42, 220))
    draw.text((325, 43), cat_text, font=font_brand, fill=(241, 245, 249))

    # 3. Word Wrap Judul Berita
    words = title.split()
    lines = []
    current_line = []
    for w in words:
        current_line.append(w)
        if len(" ".join(current_line)) > 42:
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [w]
    if current_line:
        lines.append(" ".join(current_line))
    lines = lines[:3]  # Maksimal 3 baris

    start_y = 675 - 75 - (len(lines) * 48)
    for i, line in enumerate(lines):
        draw.text((45, start_y + (i * 48)), line, font=font_title, fill=(255, 255, 255))

    # 4. Watermark Domain
    draw.text((45, 620), "padukasambas.blogspot.com", font=font_wm, fill=(203, 213, 225))

    final_img.save(output_path, quality=92)
    print(f"[+] Branded Thumbnail Paduka Sambas berhasil dibuat: {output_path}")
    return output_path


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

    # Ambil katalog artikel yang sudah ada di blog untuk Internal Linking Kontekstual
    existing_articles = get_existing_blog_articles()
    print(f"[*] Terhubung dengan {len(existing_articles)} artikel live di blog untuk Internal Linking.")

    news_item = get_fresh_article(history)
    if not news_item:
        print("[INFO] Belum ada berita baru yang belum diposting saat ini.")
        sys.exit(0)

    print(f"\n[+] Berita hangat ditemukan: '{news_item['title']}'")
    print(f"[+] Sumber: {news_item['link']}")
    print("[*] Menulis ulang dengan Google Gemini AI (Gaya Anti-Bot & Contextual Linking)...")

    try:
        rewritten = rewrite_with_gemini(api_key, news_item, existing_articles)
    except Exception as e:
        print(f"[ERROR] Gagal menulis ulang dengan Gemini: {e}")
        sys.exit(1)

    title = rewritten.get("title", news_item["title"])
    labels = rewritten.get("labels", ["Berita", "Viral", "Trending"])
    content = rewritten.get("content", "")
    image_prompt = rewritten.get("image_prompt", "")
    description = rewritten.get("description", "")
    if not description:
        description = re.sub(r"<[^>]+>", "", content).replace("\n", " ").strip()[:145]

    today_str = datetime.now().strftime("%Y-%m-%d")
    slug = slugify(title)
    file_name = f"{today_str}-{slug}.md"
    file_path = os.path.join("posts", file_name)

    os.makedirs("posts", exist_ok=True)
    os.makedirs(os.path.join("posts", "images"), exist_ok=True)

    # Buat Kartu Berita / Thumbnail Beridentitas 'PADUKA SAMBAS' (Pillow)
    image_file_name = f"{today_str}-{slug}.jpg"
    local_image_path = os.path.join("posts", "images", image_file_name)
    primary_category = labels[0] if labels else "Berita"
    
    create_branded_thumbnail(title, primary_category, news_item.get("rss_image", ""), local_image_path)
    
    # URL CDN Publik untuk Thumbnail di Blogspot
    thumbnail_url = f"https://raw.githubusercontent.com/paduksambas/github-to-blogspot/main/posts/images/{image_file_name}"
    print(f"[+] URL CDN Thumbnail: {thumbnail_url}")

    # Auto-repair internal link kosong [teks]() jika AI lupa menyalin URL lengkap
    if existing_articles and "]()" in content:
        for a in existing_articles:
            words = [w for w in a["title"].lower().split() if len(w) > 3]
            def repl(m):
                anchor = m.group(1).lower()
                if any(w in anchor for w in words):
                    return f"[{m.group(1)}]({a['url']})"
                return m.group(0)
            content = re.sub(r"\[([^\]]+)\]\(\s*\)", repl, content)
        
        # Fallback jika masih ada tanda () kosong
        if "]()" in content and existing_articles:
            content = re.sub(r"\[([^\]]+)\]\(\s*\)", f"[\\1]({existing_articles[0]['url']})", content)

    # Bersihkan URL tracking Google News mentah jika ada di luar format markdown
    content = re.sub(r'(?i)(?:sumber\s*(?:asal|referensi)?:\s*)?https?://news\.google\.com/\S+', '', content).strip()
    content = re.sub(r'(?i)sumber\s*asal:\s*https?://\S+', '', content).strip()

    # Pastikan footer referensi rapi tanpa link mentah panjang
    source_name = news_item.get("source_name", "Media Nasional")
    if "referensi:" not in content.lower():
        content += f"\n\n---\n*Referensi: Dirangkum dari liputan berita resmi {source_name}.*"

    # Masukkan thumbnail di bagian paling atas konten agar Blogger otomatis
    # mendeteksinya sebagai featured image / thumbnail postingan
    header_image_md = f"""<p style="text-align: center;">
  <img src="{thumbnail_url}" alt="{title}" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.15);" />
  <br/><em>Ilustrasi: {title}</em>
</p>

"""

    full_body_markdown = header_image_md + content

    # Susun file Markdown dengan Frontmatter (Status default: DRAFT)
    md_post = f"""---
title: "{title}"
labels: {json.dumps(labels, ensure_ascii=False)}
description: "{description}"
status: "draft"
date: "{today_str}"
thumbnail: "{thumbnail_url}"
source: "{source_name}"
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
