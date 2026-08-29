import os
import httpx
from flask import Flask, request
from supabase import create_client

app = Flask(__name__)

# Fetch Environment Variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

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
        return "Telegram Bot Server is Online!", 200

    # POST Request Processing
    try:
        json_data = request.get_json(force=True, silent=True)
        if not json_data or "message" not in json_data:
            return "OK", 200

        message = json_data["message"]
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "").strip().lower()

        if not chat_id or not text:
            return "OK", 200

        # Check credentials inside request
        if not TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
            send_telegram_message(chat_id, "⚠️ <b>Error:</b> Environment variables are missing on Vercel dashboard.")
            return "OK", 200

        # Attempt Supabase Connection
        try:
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as sb_err:
            send_telegram_message(chat_id, f"⚠️ <b>Supabase Connection Error:</b> {str(sb_err)}")
            return "OK", 200

        # Handle Commands
        if text == "/start":
            send_telegram_message(chat_id, "Hello! Type /catalog to see available items or type a product name.")
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
        # Prevent 500 error and print error in Vercel / Telegram
        print(f"CRITICAL ERROR: {str(err)}")
        if 'chat_id' in locals() and chat_id:
            send_telegram_message(chat_id, f"⚠️ <b>Bot Code Crashed:</b> {str(err)}")
        return "OK", 200
