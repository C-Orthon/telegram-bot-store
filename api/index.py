import os
import json
import asyncio
from flask import Flask, request

app = Flask(__name__)

# Safely load Environment Variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def catch_all(path):
    if request.method == 'GET':
        if not TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
            return "Server Running, but Environment Variables (TOKEN / SUPABASE) are missing in Vercel!", 500
        return "Telegram Bot Server is Online!", 200

    try:
        from telegram import Bot, Update
        from supabase import create_client

        bot = Bot(token=TOKEN)
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        json_data = request.get_json(force=True)
        update = Update.de_json(json_data, bot)

        if update and update.message and update.message.text:
            chat_id = update.message.chat_id
            text = update.message.text.strip().lower()

            async def process():
                if text == "/start":
                    await bot.send_message(chat_id=chat_id, text="Hello! Type /catalog to see available items.")
                elif text == "/catalog":
                    response = supabase.table("products").select("*").execute()
                    products = response.data
                    if not products:
                        await bot.send_message(chat_id=chat_id, text="No products found.")
                    else:
                        for item in products:
                            msg = f"<b>{item['name']}</b>\nPrice: ${item['price']}\nInfo: {item['description']}"
                            if item.get("image_url"):
                                await bot.send_photo(chat_id=chat_id, photo=item["image_url"], caption=msg, parse_mode="HTML")
                            else:
                                await bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")
                else:
                    response = supabase.table("products").select("*").execute()
                    for item in response.data:
                        if item["name"].lower() in text:
                            msg = f"<b>{item['name']}</b>\nPrice: ${item['price']}\nInfo: {item['description']}"
                            if item.get("image_url"):
                                await bot.send_photo(chat_id=chat_id, photo=item["image_url"], caption=msg, parse_mode="HTML")
                            else:
                                await bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(process())
            loop.close()

        return "OK", 200

    except Exception as e:
        return f"Execution Error: {str(e)}", 500
