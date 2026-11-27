#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generator & Publisher Video Facebook Reels 9:16 Otomatis Paduka Sambas
=====================================================================
- Mengangkat berita viral terhangat dari MD-V14.
- Menghasilkan narasi suara berita alami (Indonesian News Broadcaster) via edge-tts (100% Gratis).
- Mengolah video vertikal 9:16 (1080 x 1920 px) dengan efek visual dan teks berjalan menggunakan FFmpeg.
- Mengunggah langsung ke tab Facebook Reels Halaman via 3-Phase Meta Video Reels API.
"""

import os
import io
import re
import sys
import json
import ssl
import asyncio
import subprocess
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageOps

try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    import shutil
    FFMPEG_EXE = shutil.which("ffmpeg") or "ffmpeg"

try:
    from scripts.facebook_viral_publisher import (
        load_mdv14_feed_catalog,
        fetch_and_parse_feed,
        is_meta_compliant,
        calculate_virality_score,
        extract_opengraph_image,
        EDITORIAL_FALLBACK_IMAGES
    )
    from scripts.generate_facebook_post import get_system_font, detect_card_theme
except ImportError:
    from facebook_viral_publisher import (
        load_mdv14_feed_catalog,
        fetch_and_parse_feed,
        is_meta_compliant,
        calculate_virality_score,
        extract_opengraph_image,
        EDITORIAL_FALLBACK_IMAGES
    )
    from generate_facebook_post import get_system_font, detect_card_theme

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

REELS_HISTORY_FILE = os.path.join(REPO_ROOT, "facebook_reels_history.json")


def load_reels_history():
    if os.path.exists(REELS_HISTORY_FILE):
        try:
            with open(REELS_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_reels_history(entry):
    history = load_reels_history()
    history.append(entry)
    if len(history) > 200:
        history = history[-200:]
    with open(REELS_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    print(f"[+] Riwayat Reels Facebook diperbarui ({len(history)} entri).")


def generate_reels_script_with_gemini(article, gemini_api_key=None):
    """
    Menyusun naskah suara berita ringkas (durasi 15-20 detik) untuk narator AI.
    """
    title = article["title"]
    summary = article.get("summary", "")

    fallback_script = f"Halo Sobat Paduka, kabar penting hari ini. {title}. Peristiwa ini menyita perhatian luas masyarakat. Bagaimana pandangan Anda mengenai hal ini? Tulis pendapat Anda di kolom komentar."

    if not gemini_api_key:
        return fallback_script

    api_key_clean = str(gemini_api_key).strip().strip('"\'')
    prompt = f"""Kamu adalah Penyiar Berita Resmi Paduka Sambas.
Buatkan naskah siaran suara untuk video Facebook Reels pendek berdurasi 15 sampai 20 detik (sekitar 35 sampai 50 kata).

Topik Berita:
Judul: {title}
Ringkasan: {summary}

