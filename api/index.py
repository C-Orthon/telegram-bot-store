import os
import httpx
from flask import Flask, request
from supabase import create_client

app = Flask(__name__)

# Environment Variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip().strip("'\"")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().strip("'\"").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip().strip("'\"")

# Configurable Payment & Admin Details
OWNER_USERNAME = "@TM1845"  # Without @ symbol
BANK_ACCOUNT_INFO = "Bank: Commercial Bank\nAccount No: 1000xxxxxxxxx\nAccount Name: Store Owner"
ADMIN_TELEGRAM_IDS = []  # Optional: Put your numeric Telegram User ID here to restrict admin commands, e.g., [123456789]

if SUPABASE_URL and not SUPABASE_URL.startswith(("http://", "https://")):
    SUPABASE_URL = f"https://{SUPABASE_URL}"

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}" if TOKEN else ""

def send_telegram_message(chat_id, text, reply_markup=None):
    if not TOKEN:
        return
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        httpx.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload, timeout=5.0)
    except Exception as e:
        print(f"Failed to send message: {e}")

def send_telegram_photo(chat_id, photo_url, caption, reply_markup=None):
    if not TOKEN:
        return
    payload = {
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        httpx.post(f"{TELEGRAM_API_URL}/sendPhoto", json=payload, timeout=5.0)
    except Exception as e:
        # Fallback to text if image URL fails to load
        send_telegram_message(chat_id, caption, reply_markup)

def answer_callback_query(callback_query_id, text):
    payload = {"callback_query_id": callback_query_id, "text": text}
    try:
        httpx.post(f"{TELEGRAM_API_URL}/answerCallbackQuery", json=payload, timeout=5.0)
    except Exception as e:
        print(f"Failed to answer callback: {e}")

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def webhook(path):
    if request.method == 'GET':
        return "Telegram Bot Server is Online!", 200

    try:
        json_data = request.get_json(force=True, silent=True) or {}

        # 1. Handle Inline Button Clicks (Buy Requests)
        if "callback_query" in json_data:
            cb = json_data["callback_query"]
            cb_id = cb.get("id")
            chat_id = cb.get("message", {}).get("chat", {}).get("id")
            data = cb.get("data", "")

            if data.startswith("buy_"):
                product_name = data.replace("buy_", "")
                payment_text = (
                    f"🛒 <b>Order Request: {product_name}</b>\n\n"
                    f"💳 <b>Payment Details:</b>\n{BANK_ACCOUNT_INFO}\n\n"
                    f"📲 <b>Next Steps:</b>\n"
                    f"1. Send payment to the account above.\n"
                    f"2. Contact the owner <a href='https://t.me/{OWNER_USERNAME}'>@{OWNER_USERNAME}</a> with your payment screenshot & delivery location."
                )
                answer_callback_query(cb_id, "Payment details sent!")
                send_telegram_message(chat_id, payment_text)
            return "OK", 200

        # 2. Handle Messages
        if "message" not in json_data:
            return "OK", 200

        message = json_data["message"]
        chat_id = message.get("chat", {}).get("id")
        user_id = message.get("from", {}).get("id")
        text = message.get("text", "").strip()

        if not chat_id or not text:
            return "OK", 200

        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Command: /start
        if text.lower() == "/start":
            msg = (
                "👋 <b>Welcome to our Store Bot!</b>\n\n"
                "• Type /catalog to view all items.\n"
                "• Type item names directly to search.\n\n"
                "🛠 <b>Admin Commands:</b>\n"
                "• <code>/add Name | Price | Description | Image_URL</code>\n"
                "• <code>/delete Product Name</code>"
            )
            send_telegram_message(chat_id, msg)
            return "OK", 200

        # Command: /catalog
        if text.lower() == "/catalog":
            res = supabase.table("products").select("*").execute()
            products = res.data
            if not products:
                send_telegram_message(chat_id, "No products available in the store.")
            else:
                for item in products:
                    caption = f"📦 <b>{item['name']}</b>\n💰 Price: ${item['price']}\n📝 {item['description']}"
                    reply_markup = {
                        "inline_keyboard": [[
                            {"text": "💳 Buy / Order", "callback_data": f"buy_{item['name']}"}
                        ]]
                    }
                    if item.get("image_url"):
                        send_telegram_photo(chat_id, item["image_url"], caption, reply_markup)
                    else:
                        send_telegram_message(chat_id, caption, reply_markup)
            return "OK", 200

        # Command: /add Product (Admin)
        # Format: /add Leather Jacket | 120 | Genuine leather jacket | https://image-link.com/photo.jpg
        if text.startswith("/add"):
            raw_input = text[4:].strip()
            parts = [p.strip() for p in raw_input.split("|")]

            if len(parts) < 3:
                send_telegram_message(chat_id, "⚠️ <b>Format Error!</b>\nUse: <code>/add Name | Price | Description | Image_URL(optional)</code>")
                return "OK", 200

            p_name = parts[0]
            p_price = parts[1]
            p_desc = parts[2]
            p_img = parts[3] if len(parts) > 3 else None

            payload = {"name": p_name, "price": p_price, "description": p_desc}
            if p_img:
                payload["image_url"] = p_img

            supabase.table("products").insert(payload).execute()
            send_telegram_message(chat_id, f"✅ Product <b>{p_name}</b> added successfully!")
            return "OK", 200

        # Command: /delete Product (Admin)
        # Format: /delete Leather Jacket
        if text.startswith("/delete"):
            p_name = text[7:].strip()
            if not p_name:
                send_telegram_message(chat_id, "⚠️ <b>Format Error!</b>\nUse: <code>/delete Product Name</code>")
                return "OK", 200

            supabase.table("products").delete().eq("name", p_name).execute()
            send_telegram_message(chat_id, f"🗑 Product <b>{p_name}</b> deleted successfully!")
            return "OK", 200

        # Product Search Keyword Match
        res = supabase.table("products").select("*").execute()
        for item in res.data:
            if item["name"].lower() in text.lower():
                caption = f"📦 <b>{item['name']}</b>\n💰 Price: ${item['price']}\n📝 {item['description']}"
                reply_markup = {
                    "inline_keyboard": [[
                        {"text": "💳 Buy / Order", "callback_data": f"buy_{item['name']}"}
                    ]]
                }
                if item.get("image_url"):
                    send_telegram_photo(chat_id, item["image_url"], caption, reply_markup)
                else:
                    send_telegram_message(chat_id, caption, reply_markup)

        return "OK", 200

    except Exception as err:
        print(f"Error: {err}")
        return "OK", 200
