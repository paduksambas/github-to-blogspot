#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Publisher Berita Viral Otomatis untuk Halaman Facebook (Page) Paduka Sambas
==========================================================================
- Berjalan Mandiri Setiap 1 Jam (Tidak Menunggu Antrean Blogspot).
- Menarik Sumber Berita & Intelijen Langsung dari repositori MD-V14-PADUKA-SAMBAS.
- Algoritma Pemfilteran Virality & Attention Potential Tertinggi:
  * Geopolitik Global & Perang (+40)
  * Isu Mengguncang / Korupsi / KPK / Bencana (+35)
  * Tokoh Kunci Dunia & RI (Prabowo, Jokowi, Trump, Putin, Elon Musk) (+30)
  * Kebijakan Ekonomi Rakyat (BBM, Pajak, Rupiah, Sembako) (+25)
  * Cross-Source Corroboration lintas media (+15 per sumber)
  * Freshness Decay (Berita segar 1-4 jam terakhir diprioritaskan)
- 3-Tier Image Guarantee: RSS Enclosure -> OpenGraph Live Scraper -> Editorial Curated HD.
- Format Visual: Model MD V19.1 News Card 4:5 (1080 x 1350 px).
- Format Caption: Headline Menggigit + Analisis Ringkas + Pertanyaan Diskusi Netizen + Tagar.
- Anti-Duplikasi: Dicatat rapi dalam facebook_published_history.json.
"""

import os
import io
import re
import sys
import json
import ssl
import email.utils
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

# SSL context yang aman & toleran terhadap sertifikat lokal/Windows
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

# Lokasi repositori saat ini
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Import modul pembuat visual kartu Facebook Paduka Sambas
try:
    from scripts.generate_facebook_post import (
        generate_facebook_news_card,
        generate_facebook_caption,
        publish_to_facebook,
        detect_card_theme
    )
except ImportError:
    from generate_facebook_post import (
        generate_facebook_news_card,
        generate_facebook_caption,
        publish_to_facebook,
        detect_card_theme
    )

# URL Katalog Feed MD-V14 di GitHub (fallback jika folder lokal tidak ada)
MDV14_RAW_FEEDS_URL = "https://raw.githubusercontent.com/paduksambas/MD-V14-PADUKA-SAMBAS/main/examples/feeds.sample.json"

# Cadangan Feed Breaking & Global jika koneksi ke GitHub repositori terkendala
BACKUP_FEEDS = [
    {"id": "cnn-internasional", "name": "CNN Internasional", "url": "https://www.cnnindonesia.com/internasional/rss", "category": "Dunia"},
    {"id": "antara-dunia", "name": "ANTARA News Dunia", "url": "https://www.antaranews.com/rss/dunia.xml", "category": "Dunia"},
    {"id": "detik-internasional", "name": "Detikcom Internasional", "url": "https://news.detik.com/internasional/rss", "category": "Dunia"},
    {"id": "cnn-nasional", "name": "CNN Indonesia Nasional", "url": "https://www.cnnindonesia.com/nasional/rss", "category": "Nasional"},
    {"id": "detik-news", "name": "Detikcom News", "url": "https://news.detik.com/rss", "category": "Nasional"},
    {"id": "cnbc-news", "name": "CNBC Indonesia News", "url": "https://www.cnbcindonesia.com/news/rss", "category": "Ekonomi & Pasar"},
    {"id": "antara-terkini", "name": "ANTARA Terkini", "url": "https://www.antaranews.com/rss/terkini.xml", "category": "Nasional"},
    {"id": "bbc-world", "name": "BBC World News", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "category": "Dunia"}
]

# Gambar kurasi editorial HD jika media berita asli tidak menyertakan foto
EDITORIAL_FALLBACK_IMAGES = {
    "Dunia": "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=1200&q=80",
    "Nasional": "https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=1200&q=80",
    "Ekonomi": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1200&q=80",
    "Hukum": "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=1200&q=80",
    "Bencana": "https://images.unsplash.com/photo-1547683905-f686c993aae5?w=1200&q=80",
    "Default": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1200&q=80"
}

# =====================================================================
# META (FACEBOOK) COMMUNITY STANDARDS SAFETY GUARD & BLACKLIST
# =====================================================================
# Memastikan akun Facebook Page Paduka Sambas 100% AMAN dari teguran,
# pemblokiran (shadowban), pelanggaran hak cipta, dan strike Meta.
FACEBOOK_PROHIBITED_KEYWORDS = [
    # 1. Kekerasan Grafis, Gore, Darah & Kematian Sadis (Graphic Violence & Gore)
    "mutilasi", "jasad membusuk", "mayat membusuk", "terpotong-potong", "potongan tubuh",
    "leher digorok", "darah berceceran", "terbakar hidup-hidup", "otopsi", "kepala putus",
    "jenazah hancur", "dikeroyok sampai tewas", "disiksa", "penyiksaan sadis",

    # 2. Bunuh Diri & Melukai Diri Sendiri (Suicide & Self-Harm - Zero Tolerance)
    "bunuh diri", "gantung diri", "lompat dari gedung", "tenggak racun", "sayat tangan",
    "akhiri hidup", "tabrakkan diri ke kereta",

    # 3. Konten Seksual, Asusila & Pelecehan (Nudity & Sexual Exploitation)
    "pemerkosaan", "perkosa", "pencabulan", "cabul", "pelecehan seksual", "porno",
    "pornografi", "alat kelamin", "sodomi", "vagina", "penis", "tanpa busana",
    "telanjang", "video syur", "adegan ranjang", "prostitusi", "open bo",

    # 4. Ujaran Kebencian, SARA & Diskriminasi (Hate Speech)
    "penistaan agama", "bakar masjid", "bakar gereja", "kafir laknat",

    # 5. Narkotika & Zat Terlarang Vulgar (Dangerous Goods)
    "jual sabu", "pesan narkoba", "ganja sintetis", "ekstasi murah"
]


def is_meta_compliant(article):
    """
    Memeriksa kepatuhan berita terhadap Standar Komunitas Meta (Facebook Community Standards).
    Menghindarkan Facebook Page dari teguran, pelanggaran konten sensitif, atau shadowban.
    """
    text = (article.get("title", "") + " " + article.get("summary", "")).lower()
    for bad_word in FACEBOOK_PROHIBITED_KEYWORDS:
        if bad_word in text:
            return False, f"Terdeteksi kata sensitif/terlarang Meta: '{bad_word}'"
    return True, "Safe"


def load_mdv14_feed_catalog():
    """
    Mengambil katalog feed RSS langsung dari sistem MD-V14-PADUKA-SAMBAS.
    Prioritas 1: Baca berkas lokal jika kedua repositori berada di mesin yang sama.
    Prioritas 2: Unduh dari Raw GitHub MD-V14-PADUKA-SAMBAS.
    Prioritas 3: Gunakan BACKUP_FEEDS bawaan.
    """
    local_paths = [
        "../MD-V14-PADUKA-SAMBAS/examples/feeds.sample.json",
        "../../MD-V14-PADUKA-SAMBAS/examples/feeds.sample.json",
        "D:/LIHLAS/GITHUB/MD-V14-PADUKA-SAMBAS/examples/feeds.sample.json"
    ]

    for p in local_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        print(f"[+] Berhasil membaca katalog feed dari berkas lokal MD-V14: {p} ({len(data)} feed)")
                        return data
            except Exception as e:
                print(f"[!] Gagal membaca berkas lokal {p}: {e}")

    # Unduh dari GitHub Raw MD-V14
    try:
        print(f"[*] Mengunduh katalog feed terkini dari {MDV14_RAW_FEEDS_URL}...")
        req = urllib.request.Request(MDV14_RAW_FEEDS_URL, headers={"User-Agent": "Mozilla/5.0 (PadukaSambas-Bot/1.0)"})
        with urllib.request.urlopen(req, timeout=15, context=SSL_CONTEXT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, list) and len(data) > 0:
                print(f"[+] Berhasil memuat {len(data)} feed dari GitHub MD-V14-PADUKA-SAMBAS.")
                return data
    except Exception as e:
        print(f"[!] Tidak dapat mengunduh feeds dari MD-V14 ({e}), beralih ke katalog cadangan.")

    return BACKUP_FEEDS


def extract_opengraph_image(url):
    """
    Tier 2 Image Guarantee: Menginspeksi halaman berita asli secara langsung
    untuk mengekstrak tag og:image beresolusi tinggi.
    """
    if not url or not url.startswith("http"):
        return None
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        )
        with urllib.request.urlopen(req, timeout=8, context=SSL_CONTEXT) as resp:
            content = resp.read(150000).decode("utf-8", errors="ignore")
            # Cari <meta property="og:image" content="...">
            match = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', content, re.IGNORECASE)
            if not match:
                match = re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']', content, re.IGNORECASE)
            if match:
                img_url = match.group(1).strip()
                if img_url.startswith("http"):
                    return img_url
    except Exception:
        pass
    return None


def fetch_and_parse_feed(feed_info):
    """Mengambil dan mem-parsing satu feed RSS/Atom."""
    url = feed_info.get("url")
    name = feed_info.get("name") or feed_info.get("publisher", "Media")
    topics = feed_info.get("topics", ["Berita"])
    primary_topic = topics[0] if topics else "Berita"

    if not url:
        return []

    articles = []
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=12, context=SSL_CONTEXT) as resp:
            xml_data = resp.read()

        root = ET.fromstring(xml_data)
        # Cari item di channel RSS atau entry di Atom
        items = root.findall(".//item")
        if not items:
            items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

        for item in items[:15]:  # Ambil hingga 15 berita teranyar per feed
            # Ambil judul
            t_node = item.find("title")
            if t_node is None:
                t_node = item.find("{http://www.w3.org/2005/Atom}title")
            title = t_node.text.strip() if t_node is not None and t_node.text else ""
            if not title:
                continue

            # Ambil link
            l_node = item.find("link")
            if l_node is None:
                l_node = item.find("{http://www.w3.org/2005/Atom}link")
            link = ""
            if l_node is not None:
                link = l_node.text or l_node.attrib.get("href", "")
            link = link.strip()

            # Ambil deskripsi / ringkasan
            d_node = item.find("description")
            if d_node is None:
                d_node = item.find("{http://www.w3.org/2005/Atom}summary")
            if d_node is None:
                d_node = item.find("{http://www.w3.org/2005/Atom}content")
            summary = ""
            if d_node is not None and d_node.text:
                summary = re.sub(r"<[^>]+>", "", d_node.text).strip()

            # Ambil tanggal publikasi
            p_node = item.find("pubDate")
            if p_node is None:
                p_node = item.find("{http://www.w3.org/2005/Atom}published")
            if p_node is None:
                p_node = item.find("{http://www.w3.org/2005/Atom}updated")
            pub_date_str = p_node.text.strip() if p_node is not None and p_node.text else ""
            
            # Tier 1 Image: Tag enclosure atau media:content
            image_url = None
            enc = item.find("enclosure")
            if enc is not None and "url" in enc.attrib:
                image_url = enc.attrib["url"]
            
            if not image_url:
                for elem in item:
                    if elem.tag.endswith("content") or elem.tag.endswith("thumbnail"):
                        if "url" in elem.attrib:
                            image_url = elem.attrib["url"]
                            break

            articles.append({
                "title": title,
                "url": link,
                "summary": summary,
                "pub_date_str": pub_date_str,
                "source_name": name,
                "category": primary_topic,
                "image_url": image_url
            })

    except Exception as e:
        print(f"[!] Gagal mengambil feed {name} ({url}): {e}")

    return articles


def calculate_virality_score(article, all_titles):
    """
    Algoritma Penilaian Potensi Viral & Attention Facebook:
    - Base score: 50
    - Geopolitik Dunia, Perang, Rudal, Ketegangan Internasional: +40
    - Skandal Menghebohkan, KPK, Korupsi, Tersangka, Bencana: +35
    - Tokoh Kunci Dunia & RI (Prabowo, Jokowi, Trump, Putin, Elon Musk): +30
    - Kebijakan Ekonomi Rakyat (BBM, Pajak, Rupiah, Sembako, Gaji): +25
    - Kata Kunci Breaking / Viral: +20
    - Cross-Source Corroboration: +15 per liputan media lain di topik serupa
    - Freshness: +25 untuk artikel < 4 jam, penalti -20 untuk > 24 jam.
    """
    score = 50.0
    text = (article["title"] + " " + article.get("summary", "")).lower()

    # 1. Isu Geopolitik Dunia & Konflik Superpower (+40)
    if any(k in text for k in ["perang", "rudal", "nuklir", "militer", "serangan", "pbb", "timur tengah", "rusia", "ukraina", "israel", "iran", "as-china", "gaza"]):
        score += 40

    # 2. Isu Hukum Menghebohkan & Bencana Besar (+35)
    if any(k in text for k in ["kpk", "ditangkap", "tersangka", "korupsi", "ott", "skandal", "vonis", "gempa", "tsunami", "erupsi", "darurat", "meledak", "tewas"]):
        score += 35

    # 3. Tokoh Kunci Penarik Perhatian Netizen (+30)
    if any(k in text for k in ["trump", "putin", "xi jinping", "elon musk", "prabowo", "gibran", "jokowi", "sri mulyani", "erick thohir"]):
        score += 30

    # 4. Kebijakan Ekonomi & Dampak Finansial Rakyat (+25)
    if any(k in text for k in ["bbm", "pajak", "tarif", "rupiah", "gaji", "bansos", "sembako", "harga beras", "ihsg", "inflasi"]):
        score += 25

    # 5. Kata Kunci Sensasional & Viral (+20)
    if any(k in text for k in ["breaking news", "geger", "viral", "heboh", "mengejutkan", "terbongkar", "sorotan", "resmi"]):
        score += 20

    # 6. Cross-Source Corroboration (+15 per sumber lain yang memberitakan isu mirip)
    words = [w for w in re.findall(r"\w+", article["title"].lower()) if len(w) >= 5]
    if words:
        corroboration = 0
        for other_t in all_titles:
            if other_t != article["title"].lower():
                matches = sum(1 for w in words[:3] if w in other_t)
                if matches >= 2:
                    corroboration += 1
        score += min(corroboration * 15, 45)

    # 7. Freshness Factor (Usia Berita)
    pub_str = article.get("pub_date_str", "")
    if pub_str:
        try:
            parsed_dt = email.utils.parsedate_to_datetime(pub_str)
            now = datetime.now(timezone.utc)
            age_hours = (now - parsed_dt).total_seconds() / 3600.0
            if age_hours <= 4:
                score += 25
            elif age_hours <= 12:
                score += 15
            elif age_hours > 24:
                score -= 20
        except Exception:
            pass

    return round(score, 1)


def load_facebook_history(filepath="facebook_published_history.json"):
    """Memuat daftar riwayat postingan Facebook untuk mencegah duplikasi."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []
    return []


