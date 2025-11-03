#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram controller for UltraSyncSMSSender
Requires: python-telegram-bot>=20.0, requests
Run: python3 telegram_ultrasync_bot.py
"""

import logging
import json
import threading
from functools import wraps
from typing import List, Dict

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, CallbackQueryHandler
)

# -----------------------
# CONFIG - replace if needed (you provided these)
# -----------------------
TELEGRAM_BOT_TOKEN = "7028850279:AAFSlSqSlTaCD_Vi9vLzxxUu94pjCeKpavk"
ADMIN_TELEGRAM_ID = 5624278091  # integer

HOSTS_FILE = "hosts.json"
DEFAULT_DATA_FILE = "default_data.txt"

# -----------------------
# Logging
# -----------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# -----------------------
# Include the UltraSyncSMSSender logic (adapted from your uploaded file)
# -----------------------
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class UltraSyncSMSSender:
    def __init__(self):
        self.targets = self.load_hosts() or [
            {"name": "sms323.top", "host": "sms323.top", "url": "https://sms323.top/api/ws_send/appSend"},
            {"name": "diy22.vip", "host": "diy22.vip", "url": "https://diy22.vip/api/ws_send/appSend"},
            {"name": "tg299.shop", "host": "tg299.shop", "url": "https://tg299.shop/api/ws_send/appSend"}
        ]
        self.common_headers = {
            "apikey": "hds7839dt79to34fzhwd",
            "content-type": "application/x-www-form-urlencoded",
            "user-agent": "okhttp/4.9.0"
        }
        self.default_data = self.load_default_data() or "ddu5GkRUZ2obMkACWANyUc1uG3zngS4OI5ri9qHUBJUE%2F3Zt%2FBMWBT%2FVvJgtD1siPXX8df4l91tz%0AofaSyEyfNw%3D%3D%0A"

    def load_hosts(self) -> List[Dict]:
        try:
            with open(HOSTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            return []
        return []

    def save_hosts(self):
        try:
            with open(HOSTS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.targets, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.exception("Failed to save hosts: %s", e)

    def load_default_data(self):
        try:
            with open(DEFAULT_DATA_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return None

    def save_default_data(self):
        try:
            with open(DEFAULT_DATA_FILE, "w", encoding="utf-8") as f:
                f.write(self.default_data)
        except Exception:
            pass

    def calculate_content_length(self, data: str) -> str:
        return str(len(f"data={data}"))

    def change_data(self, new_data: str):
        self.default_data = new_data
        self.save_default_data()
        logger.info("Default data updated. length=%s", self.calculate_content_length(new_data))

    def translate_message(self, chinese_msg: str) -> str:
        translations = {
            "该号码已登出，任务取消": "Number logged out, task cancelled",
            "发送成功": "Message sent successfully",
            "系统繁忙": "System busy",
            "验证码错误": "Verification code error",
            "号码无效": "Invalid number",
            "余额不足": "Insufficient balance"
        }
        for cn, en in translations.items():
            if cn in chinese_msg:
                return chinese_msg.replace(cn, en)
        return chinese_msg

    def extract_data_from_curl(self, text: str) -> str:
        import re
        patterns = [
            r"--data(?:-urlencode)?\s+'([^']+)'",
            r"--data(?:-urlencode)?\s+\"([^\"]+)\"",
            r"data=([A-Za-z0-9%+/=]+)"
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                value = m.group(1)
                if value.startswith("data="):
                    value = value.split("data=", 1)[1]
                return value.strip()
        return text.strip()

    def _thread_worker(self, target: Dict, data: str, barrier: threading.Barrier, result_holder: dict, idx: int):
        headers = self.common_headers.copy()
        headers["Host"] = target["host"]
        headers["content-length"] = self.calculate_content_length(data)
        try:
            barrier.wait()
        except threading.BrokenBarrierError:
            pass
        sent_time = time.perf_counter()
        try:
            resp = requests.post(
                target["url"],
                headers=headers,
                data=f"data={data}",
                timeout=10,
                verify=False
            )
            recv_time = time.perf_counter()
            response_text = resp.text
            result_holder[idx] = {
                "target": target["name"],
                "success": True,
                "status": resp.status_code,
                "network_time_ms": round((recv_time - sent_time) * 1000, 1),
                "response": response_text,
                "sent_time": sent_time
            }
        except Exception as e:
            err_time = time.perf_counter()
            err_msg = str(e)
            if len(err_msg) > 120:
                err_msg = err_msg[:120] + "..."
            result_holder[idx] = {
                "target": target["name"],
                "success": False,
                "status": "Error",
                "network_time_ms": round((err_time - sent_time) * 1000, 1),
                "response": err_msg,
                "sent_time": sent_time
            }

    def send_ultra_sync(self, custom_data: str = None, timeout_sec: int = 60):
        data_to_send = custom_data or self.default_data
        total = len(self.targets)
        if total == 0:
            return {"error": "No hosts configured."}
        barrier = threading.Barrier(total)
        manager = {}
        overall_start = time.perf_counter()

        with ThreadPoolExecutor(max_workers=total) as ex:
            futures = []
            for i, target in enumerate(self.targets):
                futures.append(ex.submit(self._thread_worker, target, data_to_send, barrier, manager, i))
            for fut in as_completed(futures, timeout=timeout_sec):
                try:
                    fut.result()
                except Exception:
                    pass

        overall_end = time.perf_counter()
        total_time_ms = (overall_end - overall_start) * 1000
        results = [manager.get(i, {
            "target": self.targets[i]["name"],
            "success": False,
            "status": "NoResponse",
            "network_time_ms": 0,
            "response": "No result",
            "sent_time": None
        }) for i in range(total)]

        sent_times = [r["sent_time"] for r in results if r.get("sent_time") is not None]
        max_time_diff_ms = (max(sent_times) - min(sent_times)) * 1000 if len(sent_times) >= 2 else 0.0

        return {
            "results": results,
            "total_time_ms": total_time_ms,
            "max_send_time_diff_ms": max_time_diff_ms,
        }

    # Host helpers for bot commands
    def list_hosts(self) -> List[Dict]:
        return self.targets

    def add_host(self, host_name: str):
        new_target = {
            "name": host_name,
            "host": host_name,
            "url": f"https://{host_name}/api/ws_send/appSend"
        }
        self.targets.append(new_target)
        self.save_hosts()

    def remove_host_by_index(self, index: int):
        if 0 <= index < len(self.targets):
            removed = self.targets.pop(index)
            self.save_hosts()
            return removed
        return None

# -----------------------
# Instantiate sender
# -----------------------
SENDER = UltraSyncSMSSender()

# -----------------------
# ADMIN CHECK DECORATOR
# -----------------------
def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id if update.effective_user else None
        if user_id != ADMIN_TELEGRAM_ID:
            await update.message.reply_text("❌ অনুমোদিত ব্যবহারকারী নন।")
            logger.warning("Unauthorized access attempt by %s", user_id)
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# -----------------------
# Handlers
# -----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ ULTRA SYNC BOT চালু।\n\n"
        "Commands:\n"
        "/help - সাহায্য\n"
        "/showhosts - হোস্ট লিস্ট\n"
        "/addhost <domain> - হোস্ট যোগ কর\n"
        "/removehost <index> - হোস্ট মুছো (0-based index)\n"
        "/setdata <encoded_data_or_curl> - ডিফল্ট ডাটা সেট কর\n"
        "/showdata - বর্তমান ডাটা প্রিভিউ\n"
        "/send - ডিফল্ট ডাটা দিয়ে ULTRA SYNC পাঠাও\n"
        "/senddata <data_or_curl> - সরাসরি কাস্টম ডাটা পাঠাও\n"
        "/execcurl <curl_text> - curl থেকে data এক্সট্র্যাক্ট করে পাঠাবে\n"
        "/status - সার্ভারের সংক্ষিপ্ত ফলাফল দেখাবে"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

@admin_only
async def show_hosts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hosts = SENDER.list_hosts()
    if not hosts:
        await update.message.reply_text("Hosts list খালি।")
        return
    text = "📋 Hosts:\n"
    for i, h in enumerate(hosts):
        text += f"{i}. {h['name']} -> {h['url']}\n"
    await update.message.reply_text(text)

@admin_only
async def add_host_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("ব্যবহার: /addhost example.com")
        return
    host = args[0].strip()
    SENDER.add_host(host)
    await update.message.reply_text(f"✅ Added host: {host}")

@admin_only
async def remove_host_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("ব্যবহার: /removehost <index>")
        return
    try:
        idx = int(args[0])
    except Exception:
        await update.message.reply_text("Index integer হতে হবে (0-based).")
        return
    removed = SENDER.remove_host_by_index(idx)
    if removed:
        await update.message.reply_text(f"✅ Removed host: {removed['name']}")
    else:
        await update.message.reply_text("Invalid index।")

@admin_only
async def setdata_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args and not update.message.reply_to_message:
        await update.message.reply_text("ব্যবহার: /setdata <data_or_curl>  OR reply to a message containing data/curl")
        return
    if context.args:
        text = " ".join(context.args)
    else:
        text = update.message.reply_to_message.text or ""
    extracted = SENDER.extract_data_from_curl(text)
    SENDER.change_data(extracted)
    await update.message.reply_text(f"✅ Default data updated. preview:\n{extracted[:200]}")

@admin_only
async def showdata_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    preview = SENDER.default_data
    await update.message.reply_text(f"📦 Default data (preview):\n{preview[:800]}")

@admin_only
async def send_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("▶️ Sending ULTRA SYNC with default data... This may take a few seconds.")
    res = SENDER.send_ultra_sync()
    # Summarize results
    results = res.get("results", [])
    ok = sum(1 for r in results if r["success"])
    total = len(results)
    text = f"✅ Completed. Success {ok}/{total}\nTotal wall-time: {res.get('total_time_ms'):.1f} ms\nMax send-time diff: {res.get('max_send_time_diff_ms'):.3f} ms\n\nTop responses:\n"
    for r in results[:6]:
        status = "OK" if r["success"] else "ERR"
        snippet = (r["response"] or "")[:200].replace("\n", " ")
        text += f"- {r['target']}: {status} | {r['network_time_ms']} ms | {snippet}\n"
    await update.message.reply_text(text)

@admin_only
async def senddata_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args and not update.message.reply_to_message:
        await update.message.reply_text("ব্যবহার: /senddata <data_or_curl> OR reply to a message containing data/curl")
        return
    if context.args:
        text = " ".join(context.args)
    else:
        text = update.message.reply_to_message.text or ""
    extracted = SENDER.extract_data_from_curl(text)
    await update.message.reply_text("▶️ Sending provided data...")
    res = SENDER.send_ultra_sync(custom_data=extracted)
    results = res.get("results", [])
    ok = sum(1 for r in results if r["success"])
    total = len(results)
    await update.message.reply_text(f"✅ Done. Success {ok}/{total}")

@admin_only
async def execcurl_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args and not update.message.reply_to_message:
        await update.message.reply_text("ব্যবহার: /execcurl <curl_text> OR reply to curl")
        return
    text = " ".join(context.args) if context.args else (update.message.reply_to_message.text or "")
    extracted = SENDER.extract_data_from_curl(text)
    await update.message.reply_text(f"🔎 Extracted data (preview):\n{extracted[:400]}\n\n▶️ Sending...")
    res = SENDER.send_ultra_sync(custom_data=extracted)
    ok = sum(1 for r in res.get("results", []) if r["success"])
    total = len(res.get("results", []))
    await update.message.reply_text(f"✅ Done. Success {ok}/{total}")

@admin_only
async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hosts = SENDER.list_hosts()
    text = f"Hosts: {len(hosts)}\nDefault data len: {len(SENDER.default_data)}\n"
    await update.message.reply_text(text)

# Generic message echo for admin (optional helper)
@admin_only
async def echo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Received. Use commands to control the bot. /help")

# -----------------------
# Main entry
# -----------------------
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("showhosts", show_hosts))
    app.add_handler(CommandHandler("addhost", add_host_cmd))
    app.add_handler(CommandHandler("removehost", remove_host_cmd))
    app.add_handler(CommandHandler("setdata", setdata_cmd))
    app.add_handler(CommandHandler("showdata", showdata_cmd))
    app.add_handler(CommandHandler("send", send_cmd))
    app.add_handler(CommandHandler("senddata", senddata_cmd))
    app.add_handler(CommandHandler("execcurl", execcurl_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    # fallback: any text message from admin will be acknowledged
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), echo_message))

    logger.info("Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
