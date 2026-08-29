import os
import asyncio
from flask import Flask, request
from telegram import Bot, Update
from supabase import create_client

app = Flask(__name__)

# Fetch Environment Variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

async def process_telegram_update(json_data):
    bot = Bot(token=TOKEN)
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    update = Update.de_json(json_data, bot)

    if not update or not update.message or not update.message.text:
        return

    chat_id = update.message.chat_id
    text = update.message.text.strip().lower()

    # Command: /start
    if text == "/start":
        await bot.send_message(chat_id=chat_id, text="Hello! Type /catalog to see available items or ask for a product name.")
        return

    # Command: /catalog
    if text == "/catalog":
        response = supabase.table("products").select("*").execute()
        products = response.data

        if not products:
            await bot.send_message(chat_id=chat_id, text="No products found in the store.")
        else:
            for item in products:
                caption_text = f"<b>{item['name']}</b>\nPrice: ${item['price']}\nInfo: {item['description']}"
                if item.get("image_url"):
                    await bot.send_photo(chat_id=chat_id, photo=item["image_url"], caption=caption_text, parse_mode="HTML")
                else:
                    await bot.send_message(chat_id=chat_id, text=caption_text, parse_mode="HTML")
        return

    # Keyword Search for Products
    response = supabase.table("products").select("*").execute()
    products = response.data

    if products:
        for item in products:
            if item["name"].lower() in text:
                reply_text = f"<b>{item['name']}</b>\nPrice: ${item['price']}\nInfo: {item['description']}"
                if item.get("image_url"):
                    await bot.send_photo(chat_id=chat_id, photo=item["image_url"], caption=reply_text, parse_mode="HTML")
                else:
                    await bot.send_message(chat_id=chat_id, text=reply_text, parse_mode="HTML")


@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def webhook(path):
    if request.method == 'GET':
        if not TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
            return "Missing Environment Variables in Vercel!", 500
        return "Telegram Bot Server is Online!", 200

    try:
        json_data = request.get_json(force=True)
        
        # Run async update processor in a isolated event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(process_telegram_update(json_data))
        loop.close()

        return "OK", 200

    except Exception as e:
        print(f"Webhook Execution Error: {str(e)}")
        return f"Error: {str(e)}", 500
