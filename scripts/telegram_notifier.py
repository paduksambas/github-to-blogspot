#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Instant Failure & Health Alerter - Paduka Sambas
=========================================================
Mengirimkan notifikasi peringatan instan ke Telegram Admin apabila
terjadi kegagalan eksekusi workflow atau token Meta bermasalah.
"""

import os
import sys
import ssl
import argparse
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE


def get_wib_now():
    wib_tz = timezone(timedelta(hours=7))
    return datetime.now(wib_tz).strftime("%Y-%m-%d %H:%M:%S WIB")


def send_telegram_alert(title, details, run_url=None):
    """Mengirim pesan peringatan instan ke Telegram menggunakan secrets repository."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id:
        print("[!] TELEGRAM_BOT_TOKEN atau TELEGRAM_CHAT_ID belum disetel. Skip notifikasi Telegram.")
        return False

    lines = [
        f"🚨 *{title}*",
        f"🕒 Waktu: `{get_wib_now()}`",
        "",
        details
    ]
    if run_url:
        lines.append("")
        lines.append(f"🔗 [Buka Log Error di GitHub Actions]({run_url})")

    lines.append("🌐 [Buka Dashboard Monitoring](https://paduksambas.github.io/github-to-blogspot/)")
    msg_text = "\n".join(lines)

    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=urllib.parse.urlencode({
                "chat_id": chat_id,
                "text": msg_text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": "true"
            }).encode("utf-8")
        )
        with urllib.request.urlopen(req, timeout=15, context=SSL_CONTEXT) as resp:
            print(f"[+] Notifikasi Telegram terkirim (HTTP {resp.status}).")
            return True
    except Exception as e:
        print(f"[!] Gagal mengirim notifikasi Telegram: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Telegram Instant Failure Alerter")
    parser.add_argument("--workflow", required=True, help="Nama workflow yang gagal/melapor")
    parser.add_argument("--status", default="FAILURE", help="Status eksekusi (FAILURE/WARNING)")
    parser.add_argument("--message", default="Terjadi kegagalan saat menjalankan tugas otomatis atau upload ke Facebook.", help="Pesan detail")
    parser.add_argument("--run-url", default="", help="Link ke halaman log GitHub Actions")
    args = parser.parse_args()

    title = f"ALARM {args.status}: {args.workflow}"
    details = f"⚠️ *Detail:* {args.message}\n📌 Silakan cek status token Meta atau jaringan pada log di bawah ini."
    send_telegram_alert(title, details, run_url=args.run_url)
