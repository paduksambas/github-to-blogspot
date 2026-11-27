#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generator & Publisher Postingan Teks Diskusi Harian Facebook Page Paduka Sambas
=============================================================================
- Mengangkat isu berita terhangat hari ini dari katalog MD-V14.
- Dirancang khusus untuk memicu interaksi komentar netizen di jam istirahat.
- 100% Patuh Standar Komunitas Meta: Tanpa engagement-baiting murahan ("Ketik 1/Amin"),
  melainkan pertanyaan jurnalistik terbuka yang santun dan reflektif.
- Mempublikasikan status teks murni ke timeline Halaman Facebook via Meta Graph API POST /{page_id}/feed.
"""

import os
import sys
import json
import ssl
import random
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

# Impor fungsi pengambil feed dan penyaring keamanan dari facebook_viral_publisher
try:
    from scripts.facebook_viral_publisher import (
        load_mdv14_feed_catalog,
        fetch_and_parse_feed,
        is_meta_compliant,
        calculate_virality_score
    )
except ImportError:
    from facebook_viral_publisher import (
        load_mdv14_feed_catalog,
        fetch_and_parse_feed,
        is_meta_compliant,
        calculate_virality_score
    )

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

TEXT_HISTORY_FILE = os.path.join(REPO_ROOT, "facebook_text_history.json")


def load_text_history():
    if os.path.exists(TEXT_HISTORY_FILE):
        try:
            with open(TEXT_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_text_history(entry):
    history = load_text_history()
    history.append(entry)
    if len(history) > 200:
        history = history[-200:]
    with open(TEXT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    print(f"[+] Riwayat postingan teks diperbarui: {len(history)} entri.")


def generate_discussion_prompt_with_gemini(article, gemini_api_key=None):
    """
    Menggunakan Gemini AI untuk menyusun postingan teks diskusi Facebook
    yang cerdas, santun, dan sangat memicu respons netizen.
    """
    title = article["title"]
    summary = article.get("summary", "")
    source = article.get("source_name", "Media Nasional")

    # Fallback template cerdas jika API tidak tersedia
    fallback_templates = [
        f"📢 POLLING WARGA PADUKA SAMBAS\n\nMengenai isu: \"{title}\".\n\nBagaimana pandangan dan pengalaman pribadi Anda mengenai hal ini di lingkungan sekitar Anda? Apakah kebijakan atau kondisi ini sudah terasa dampaknya?\n\nTulis tanggapan santun dan pendapat Anda di kolom komentar! 👇\n\n#PadukaSambas #SuaraWarga #DiskusiPublik #KalbarHariIni",
        f"💬 RUANG DISKUSI WARGA\n\nSedang ramai diperbincangkan: {title}.\n\nJika melihat kondisi riil di lapangan saat ini, menurut Anda langkah apa yang paling tepat dan mendesak untuk dilakukan?\n\nMari berbagi sudut pandang santun di kolom komentar ya! 👇\n\n#PadukaSambas #KabarTerkini #OpiniWarga",
        f"☕ OBROLAN SIANG PADUKA SAMBAS\n\nSimak isu terkini: \"{title}\".\n\nBagaimana penilaian Anda mengenai peristiwa ini? Tulis pendapat Anda secara bijak di bawah ya!\n\n(Referensi: {source})\n\n#PadukaSambas #DiskusiHangat #KalbarUpdate"
    ]

    if not gemini_api_key:
        return random.choice(fallback_templates)

    api_key_clean = str(gemini_api_key).strip().strip('"\'')
    prompt = f"""Kamu adalah Manajer Komunitas Halaman Facebook Paduka Sambas.
Tugasmu adalah membuat 1 postingan status teks murni (tanpa gambar) untuk memicu ratusan komentar warga di jam istirahat.

Topik Berita:
Judul: {title}
Ringkasan: {summary}
Sumber: {source}

ATURAN KETAT META & KOMUNITAS:
1. DILARANG menggunakan engagement-bait murahan seperti: "Ketik 1", "Share jika setuju", "Komentar Amin", "Tag temanmu".
2. Buat pembuka dengan emoji menarik dan judul singkat (contoh: ☕ OBROLAN SIANG WARGA atau 💬 SUARA PUBLIK SAMBAS).
3. Rangkum inti isu dalam 1 kalimat padat yang mudah dipahami orang awam.
4. Buat 1-2 pertanyaan reflektif/terbuka yang membuat netizen ingin menceritakan pengalaman pribadi atau opininya.
5. Gunakan bahasa Indonesia yang santun, ramah, bersahabat, dan mengajak diskusi secara beradab.
6. Sertakan atribusi sumber singkat dan 3-4 tagar di akhir.
7. Panjang teks: 3-5 paragraf pendek (sekitar 60-120 kata).

