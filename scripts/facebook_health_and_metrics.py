#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Facebook Token Health & Page Metrics Collector - Paduka Sambas
==============================================================
Memeriksa kesehatan token akses Facebook Page (ONLINE / EXPIRED)
serta mencatat jumlah pengikut (followers) dan likes secara berkala
untuk ditampilkan pada Dashboard Monitoring Live.
"""

import os
import sys
import json
import ssl
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone, timedelta

try:
    from scripts.telegram_notifier import send_telegram_alert
except ImportError:
    from telegram_notifier import send_telegram_alert

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METRICS_FILE = os.path.join(REPO_ROOT, "facebook_metrics.json")

SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE


def get_wib_now():
    wib_tz = timezone(timedelta(hours=7))
    return datetime.now(wib_tz)


def load_metrics():
    if os.path.exists(METRICS_FILE):
        try:
            with open(METRICS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "page_name": "Paduka Sambas",
        "followers_count": 948,
        "fan_count": 0,
        "token_status": "CHECKING",
        "error_message": "",
        "checked_at": "-",
        "history": []
    }


def check_and_collect_metrics():
    raw_page_id = os.environ.get("FB_PAGE_ID", "")
    raw_page_token = os.environ.get("FB_PAGE_ACCESS_TOKEN", "")
    page_id = str(raw_page_id).strip().strip('"\'')
    page_token = str(raw_page_token).strip().strip('"\'')

    data = load_metrics()
    now_wib = get_wib_now()
    today_str = now_wib.strftime("%Y-%m-%d")
    checked_str = now_wib.strftime("%Y-%m-%d %H:%M:%S WIB")
    data["checked_at"] = checked_str

    if not page_id or not page_token:
        data["token_status"] = "MISSING_SECRETS"
        data["error_message"] = "FB_PAGE_ID atau FB_PAGE_ACCESS_TOKEN belum disetel."
        with open(METRICS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("[!] Secrets Facebook belum disetel.")
        return False

    url = (
        f"https://graph.facebook.com/v19.0/{page_id}"
        f"?fields=name,followers_count,fan_count&access_token={urllib.parse.quote(page_token)}"
    )

    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=20, context=SSL_CONTEXT) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            followers = res.get("followers_count", data.get("followers_count", 0))
            fans = res.get("fan_count", data.get("fan_count", 0))
            name = res.get("name", "Paduka Sambas")

            data["page_name"] = name
            data["followers_count"] = followers
            data["fan_count"] = fans
            data["token_status"] = "ONLINE"
            data["error_message"] = ""

            # Simpan riwayat harian (maks 30 hari terakhir)
            hist = data.get("history", [])
            updated_today = False
            for h in hist:
                if h.get("date") == today_str:
                    h["followers_count"] = followers
                    h["fan_count"] = fans
                    updated_today = True
                    break
            if not updated_today:
                hist.append({
                    "date": today_str,
                    "followers_count": followers,
                    "fan_count": fans
                })
            data["history"] = hist[-30:]

            with open(METRICS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"[+] Token Facebook ONLINE! Halaman: {name} | Pengikut: {followers} | Suka: {fans}")
            return True

    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        print(f"[!] Token Facebook bermasalah (HTTP {e.code}): {err_body}")
        data["token_status"] = "EXPIRED"
        data["error_message"] = err_body[:240]
        with open(METRICS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        send_telegram_alert(
            "PERINGATAN TOKEN FACEBOOK BERMASALAH",
            f"⚠️ Status Token: *EXPIRED / ERROR*\n🔍 Detail: `{err_body[:180]}`\n\nSegera perbarui secret `FB_PAGE_ACCESS_TOKEN` di GitHub agar postingan otomatis tidak terhenti."
        )
        return False

    except Exception as e:
        print(f"[!] Gagal memeriksa metrik Facebook: {e}")
        data["token_status"] = "ERROR"
        data["error_message"] = str(e)[:200]
        with open(METRICS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return False


if __name__ == "__main__":
    ok = check_and_collect_metrics()
    if not ok:
        sys.exit(1)
