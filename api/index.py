import os
import httpx
from flask import Flask, request
from supabase import create_client

app = Flask(__name__)

# Fetch and clean Environment Variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip().strip("'\"")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().strip("'\"").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip().strip("'\"")

# Auto-format SUPABASE_URL if missing protocol
if SUPABASE_URL and not SUPABASE_URL.startswith("http://") and not SUPABASE_URL.startswith("https://"):
    SUPABASE_URL = f"https://{SUPABASE_URL}"

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}" if TOKEN else ""

def send_telegram_message(chat_id, text):
    if not TOKEN:
        return
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        httpx.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload, timeout=5.0)
    except Exception as e:
        print(f"Failed to send telegram msg: {e}")

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def webhook(path):
    if request.method == 'GET':
        missing = []
        if not TOKEN: missing.append("TELEGRAM_BOT_TOKEN")
        if not SUPABASE_URL: missing.append("SUPABASE_URL")
        if not SUPABASE_KEY: missing.append("SUPABASE_KEY")
        
        if missing:
            return f"Missing Environment Variables: {', '.join(missing)}", 200
        return f"Telegram Bot Server is Online! URL: {SUPABASE_URL}", 200

    try:
        json_data = request.get_json(force=True, silent=True)
        if not json_data or "message" not in json_data:
            return "OK", 200

        message = json_data["message"]
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "").strip().lower()

        if not chat_id or not text:
            return "OK", 200

        if not TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
            send_telegram_message(chat_id, "⚠️ <b>Error:</b> Environment variables missing on Vercel.")
            return "OK", 200

        # Initialize Supabase client
        try:
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as sb_err:
            send_telegram_message(chat_id, f"⚠️ <b>Supabase Error ({SUPABASE_URL}):</b> {str(sb_err)}")
            return "OK", 200

        # Handle Commands
        if text == "/start":
            send_telegram_message(chat_id, "Hello! Type /catalog to see available items or search for a product.")
            return "OK", 200

        if text == "/catalog":
            res = supabase.table("products").select("*").execute()
            products = res.data
            if not products:
                send_telegram_message(chat_id, "No products found in database.")
            else:
                for item in products:
                    send_telegram_message(chat_id, f"<b>{item['name']}</b>\nPrice: ${item['price']}\nInfo: {item['description']}")
            return "OK", 200

        # Search Products
        res = supabase.table("products").select("*").execute()
        for item in res.data:
            if item["name"].lower() in text:
                send_telegram_message(chat_id, f"<b>{item['name']}</b>\nPrice: ${item['price']}\nInfo: {item['description']}")

        return "OK", 200

    except Exception as err:
        print(f"CRITICAL ERROR: {str(err)}")
        if 'chat_id' in locals() and chat_id:
            send_telegram_message(chat_id, f"⚠️ <b>Bot Execution Error:</b> {str(err)}")
        return "OK", 200
