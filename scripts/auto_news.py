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

# Sumber RSS berita Nasional & Global terpercaya (Fokus pada isu berdampak luas, trending & potensi view tinggi)
RSS_FEEDS = [
    # --- ISU GLOBAL / INTERNASIONAL & GEOPOLITIK ---
    "https://www.cnnindonesia.com/internasional/rss",
    "https://www.antaranews.com/rss/dunia.xml",
    "https://news.detik.com/internasional/rss",
    "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pWVXlnQVAB?hl=id&gl=ID&ceid=ID:id",
    # --- ISU BISNIS, FINANSIAL & KOMODITAS GLOBAL/NASIONAL ---
    "https://www.cnbcindonesia.com/news/rss",
    "https://finance.detik.com/rss",
    "https://www.antaranews.com/rss/ekonomi.xml",
    "https://www.cnnindonesia.com/ekonomi/rss",
    # --- ISU NASIONAL STRATEGIS & BREAKING NEWS ---
    "https://www.cnnindonesia.com/nasional/rss",
    "https://news.detik.com/rss",
    "https://www.antaranews.com/rss/terkini.xml",
    "https://www.cna.id/api/v1/rss-outbound-feed?_format=xml",
    # --- OLAHRAGA INTERNASIONAL & SEPAK BOLA DUNIA ---
    "https://sepakbola.detik.com/rss",
    "https://www.antaranews.com/rss/sepak-bola.xml",
    # --- GOOGLE NEWS TRENDING ---
    "https://news.google.com/rss?hl=id&gl=ID&ceid=ID:id"
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
                
                # Deteksi gambar jika tersedia di RSS (mendukung enclosure, media:content, media:thumbnail, img tag)
                image_url = ""
                for child in item:
                    tag_lower = child.tag.lower()
                    if any(k in tag_lower for k in ["content", "thumbnail", "enclosure"]):
                        u = child.get("url")
                        if u and (u.startswith("http://") or u.startswith("https://")):
                            image_url = u
                            break

                if not image_url and description:
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


def is_duplicate_event(candidate_title, candidate_link, history):
    """
    Mendeteksi apakah peristiwa berita ini sudah pernah diposting sebelumnya,
    bahkan jika dilaporkan oleh media berbeda dengan variasi susunan kata yang berbeda.
    """
    # 1. Cek langsung kecocokan judul eksak atau link URL
    title_key = candidate_title.lower().strip()
    if title_key in history or candidate_link in history:
        return True

    # 2. Ekstraksi kata kunci utama peristiwa (buang nama portal & stop words)
    clean_candidate = re.sub(r"(?i)\s*[-|]\s*(detiknews|antara|cnn indonesia|kompas|tribun|cnbc|cna|kumparan).*$", "", candidate_title)
    stop_words = {
        "di", "ke", "dari", "dan", "yang", "untuk", "pada", "ini", "itu", "saat", "usai",
        "jadi", "terkait", "soal", "oleh", "adalah", "dengan", "akan", "telah", "bisa",
        "tak", "tidak", "ada", "lagi", "atas", "hingga", "dalam", "bukan", "hanya", "juga",
        "resmi", "viral", "begini", "kata", "soal", "ungkap"
    }
    candidate_words = set(re.findall(r"\w+", clean_candidate.lower())) - stop_words
    if len(candidate_words) < 2:
        return False

    for hist_key, hist_val in history.items():
        if hist_key.startswith("__"):
            continue

        clean_hist = re.sub(r"(?i)\s*[-|]\s*(detiknews|antara|cnn indonesia|kompas|tribun|cnbc|cna|kumparan).*$", "", hist_key)
        hist_words = set(re.findall(r"\w+", clean_hist.lower())) - stop_words

        pub_title = ""
        if isinstance(hist_val, dict):
            pub_title = hist_val.get("published_title", "")
        if pub_title:
            pub_words = set(re.findall(r"\w+", pub_title.lower())) - stop_words
            hist_words = hist_words.union(pub_words)

        overlap = candidate_words.intersection(hist_words)
        if len(overlap) >= 3:
            similarity = len(overlap) / min(len(candidate_words), len(hist_words))
            if similarity >= 0.45:
                print(f"[*] Deteksi topik duplikat dilewati: '{candidate_title[:45]}...' (Sama dengan peristiwa: {list(overlap)[:3]})")
                return True

    return False


def calculate_virality_score(article, all_candidates):
    """
    Menghitung skor potensi jangkauan pembaca (Virality & Attention Potential).
    Memfilter berita dengan potensi view tinggi (Global, Nasional, Geopolitik, Tokoh Utama, Isu Strategis).
    """
    score = 10.0
    title_lower = article["title"].lower()

    # Kata kunci bernilai tinggi (Global, Geopolitik, Isu Strategis, Tokoh Kunci)
    high_impact_keywords = [
        # Geopolitik & Berita Global
        "china", "tiongkok", "amerika", "as", "rusia", "ukraina", "timur tengah", "israel", "iran",
        "trump", "putin", "xi jinping", "biden", "global", "dunia", "internasional", "pbb", "nato",
        # Isu Strategis, Proyek Raksasa & Pasar Finansial
        "raksasa", "investasi", "triliun", "miliar", "kereta", "tambang", "emas", "minyak",
        "saham", "ihsg", "rupiah", "dolar", "bumn", "danantara", "ekonomi",
        # Tokoh Utama & Politik Nasional
        "presiden", "prabowo", "gibran", "menteri", "kapolri", "kpk", "kejagung", "dpr", "mk",
        "dkpp", "sidang", "etik", "haji isam",
        # Peristiwa Besar & Sensasional
        "tersangka", "ditahan", "vonis", "korupsi", "skandal", "tragedi", "tewas", "mogok", "pecah", "darurat", "viral"
    ]
    for kw in high_impact_keywords:
        if kw in title_lower:
            score += 15.0

    # Prioritas ekstra untuk isu Global / Internasional
    if any(k in title_lower for k in ["china", "amerika", "as", "dunia", "global", "rusia", "internasional", "timur tengah"]):
        score += 25.0

    # Cross-Source Trending Bonus (Topik yang diliput oleh beberapa media sekaligus)
    clean_words = set(re.findall(r"\w{4,}", title_lower)) - {"dari", "pada", "yang", "untuk", "dengan", "dalam", "resmi", "soal", "usai"}
    matches = 0
    for other in all_candidates:
        if other["link"] != article["link"]:
            other_words = set(re.findall(r"\w{4,}", other["title"].lower()))
            if len(clean_words.intersection(other_words)) >= 2:
                matches += 1
    score += (matches * 10.0)

    return score


def get_fresh_article(history):
    """
    Mengumpulkan kandidat berita dari seluruh feed (Nasional & Global),
    memfilter topik duplikat, lalu memilih artikel dengan skor potensi view tertinggi.
    """
    all_raw_articles = []
    for feed in RSS_FEEDS:
        print(f"[*] Memeriksa sumber berita: {feed}")
        items = fetch_news_from_rss(feed)
        all_raw_articles.extend(items)

    # Filter kandidat yang belum pernah diposting
    unique_candidates = []
    for it in all_raw_articles:
        if not is_duplicate_event(it["title"], it["link"], history):
            unique_candidates.append(it)

    if not unique_candidates:
        print("[!] Tidak ada artikel baru yang belum pernah dipublikasikan.")
        return None

    # Berikan skor virality pada setiap kandidat
    scored_candidates = []
    for cand in unique_candidates:
        score = calculate_virality_score(cand, unique_candidates)
        scored_candidates.append((score, cand))

    # Urutkan dari skor tertinggi (potensi view paling besar)
    scored_candidates.sort(key=lambda x: x[0], reverse=True)

    best_score, best_article = scored_candidates[0]
    print(f"\n[★] Artikel terpilih dengan potensi view tertinggi (Skor: {best_score:.1f}):")
    print(f"    Judul : {best_article['title']}")
    print(f"    Sumber: {best_article.get('source_name', 'Media')}")
    print(f"    Link  : {best_article['link']}\n")

    return best_article


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
Anda adalah editor kepala dan jurnalis intelijen berita investigasi untuk portal berita 'Paduka Sambas'.
Tulisan Anda harus mengikuti standar tertinggi jurnalisme berita modern, mematuhi PANDUAN KUALITAS GOOGLE SEARCH CENTRAL (E-E-A-T & HELPFUL CONTENT SYSTEM), serta PEDOMAN PENULISAN RESMI BLOGGER.

TUGAS UTAMA:
Tulis ulang topik berita berikut menjadi artikel berita yang BARU, MENDALAM (COMPREHENSIVE), ORISINAL, dan 100% BEBAS DARI PENALTI KONTEN DUPLIKAT (DUPLICATE CONTENT / CONTENT SPINNING).

Data Berita Asli:
- Judul Asal: {original_news['title']}
- Fakta Peristiwa: {original_news['description']}
- Sumber Media: {source_label}

{internal_links_context}

================================================================================
ATURAN WAJIB LOLOS PENGUJIAN KONTEN DUPLIKAT GOOGLE (INFORMATION GAIN):
1. JANGAN HANYA MEMPARAFRASE KALIMAT BERITA ASLI!
   Google menghukum artikel yang hanya mengganti kata per kata dengan alur yang sama persis (article spinning).
2. TAMBAHKAN NILAI TAMBAH ORISINAL (INFORMATION GAIN):
   - Latar Belakang Konteks: Jelaskan mengapa masalah ini bisa terjadi, riwayat regulasi, atau kasus serupa sebelumnya.
   - Analisis Multiperspektif: Ulas dampak peristiwa dari kacamata masyarakat awam, pakar/pengamat, serta lembaga terkait.
   - Proyeksi ke Depan (Forward-Looking): Apa konsekuensi jangka pendek dan jangka panjang dari peristiwa ini.
3. KEDALAMAN KONTEN (MINIMAL 500 - 750 KATA):
   Tulis artikel yang berbobot dan tuntas, bukan artikel pendek (thin content) yang dangkal.

================================================================================
PEDOMAN PENULISAN SESUAI PANDUAN RESMI BLOGGER & SEO SEARCH CENTRAL:
1. HIERARKI HEADING YANG SEMPURNA:
   - Gunakan minimal 3 Sub-heading H2 (##) yang DINAMIS dan deskriptif sesuai topik cerita (DILARANG pakai template kaku seperti "Fakta dan Kronologi").
   - Gunakan Sub-heading H3 (###) jika ada rincian data, poin penting, atau kronologi terperinci.
2. KETERBACAAN TINGGI (MOBILE READABILITY):
   - Paragraf pendek (maksimal 2 hingga 3 kalimat per paragraf) agar nyaman dibaca di layar smartphone.
   - Berikan cetak TEBAL (**bold**) pada kata kunci penting, nama lembaga, atau angka kunci.
   - Gunakan format DAFTAR POIN (bullet list '-' atau nomor '1.') untuk memudahkan pembaca menyerap fakta penting.
   - Gunakan BLOCKQUOTE ('>') untuk kutipan narasumber resmi agar tampilan profesional.
3. RITME BAHASA ALAMI (BURSTINESS ANTI-BOT):
   - Variasikan panjang kalimat secara dinamis: selingi kalimat pendek lugas dengan kalimat majemuk.
   - DILARANG KERAS menggunakan kata klise khas AI seperti: "Di era digital yang serba cepat...", "Kesimpulannya...", "Penting untuk diingat bahwa...", "Tentu saja...", "Mari kita telaah...".
   - Gunakan kosakata jurnalisme bertutur yang hidup, cerdas, dan lugas.
4. INTERNAL LINKING RELEVAN:
   - Sisipkan 1 tautan kontekstual dari daftar artikel blog Paduka Sambas yang paling berhubungan ke dalam narasi kalimat.
5. LABEL RESMI (Pilih 1-3 dari: "Berita", "Bisnis", "Bola", "Hot", "Travel").
6. DESKRIPSI PENELUSURAN (SEARCH DESCRIPTION):
   - Ringkasan SEO 130–150 karakter padat yang memuat kata kunci utama untuk cuplikan Google Search.
7. THUMBNAIL VISUAL REALISTIS (15-20 kata bahasa Inggris menggambarkan foto pers jurnalisme).
8. PENUTUP & KREDIT MEDIA RESMI:
   - Akhiri dengan pertanyaan reflektif untuk diskusi di kolom komentar.
   - Tulis kredit sumber resmi di baris paling akhir:
     *Referensi: Dirangkum dari liputan berita resmi {source_label}.*

FORMAT OUTPUT WAJIB HANYA JSON MURNI TANPA BACKTICKS (```json ... ```):
{{
  "title": "Judul Baru yang Kuat, Padat, dan Ramah SEO",
  "labels": ["Kategori1", "Kategori2"],
  "description": "Deskripsi penelusuran SEO 130-150 karakter...",
  "image_prompt": "English prompt for realistic news photo...",
  "content": "Isi artikel lengkap dalam format Markdown sesuai seluruh pedoman di atas..."
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
            "maxOutputTokens": 3072
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


CURATED_EDITORIAL_POOL = {
    "Politik": [
        "https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=1200&q=80",
        "https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?w=1200&q=80",
        "https://images.unsplash.com/photo-1577495508048-b635879837f1?w=1200&q=80",
        "https://images.unsplash.com/photo-1575320181282-9afab399332c?w=1200&q=80"
    ],
    "Hukum": [
        "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=1200&q=80",
        "https://images.unsplash.com/photo-1453728013993-6d66e9c9123a?w=1200&q=80",
        "https://images.unsplash.com/photo-1505664194779-8beaceb93744?w=1200&q=80"
    ],
    "Transportasi": [
        "https://images.unsplash.com/photo-1474487548417-781cb71495f3?w=1200&q=80",
        "https://images.unsplash.com/photo-1517649763962-0c623266ddc0?w=1200&q=80",
        "https://images.unsplash.com/photo-1508873696983-2df5703bc20d?w=1200&q=80"
    ],
    "Bisnis": [
        "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=1200&q=80",
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1200&q=80",
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1200&q=80"
    ],
    "Bola": [
        "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?w=1200&q=80",
        "https://images.unsplash.com/photo-1574629810360-7efbbe195018?w=1200&q=80",
        "https://images.unsplash.com/photo-1518091043644-c1d4457512c6?w=1200&q=80"
    ],
    "Umum": [
        "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1200&q=80",
        "https://images.unsplash.com/photo-1495020689067-958852a7765e?w=1200&q=80",
        "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=1200&q=80"
    ]
}


def get_unique_background_image(title, category, used_images=None):
    """
    Memilih foto latar belakang yang selalu unik dan belum pernah dipakai sebelumnya,
    disesuaikan dengan topik berita (Wikimedia Commons Search atau Pool Editorial Tematik).
    """
    if used_images is None:
        used_images = set()

    title_lower = title.lower()

    # 1. Coba cari foto editorial relevan dari Wikimedia Commons API
    search_keywords = []
    if "lrt" in title_lower or "kereta" in title_lower:
        search_keywords = ["LRT Jabodebek", "LRT Jakarta", "KRL Commuter"]
    elif "polri" in title_lower or "polisi" in title_lower or "kapolri" in title_lower:
        search_keywords = ["Kepolisian Indonesia", "Markas Besar Kepolisian", "Polri"]
    elif "dpr" in title_lower or "sidang" in title_lower or "menteri" in title_lower:
        search_keywords = ["Gedung DPR RI", "Sidang Parlemen Indonesia"]
    elif "tambang" in title_lower:
        search_keywords = ["Tambang Indonesia", "Tambang Emas"]
    elif "timnas" in title_lower or "sepak bola" in title_lower or "liga" in title_lower:
        search_keywords = ["Timnas Indonesia sepak bola", "Stadion Gelora Bung Karno"]

    for kw in search_keywords:
        try:
            url = f"https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch={urllib.parse.quote(kw)}&gsrnamespace=6&gsrlimit=5&prop=imageinfo&iiprop=url&format=json"
            req = urllib.request.Request(url, headers={"User-Agent": "PadukaBot/1.0 (padukasambas@gmail.com)"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode("utf-8"))
                pages = data.get("query", {}).get("pages", {})
                for pid, p in pages.items():
                    info = p.get("imageinfo", [{}])[0]
                    u = info.get("url")
                    if u and u not in used_images and any(ext in u.lower() for ext in [".jpg", ".jpeg", ".png"]):
                        print(f"[*] Menemukan foto topik unik dari Wikimedia: {kw}")
                        return u
        except Exception:
            pass

    # 2. Ambil dari Curated Editorial Pool berdasarkan topik
    cat_key = "Umum"
    if any(k in title_lower for k in ["kereta", "lrt", "mrt", "krl", "bus", "jalan", "tol", "bandara", "pesawat"]):
        cat_key = "Transportasi"
    elif any(k in title_lower for k in ["sidang", "polisi", "polri", "jaksa", "hakim", "kpk", "korupsi", "hukum", "etik"]):
        cat_key = "Hukum"
    elif any(k in title_lower for k in ["presiden", "menteri", "dpr", "pemilu", "pilkada", "politik", "gibran", "prabowo"]):
        cat_key = "Politik"
    elif any(k in title_lower for k in ["saham", "ihsg", "rupiah", "bank", "ekonomi", "bisnis", "inflasi"]):
        cat_key = "Bisnis"
    elif any(k in title_lower for k in ["bola", "timnas", "liga", "stadion", "gol"]):
        cat_key = "Bola"
    elif category in CURATED_EDITORIAL_POOL:
        cat_key = category

    pool = CURATED_EDITORIAL_POOL.get(cat_key, CURATED_EDITORIAL_POOL["Umum"])
    for u in pool:
        if u not in used_images:
            return u

    # 3. Fallback: Cari dari seluruh pool apa pun yang belum pernah dipakai
    for sub_pool in CURATED_EDITORIAL_POOL.values():
        for u in sub_pool:
            if u not in used_images:
                return u

    return pool[0]


def create_branded_thumbnail(title, category, rss_image="", used_images=None, output_path="posts/images/thumb.jpg"):
    """
    Membuat Kartu Berita (Branded News Banner 16:9) beresolusi tinggi dengan:
    1. Foto jurnalistik ASLI dari RSS berita atau foto editorial UNIK (tidak pernah sama antar artikel).
    2. Badge merek resmi 'PADUKA SAMBAS' di pojok kiri atas.
    3. Badge kategori berita [BERITA / BOLA / BISNIS / HOT / TRAVEL].
    4. Tipografi judul berita tebal berbayang dengan latar belakang dark vignette gradient.
    5. Bar kapsul 4 akun media sosial resmi Paduka Sambas di bagian bawah.
    """
    if used_images is None:
        used_images = set()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    target_w, target_h = 1200, 675
    
    bg_img = None
    chosen_bg_url = ""
    candidate_urls = []

    # Prioritaskan foto jurnalisme riil dari sumber berita asal jika belum pernah dipakai
    if rss_image and rss_image.startswith("http") and rss_image not in used_images:
        candidate_urls.append(rss_image)

    # Dapatkan foto latar yang selalu unik dan belum pernah dipakai
    unique_fallback = get_unique_background_image(title, category, used_images)
    if unique_fallback and unique_fallback not in candidate_urls:
        candidate_urls.append(unique_fallback)

    for u in candidate_urls:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            req = urllib.request.Request(u, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as r:
                raw_data = r.read()
                bg_img = Image.open(io.BytesIO(raw_data)).convert("RGBA")
                chosen_bg_url = u
                print(f"[+] Berhasil mengunduh foto latar unik: {u[:80]}...")
                break
        except Exception as e:
            print(f"[!] Gagal download foto latar {u}: {e}")

    if not bg_img:
        bg_img = Image.new("RGBA", (target_w, target_h), (20, 24, 33, 255))

    # Resize dan crop proporsional 16:9
    bg_img = ImageOps.fit(bg_img, (target_w, target_h), method=Image.Resampling.LANCZOS)

    # Simpan foto mentah bersih tanpa teks untuk keperluan News Card Facebook
    try:
        raw_out_path = os.path.join(os.path.dirname(output_path), "raw_" + os.path.basename(output_path))
        bg_img.convert("RGB").save(raw_out_path, "JPEG", quality=95)
    except Exception as e:
        print(f"[!] Info simpan foto mentah: {e}")

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
    font_social = None
    font_icon = None

    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeui.ttf"
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                font_brand = ImageFont.truetype(p, 24)
                font_title = ImageFont.truetype(p, 36)
                font_social = ImageFont.truetype(p, 15)
                font_icon = ImageFont.truetype(p, 14)
                break
            except Exception:
                pass

    if not font_brand:
        font_brand = ImageFont.load_default()
        font_title = font_brand
        font_social = font_brand
        font_icon = font_brand

    # 1. Badge Merah 'PADUKA SAMBAS'
    draw.rounded_rectangle([45, 35, 275, 80], radius=8, fill=(225, 29, 72))
    draw.text((60, 43), "PADUKA SAMBAS", font=font_brand, fill=(255, 255, 255))

    # 2. Badge Kategori '[ BERITA / BOLA / BISNIS ]'
    cat_text = category.upper() if category else "BERITA"
    draw.rounded_rectangle([290, 35, 415, 80], radius=8, fill=(15, 23, 42, 220))
    draw.text((310, 43), cat_text, font=font_brand, fill=(241, 245, 249))

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

    y_badge = 605
    start_y = y_badge - 25 - (len(lines) * 48)
    for i, line in enumerate(lines):
        # Bayangan halus teks agar terbaca jelas di atas gambar apa pun
        draw.text((47, start_y + (i * 48) + 2), line, font=font_title, fill=(0, 0, 0))
        draw.text((45, start_y + (i * 48)), line, font=font_title, fill=(255, 255, 255))

    # 4. Kapsul Akun Media Sosial Resmi Paduka Sambas
    socials = [
        {"icon": "B", "icon_bg": (245, 124, 0), "text": "padukasambas.blogspot.com"},
        {"icon": "f", "icon_bg": (24, 119, 242), "text": "paduka.sambas"},
        {"icon": "IG", "icon_bg": (225, 48, 108), "text": "@paduka_sambas"},
        {"icon": "YT", "icon_bg": (255, 0, 0), "text": "@PadukaSambas"}
    ]

    curr_x = 45
    h_badge = 36

    for s in socials:
        try:
            bbox = font_social.getbbox(s["text"])
            text_w = bbox[2] - bbox[0]
        except Exception:
            text_w = len(s["text"]) * 8
        total_w = 34 + text_w + 20

        # Kapsul latar gelap semi-transparan
        draw.rounded_rectangle([curr_x, y_badge, curr_x + total_w, y_badge + h_badge], radius=18, fill=(15, 23, 42, 220), outline=(51, 65, 85), width=1)

        # Ikon platform berwarna resmi
        draw.rounded_rectangle([curr_x + 4, y_badge + 4, curr_x + 30, y_badge + 32], radius=14, fill=s["icon_bg"])

        # Huruf inisial ikon platform di tengah
        try:
            ibox = font_icon.getbbox(s["icon"])
            iw = ibox[2] - ibox[0]
            ih = ibox[3] - ibox[1]
        except Exception:
            iw, ih = 10, 10
        draw.text((curr_x + 17 - iw // 2, y_badge + 18 - ih // 2 - 2), s["icon"], font=font_icon, fill=(255, 255, 255))

        # Teks nama akun
        draw.text((curr_x + 37, y_badge + 9), s["text"], font=font_social, fill=(241, 245, 249))

        curr_x += total_w + 12

    final_img.save(output_path, quality=92)
    print(f"[+] Branded Thumbnail Paduka Sambas berhasil dibuat: {output_path}")
    return output_path, chosen_bg_url


def slugify(text):
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:50].strip("-")


def send_telegram_alert(title, category):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        msg = f"📰 *DRAF ARTIKEL BARU TERSEDIA*\n\n📌 *Judul:* {title}\n🏷️ *Kategori:* {category}\n⏳ *Status:* Draf Tersimpan di Blogger\n\n_Silakan tinjau dan klik Publikasikan di Blogger jika sudah sesuai!_"
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=urllib.parse.urlencode({"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}).encode("utf-8")
        )
        with urllib.request.urlopen(req, timeout=10):
            print("[+] Notifikasi Telegram berhasil dikirim ke Pimpinan Redaksi!")
    except Exception as e:
        print(f"[!] Gagal kirim notifikasi Telegram: {e}")


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
    
    # Kumpulkan daftar gambar yang sudah pernah dipakai agar tidak pernah ada gambar yang sama
    used_images = set(history.get("__used_bg_images__", []))
    for hist_item in history.values():
        if isinstance(hist_item, dict) and hist_item.get("bg_image"):
            used_images.add(hist_item["bg_image"])

    _, chosen_bg = create_branded_thumbnail(
        title, primary_category, news_item.get("rss_image", ""), used_images, local_image_path
    )
    
    # URL Global CDN Berkecepatan Tinggi (jsDelivr Multi-CDN Fastly + Cloudflare)
    # Bebas batas kuota GitHub, loading gambar super cepat di Indonesia & Global
    thumbnail_url = f"https://cdn.jsdelivr.net/gh/paduksambas/github-to-blogspot@main/posts/images/{image_file_name}"
    print(f"[+] URL CDN Thumbnail (jsDelivr High-Speed): {thumbnail_url}")

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
            "bg_image": chosen_bg,
            "original_url": news_item["link"]
        }
        if chosen_bg:
            used_list = history.setdefault("__used_bg_images__", [])
            if chosen_bg not in used_list:
                used_list.append(chosen_bg)
        save_history(history)
        print(f"\n🎉 Berita viral '{title}' dengan THUMBNAIL OTOMATIS berhasil dipublikasikan ke Blogspot!")
        send_telegram_alert(title, primary_category)
    else:
        print("\n[!] Gagal menerbitkan artikel ke Blogspot.")
        sys.exit(1)


if __name__ == "__main__":
    main()
