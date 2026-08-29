import os
import httpx
from flask import Flask, request
from supabase import create_client

app = Flask(__name__)

# Fetch Environment Variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"

def send_telegram_message(chat_id, text):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    httpx.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)

def send_telegram_photo(chat_id, photo_url, caption):
    payload = {
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML"
    }
    httpx.post(f"{TELEGRAM_API_URL}/sendPhoto", json=payload)

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def webhook(path):
    if request.method == 'GET':
        if not TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
            return "Missing Environment Variables in Vercel!", 500
        return "Telegram Bot Server is Online!", 200

    try:
        json_data = request.get_json(force=True)
        
        if not json_data or "message" not in json_data:
            return "OK", 200

        message = json_data["message"]
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "").strip().lower()

        if not chat_id or not text:
            return "OK", 200

        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Command: /start
        if text == "/start":
            send_telegram_message(chat_id, "Hello! Type /catalog to see available items or ask for a product name.")
            return "OK", 200

        # Command: /catalog
        if text == "/catalog":
            response = supabase.table("products").select("*").execute()
            products = response.data

            if not products:
                send_telegram_message(chat_id, "No products found in the store.")
            else:
                for item in products:
                    caption = f"<b>{item['name']}</b>\nPrice: ${item['price']}\nInfo: {item['description']}"
                    if item.get("image_url"):
                        send_telegram_photo(chat_id, item["image_url"], caption)
                    else:
                        send_telegram_message(chat_id, caption)
            return "OK", 200

        # Keyword Search
        response = supabase.table("products").select("*").execute()
        products = response.data

        if products:
            for item in products:
                if item["name"].lower() in text:
                    caption = f"<b>{item['name']}</b>\nPrice: ${item['price']}\nInfo: {item['description']}"
                    if item.get("image_url"):
                        send_telegram_photo(chat_id, item["image_url"], caption)
                    else:
                        send_telegram_message(chat_id, caption)

        return "OK", 200

    except Exception as e:
        print(f"Error: {str(e)}")
        return f"Error: {str(e)}", 500
