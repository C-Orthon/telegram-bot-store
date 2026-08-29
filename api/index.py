import os
import json
import asyncio
from http.server import BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from supabase import create_client, Client

# Environment Variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ADMIN_USERNAMES = ["BrandCatalogbot"]  # Replace with your username (without @)

# Initialize Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize Telegram App
app = ApplicationBuilder().token(TOKEN).build()

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Ask about any merchandise or type /catalog to see our items.")

async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = supabase.table("products").select("*").execute()
    products = response.data

    if not products:
        await update.message.reply_text("No products available right now.")
        return

    for item in products:
        msg = f"<b>{item['name']}</b>\nPrice: ${item['price']}\nInfo: {item['description']}"
        if item.get("image_url"):
            await update.message.reply_photo(photo=item["image_url"], caption=msg, parse_mode="HTML")
        else:
            await update.message.reply_text(msg, parse_mode="HTML")

async def handle_inquiry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    response = supabase.table("products").select("*").execute()
    products = response.data

    for item in products:
        if item["name"].lower() in text:
            reply = f"<b>{item['name']}</b>\nPrice: ${item['price']}\nInfo: {item['description']}"
            if item.get("image_url"):
                await update.message.reply_photo(photo=item["image_url"], caption=reply, parse_mode="HTML")
            else:
                await update.message.reply_text(reply, parse_mode="HTML")

# Register Handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("catalog", catalog))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_inquiry))

# --- Serverless Handler for Vercel ---
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        json_data = json.loads(post_data.decode('utf-8'))

        # Process update asynchronously
        async def process():
            await app.initialize()
            update = Update.de_json(json_data, app.bot)
            await app.process_update(update)

        asyncio.run(process())

        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'OK')