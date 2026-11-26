#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generator Postingan Halaman Facebook (Page) Paduka Sambas
========================================================
Standar Resmi: Zero-Link Posting (Jurnalisme Native)
Format Visual: Master News Card 4:5 (1080 x 1350 px) PNG
Palet Warna  : Hijau Zamrud Sangat Gelap (#0B251C) & Kuning Emas Melayu (#F4C430)
"""

import os
import io
import re
import sys
import json
import urllib.request
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageOps


def get_system_font(font_type="bold", size=24):
    """Mencari font sistem yang tersedia di Windows maupun Linux (GitHub Actions)."""
    if font_type == "bold":
        candidate_paths = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        ]
    else:
        candidate_paths = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
        ]

    for p in candidate_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass

    try:
        return ImageFont.load_default()
    except Exception:
        return None


def generate_facebook_news_card(data, output_path="posts/facebook_drafts/news_card.png"):
    """
    Menghasilkan gambar Master News Card 4:5 (1080 x 1350 px) berstandar resmi Paduka Sambas.
    Mendukung dua mode otomatis:
    - Mode A: Berita Berbasis Data / Angka
    - Mode B: Berita Peristiwa / Non-Angka
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    w, h = 1080, 1350
    margin_x = 84

    # 1. Unduh / Buka Foto Latar Belakang
    bg_img = None
    photo_url = data.get("photo_url", "")
    if photo_url and photo_url.startswith("http"):
        try:
            req = urllib.request.Request(photo_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                bg_img = Image.open(io.BytesIO(resp.read())).convert("RGBA")
        except Exception as e:
            print(f"[!] Gagal unduh foto latar {photo_url}: {e}")

    if not bg_img:
        # Fallback warna gelap jika foto tidak tersedia
        bg_img = Image.new("RGBA", (w, h), (15, 23, 42, 255))

    # Resize dan crop proporsional ke 4:5
    bg_img = ImageOps.fit(bg_img, (w, h), method=Image.Resampling.LANCZOS)

    # 2. Lapisan Vignette Scrim (Hijau Zamrud Gelap Melayu Sambas #0B251C)
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)

    # Gradien atas untuk badge & logo
    for y in range(0, 220):
        alpha = int((1 - (y / 220)) * 180)
        draw_ov.line([(0, y), (w, y)], fill=(8, 14, 18, alpha))

    # Gradien bawah untuk judul dan blok data
    for y in range(500, h):
        prog = (y - 500) / (h - 500)
        alpha = int((prog ** 1.35) * 252)
        draw_ov.line([(0, y), (w, y)], fill=(8, 22, 18, alpha))

    final_img = Image.alpha_composite(bg_img, overlay).convert("RGB")
    draw = ImageDraw.Draw(final_img)

    # 3. Muat Font Resmi
    font_logo = get_system_font("bold", 22)
    font_badge = get_system_font("bold", 20)
    font_kicker = get_system_font("bold", 22)
    font_headline = get_system_font("bold", 56)
    font_sub = get_system_font("regular", 25)
    font_meta = get_system_font("bold", 19)

    is_data_mode = data.get("is_data_mode", False)

    # 4. ZONA ATAS (Header & Branding)
    # Badge Kiri: Urgensi (Merah) & Topik (Emas)
    badge_red_text = data.get("badge_red", "INFO SAMBAS")
    bbox_br = font_badge.getbbox(badge_red_text)
    br_w = bbox_br[2] - bbox_br[0]
    draw.rounded_rectangle([margin_x, 70, margin_x + br_w + 35, 118], radius=8, fill=(217, 45, 32))
    draw.text((margin_x + 18, 80), badge_red_text, font=font_badge, fill=(255, 255, 255))

    badge_gold_text = data.get("badge_gold", "BERITA TERBARU")
    bbox_bg = font_badge.getbbox(badge_gold_text)
    bg_w = bbox_bg[2] - bbox_bg[0]
    start_gold_x = margin_x + br_w + 50
    draw.rounded_rectangle([start_gold_x, 70, start_gold_x + bg_w + 35, 118], radius=8, fill=(11, 37, 28, 220), outline=(244, 196, 48), width=1)
    draw.text((start_gold_x + 18, 80), badge_gold_text, font=font_badge, fill=(244, 196, 48))

    # Logo Resmi Kanan Atas
    logo_text = "PADUKA SAMBAS"
    bbox_logo = font_logo.getbbox(logo_text)
    lw = bbox_logo[2] - bbox_logo[0]
    logo_x0 = w - margin_x - lw - 40
    draw.rounded_rectangle([logo_x0, 70, w - margin_x, 118], radius=8, fill=(15, 23, 42, 230), outline=(51, 65, 85), width=1)
    draw.text((logo_x0 + 20, 80), logo_text, font=font_logo, fill=(255, 255, 255))

    # 5. ZONA BAWAH (Lower-Third Headline & Kotak Informasi)
    y_anchor = 720
    # Garis Aksen Emas Melayu
    draw.line([(margin_x, y_anchor), (margin_x + 90, y_anchor)], fill=(244, 196, 48), width=5)

    kicker_text = data.get("kicker", "KABAR DAERAH SAMBAS").upper()
    draw.text((margin_x + 105, y_anchor - 12), kicker_text, font=font_kicker, fill=(244, 196, 48))

    # Headline Baris 1
    head_line1 = data.get("headline_line1", "")
    y_head = y_anchor + 35
    draw.text((margin_x, y_head), head_line1, font=font_headline, fill=(255, 255, 255))

    # Headline Baris 2 dengan Keyword Highlighting Emas
    head_line2_prefix = data.get("headline_line2_prefix", "")
    head_keyword = data.get("keyword_highlight", "")
    y_head2 = y_head + 72

    draw.text((margin_x, y_head2), head_line2_prefix, font=font_headline, fill=(255, 255, 255))
    bbox_prefix = font_headline.getbbox(head_line2_prefix)
    x_kw = margin_x + (bbox_prefix[2] - bbox_prefix[0])
    draw.text((x_kw, y_head2), head_keyword, font=font_headline, fill=(244, 196, 48))

    # 6. DUA KOTAK METRIK / FAKTA KUNCI
    y_box = y_head2 + 100
    box_w = (w - (2 * margin_x) - 25) // 2
    box_h = 110

    if is_data_mode:
        # Mode Data Angka: Angka besar di atas, label di bawah
        font_box_val = get_system_font("bold", 40)
        font_box_lbl = get_system_font("bold", 19)

        # Kotak 1 (Emas)
        draw.rounded_rectangle([margin_x, y_box, margin_x + box_w, y_box + box_h], radius=14, fill=(11, 37, 28, 235), outline=(244, 196, 48, 160), width=2)
        draw.text((margin_x + 25, y_box + 18), data.get("box1_val", "0%"), font=font_box_val, fill=(244, 196, 48))
        draw.text((margin_x + 25, y_box + 66), data.get("box1_lbl", ""), font=font_box_lbl, fill=(203, 213, 225))

        # Kotak 2 (Cyan)
        draw.rounded_rectangle([margin_x + box_w + 25, y_box, w - margin_x, y_box + box_h], radius=14, fill=(11, 37, 28, 235), outline=(56, 189, 248, 140), width=1)
        draw.text((margin_x + box_w + 45, y_box + 18), data.get("box2_val", "UNGGULAN"), font=font_box_val, fill=(56, 189, 248))
        draw.text((margin_x + box_w + 45, y_box + 66), data.get("box2_lbl", ""), font=font_box_lbl, fill=(203, 213, 225))
    else:
        # Mode Non-Angka / Peristiwa: Judul kategori status di atas, isi teks di bawah
        font_box_title = get_system_font("bold", 22)
        font_box_body = get_system_font("bold", 28)

        # Kotak 1 (Emas)
        draw.rounded_rectangle([margin_x, y_box, margin_x + box_w, y_box + box_h], radius=14, fill=(11, 37, 28, 235), outline=(244, 196, 48, 160), width=2)
        draw.text((margin_x + 25, y_box + 18), data.get("box1_title", "STATUS"), font=font_box_title, fill=(244, 196, 48))
        draw.text((margin_x + 25, y_box + 56), data.get("box1_body", "Penanganan Berjalan"), font=font_box_body, fill=(255, 255, 255))

        # Kotak 2 (Cyan)
        draw.rounded_rectangle([margin_x + box_w + 25, y_box, w - margin_x, y_box + box_h], radius=14, fill=(11, 37, 28, 235), outline=(56, 189, 248, 140), width=1)
        draw.text((margin_x + box_w + 45, y_box + 18), data.get("box2_title", "DAMPAK / SOLUSI"), font=font_box_title, fill=(56, 189, 248))
        draw.text((margin_x + box_w + 45, y_box + 56), data.get("box2_body", "Normal Kembali"), font=font_box_body, fill=(255, 255, 255))

    # Sub-keterangan 1 baris
    y_sub = y_box + box_h + 20
    sub_text = data.get("subtext", "")
    draw.text((margin_x, y_sub), sub_text, font=font_sub, fill=(226, 232, 240))

    # Footer Baris Bawah
    y_foot = 1235
    draw.line([(margin_x, y_foot), (w - margin_x, y_foot)], fill=(45, 70, 60), width=1)
    draw.text((margin_x, y_foot + 20), "f  Halaman Resmi: Paduka Sambas", font=font_meta, fill=(241, 245, 249))

    source_text = f"Foto / Sumber: {data.get('source_credit', 'Paduka Sambas')}"
    bbox_src = font_meta.getbbox(source_text)
    src_w = bbox_src[2] - bbox_src[0]
    draw.text((w - margin_x - src_w, y_foot + 20), source_text, font=font_meta, fill=(148, 163, 184))

    # Ekspor ke PNG tanpa kompresi pecah
    final_img.save(output_path, "PNG")
    print(f"[+] Master News Card 4:5 berhasil dibuat: {output_path}")
    return output_path


def generate_facebook_caption(data):
    """
    Menyusun narasi caption Facebook resmi berformat Zero-Link (5W+1H tuntas tanpa tautan luar).
    """
    title = data.get("title", "").strip()
    lead = data.get("lead", "").strip()
    body = data.get("body", "").strip()
    impact = data.get("impact", "").strip()
    discussion = data.get("discussion_prompt", "Bagaimana tanggapan Anda mengenai kabar ini? Sampaikan di kolom komentar!")
    source = data.get("source_credit", "Paduka Sambas")
    hashtags = data.get("hashtags", ["PadukaSambas", "KabarSambas", "SambasTerkini", "KalbarHariIni"])

    ht_str = " ".join([f"#{t.replace('#', '')}" for t in hashtags])

    caption = f"""📌 {title.upper()}

SAMBAS (PADUKA SAMBAS) — {lead}

{body}

{impact}

---
💬 {discussion}

(Foto / Sumber: {source})

{ht_str}"""
    return caption.strip()


# =====================================================================
# CONTOH DATA SIMULASI (UNTUK UJI COBA INTERNAL / DRY-RUN)
# =====================================================================
SAMPLE_DATA_NEWS = {
    "is_data_mode": True,
    "photo_url": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1200&q=80",
    "badge_red": "INFO SAMBAS",
    "badge_gold": "DATA BPS TERBARU",
    "kicker": "KABAR BAIK KETENAGAKERJAAN DAERAH",
    "headline_line1": "Pengangguran di Sambas",
    "headline_line2_prefix": "Turun Tajam ke ",
    "keyword_highlight": "3,92%",
    "box1_val": "96,08%",
    "box1_lbl": "Tingkat Kesempatan Kerja (TKK)",
    "box2_val": "UNGGULAN",
    "box2_lbl": "Perdagangan & Pertanian Lokal",
    "subtext": "Pemulihan ekonomi daerah serap ribuan tenaga kerja baru di usia produktif.",
    "source_credit": "BPS Kabupaten Sambas",
    "title": "Tingkat Pengangguran Terbuka di Sambas Turun ke 3,92%",
    "lead": "Berdasarkan rilis indikator ketenagakerjaan Badan Pusat Statistik (BPS) terbaru, Tingkat Pengangguran Terbuka (TPT) di Kabupaten Sambas berhasil ditekan hingga menyentuh angka 3,92%.",
    "body": "Penurunan ini selaras dengan meningkatnya Tingkat Kesempatan Kerja (TKK) yang kini mencapai 96,08%. Sektor pertanian, perdagangan lokal, dan hilirisasi produk unggulan daerah menjadi penyumbang terbesar penyerapan tenaga kerja produktif.",
    "impact": "Pemerintah daerah terus mengarahkan penguatan vokasi dan kemudahan berusaha bagi pelaku UMKM agar tren penyerapan tenaga kerja positif ini tetap berkesinambungan.",
    "discussion_prompt": "Bagaimana pandangan Anda mengenai geliat lapangan kerja dan iklim usaha di Sambas saat ini? Sampaikan di kolom komentar!",
    "hashtags": ["PadukaSambas", "EkonomiSambas", "KabarSambas", "SambasTerkini", "KalbarHariIni"]
}

SAMPLE_EVENT_NEWS = {
    "is_data_mode": False,
    "photo_url": "https://images.unsplash.com/photo-1474487548417-781cb71495f3?w=1200&q=80",
    "badge_red": "INFO SAMBAS",
    "badge_gold": "INFRASTRUKTUR",
    "kicker": "RESPON CEPAT KELUHAN WARGA",
    "headline_line1": "Jembatan Rusak di Sambas",
    "headline_line2_prefix": "Resmi ",
    "keyword_highlight": "MULAI DIPERBAIKI",
    "box1_title": "STATUS PEKERJAAN",
    "box1_body": "Pondasi Tiang Pancang",
    "box2_title": "JALUR ALTERNATIF",
    "box2_body": "Dialihkan ke Jalan Lingkar",
    "subtext": "Dinas PUPR targetkan akses transportasi warga segera normal kembali.",
    "source_credit": "Pemkab Sambas / PUPR",
    "title": "Jembatan Penghubung di Sambas Resmi Mulai Diperbaiki",
    "lead": "Pemerintah daerah melalui instansi teknis resmi memulai pengerjaan perbaikan jembatan penghubung utama yang sebelumnya mengalami kerusakan dan dikeluhkan masyarakat.",
    "body": "Fokus pengerjaan tahap awal mencakup pemasangan tiang pancang baja dan penguatan abutmen guna memastikan struktur jembatan kokoh dilalui kendaraan tonase sedang.",
    "impact": "Selama pengerjaan berlangsung, arus lalu lintas warga dialihkan sementara melalui jalan lingkar alternatif guna menghindari kemacetan dan menjaga keselamatan pengendara.",
    "discussion_prompt": "Bagaimana kondisi infrastruktur jembatan dan jalan di sekitar lingkungan Anda? Berikan laporan Anda di kolom komentar!",
    "hashtags": ["PadukaSambas", "InfrastrukturSambas", "KabarSambas", "SambasMaju", "KalbarHariIni"]
}


def publish_to_facebook(image_path, caption, page_id=None, page_token=None):
    """
    Mengunggah foto dan caption berita secara otomatis ke Halaman Facebook via Meta Graph API.
    """
    page_id = page_id or os.environ.get("FB_PAGE_ID")
    page_token = page_token or os.environ.get("FB_PAGE_ACCESS_TOKEN")

    if not page_id or not page_token:
        print("[!] Gagal: FB_PAGE_ID atau FB_PAGE_ACCESS_TOKEN belum disetel di environment.")
        return False

    url = f"https://graph.facebook.com/v19.0/{page_id}/photos"
    print(f"[*] Mengirim postingan otomatis ke Halaman Facebook ID: {page_id}...")

    # Membaca data gambar binary untuk multipart upload
    with open(image_path, "rb") as f:
        img_bytes = f.read()

    boundary = "----WebKitFormBoundaryPadukaSambas"
    body = io.BytesIO()

    # Part: caption
    body.write(f"--{boundary}\r\n".encode("utf-8"))
    body.write(b'Content-Disposition: form-data; name="caption"\r\n\r\n')
    body.write(caption.encode("utf-8"))
    body.write(b"\r\n")

    # Part: access_token
    body.write(f"--{boundary}\r\n".encode("utf-8"))
    body.write(b'Content-Disposition: form-data; name="access_token"\r\n\r\n')
    body.write(page_token.encode("utf-8"))
    body.write(b"\r\n")

    # Part: source (photo)
    body.write(f"--{boundary}\r\n".encode("utf-8"))
    body.write(b'Content-Disposition: form-data; name="source"; filename="news_card.png"\r\n')
    body.write(b"Content-Type: image/png\r\n\r\n")
    body.write(img_bytes)
    body.write(b"\r\n")

    body.write(f"--{boundary}--\r\n".encode("utf-8"))
    payload = body.getvalue()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(payload))
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            post_id = res_data.get("id") or res_data.get("post_id")
            print(f"[+] BERHASIL! Postingan otomatis telah terbit di Facebook dengan Post ID: {post_id}")
            return True
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"[!] Gagal posting ke Facebook: {err_msg}")
        return False
    except Exception as e:
        print(f"[!] Terjadi kesalahan jaringan: {e}")
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generator Postingan Facebook Paduka Sambas")
    parser.add_argument("--test-data", action="store_true", help="Uji pembuatan kartu berita berbasis data angka")
    parser.add_argument("--test-event", action="store_true", help="Uji pembuatan kartu berita berbasis peristiwa non-angka")
    parser.add_argument("--publish-test", action="store_true", help="Uji coba otomatis posting 1 berita ke Halaman Facebook")
    args = parser.parse_args()

    out_dir = "posts/facebook_drafts"
    os.makedirs(out_dir, exist_ok=True)

    if args.publish_test:
        print("[*] MEMULAI UJI COBA OTOMATIS POSTING 1 BERITA KE FACEBOOK PAGE...")
        img_file = os.path.join(out_dir, "draft_data_news.png")
        cap_file = os.path.join(out_dir, "draft_data_caption.txt")
        if not os.path.exists(img_file) or not os.path.exists(cap_file):
            generate_facebook_news_card(SAMPLE_DATA_NEWS, img_file)
            with open(cap_file, "w", encoding="utf-8") as f:
                f.write(generate_facebook_caption(SAMPLE_DATA_NEWS))

        with open(cap_file, "r", encoding="utf-8") as f:
            caption_text = f.read()

        publish_to_facebook(img_file, caption_text)

    elif args.test_event:
        print("[*] Menjalankan uji coba: Berita Peristiwa Non-Angka...")
        img_file = generate_facebook_news_card(SAMPLE_EVENT_NEWS, os.path.join(out_dir, "draft_event_news.png"))
        caption = generate_facebook_caption(SAMPLE_EVENT_NEWS)
        with open(os.path.join(out_dir, "draft_event_caption.txt"), "w", encoding="utf-8") as f:
            f.write(caption)
        print(f"[+] Draf Berita Peristiwa selesai dibuat di: {out_dir}")
        print("\n--- CONTOH CAPTION ---")
        print(caption)

    else:
        # Default: Uji coba Berita Data Angka
        print("[*] Menjalankan uji coba: Berita Data Angka...")
        img_file = generate_facebook_news_card(SAMPLE_DATA_NEWS, os.path.join(out_dir, "draft_data_news.png"))
        caption = generate_facebook_caption(SAMPLE_DATA_NEWS)
        with open(os.path.join(out_dir, "draft_data_caption.txt"), "w", encoding="utf-8") as f:
            f.write(caption)
        print(f"[+] Draf Berita Data selesai dibuat di: {out_dir}")
        print("\n--- CONTOH CAPTION ---")
        print(caption)