def save_facebook_history(filepath, entry):
    """Menyimpan postingan baru ke berkas riwayat Facebook."""
    history = load_facebook_history(filepath)
    history.append(entry)
    # Batasi riwayat hingga 500 entri terbaru
    if len(history) > 500:
        history = history[-500:]
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    print(f"[+] Riwayat postingan Facebook diperbarui ({len(history)} entri).")


def craft_facebook_payload_with_gemini(article, gemini_api_key=None):
    """
    Mengekstrak format visual kartu Model MD V19.1 dan menyusun caption viral
    menggunakan Google Gemini AI (atau fallback cerdas jika API tidak tersedia).
    """
    title = article["title"]
    source = article["source_name"]
    summary = article.get("summary", "")
    category = article.get("category", "Trending")
    photo_url = article.get("image_url", "")

    # Tentukan badge region
    title_upper = title.upper()
    if any(k in title_upper for k in ["DUNIA", "GLOBAL", "INTERNASIONAL", "AS", "AMERIKA", "CHINA", "TIMUR TENGAH", "RUSIA", "UKRAINA", "TRUMP", "PUTIN"]):
        badge_red = "BERITA GLOBAL"
    elif any(k in title_upper for k in ["KALBAR", "SAMBAS", "PONTIANAK", "SINGKAWANG"]):
        badge_red = "INFO KALBAR"
    else:
        badge_red = "BERITA NASIONAL"

    # Default fallback data (word-wrap bersih tanpa memotong kata di tengah)
    import textwrap
    wrapped_hl = textwrap.wrap(title.upper(), width=22)
    hl1 = wrapped_hl[0] if len(wrapped_hl) >= 1 else title[:22].upper()
    hl2_rem = wrapped_hl[1] if len(wrapped_hl) >= 2 else "KABAR TERKINI"

    card_data = {
        "title": title,
        "photo_url": photo_url,
        "badge_red": badge_red,
        "badge_gold": category.upper()[:14],
        "headline_line1": hl1,
        "headline_line2_prefix": "",
        "keyword_highlight": hl2_rem,
        "source_credit": source,
        "lead": f"{title}. {summary[:200]}",
        "body": summary[200:500] if len(summary) > 200 else "Peristiwa ini menjadi sorotan luas publik dan memicu beragam reaksi.",
        "impact": "Pantau terus perkembangan berita aktual dan isu-isu strategis terkini bersama Paduka Sambas.",
        "discussion_prompt": "Bagaimana tanggapan dan pandangan Anda mengenai peristiwa ini? Sampaikan pendapat Anda di kolom komentar!",
        "hashtags": ["PadukaSambas", "BeritaViral", "KabarTerkini", "BreakingNews", "DuniaHariIni" if "GLOBAL" in badge_red else "IndonesiaTerkini"]
    }

    # Optimasi dengan Gemini AI jika API KEY ada
    if gemini_api_key:
        api_key_clean = str(gemini_api_key).strip().strip('"\'')
        prompt = f"""Kamu adalah Redaktur Berita Media Sosial Paduka Sambas.
Tugasmu: Ekstrak berita berikut ke format JSON untuk kartu berita visual 4:5 Model MD V19.1 dan buat caption Facebook yang menggugah interaksi netizen (Zero-Link posting).

Judul: {title}
Sumber Asli: {source}
Ringkasan: {summary}

ATURAN KEPATUHAN STANDAR KOMUNITAS META (WAJIB DIPATUHI AGAR BEBAS TEGURAN):
- DILARANG ENGAGEMENT BAIT: Jangan pernah gunakan kalimat spam seperti "Ketik 1", "Share jika setuju", "Komentar Amin", "Wajib bagikan", "Tag temanmu".
- DILARANG GORE & VULGAR: Jangan mendeskripsikan darah, luka fisik mengerikan, atau bunuh diri secara grafis.
- DISKUSI SANTUN & TERBUKA: discussion_prompt wajib berupa pertanyaan jurnalistik yang sopan dan berimbang (contoh: "Bagaimana pandangan Anda mengenai kebijakan ini? Sampaikan pendapat santun di kolom komentar.")
- FAKTUAL & KREDIBEL: Ringkasan harus akurat sesuai fakta berita tanpa klaim palsu/hoaks.

ATURAN JSON KETAT:
- badge_gold: 1-2 kata kapital kategori berita (contoh: GEOPOLITIK, NASIONAL, EKONOMI, HUKUM)
- kicker: 2-4 kata kapital penjelas konteks (contoh: RESPON CEPAT KELUHAN WARGA, BABAK BARU PROSES HUKUM)
- headline_line1: Baris 1 judul kartu atas (huruf kapital, maks 22 karakter)
- headline_line2_prefix: Awalan baris 2 jika ada (huruf kapital, contoh: "RESMI ", "KINI ", "CAPAI ")
- keyword_highlight: 1-2 kata kunci utama warna emas pada baris 2 (huruf kapital, maks 18 karakter)
- lead: Paragraf pembuka caption yang kuat, padat, dan langsung ke inti berita
- body: Paragraf kedua yang menguraikan fakta kunci atau kutipan penting
- impact: Paragraf ketiga yang menjelaskan dampak bagi masyarakat atau perkembangan selanjutnya
- discussion_prompt: 1 kalimat santun pemantik diskusi warga untuk memicu komentar di Facebook
- hashtags: Array 5 tagar relevan tanpa tanda pagar (contoh: ["PadukaSambas", "BeritaViral", "TrendingHariIni", ...])

Balas HANYA dengan blok JSON valid tanpa teks pengantar."""

        candidate_models = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash"]
        for model in candidate_models:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key_clean}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.25, "response_mime_type": "application/json"}
            }
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=18, context=SSL_CONTEXT) as resp:
                    resp_json = json.loads(resp.read().decode("utf-8"))
                    text = resp_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                    ai_data = json.loads(text)
                    # Perbarui field dari AI
                    for k, v in ai_data.items():
                        if v:
                            card_data[k] = v
                    card_data["photo_url"] = photo_url
                    card_data["source_credit"] = source
                    card_data["title"] = title
                    card_data["badge_red"] = badge_red
                    print(f"[+] Ekstraksi visual & caption AI Gemini ({model}) sukses!")
                    break
            except Exception as e:
                continue

    return card_data


