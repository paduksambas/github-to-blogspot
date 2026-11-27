#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generator & Publisher Facebook Stories 9:16 (1080 x 1920 px) Paduka Sambas
==========================================================================
- Memilih berita viral teratas dari MD-V14.
- Merender format kanvas vertikal 9:16 penuh layar ponsel dengan tema dinamis.
- Mengunggah ke Facebook Page Stories via Meta Graph API:
  1. POST /{page_id}/photos (published=false) -> mengembalikan photo_id
  2. POST /{page_id}/fb_stories (photo_id=...) -> terbit live sebagai Story 24 jam.
"""

import os
import io
import re
import sys
import json
import ssl
import textwrap
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageOps

try:
    from scripts.facebook_viral_publisher import (
        load_mdv14_feed_catalog,
        fetch_and_parse_feed,
        is_meta_compliant,
        calculate_virality_score,
        extract_opengraph_image,
        EDITORIAL_FALLBACK_IMAGES,
        load_all_facebook_published_history
    )
    from scripts.generate_facebook_post import get_system_font, detect_card_theme
except ImportError:
    from facebook_viral_publisher import (
        load_mdv14_feed_catalog,
        fetch_and_parse_feed,
        is_meta_compliant,
        calculate_virality_score,
        extract_opengraph_image,
        EDITORIAL_FALLBACK_IMAGES,
        load_all_facebook_published_history
    )
    from generate_facebook_post import get_system_font, detect_card_theme

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

STORY_HISTORY_FILE = os.path.join(REPO_ROOT, "facebook_story_history.json")


def load_story_history():
    if os.path.exists(STORY_HISTORY_FILE):
        try:
            with open(STORY_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_story_history(entry):
    history = load_story_history()
    history.append(entry)
    if len(history) > 200:
        history = history[-200:]
    with open(STORY_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    print(f"[+] Riwayat Story Facebook diperbarui ({len(history)} entri).")


def render_story_card_916(data, output_path="posts/facebook_drafts/story_card.png"):
    """
    Merender Master Story Card 9:16 (1080 x 1920 px) berstandar visual Instagram/Facebook Story:
    - 0 - 280 px   : Header Story (Logo Paduka Sambas, badge kategori, indikator update)
    - 280 - 1280 px: Frame Foto Utama Besar (1000 px tinggi proporsional)
    - 1280 - 1750 px: Box Judul & Ringkasan Kontras Tinggi
    - 1750 - 1920 px: Call to Action (Ajakan membaca selengkapnya di Feed)
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    w, h = 1080, 1920
    theme = detect_card_theme(data.get("title", ""), data.get("category", ""))

    # Palet Warna Sesuai Tema
    if theme == "finance":
        theme_bg = (12, 28, 58)
        accent = (0, 220, 255)
        badge_bg = (0, 220, 255)
        badge_fg = (5, 15, 30)
        box_bg = (245, 245, 245)
        box_fg = (10, 20, 40)
    elif theme == "justice":
        theme_bg = (22, 24, 28)
        accent = (220, 38, 38)
        badge_bg = (220, 38, 38)
        badge_fg = (255, 255, 255)
        box_bg = (235, 235, 238)
        box_fg = (15, 15, 20)
    elif theme == "daerah":
        theme_bg = (11, 55, 35)
        accent = (250, 195, 30)
        badge_bg = (250, 195, 30)
        badge_fg = (10, 40, 25)
        box_bg = (250, 195, 30)
        box_fg = (10, 35, 20)
    elif theme == "tech":
        theme_bg = (15, 23, 42)
        accent = (6, 182, 212)
        badge_bg = (6, 182, 212)
        badge_fg = (15, 23, 42)
        box_bg = (226, 232, 240)
        box_fg = (15, 23, 42)
    else:  # 'breaking'
        theme_bg = (215, 25, 25)
        accent = (255, 215, 0)
        badge_bg = (255, 215, 0)
        badge_fg = (0, 0, 0)
        box_bg = (255, 215, 0)
        box_fg = (10, 10, 10)

    card = Image.new("RGB", (w, h), (14, 14, 14))
    draw = ImageDraw.Draw(card)

    # 1. ZONA ATAS (HEADER STORY: 0 - 280 px)
    draw.rectangle([0, 0, w, 280], fill=theme_bg)
    for i in range(4):
        x = w - 160 + (i * 32)
        draw.polygon([(x, 0), (x + 18, 0), (x - 30, 280), (x - 48, 280)], fill=accent)

    # Badge Logo
    draw.rounded_rectangle([35, 45, 35 + 260, 45 + 105], radius=18, fill=badge_bg, outline=(0, 0, 0), width=3)
    f_b1 = get_system_font("impact", 30)
    f_b2 = get_system_font("impact", 24)
    draw.text((55, 55), "PADUKA SAMBAS", font=f_b1, fill=badge_fg)
    draw.text((55, 92), "STORY UPDATE", font=f_b2, fill=badge_fg)

    # Label Kanan Atas
    f_cat = get_system_font("bold", 28)
    cat_text = data.get("category", "KABAR TERKINI").upper()[:16]
    draw.text((320, 65), "SOROTAN UTAMA", font=f_cat, fill=(255, 255, 255))
    f_date = get_system_font("regular", 22)
    draw.text((320, 105), datetime.now().strftime("%d %B %Y | Berita Terpilih"), font=f_date, fill=accent)

    draw.line([(0, 280), (w, 280)], fill=(0, 0, 0), width=6)

    # 2. ZONA TENGAH (FOTO UTAMA BESAR: 280 - 1280 px)
    photo_url = data.get("image_url", "")
    p_img = None
    if photo_url and photo_url.startswith("http"):
        try:
            req = urllib.request.Request(photo_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10, context=SSL_CONTEXT) as resp:
                p_img = Image.open(io.BytesIO(resp.read())).convert("RGB")
        except Exception:
            pass
    if not p_img:
        p_img = Image.new("RGB", (w, 1000), (30, 35, 45))
        d_p = ImageDraw.Draw(p_img)
        d_p.text((w // 4, 450), "DOKUMENTASI REDAKSI", font=get_system_font("bold", 36), fill=(180, 180, 180))
    else:
        p_img = ImageOps.fit(p_img, (w, 1000), method=Image.Resampling.LANCZOS)

    card.paste(p_img, (0, 280))

    # Aksen Diagonal Bawah Foto
    for i in range(3):
        ox = 0 + (i * 30)
        draw.polygon([(ox, 1280), (ox + 18, 1280), (ox + 85, 1180), (ox + 67, 1180)], fill=accent)

    # 3. ZONA BOX JUDUL & RINGKASAN (1280 - 1720 px)
    draw.rectangle([0, 1280, w, 1720], fill=box_bg)
    draw.line([(0, 1280), (w, 1280)], fill=(0, 0, 0), width=6)

    # Judul Besar
    title = data.get("title", "")
    f_stitle = get_system_font("bold", 46)
    lines = textwrap.wrap(title, width=34)
    y_pos = 1315
    for l in lines[:3]:
        draw.text((50, y_pos), l, font=f_stitle, fill=box_fg)
        y_pos += 62

    # Ringkasan Singkat
    summary = data.get("summary", "")
    if summary:
        f_sum = get_system_font("regular", 26)
        s_lines = textwrap.wrap(summary, width=54)
        y_pos += 15
        for sl in s_lines[:3]:
            draw.text((50, y_pos), sl, font=f_sum, fill=(40, 40, 40) if theme in ["finance", "justice", "tech"] else (20, 20, 20))
            y_pos += 38

    # 4. ZONA FOOTER CALL TO ACTION (1720 - 1920 px)
    draw.rectangle([0, 1720, w, 1920], fill=theme_bg)
    draw.line([(0, 1720), (w, 1720)], fill=accent, width=5)

    f_cta1 = get_system_font("impact", 36)
    f_cta2 = get_system_font("bold", 24)
    draw.text((w // 2 - 210, 1760), "CEK BERITA DI FEED", font=f_cta1, fill=(255, 255, 255))
    draw.text((w // 2 - 270, 1820), "👆 Buka Profil Paduka Sambas untuk Ulasan Lengkap", font=f_cta2, fill=accent)

    card.save(output_path, "PNG", quality=95)
    print(f"[+] Master Story Card 9:16 berhasil dibuat: {output_path}")
    return output_path


def publish_story_to_facebook(image_path, page_id=None, page_token=None):
    """
    Menerbitkan Story Foto Halaman Facebook via Meta Graph API:
    Tahap 1: Upload foto sebagai unpublished photo -> POST /{page_id}/photos?published=false
    Tahap 2: Buat story dari photo_id -> POST /{page_id}/fb_stories?photo_id={photo_id}
    """
    raw_page_id = page_id or os.environ.get("FB_PAGE_ID", "")
    raw_page_token = page_token or os.environ.get("FB_PAGE_ACCESS_TOKEN", "")

    page_id = str(raw_page_id).strip().strip('"\'')
    page_token = str(raw_page_token).strip().strip('"\'')

    if not page_id or not page_token:
        print("[!] Gagal: FB_PAGE_ID atau FB_PAGE_ACCESS_TOKEN belum disetel.")
        return False

    # Tahap 1: Upload Foto Unpublished
    upload_url = f"https://graph.facebook.com/v19.0/{page_id}/photos"
    boundary = "----WebKitFormBoundaryStoryPaduka"
    body = io.BytesIO()

    # Part: published=false
    body.write(f"--{boundary}\r\n".encode("utf-8"))
    body.write(b'Content-Disposition: form-data; name="published"\r\n\r\nfalse\r\n')

    # Part: access_token
    body.write(f"--{boundary}\r\n".encode("utf-8"))
    body.write(b'Content-Disposition: form-data; name="access_token"\r\n\r\n')
    body.write(page_token.encode("utf-8"))
    body.write(b"\r\n")

    # Part: source (image binary)
    with open(image_path, "rb") as f:
        img_bytes = f.read()

    body.write(f"--{boundary}\r\n".encode("utf-8"))
    body.write(b'Content-Disposition: form-data; name="source"; filename="story.png"\r\n')
    body.write(b"Content-Type: image/png\r\n\r\n")
    body.write(img_bytes)
    body.write(b"\r\n")
    body.write(f"--{boundary}--\r\n".encode("utf-8"))

    payload = body.getvalue()
    req = urllib.request.Request(
        upload_url,
        data=payload,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(payload))
        }
    )

    try:
        print("[*] Tahap 1: Mengunggah aset foto Story ke server Meta...")
        with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as resp:
            res1 = json.loads(resp.read().decode("utf-8"))
            photo_id = res1.get("id")
            if not photo_id:
                print(f"[!] Gagal mendapatkan photo_id: {res1}")
                return False
            print(f"[+] Foto Story terunggah dengan ID: {photo_id}")

        # Tahap 2: Terbitkan sebagai Facebook Photo Story
        story_url = f"https://graph.facebook.com/v19.0/{page_id}/photo_stories"
        story_payload = urllib.parse.urlencode({
            "photo_id": photo_id,
            "access_token": page_token
        }).encode("utf-8")

        req2 = urllib.request.Request(story_url, data=story_payload, method="POST")
        print("[*] Tahap 2: Menerbitkan Story ke Facebook Page Paduka Sambas...")
        with urllib.request.urlopen(req2, timeout=25, context=SSL_CONTEXT) as resp2:
            res2 = json.loads(resp2.read().decode("utf-8"))
            story_id = res2.get("story_id") or res2.get("id") or "PUBLISHED"
            print(f"[+] BERHASIL! Facebook Story telah tayang (Story ID: {story_id})")
            return story_id

    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"[!] Gagal menerbitkan Story Facebook: {err_msg}")
        return False
    except Exception as e:
        print(f"[!] Terjadi kesalahan: {e}")
        return False


def run_story_publisher(dry_run=False, force=False):
    """Menjalankan siklus penerbitan Story Facebook."""
    print("\n" + "=" * 70)
    print("PADUKA SAMBAS — FACEBOOK STORIES (9:16) PUBLISHER")
    print(f"Waktu Eksekusi: {datetime.now().strftime('%Y-%m-%d %H:%M:%S WIB')}")
    print("=" * 70)

    history = load_story_history()
    published_urls = {h.get("url") for h in history if h.get("url")}
    published_titles = {h.get("title", "").strip().lower() for h in history if h.get("title")}
    cross_urls, cross_titles = load_all_facebook_published_history()

    # 1. Ambil artikel dari katalog MD-V14
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

    # 2. Filter & Skoring
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
        print("[*] Semua berita terbaru sudah pernah diangkat ke Story.")
        return True

    candidates.sort(key=lambda x: x["score"], reverse=True)
    fresh_cross = [
        c for c in candidates
        if c.get("url", "") not in cross_urls and c.get("title", "").strip().lower() not in cross_titles
    ]
    chosen = fresh_cross[0] if fresh_cross else candidates[0]

    # Pastikan gambar tersedia
    final_img = chosen.get("image_url")
    if not final_img or not final_img.startswith("http"):
        final_img = extract_opengraph_image(chosen.get("url"))
    if not final_img or not final_img.startswith("http"):
        final_img = EDITORIAL_FALLBACK_IMAGES.get(chosen.get("category", "Default"), EDITORIAL_FALLBACK_IMAGES["Default"])
    chosen["image_url"] = final_img

    print(f"[★] Berita Terpilih untuk Story: {chosen['title']}")

    # 3. Render Kartu Story 9:16
    draft_dir = os.path.join(REPO_ROOT, "posts", "facebook_drafts")
    os.makedirs(draft_dir, exist_ok=True)
    out_file = os.path.join(draft_dir, f"fb_story_card_{int(datetime.now().timestamp())}.png")
    render_story_card_916(chosen, out_file)

    if dry_run:
        print("[*] Mode DRY-RUN aktif: Kartu Story 9:16 berhasil dibuat tanpa diunggah.")
        return True

    story_id = publish_story_to_facebook(out_file)
    if story_id:
        record = {
            "title": chosen["title"],
            "url": chosen["url"],
            "published_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB"),
            "story_id": story_id,
            "type": "story_916"
        }
        save_story_history(record)
        return True
    return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Facebook Story 9:16 Publisher")
    parser.add_argument("--dry-run", action="store_true", help="Uji coba render Story tanpa posting")
    parser.add_argument("--force", action="store_true", help="Abaikan riwayat Story")
    args = parser.parse_args()

    ok = run_story_publisher(dry_run=args.dry_run, force=args.force)
    if not ok:
        sys.exit(1)
