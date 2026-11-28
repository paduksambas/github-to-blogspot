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
from datetime import datetime, timezone, timedelta

def get_wib_now():
    return datetime.now(timezone(timedelta(hours=7)))
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
        EDITORIAL_FALLBACK_IMAGES,
        load_all_facebook_published_history,
        is_duplicate_news,
        sanitize_caption_anti_clickbait,
        get_dynamic_hashtags
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
        load_all_facebook_published_history,
        is_duplicate_news,
        sanitize_caption_anti_clickbait,
        get_dynamic_hashtags
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
    Menyusun naskah suara berita Reels berorientasi High-Engagement & Retensi Tinggi (15-20 detik).
    Menggunakan formula Viral Hook (Detik 0-3) + Fakta Inti (Detik 4-15) + Debate Trigger CTA (Detik 16-20).
    """
    title = article["title"]
    summary = article.get("summary", "")

    fallback_script = f"Kabar mengejutkan hari ini! {title}. Peristiwa ini langsung menuai sorotan luas masyarakat. Menurut Anda, bagaimana langkah terbaik menyikapi hal ini? Tulis pendapat jujur Anda di kolom komentar!"

    if not gemini_api_key:
        return fallback_script

    api_key_clean = str(gemini_api_key).strip().strip('"\'')
    prompt = f"""Kamu adalah Scriptwriter Video Pendek (Facebook Reels / TikTok) Berita Viral Profesional untuk Paduka Sambas.
Tugasmu: Tulis naskah suara berita yang sangat memikat, berdurasi 15-20 detik (sekitar 35-48 kata) dengan retensi penonton dan interaksi komentar TINGGI.

Judul Berita: {title}
Ringkasan: {summary}

STRUKTUR WAJIB NASKAH (FORMULA VIRAL HOOK):
1. HOOK (Detik 0-3): JANGAN gunakan salam pembuka seperti 'Halo sobat'. LANGSUNG buka dengan kalimat pembuka yang mengejutkan, mengusik rasa penasaran, atau fakta mencengangkan!
   Contoh: "Peristiwa ini mendadak bikin heboh warganet!" / "Warga wajib tahu fakta mengejutkan soal ini!" / "Pemerintah baru saja putuskan aturan kontroversial ini!"
2. INTI FAKTA (Detik 4-15): Jelaskan 1-2 inti peristiwa secara lugas, cepat, dan jelas tanpa bertele-tele.
3. CALL TO ACTION / DEBATE TRIGGER (Detik 16-20): Tutup dengan pertanyaan yang memancing emosi / opini penonton untuk berdebat di komentar.
   Contoh: "Menurut Anda, keputusan ini sudah tepat atau belum? Tulis pendapat jujur Anda di bawah!"