Kirim HANYA teks status siap posting tanpa tanda petik pembuka/penutup."""

    candidate_models = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash"]
    for model in candidate_models:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key_clean}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4}
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
                if len(text) > 50:
                    print(f"[+] Teks diskusi AI Gemini ({model}) sukses disusun!")
                    return text
        except Exception:
            continue

    return random.choice(fallback_templates)


def publish_text_post_to_facebook(message, page_id=None, page_token=None):
    """Mempublikasikan postingan teks murni ke timeline Halaman Facebook via Graph API."""
    raw_page_id = page_id or os.environ.get("FB_PAGE_ID", "")
    raw_page_token = page_token or os.environ.get("FB_PAGE_ACCESS_TOKEN", "")

    page_id = str(raw_page_id).strip().strip('"\'')
    page_token = str(raw_page_token).strip().strip('"\'')

    if not page_id or not page_token:
        print("[!] Gagal: FB_PAGE_ID atau FB_PAGE_ACCESS_TOKEN belum disetel.")
        return False

    url = f"https://graph.facebook.com/v19.0/{page_id}/feed"
    payload = urllib.parse.urlencode({
        "message": message,
        "access_token": page_token
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=25, context=SSL_CONTEXT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            post_id = data.get("id")
            print(f"[+] BERHASIL! Status teks diskusi terbit di Facebook dengan Post ID: {post_id}")
            return post_id
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"[!] Gagal posting status teks ke Facebook: {err_msg}")
        return False
    except Exception as e:
        print(f"[!] Terjadi kesalahan jaringan: {e}")
        return False


def run_daily_text_publisher(dry_run=False, force=False):
    """Menjalankan siklus postingan teks diskusi harian."""
    print("\n" + "=" * 70)
    print("PADUKA SAMBAS — DAILY FACEBOOK TEXT DISCUSSION PUBLISHER")
    print(f"Waktu Eksekusi: {datetime.now().strftime('%Y-%m-%d %H:%M:%S WIB')}")
    print("=" * 70)

    history = load_text_history()
    published_urls = {h.get("url") for h in history if h.get("url")}
    published_titles = {h.get("title", "").strip().lower() for h in history if h.get("title")}

    # 1. Muat artikel dari katalog MD-V14
    feed_catalog = load_mdv14_feed_catalog()
    enabled_feeds = [f for f in feed_catalog if f.get("enabled", True)]

    all_articles = []
    for f_info in enabled_feeds:
        articles = fetch_and_parse_feed(f_info)
        all_articles.extend(articles)

    if not all_articles:
        print("[!] Tidak ada artikel yang berhasil dimuat.")
        return False

    all_titles = [a["title"].strip().lower() for a in all_articles]

    # 2. Filter kepatuhan & urutkan topik diskusi terbaik
    candidates = []
    for item in all_articles:
        url = item.get("url", "")
        t_clean = item.get("title", "").strip().lower()

        if not force:
            if url in published_urls or t_clean in published_titles:
                continue

        is_safe, _ = is_meta_compliant(item)
        if not is_safe:
            continue

        score = calculate_virality_score(item, all_titles)
        item["score"] = score
        candidates.append(item)

    if not candidates:
        print("[*] Semua topik terbaru sudah pernah diangkat. Tidak ada postingan teks baru.")
        return True

    # Utamakan isu sosial, ekonomi rakyat, atau isu nasional/daerah yang relatable
    candidates.sort(key=lambda x: x["score"], reverse=True)
    chosen = candidates[0]

    print(f"[★] Topik Diskusi Terpilih: {chosen['title']} ({chosen['source_name']})")

    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    message_text = generate_discussion_prompt_with_gemini(chosen, gemini_key)

    print("\n" + "=" * 50)
    print("PREVIEW TEKS STATUS DISKUSI:")
    print("=" * 50)
    print(message_text)
    print("=" * 50 + "\n")

    if dry_run:
        print("[*] Mode DRY-RUN aktif: Status teks berhasil dibuat tanpa diposting.")
        return True

    post_id = publish_text_post_to_facebook(message_text)
    if post_id:
        record = {
            "title": chosen["title"],
            "url": chosen["url"],
            "published_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB"),
            "post_id": post_id,
            "type": "text_discussion"
        }
        save_text_history(record)
        return True
    return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Facebook Daily Text Discussion Publisher")
    parser.add_argument("--dry-run", action="store_true", help="Uji coba pembuatan teks tanpa posting")
    parser.add_argument("--force", action="store_true", help="Abaikan riwayat pernah tayang")
    args = parser.parse_args()

    run_daily_text_publisher(dry_run=args.dry_run, force=args.force)