ATURAN NASKAH:
1. Awali dengan salam ramah: "Halo Sobat Paduka, kabar penting hari ini..."
2. Jelaskan fakta kunci berita secara lugas, ringkas, dan jelas.
3. Akhiri dengan pertanyaan mengajak warga berdiskusi: "Bagaimana pandangan Anda mengenai hal ini? Tulis di kolom komentar ya."
4. Gunakan bahasa Indonesia baku namun luwes dan komunikatif.
5. HANYA kirimkan teks naskah suara yang akan dibacakan narator, tanpa tanda petik atau pengantar."""

    candidate_models = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash", "gemini-2.5-flash"]
    for model in candidate_models:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key_clean}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3}
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
                script = resp_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                if 20 < len(script) < 350:
                    print(f"[+] Naskah Reels AI Gemini ({model}) sukses disusun!")
                    return script
        except Exception:
            continue

    return fallback_script


async def create_voiceover(text, output_audio_path, voice="id-ID-ArdiNeural"):
    """Menghasilkan file audio MP3 narasi suara menggunakan edge-tts."""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_audio_path)
    print(f"[+] Audio narasi suara berhasil dibuat: {output_audio_path}")


def get_audio_duration(audio_path):
    """Mendapatkan durasi audio dalam detik menggunakan ffprobe / ffmpeg."""
    cmd = [
        FFMPEG_EXE, "-i", audio_path
    ]
    try:
        proc = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        # Cari Duration: 00:00:15.34
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", proc.stderr)
        if m:
            hours, mins, secs = float(m.group(1)), float(m.group(2)), float(m.group(3))
            return hours * 3600 + mins * 60 + secs
    except Exception:
        pass
    return 15.0  # Default 15 detik


def render_reels_base_frame(article, output_frame_path):
    """
    Membuat bingkai grafis dasar 1080 x 1920 (9:16) untuk video Reels:
    - Zona Atas: Badge "PADUKA SAMBAS REELS | BERITA VIRAL"
    - Zona Tengah: Foto Berita Resolusi Tinggi 16:9
    - Zona Bawah: Headline Berita Bold & Subtitle Box
    """
    w, h = 1080, 1920
    theme = detect_card_theme(article.get("title", ""), article.get("category", ""))

    if theme == "finance":
        theme_bg = (12, 28, 58)
        accent = (0, 220, 255)
        box_bg = (245, 245, 245)
        box_fg = (10, 20, 40)
    elif theme == "justice":
        theme_bg = (22, 24, 28)
        accent = (220, 38, 38)
        box_bg = (235, 235, 238)
        box_fg = (15, 15, 20)
    elif theme == "daerah":
        theme_bg = (11, 55, 35)
        accent = (250, 195, 30)
        box_bg = (250, 195, 30)
        box_fg = (10, 35, 20)
    elif theme == "tech":
        theme_bg = (15, 23, 42)
        accent = (6, 182, 212)
        box_bg = (226, 232, 240)
        box_fg = (15, 23, 42)
    else:  # 'breaking'
        theme_bg = (215, 25, 25)
        accent = (255, 215, 0)
        box_bg = (255, 215, 0)
        box_fg = (10, 10, 10)

    frame = Image.new("RGB", (w, h), (14, 14, 16))
    draw = ImageDraw.Draw(frame)

    # 1. Header (0 - 260 px)
    draw.rectangle([0, 0, w, 260], fill=theme_bg)
    for i in range(4):
        x = w - 160 + (i * 32)
        draw.polygon([(x, 0), (x + 18, 0), (x - 30, 260), (x - 48, 260)], fill=accent)

    draw.rounded_rectangle([35, 45, 35 + 260, 45 + 105], radius=18, fill=accent, outline=(0, 0, 0), width=3)
    f_b1 = get_system_font("impact", 30)
    f_b2 = get_system_font("impact", 24)
    draw.text((55, 55), "PADUKA SAMBAS", font=f_b1, fill=(0, 0, 0))
    draw.text((55, 92), "REELS UPDATE", font=f_b2, fill=(0, 0, 0))

    f_cat = get_system_font("bold", 28)
    draw.text((320, 70), "KILAS BERITA VIRAL", font=f_cat, fill=(255, 255, 255))
    f_sub = get_system_font("regular", 22)
    draw.text((320, 110), "Tonton Ringkasan Berita Cepat & Beri Pendapat", font=f_sub, fill=accent)

    # 2. Foto Berita Tengah (260 - 1200 px)
    photo_url = article.get("image_url", "")
    p_img = None
    if photo_url and photo_url.startswith("http"):
        try:
            req = urllib.request.Request(photo_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10, context=SSL_CONTEXT) as resp:
                p_img = Image.open(io.BytesIO(resp.read())).convert("RGB")
        except Exception:
            pass
    if not p_img:
        p_img = Image.new("RGB", (w, 940), (35, 40, 50))
    else:
        p_img = ImageOps.fit(p_img, (w, 940), method=Image.Resampling.LANCZOS)

    frame.paste(p_img, (0, 260))

    # Aksen Garis
    draw.line([(0, 260), (w, 260)], fill=(0, 0, 0), width=6)
    draw.line([(0, 1200), (w, 1200)], fill=(0, 0, 0), width=6)

    # 3. Box Headline (1200 - 1650 px)
    import textwrap
    draw.rectangle([0, 1200, w, 1650], fill=box_bg)
    f_ht = get_system_font("bold", 45)
    lines = textwrap.wrap(article.get("title", ""), width=34)
    y_pos = 1240
    for l in lines[:3]:
        draw.text((50, y_pos), l, font=f_ht, fill=box_fg)
        y_pos += 62

    # Sumber & Tagar
    f_src = get_system_font("bold", 24)
    src_text = f"Sumber: {article.get('source_name', 'Redaksi')}  •  PADUKA SAMBAS REELS"
    draw.text((50, 1570), src_text, font=f_src, fill=(80, 80, 80) if theme in ["finance", "justice", "tech"] else (40, 40, 40))

    # 4. Footer CTA (1650 - 1920 px)
    draw.rectangle([0, 1650, w, 1920], fill=theme_bg)
    draw.line([(0, 1650), (w, 1650)], fill=accent, width=5)

    f_cta = get_system_font("impact", 36)
    f_cta2 = get_system_font("bold", 24)
    draw.text((w // 2 - 250, 1720), "IKUTI @PADUKASAMBAS", font=f_cta, fill=(255, 255, 255))
    draw.text((w // 2 - 290, 1785), "💬 Tuliskan Pendapat Anda di Kolom Komentar 👇", font=f_cta2, fill=accent)

    frame.save(output_frame_path, "PNG")
    print(f"[+] Frame visual Reels siap: {output_frame_path}")
    return output_frame_path


def compile_reels_video(frame_path, audio_path, output_video_path):
    """
    Menggabungkan frame grafis dan audio narasi menjadi video MP4 1080x1920 H.264/AAC.
    """
    duration = get_audio_duration(audio_path)
    print(f"[*] Durasi video Reels: {duration:.1f} detik. Memproses kompilasi MP4...")

    cmd = [
        FFMPEG_EXE, "-y",
        "-loop", "1", "-i", frame_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-t", str(duration + 0.8),
        output_video_path
    ]

    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    print(f"[+] Video MP4 Reels berhasil dirender: {output_video_path} ({os.path.getsize(output_video_path)} bytes)")
    return output_video_path


def publish_reels_to_facebook(video_path, caption, page_id=None, page_token=None):
    """
    Menerbitkan Video Facebook Reels via Meta 3-Phase Resumable API:
    Fase 1: Inisialisasi -> POST /{page-id}/video_reels (upload_phase=start) -> video_id
    Fase 2: Upload Binary -> POST https://rupload.facebook.com/video-upload/v19.0/{video_id}
    Fase 3: Publikasi -> POST /{page-id}/video_reels (upload_phase=finish, video_state=PUBLISHED)
    """
    raw_page_id = page_id or os.environ.get("FB_PAGE_ID", "")
    raw_page_token = page_token or os.environ.get("FB_PAGE_ACCESS_TOKEN", "")

    page_id = str(raw_page_id).strip().strip('"\'')
    page_token = str(raw_page_token).strip().strip('"\'')

    if not page_id or not page_token:
        print("[!] Gagal: FB_PAGE_ID atau FB_PAGE_ACCESS_TOKEN belum disetel.")
        return False

    file_size = os.path.getsize(video_path)

    # Fase 1: Inisialisasi Session Reels
    init_url = f"https://graph.facebook.com/v19.0/{page_id}/video_reels"
    init_data = urllib.parse.urlencode({
        "upload_phase": "start",
        "access_token": page_token
    }).encode("utf-8")

    try:
        print("[*] Reels Fase 1: Menginisialisasi sesi unggah video Reels...")
        req1 = urllib.request.Request(init_url, data=init_data, method="POST")
        with urllib.request.urlopen(req1, timeout=25, context=SSL_CONTEXT) as resp:
            res1 = json.loads(resp.read().decode("utf-8"))
            video_id = res1.get("video_id")
            if not video_id:
                print(f"[!] Gagal inisialisasi sesi Reels: {res1}")
                return False
            print(f"[+] Sesi Reels aktif dengan Video ID: {video_id}")

        # Fase 2: Upload Binary ke rupload.facebook.com
        upload_url = f"https://rupload.facebook.com/video-upload/v19.0/{video_id}"
        print(f"[*] Reels Fase 2: Mengunggah binary MP4 ({file_size} bytes) ke rupload.facebook.com...")
        with open(video_path, "rb") as vf:
            video_bytes = vf.read()

        req2 = urllib.request.Request(
            upload_url,
            data=video_bytes,
            headers={
                "Authorization": f"OAuth {page_token}",
                "offset": "0",
                "file_size": str(file_size),
                "Content-Type": "application/octet-stream"
            },
            method="POST"
        )
        with urllib.request.urlopen(req2, timeout=60, context=SSL_CONTEXT) as resp2:
            res2 = json.loads(resp2.read().decode("utf-8"))
            print(f"[+] Unggah binary Reels selesai: {res2}")

        # Fase 3: Selesaikan dan Terbitkan (Finish)
        print("[*] Reels Fase 3: Memproses dan menerbitkan Reels ke Facebook...")
        finish_data = urllib.parse.urlencode({
            "upload_phase": "finish",
            "video_id": video_id,
            "video_state": "PUBLISHED",
            "description": caption,
            "access_token": page_token
        }).encode("utf-8")

        req3 = urllib.request.Request(init_url, data=finish_data, method="POST")
        with urllib.request.urlopen(req3, timeout=30, context=SSL_CONTEXT) as resp3:
            res3 = json.loads(resp3.read().decode("utf-8"))
            if res3.get("success") or res3.get("id"):
                print(f"[+] SUKSES BESAR! Facebook Reel telah resmi terbit (Video ID: {video_id})")
                return video_id
            print(f"[!] Respon fase finish: {res3}")
            return video_id

    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"[!] Gagal menerbitkan Facebook Reel: {err_msg}")
        return False
    except Exception as e:
        print(f"[!] Terjadi kesalahan jaringan Reels: {e}")
        return False


def run_reels_publisher(dry_run=False, force=False):
    """Menjalankan siklus otomatisasi Facebook Reels."""
    print("\n" + "=" * 70)
    print("PADUKA SAMBAS — FACEBOOK REELS (9:16) PUBLISHER")
    print(f"Waktu Eksekusi: {datetime.now().strftime('%Y-%m-%d %H:%M:%S WIB')}")
    print("=" * 70)

    history = load_reels_history()
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
        print("[*] Semua berita terbaru sudah pernah diangkat ke Reels.")
        return True

    candidates.sort(key=lambda x: x["score"], reverse=True)
    chosen = candidates[0]

    # Pastikan foto tersedia
    final_img = chosen.get("image_url")
    if not final_img or not final_img.startswith("http"):
        final_img = extract_opengraph_image(chosen.get("url"))
    if not final_img or not final_img.startswith("http"):
        final_img = EDITORIAL_FALLBACK_IMAGES.get(chosen.get("category", "Default"), EDITORIAL_FALLBACK_IMAGES["Default"])
    chosen["image_url"] = final_img

    print(f"[★] Berita Terpilih untuk Reels: {chosen['title']}")

    draft_dir = os.path.join(REPO_ROOT, "posts", "facebook_drafts")
    os.makedirs(draft_dir, exist_ok=True)
    timestamp_id = int(datetime.now().timestamp())

    # 2. Susun Naskah & Hasilkan Suara Narator AI
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    reels_script = generate_reels_script_with_gemini(chosen, gemini_key)
    audio_path = os.path.join(draft_dir, f"reel_voice_{timestamp_id}.mp3")

    asyncio.run(create_voiceover(reels_script, audio_path, voice="id-ID-ArdiNeural"))

    # 3. Buat Frame Grafis
    frame_path = os.path.join(draft_dir, f"reel_frame_{timestamp_id}.png")
    render_reels_base_frame(chosen, frame_path)

    # 4. Render Video MP4
    video_output_path = os.path.join(draft_dir, f"reel_video_{timestamp_id}.mp4")
    compile_reels_video(frame_path, audio_path, video_output_path)

    caption = f"📌 {chosen['title']}\n\n{reels_script}\n\n(Sumber: {chosen['source_name']})\n\n#PadukaSambas #ReelsViral #BeritaTerkini #KabarDunia #FYP"

    if dry_run:
        print("\n" + "=" * 50)
        print("PREVIEW CAPTION REELS:")
        print("=" * 50)
        print(caption)
        print("=" * 50)
        print(f"[*] Mode DRY-RUN aktif: Video Reels berhasil dibuat di {video_output_path} tanpa diunggah.")
        return True

    video_id = publish_reels_to_facebook(video_output_path, caption)
    if video_id:
        record = {
            "title": chosen["title"],
            "url": chosen["url"],
            "video_id": video_id,
            "published_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB"),
            "video_file": video_output_path
        }
        save_reels_history(record)
        return True
    return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Facebook Reels 9:16 Video Publisher")
    parser.add_argument("--dry-run", action="store_true", help="Render video tanpa unggah ke Facebook")
    parser.add_argument("--force", action="store_true", help="Abaikan riwayat Reels")
    args = parser.parse_args()

    run_reels_publisher(dry_run=args.dry_run, force=args.force)