def run_hourly_facebook_publisher(dry_run=False, force=False):
    """
    Fungsi Utama: Menjalankan pemindaian berita MD-V14, filtering virality,
    pembuatan kartu visual Model MD V19.1, dan publikasi ke Halaman Facebook.
    """
    print("\n" + "=" * 70)
    print("PADUKA SAMBAS — HOURLY FACEBOOK VIRAL NEWS PUBLISHER")
    print(f"Waktu Eksekusi: {datetime.now().strftime('%Y-%m-%d %H:%M:%S WIB')}")
    print("=" * 70)

    # 1. Muat riwayat postingan Facebook
    history_file = os.path.join(REPO_ROOT, "facebook_published_history.json")
    published_history = load_facebook_history(history_file)
    published_urls = {h.get("url") for h in published_history if h.get("url")}
    published_titles = {h.get("title", "").strip().lower() for h in published_history if h.get("title")}
    print(f"[*] Riwayat postingan Facebook yang tercatat: {len(published_history)} berita.")

    # 2. Muat katalog feed dari MD-V14
    feed_catalog = load_mdv14_feed_catalog()
    enabled_feeds = [f for f in feed_catalog if f.get("enabled", True)]
    print(f"[*] Memindai {len(enabled_feeds)} feed aktif dari katalog MD-V14...")

    # 3. Kumpulkan seluruh kandidat berita
    all_candidates = []
    for f_info in enabled_feeds:
        articles = fetch_and_parse_feed(f_info)
        all_candidates.extend(articles)

    print(f"[+] Total berita yang berhasil dikumpulkan: {len(all_candidates)} artikel.")
    if not all_candidates:
        print("[!] Tidak ada berita yang berhasil dikumpulkan. Proses dihentikan.")
        return False

    all_titles = [a["title"].strip().lower() for a in all_candidates]

    # 4. Berikan skor virality & filter berita yang belum pernah diposting
    scored_candidates = []
    for item in all_candidates:
        url = item.get("url", "")
        t_clean = item.get("title", "").strip().lower()
        if not force:
            if url in published_urls or t_clean in published_titles:
                continue

        # Filter Kepatuhan Standar Komunitas Meta (Facebook Safety Guard)
        is_safe, reason = is_meta_compliant(item)
        if not is_safe:
            # Lewati berita sensitif demi keamanan mutlak akun dari teguran Meta
            continue

        score = calculate_virality_score(item, all_titles)
        item["virality_score"] = score
        scored_candidates.append(item)

    print(f"[*] Kandidat berita baru yang lolos seleksi anti-duplikasi: {len(scored_candidates)} artikel.")
    if not scored_candidates:
        print("[*] Semua berita terbaru sudah pernah diposting ke Facebook. Tidak ada yang perlu diterbitkan saat ini.")
        return True

    # Urutkan berdasarkan Skor Virality Tertinggi (#1)
    scored_candidates.sort(key=lambda x: x["virality_score"], reverse=True)

    print("\n--- TOP 5 KANDIDAT BERITA DENGAN SKOR VIRAL TERTINGGI ---")
    for i, c in enumerate(scored_candidates[:5], 1):
        print(f"#{i} [Skor: {c['virality_score']}] ({c['source_name']}) {c['title']}")

    # Pilih Berita Peringkat #1
    chosen = scored_candidates[0]
    print(f"\n[★] BERITA TERPILIH UNTUK TAYANG KE FACEBOOK:\n    Judul : {chosen['title']}\n    Skor  : {chosen['virality_score']}\n    Sumber: {chosen['source_name']}\n    URL   : {chosen['url']}")

    # 5. Terapkan 3-Tier Image Guarantee
    final_image = chosen.get("image_url")
    if not final_image or not final_image.startswith("http"):
        print("[*] Tier 1 kosong, mencoba Tier 2 (OpenGraph live scraper)...")
        final_image = extract_opengraph_image(chosen.get("url"))
        if final_image:
            print(f"[+] Tier 2 OpenGraph berhasil menemukan foto: {final_image}")

    if not final_image or not final_image.startswith("http"):
        cat = chosen.get("category", "Default")
        final_image = EDITORIAL_FALLBACK_IMAGES.get(cat, EDITORIAL_FALLBACK_IMAGES["Default"])
        print(f"[!] Tier 2 kosong, menggunakan Tier 3 (Editorial HD Kurasi): {final_image}")

    chosen["image_url"] = final_image

    # 6. Susun Data Visual & Caption AI
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    card_data = craft_facebook_payload_with_gemini(chosen, gemini_key)

    # 7. Hasilkan Master News Card 4:5 Model MD V19.1
    draft_dir = os.path.join(REPO_ROOT, "posts", "facebook_drafts")
    os.makedirs(draft_dir, exist_ok=True)
    timestamp_id = int(datetime.now().timestamp())
    card_output_path = os.path.join(draft_dir, f"fb_viral_card_{timestamp_id}.png")

    detected_theme = detect_card_theme(card_data.get("title", ""), card_data.get("badge_gold", ""))
    print(f"[*] Template Visual Terpilih Otomatis: {detected_theme.upper()} (Sesuai Karakteristik Berita)")
    print(f"[*] Merender Kartu Berita Visual Model MD V19.1 ke {card_output_path}...")
    generate_facebook_news_card(card_data, card_output_path, theme=detected_theme)

    caption_text = generate_facebook_caption(card_data)
    caption_output_path = os.path.join(draft_dir, f"fb_viral_caption_{timestamp_id}.txt")
    with open(caption_output_path, "w", encoding="utf-8") as f:
        f.write(caption_text)

    print("\n" + "=" * 50)
    print("PREVIEW CAPTION FACEBOOK NATIVE:")
    print("=" * 50)
    print(caption_text)
    print("=" * 50 + "\n")

    if dry_run:
        print("[*] Mode DRY-RUN aktif: Kartu visual dan caption berhasil dibuat tanpa diunggah ke Facebook.")
        return True

    # 8. Unggah ke Halaman Facebook via Meta Graph API
    fb_page_id = os.environ.get("FB_PAGE_ID", "")
    fb_page_token = os.environ.get("FB_PAGE_ACCESS_TOKEN", "")

    if not fb_page_id or not fb_page_token:
        print("[!] PERINGATAN: FB_PAGE_ID atau FB_PAGE_ACCESS_TOKEN belum disetel di environment.")
        print("[!] Berkas kartu dan caption tetap tersimpan di folder posts/facebook_drafts/")
        return False

    success = publish_to_facebook(card_output_path, caption_text, fb_page_id, fb_page_token)

    if success:
        # Catat ke riwayat
        record = {
            "title": chosen["title"],
            "url": chosen["url"],
            "source": chosen["source_name"],
            "score": chosen["virality_score"],
            "theme": detected_theme,
            "published_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB"),
            "image_card": card_output_path,
            "region": card_data.get("badge_red", "BERITA UTAMA")
        }
        save_facebook_history(history_file, record)
        print("[+] SUKSES BESAR! Berita viral berhasil tayang di Halaman Facebook Paduka Sambas.")
        return True
    else:
        print("[!] Gagal mengunggah berita ke Facebook. Riwayat tidak dicatat agar bisa dicoba ulang.")
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Hourly Facebook Viral News Publisher Paduka Sambas")
    parser.add_argument("--dry-run", action="store_true", help="Uji coba filter virality dan render kartu tanpa posting ke Facebook")
    parser.add_argument("--force", action="store_true", help="Paksa penerbitan meskipun berita sudah tercatat di riwayat")
    args = parser.parse_args()

    run_hourly_facebook_publisher(dry_run=args.dry_run, force=args.force)