ATURAN KETAT:
- Bahasa Indonesia lugas, bertempo cepat, dan enak didengar.
- HANYA kirimkan teks naskah suara murni yang akan dibacakan, tanpa tanda petik, tanpa label (seperti [Hook]), dan tanpa penjelasan tambahan."""

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
                    print(f"[+] Naskah Reels High-Engagement AI Gemini ({model}) sukses disusun!")
                    return script
        except Exception:
            continue

    return fallback_script


async def create_voiceover_and_cues(text, output_audio_path, voice="id-ID-ArdiNeural"):
    """
    Menghasilkan file audio MP3 narasi suara menggunakan edge-tts,
    sekaligus mengekstrak penanda waktu per kalimat (cues) untuk subtitle & sinkronisasi animasi bibir.
    """
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    cues = []
    with open(output_audio_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "SentenceBoundary":
                start_sec = chunk["offset"] / 10000000.0
                dur_sec = chunk["duration"] / 10000000.0
                cues.append({
                    "start": start_sec,
                    "end": start_sec + dur_sec,
                    "text": chunk["text"]
                })
    print(f"[+] Audio narasi suara berhasil dibuat: {output_audio_path}")
    print(f"[+] Penanda waktu subtitle ({len(cues)} kalimat) berhasil diekstrak.")
    return cues


def get_audio_duration(audio_path):
    """Mendapatkan durasi audio dalam detik menggunakan ffprobe / ffmpeg."""
    cmd = [
        FFMPEG_EXE, "-i", audio_path
    ]
    try:
        proc = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", proc.stderr)
        if m:
            hours, mins, secs = float(m.group(1)), float(m.group(2)), float(m.group(3))
            return hours * 3600 + mins * 60 + secs
    except Exception:
        pass
    return 15.0


def render_and_compile_reels_video(article, script_text, audio_path, cues, output_video_path):
    """
    Merender video Reels 1080x1920 (9:16) berorientasi HIGH-ENGAGEMENT:
    1. Header Bar: Glowing Live Broadcast Alert & Punchy Mega Title
    2. Visual Utama (Atas): Foto Liputan Aktual dengan Dinamika Ken Burns Slow Zoom
    3. Live Subtitle Box (Tengah): High-Contrast Bold Subtitles bergaya Dopamin-Reading
    4. Presenter Singa Berjas (Bawah): Studio News Desk TV dengan animasi gerak bibir (Lip-Sync)
    5. Footer CTA (Bawah): Banner Interaksi Penggerak Komentar & Debat Warga
    Mengalirkan frame secara efisien ke FFmpeg stdin tanpa membebani disk/RAM.
    """
    import textwrap
    w, h = 1080, 1920
    fps = 10  # 10 fps sangat stabil untuk animasi maskot dan takarir teks

    duration = get_audio_duration(audio_path) + 0.6
    total_frames = int(duration * fps)
    theme = detect_card_theme(article.get("title", ""), article.get("category", ""))

    print(f"[*] Merender {total_frames} frame video Reels High-Engagement ({duration:.1f} detik)...")

    # Palet Warna Sesuai Tema Berita
    if theme == "finance":
        theme_bg = (10, 25, 50)
        accent = (0, 220, 255)
        tag_label = "📊 KABAR EKONOMI"
    elif theme == "justice":
        theme_bg = (20, 22, 28)
        accent = (239, 68, 68)
        tag_label = "⚖️ HUKUM & KEADILAN"
    elif theme == "daerah":
        theme_bg = (10, 48, 30)
        accent = (250, 204, 21)
        tag_label = "🌴 KABAR SAMBAS"
    elif theme == "tech":
        theme_bg = (15, 23, 42)
        accent = (6, 182, 212)
        tag_label = "🚀 SAINS & TEKNOLOGI"
    else:  # breaking
        theme_bg = (185, 20, 20)
        accent = (255, 220, 0)
        tag_label = "🔥 BREAKING NEWS"

    # Muat Aset Maskot Singa Dinamis
    assets_dir = os.path.join(REPO_ROOT, "assets")
    mascot_map = {
        "finance": ("lion_finance_closed.jpg", "lion_finance_speaking.jpg", "📊 ANALIS EKONOMI SAMBAS"),
        "justice": ("lion_justice_closed.jpg", "lion_justice_speaking.jpg", "⚖️ REPORTER INVESTIGASI"),
        "daerah": ("lion_daerah_closed.jpg", "lion_daerah_speaking.jpg", "🌴 DUTA KABAR SAMBAS"),
        "tech": ("lion_tech_closed.jpg", "lion_tech_speaking.jpg", "💻 PRESENTER SAINS & AI"),
        "breaking": ("lion_anchor_closed.jpg", "lion_anchor_speaking.jpg", "🦁 PRESENTER UTAMA SAMBAS"),
    }
    closed_file, open_file, presenter_label = mascot_map.get(theme, mascot_map["breaking"])
    closed_path = os.path.join(assets_dir, closed_file)
    open_path = os.path.join(assets_dir, open_file)

    if not (os.path.exists(closed_path) and os.path.exists(open_path)):
        closed_path = os.path.join(assets_dir, "lion_anchor_closed.jpg")
        open_path = os.path.join(assets_dir, "lion_anchor_speaking.jpg")

    print(f"[+] Maskot Presenter: {presenter_label} (Tema: {theme})")

    lion_size = (620, 620)
    if os.path.exists(closed_path) and os.path.exists(open_path):
        lion_closed = Image.open(closed_path).convert("RGB").resize(lion_size, Image.Resampling.LANCZOS)
        lion_open = Image.open(open_path).convert("RGB").resize(lion_size, Image.Resampling.LANCZOS)
    else:
        lion_closed = Image.new("RGB", lion_size, (25, 35, 55))
        lion_open = Image.new("RGB", lion_size, (35, 45, 65))

    lion_mask = Image.new("L", lion_size, 0)
    mask_draw = ImageDraw.Draw(lion_mask)
    mask_draw.rounded_rectangle([0, 0, lion_size[0], lion_size[1]], radius=45, fill=255)

    # Muat Foto Berita Utama untuk efek Ken Burns (Zoom Pelan)
    photo_url = article.get("image_url", "")
    p_img_raw = None
    if photo_url and photo_url.startswith("http"):
        try:
            req = urllib.request.Request(photo_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10, context=SSL_CONTEXT) as resp:
                p_img_raw = Image.open(io.BytesIO(resp.read())).convert("RGB")
        except Exception:
            pass
    if not p_img_raw:
        p_img_raw = Image.new("RGB", (w, 810), (30, 38, 50))
    else:
        p_img_raw = ImageOps.fit(p_img_raw, (w, 810), method=Image.Resampling.LANCZOS)

    # Pre-render Static Base Components
    f_impact_l = get_system_font("impact", 36)
    f_bold_l = get_system_font("bold", 30)
    f_bold_m = get_system_font("bold", 24)
    f_sub = get_system_font("bold", 38)
    f_cta = get_system_font("impact", 30)

    # 2. Buka Pipa Kompilasi FFmpeg
    cmd = [
        FFMPEG_EXE, "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{w}x{h}",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "-",  # Pipe input dari Python
        "-i", audio_path,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output_video_path
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    lion_pos_x = (w - lion_size[0]) // 2
    lion_pos_y = 1200

    # 3. Render Setiap Frame Berdasarkan Waktu t
    for frame_idx in range(total_frames):
        t = frame_idx / float(fps)

        # Frame Base
        frame = Image.new("RGB", (w, h), (10, 14, 24))
        draw = ImageDraw.Draw(frame)

        # ========================================================
        # 1. HEADER BROADCAST & HOOK (0 - 240 px)
        # ========================================================
        draw.rectangle([0, 0, w, 240], fill=theme_bg)
        
        # Live Red Beaming Pill
        draw.rounded_rectangle([35, 25, 340, 68], radius=22, fill=(220, 38, 38), outline=(255, 255, 255), width=2)
        draw.text((50, 32), "🔴 LIVE REPORT", font=get_system_font("bold", 22), fill=(255, 255, 255))
        draw.text((220, 32), "• SAMBAS", font=get_system_font("bold", 22), fill=(254, 240, 138))

        # Channel Tag Pill
        draw.rounded_rectangle([w - 320, 25, w - 35, 68], radius=22, fill=(15, 23, 42), outline=accent, width=2)
        draw.text((w - 305, 33), "🦁 PADUKA SAMBAS", font=get_system_font("bold", 20), fill=accent)

        # Mega Headline Banner (2 lines max)
        title_text = article.get("title", "")
        title_lines = textwrap.wrap(title_text, width=32)
        title_y = 85
        for tl in title_lines[:2]:
            bbox = f_impact_l.getbbox(tl)
            tw = bbox[2] - bbox[0]
            tx = max(35, (w - tw) // 2)
            # Heavy drop shadow
            draw.text((tx + 2, title_y + 2), tl, font=f_impact_l, fill=(0, 0, 0))
            draw.text((tx, title_y), tl, font=f_impact_l, fill=(255, 255, 255))
            title_y += 50

        draw.line([(0, 240), (w, 240)], fill=accent, width=4)

        # ========================================================
        # 2. FOTO BERITA DENGAN KEN BURNS MOTION (240 - 1050 px)
        # ========================================================
        # Zoom factor perlahan dari 1.0 ke 1.07 agar foto bergerak hidup
        zoom = 1.0 + (t / max(duration, 1.0)) * 0.07
        crop_w = int(w / zoom)
        crop_h = int(810 / zoom)
        crop_x = (w - crop_w) // 2
        crop_y = (810 - crop_h) // 2
        
        p_cropped = p_img_raw.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))
        p_resized = p_cropped.resize((w, 810), Image.Resampling.BILINEAR)
        frame.paste(p_resized, (0, 240))

        # Gradient vignette di bawah foto agar menyatu halus
        overlay_shade = Image.new("RGBA", (w, 140), (0, 0, 0, 220))
        frame.paste(overlay_shade, (0, 910), overlay_shade)
        draw.line([(0, 1050), (w, 1050)], fill=accent, width=4)

        # Topik Badge di sudut foto
        draw.rounded_rectangle([35, 930, 35 + 260, 975], radius=10, fill=(15, 23, 42), outline=accent, width=2)
        draw.text((50, 938), tag_label, font=get_system_font("bold", 20), fill=accent)

        # ========================================================
        # 3. PRESENTER SINGA AI & NEWS DESK (1200 - 1820 px)
        # ========================================================
        # Cek status bicara (lip-sync)
        is_speaking = False
        active_subtitle = ""
        for cue in cues:
            if cue["start"] <= t <= cue["end"]:
                is_speaking = True
                active_subtitle = cue["text"]
                break

        mouth_open = is_speaking and (int(t * 7) % 2 == 1)
        current_lion = lion_open if mouth_open else lion_closed

        # Studio Desk Frame
        draw.rounded_rectangle(
            [lion_pos_x - 10, lion_pos_y - 10, lion_pos_x + lion_size[0] + 10, lion_pos_y + lion_size[1] + 10],
            radius=52, fill=accent
        )
        frame.paste(current_lion, (lion_pos_x, lion_pos_y), lion_mask)

        # Anchor Microphone Badge
        f_badge = get_system_font("bold", 22)
        draw.rounded_rectangle(
            [lion_pos_x + 60, lion_pos_y + lion_size[1] - 36, lion_pos_x + lion_size[0] - 60, lion_pos_y + lion_size[1] + 12],
            radius=14, fill=(10, 15, 28), outline=accent, width=3
        )
        badge_txt = f"🎙️ {presenter_label}"
        bbox_p = f_badge.getbbox(badge_txt)
        pw = bbox_p[2] - bbox_p[0]
        px = lion_pos_x + (lion_size[0] - pw) // 2
        draw.text((px, lion_pos_y + lion_size[1] - 30), badge_txt, font=f_badge, fill=accent)

        # ========================================================
        # 4. LIVE HIGH-DOPAMINE SUBTITLE BOX (1060 - 1220 px)
        # ========================================================
        if active_subtitle:
            sub_lines = textwrap.wrap(active_subtitle, width=28)
            box_h = 50 * len(sub_lines) + 26
            box_y = 1130 - (box_h // 2)

            sub_overlay = Image.new("RGBA", (w - 80, box_h), (8, 12, 22, 235))
            sub_d = ImageDraw.Draw(sub_overlay)
            sub_d.rounded_rectangle([0, 0, w - 80, box_h], radius=18, outline=accent, width=3)
            frame.paste(sub_overlay, (40, box_y), sub_overlay)

            # Teks Kuning Neon Berbayang Kuat
            text_y = box_y + 14
            for s_line in sub_lines:
                bbox_s = f_sub.getbbox(s_line)
                lw = bbox_s[2] - bbox_s[0]
                lx = (w - lw) // 2
                # Triple shadow untuk keterbacaan 100%
                for dx, dy in [(-2,0), (2,0), (0,-2), (0,2), (2,2)]:
                    draw.text((lx + dx, text_y + dy), s_line, font=f_sub, fill=(0, 0, 0))
                draw.text((lx, text_y), s_line, font=f_sub, fill=(255, 234, 0))
                text_y += 50

        # ========================================================
        # 5. FOOTER CALL-TO-ACTION FOR HIGH ENGAGEMENT (1820 - 1920 px)
        # ========================================================
        draw.rectangle([0, 1820, w, 1920], fill=(220, 38, 38))
        cta_text = "💬 TULIS PENDAPAT ANDA DI KOMENTAR! ⬇️"
        bbox_cta = f_cta.getbbox(cta_text)
        cw = bbox_cta[2] - bbox_cta[0]
        draw.text(((w - cw) // 2, 1850), cta_text, font=f_cta, fill=(255, 255, 255))

        # Tulis frame raw RGB bytes ke FFmpeg stdin
        proc.stdin.write(frame.tobytes())

    proc.stdin.close()
    proc.wait()

    print(f"[+] Video Reels High-Engagement Singa Berjas berhasil dirender: {output_video_path} ({os.path.getsize(output_video_path)} bytes)")
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
    print(f"Waktu Eksekusi: {get_wib_now().strftime('%Y-%m-%d %H:%M:%S WIB')}")
    print("=" * 70)

    all_published_items = load_all_facebook_published_history()

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
        title = item.get("title", "")

        if not force:
            is_dup, _ = is_duplicate_news(title, url, all_published_items)
            if is_dup:
                continue

        is_safe, _ = is_meta_compliant(item)
        if not is_safe:
            continue

        score = calculate_virality_score(item, all_titles)
        item["score"] = score
        candidates.append(item)

    if not candidates:
        print("[*] Semua berita terbaru sudah pernah diangkat di pilar Facebook/Blogger. Berhenti demi mencegah duplikasi.")
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

    # 2. Susun Naskah & Hasilkan Suara Narator AI + Timestamps Subtitle
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    reels_script = generate_reels_script_with_gemini(chosen, gemini_key)
    audio_path = os.path.join(draft_dir, f"reel_voice_{timestamp_id}.mp3")

    cues = asyncio.run(create_voiceover_and_cues(reels_script, audio_path, voice="id-ID-ArdiNeural"))

    # 3. Render Video MP4 dengan Animasi Maskot Singa Berjas & Subtitle Bergerak
    video_output_path = os.path.join(draft_dir, f"reel_video_{timestamp_id}.mp4")
    render_and_compile_reels_video(chosen, reels_script, audio_path, cues, video_output_path)

    theme_detected = detect_card_theme(chosen.get("title", ""), chosen.get("category", ""))
    dynamic_tags = " ".join(f"#{t}" for t in get_dynamic_hashtags(theme_detected))
    raw_caption = f"📌 {chosen['title']}\n\n{reels_script}\n\n(Sumber: {chosen['source_name']})\n\n{dynamic_tags}"
    caption = sanitize_caption_anti_clickbait(raw_caption)

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
            "published_at": get_wib_now().strftime("%Y-%m-%d %H:%M:%S WIB"),
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

    ok = run_reels_publisher(dry_run=args.dry_run, force=args.force)
    if not ok:
        sys.exit(1)
