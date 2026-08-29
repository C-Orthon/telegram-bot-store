import os
import asyncio
from flask import Flask, request, jsonify
from telegram import Bot, Update
from supabase import create_client, Client

app = Flask(__name__)

# Fetch environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

bot = Bot(token=TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

async def handle_update(json_data):
    update = Update.de_json(json_data, bot)
    
    if not update or not update.message or not update.message.text:
        return

    chat_id = update.message.chat_id
    text = update.message.text.strip().lower()

    # Reply to /start
    if text == "/start":
        await bot.send_message(chat_id=chat_id, text="Hello! Type /catalog to see our store items or ask about any product.")
        return

    # Reply to /catalog
    if text == "/catalog":
        response = supabase.table("products").select("*").execute()
        products = response.data

        if not products:
            await bot.send_message(chat_id=chat_id, text="No products available in the database.")
            return

        for item in products:
            msg = f"<b>{item['name']}</b>\nPrice: ${item['price']}\nInfo: {item['description']}"
            if item.get("image_url"):
                await bot.send_photo(chat_id=chat_id, photo=item["image_url"], caption=msg, parse_mode="HTML")
            else:
                await bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")
        return

    # Search products by name match
    response = supabase.table("products").select("*").execute()
    products = response.data

    for item in products:
        if item["name"].lower() in text:
            reply = f"<b>{item['name']}</b>\nPrice: ${item['price']}\nInfo: {item['description']}"
            if item.get("image_url"):
                await bot.send_photo(chat_id=chat_id, photo=item["image_url"], caption=reply, parse_mode="HTML")
            else:
                await bot.send_message(chat_id=chat_id, text=reply, parse_mode="HTML")

@app.route('/api/index', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return "Bot Server is Online!", 200

    json_data = request.get_json(force=True)
    
    # Run async function safely inside Flask
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(handle_update(json_data))
    loop.close()

    return jsonify({"status": "ok"}), 200
