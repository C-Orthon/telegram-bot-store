import os
import json
import asyncio
from http.server import BaseHTTPRequestHandler
from telegram import Bot, Update
from supabase import create_client, Client

# Environment Variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Clients
bot = Bot(token=TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

async def process_update(update_data):
    update = Update.de_json(update_data, bot)
    
    if not update.message or not update.message.text:
        return

    chat_id = update.message.chat_id
    text = update.message.text.strip().lower()

    # Handle /start command
    if text == "/start":
        await bot.send_message(chat_id=chat_id, text="Hello! Ask about any merchandise or type /catalog to see our items.")
        return

    # Handle /catalog command
    if text == "/catalog":
        response = supabase.table("products").select("*").execute()
        products = response.data

        if not products:
            await bot.send_message(chat_id=chat_id, text="No products available right now.")
            return

        for item in products:
            msg = f"<b>{item['name']}</b>\nPrice: ${item['price']}\nInfo: {item['description']}"
            if item.get("image_url"):
                await bot.send_photo(chat_id=chat_id, photo=item["image_url"], caption=msg, parse_mode="HTML")
            else:
                await bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")
        return

    # Handle Product Inquiry Search
    response = supabase.table("products").select("*").execute()
    products = response.data

    for item in products:
        if item["name"].lower() in text:
            reply = f"<b>{item['name']}</b>\nPrice: ${item['price']}\nInfo: {item['description']}"
            if item.get("image_url"):
                await bot.send_photo(chat_id=chat_id, photo=item["image_url"], caption=reply, parse_mode="HTML")
            else:
                await bot.send_message(chat_id=chat_id, text=reply, parse_mode="HTML")


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        json_data = json.loads(post_data.decode('utf-8'))

        # Run async bot code safely in Serverless runtime
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        loop.run_until_complete(process_update(json_data))

        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'OK')

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot status: Active')
