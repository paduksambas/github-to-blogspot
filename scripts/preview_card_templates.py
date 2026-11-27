#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generator Multi-Template Master News Card Facebook Paduka Sambas
Menghasilkan 5 Varian Desain Kartu Berdasarkan Kategori Topik Berita:
1. THE CRIMSON STRIKER   -> Breaking News, Geopolitik, Perang, Bencana (Merah & Emas)
2. THE ROYAL FINANCE     -> Ekonomi, Bisnis, Pasar, Rupiah, BBM, Pajak (Navy Blue & Emas)
3. THE OBSIDIAN JUSTICE  -> Hukum, Skandal, Korupsi, Penangkapan, Kepolisian (Hitam Obsidian & Marun)
4. THE SAMBAS EMERALD    -> Berita Daerah, Sambas, Kalbar, Budaya, Human Interest (Hijau Zamrud & Kuning Melayu)
5. THE CYBER HORIZON     -> Teknologi, AI, Sains, Otomotif, Antariksa (Dark Slate & Neon Cyan)
"""

import os
import io
import re
import urllib.request
import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageOps

ARTIFACT_DIR = r"C:\Users\ASUS\.gemini\antigravity\brain\9ae8aa92-e27b-40d8-a25e-a77db5f45141"
os.makedirs(ARTIFACT_DIR, exist_ok=True)


def get_font(font_type="bold", size=24):
    if font_type == "impact":
        candidate_paths = [
            "C:/Windows/Fonts/impact.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf",
            "C:/Windows/Fonts/arialbd.ttf"
        ]
    elif font_type == "bold":
        candidate_paths = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        ]
    else:
        candidate_paths = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]

    for p in candidate_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def download_or_create_photo(url, w=1080, h=640, label="DOKUMENTASI FOTO"):
    p_img = None
    if url and url.startswith("http"):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                p_img = Image.open(io.BytesIO(resp.read())).convert("RGB")
        except Exception:
            pass
    if not p_img:
        p_img = Image.new("RGB", (w, h), (30, 35, 45))
        d = ImageDraw.Draw(p_img)
        f = get_font("bold", 30)
        d.text((w // 4, h // 2), label, font=f, fill=(180, 180, 180))
    else:
        p_img = ImageOps.fit(p_img, (w, h), method=Image.Resampling.LANCZOS)
    return p_img


def render_card(theme, data, output_path):
    """
    Merender Master News Card 4:5 (1080 x 1350 px) dengan palet tema dinamis.
    Theme: 'breaking', 'finance', 'justice', 'daerah', 'tech'
    """
    w, h = 1080, 1350
    card = Image.new("RGB", (w, h), (14, 14, 14))
    draw = ImageDraw.Draw(card)

    # 1. Konfigurasi Warna Tema
    if theme == "breaking":
        # Merah & Emas Alert
        top_bg = (215, 25, 25)
        accent_color = (255, 215, 0)
        badge_bg = (255, 215, 0)
        badge_fg = (0, 0, 0)
        bottom_bg = (255, 215, 0)
        bottom_fg = (15, 15, 15)
        accent_stripes = (215, 25, 25)
        sub_bar_bg = (20, 20, 22)
        theme_tag = "BERITA UTAMA • GEOPOLITIK"
        footer_bg = (10, 10, 10)
    elif theme == "finance":
        # Royal Navy & Emerald Gold
        top_bg = (12, 28, 58)
        accent_color = (0, 220, 255)
        badge_bg = (0, 220, 255)
        badge_fg = (5, 15, 30)
        bottom_bg = (245, 245, 245)
        bottom_fg = (10, 20, 40)
        accent_stripes = (12, 28, 58)
        sub_bar_bg = (7, 18, 38)
        theme_tag = "EKONOMI • FINANSIAL & PASAR"
        footer_bg = (5, 12, 25)
    elif theme == "justice":
        # Obsidian Charcoal & Blood Red
        top_bg = (22, 24, 28)
        accent_color = (220, 38, 38)
        badge_bg = (220, 38, 38)
        badge_fg = (255, 255, 255)
        bottom_bg = (235, 235, 238)
        bottom_fg = (15, 15, 20)
        accent_stripes = (220, 38, 38)
        sub_bar_bg = (15, 16, 20)
        theme_tag = "HUKUM • INVESTIGASI & PERADILAN"
        footer_bg = (8, 9, 12)
    elif theme == "daerah":
        # Hijau Zamrud Kesultanan & Emas Melayu
        top_bg = (11, 55, 35)
        accent_color = (250, 195, 30)
        badge_bg = (250, 195, 30)
        badge_fg = (10, 40, 25)
        bottom_bg = (250, 195, 30)
        bottom_fg = (10, 35, 20)
        accent_stripes = (11, 55, 35)
        sub_bar_bg = (8, 38, 24)
        theme_tag = "KALIMANTAN BARAT • KABAR DAERAH"
        footer_bg = (5, 25, 15)
    else:  # 'tech'
        # Cyber Slate & Neon Cyan
        top_bg = (15, 23, 42)
        accent_color = (6, 182, 212)
        badge_bg = (6, 182, 212)
        badge_fg = (15, 23, 42)
        bottom_bg = (226, 232, 240)
        bottom_fg = (15, 23, 42)
        accent_stripes = (6, 182, 212)
        sub_bar_bg = (10, 15, 30)
        theme_tag = "TEKNOLOGI • SAINS & INOVASI"
        footer_bg = (5, 8, 18)

    # -------------------------------------------------------------
    # 1. ZONA ATAS (HEADER BANNER: 0 - 250 px)
    # -------------------------------------------------------------
    draw.rectangle([0, 0, w, 250], fill=top_bg)

    # Aksen Garis Diagonal di Kanan Atas
    for i in range(4):
        x = w - 160 + (i * 32)
        draw.polygon([(x, 0), (x + 18, 0), (x - 30, 250), (x - 48, 250)], fill=accent_color)

    # Aksen Dot Matrix Kanan Atas
    for r in range(4):
        for c in range(6):
            cx = w - 190 - (c * 16)
            cy = 35 + (r * 16)
            draw.ellipse([cx, cy, cx + 6, cy + 6], fill=accent_color)

    # Badge Logo Kiri Atas
    badge_w, badge_h = 240, 95
    draw.rounded_rectangle([25, 20, 25 + badge_w, 20 + badge_h], radius=18, fill=badge_bg, outline=(0, 0, 0), width=3)
    f_badge1 = get_font("impact", 28)
    f_badge2 = get_font("impact", 22)
    draw.text((42, 28), "PADUKA SAMBAS", font=f_badge1, fill=badge_fg)
    badge_sub = data.get("badge_sub", theme_tag.split("•")[0].strip())
    draw.text((42, 60), badge_sub.upper()[:14], font=f_badge2, fill=badge_fg)

    # Headline Atas (Gaya Impact 2 Baris)
    hl1 = data.get("headline_line1", "PERISTIWA UTAMA").upper()[:24]
    hl2 = data.get("headline_line2", "SOROTAN TERKINI").upper()[:24]

    font_top = get_font("impact", 64)
    avail_x = 285
    avail_w = w - avail_x - 110

    b1 = font_top.getbbox(hl1)
    x1 = avail_x + max(0, (avail_w - (b1[2] - b1[0])) // 2)
    b2 = font_top.getbbox(hl2)
    x2 = avail_x + max(0, (avail_w - (b2[2] - b2[0])) // 2)

    draw.text((x1, 32), hl1, font=font_top, fill=(255, 255, 255), stroke_width=6, stroke_fill=(0, 0, 0))
    draw.text((x2, 116), hl2, font=font_top, fill=accent_color, stroke_width=6, stroke_fill=(0, 0, 0))

    # Garis Pembatas Hitam
    draw.line([(0, 250), (w, 250)], fill=(0, 0, 0), width=6)

    # -------------------------------------------------------------
    # 2. ZONA TENGAH (FOTO PROPORSIONAL 16:9: 250 - 890 px)
    # -------------------------------------------------------------
    photo = download_or_create_photo(data.get("photo_url"), w, 640, data.get("title", ""))
    card.paste(photo, (0, 250))

    # Aksen Stripes Kiri & Kanan Bawah Foto
    for i in range(3):
        ox = 0 + (i * 26)
        col = accent_color if i % 2 == 0 else top_bg
        draw.polygon([(ox, 890), (ox + 16, 890), (ox + 75, 800), (ox + 59, 800)], fill=col)

    for i in range(3):
        ox = w - 10 + (i * 26)
        col = accent_color if i % 2 == 0 else top_bg
        draw.polygon([(ox - 60, 890), (ox - 44, 890), (ox, 800), (ox - 16, 800)], fill=col)

    # -------------------------------------------------------------
    # 3. ZONA BAWAH (BOX JUDUL: 890 - 1150 px)
    # -------------------------------------------------------------
    draw.rectangle([0, 890, w, 1150], fill=bottom_bg)
    draw.line([(0, 890), (w, 890)], fill=(0, 0, 0), width=5)

    # Aksen Garis di Sisi Kiri Box
    for i in range(3):
        ox = 18 + (i * 26)
        draw.polygon([(ox, 1150), (ox + 15, 1150), (ox + 65, 890), (ox + 50, 890)], fill=accent_stripes)

    title_text = data.get("title", "")
    f_title = get_font("bold", 43)
    lines = textwrap.wrap(title_text, width=37)
    y_t = 915 if len(lines) <= 2 else 905
    line_spacing = 58 if len(lines) <= 2 else 52
    for line in lines[:3]:
        draw.text((140, y_t), line, font=f_title, fill=bottom_fg)
        y_t += line_spacing

    # -------------------------------------------------------------
    # 4. METADATA SUB-BAR (1150 - 1225 px)
    # -------------------------------------------------------------
    draw.rectangle([0, 1150, w, 1225], fill=sub_bar_bg)

    # Ikon Info (i)
    draw.ellipse([30, 1166, 68, 1204], fill=accent_color)
    draw.text((45, 1172), "i", font=get_font("bold", 24), fill=(0, 0, 0) if theme in ["breaking", "daerah"] else (255, 255, 255))

    cat_name = data.get("category", theme_tag.split("•")[0].strip()).upper()
    source_cr = data.get("source_credit", "Redaksi Media").upper()
    region_tag = data.get("region_tag", theme_tag.split("•")[-1].strip()).upper()

    sub_text = f"{cat_name}  •  SUMBER: {source_cr}  •  {region_tag}"
    draw.text((85, 1176), sub_text, font=get_font("bold", 21), fill=(240, 240, 240))

    # Aksen Dots Kanan
    for c in range(5):
        for r in range(2):
            cx = w - 40 - (c * 14)
            cy = 1178 + (r * 14)
            draw.ellipse([cx, cy, cx + 5, cy + 5], fill=accent_color)

    # -------------------------------------------------------------
    # 5. ZONA FOOTER (1225 - 1350 px)
    # -------------------------------------------------------------
    draw.rectangle([0, 1225, w, 1350], fill=footer_bg)
    draw.line([(0, 1225), (w, 1225)], fill=accent_color, width=4)

    f_foot1 = get_font("bold", 27)
    f_foot2 = get_font("regular", 20)

    footer_title = f"PADUKA SAMBAS  |  {region_tag}"
    draw.text((45, 1250), footer_title, font=f_foot1, fill=(255, 255, 255))
    draw.text((45, 1290), "Portal Berita Terpercaya & Sistem Analisis Intelijen Daerah", font=f_foot2, fill=(180, 180, 180))

    # Badge Kanan Footer
    draw.rounded_rectangle([w - 240, 1248, w - 35, 1318], radius=12, fill=top_bg, outline=accent_color, width=2)
    draw.text((w - 225, 1268), "EDISI TERBARU", font=get_font("bold", 23), fill=accent_color)

    card.save(output_path, "PNG", quality=95)
    print(f"[+] Kartu tema '{theme}' berhasil disimpan: {output_path}")
    return output_path


if __name__ == "__main__":
    samples = [
        {
            "theme": "breaking",
            "filename": "card_preview_breaking.png",
            "data": {
                "headline_line1": "TARIF BARU TRUMP",
                "headline_line2": "GUNCANG DUNIA",
                "badge_sub": "BREAKING NEWS",
                "title": "Trump Usul Tarif Baru ke 14 Negara sampai Netanyahu Gugat Hasil Pemilu",
                "category": "GEOPOLITIK",
                "source_credit": "CNN INTERNASIONAL",
                "region_tag": "BERITA GLOBAL",
                "photo_url": "https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=1200&q=80"
            }
        },
        {
            "theme": "finance",
            "filename": "card_preview_finance.png",
            "data": {
                "headline_line1": "RUPIAH MENGUAT",
                "headline_line2": "BI TAHAN SUKU BUNGA",
                "badge_sub": "PASAR MODAL",
                "title": "Rupiah Menguat ke Rp15.800 per Dolar AS, Bank Indonesia Tahan Suku Bunga 6%",
                "category": "EKONOMI",
                "source_credit": "CNBC INDONESIA",
                "region_tag": "BERITA NASIONAL",
                "photo_url": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1200&q=80"
            }
        },
        {
            "theme": "justice",
            "filename": "card_preview_justice.png",
            "data": {
                "headline_line1": "KPK RESMI TAHAN",
                "headline_line2": "TERSANGKA KORUPSI",
                "badge_sub": "HUKUM & ETIK",
                "title": "KPK Resmi Tahan Eks Pejabat Daerah Terkait Dugaan Korupsi Proyek Infrastruktur",
                "category": "HUKUM",
                "source_credit": "DETIK NEWS",
                "region_tag": "BERITA NASIONAL",
                "photo_url": "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=1200&q=80"
            }
        },
        {
            "theme": "daerah",
            "filename": "card_preview_daerah.png",
            "data": {
                "headline_line1": "JEMBATAN SAMBAS",
                "headline_line2": "RAMPUNG DIPERBAIKI",
                "badge_sub": "INFO SAMBAS",
                "title": "Akses Transportasi Warga Kembali Normal, Jembatan Penghubung di Sambas Tuntas Dikerjakan",
                "category": "INFRASTRUKTUR",
                "source_credit": "PEMKAB SAMBAS",
                "region_tag": "KALIMANTAN BARAT",
                "photo_url": "https://images.unsplash.com/photo-1545558014-8692077e9b5c?w=1200&q=80"
            }
        },
        {
            "theme": "tech",
            "filename": "card_preview_tech.png",
            "data": {
                "headline_line1": "SATELIT GENERASI BARU",
                "headline_line2": "INTERNET SUPER CEPAT",
                "badge_sub": "INOVASI SAINS",
                "title": "Peluncuran Satelit Generasi Baru Siap Perluas Jaringan Internet Cepat ke Pelosok Nusantara",
                "category": "TEKNOLOGI",
                "source_credit": "ANTARA TEKNO",
                "region_tag": "SAINS & DIGITAL",
                "photo_url": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&q=80"
            }
        }
    ]

    print("[*] Memulai perenderan 5 varian Master News Card...")
    for item in samples:
        out = os.path.join(ARTIFACT_DIR, item["filename"])
        render_card(item["theme"], item["data"], out)

    print("\n[+] Selesai! Semua 5 varian kartu telah dibuat di artifact directory.")
