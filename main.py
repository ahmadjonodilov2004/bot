import os
import asyncio
from aiohttp import web
from datetime import datetime, timedelta
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telethon import TelegramClient, events, functions
from telethon.tl.functions.account import UpdateProfileRequest

# ================= SOZLAMALAR =================
BOT_TOKEN = "8306862864:AAGRndw5uMx5ifjOii3Kj2mzyRCA9bKxCH8"
API_ID = 946606
API_HASH = "a183e9d1503a9c6514bd086dd03aeb8e"
OWNER_ID = 7035377346

DIR = Path("sessions")
DIR.mkdir(exist_ok=True)
clients = {}

def ok(u: Update): return u.effective_user and u.effective_user.id == OWNER_ID

# ================= USERBOT MANTIQ LARI =================
async def task_runner(client, task_type):
    try:
        while client.is_connected():
            if task_type == 'online':
                await client(functions.account.UpdateStatusRequest(offline=False))
                await client(functions.updates.GetStateRequest())
                await asyncio.sleep(60)
            elif task_type == 'time':
                now = datetime.utcnow() + timedelta(hours=5)
                try: await client(UpdateProfileRequest(last_name=now.strftime("%H:%M")))
                except: pass
                await asyncio.sleep(60 - (datetime.utcnow() + timedelta(hours=5)).second)
    except Exception: pass

async def auto_responder(event):
    if getattr(event.client, 'auto_reply', False) and event.is_private:
        sender = await event.get_sender()
        if sender and not sender.bot and not sender.is_self:
            await event.reply("Xozir javob qaytaraman\n\n(avto javob qaytargich 🤖)")

def add_handlers(client: TelegramClient):
    client.add_event_handler(lambda e: setattr(client, 'on_t', asyncio.create_task(task_runner(client, 'online'))) or e.edit("🟢 Onlayn!"), events.NewMessage(pattern=r"(?i)^/online_on", outgoing=True))
    client.add_event_handler(lambda e: getattr(client, 'on_t').cancel() or e.edit("🔴 Oflayn."), events.NewMessage(pattern=r"(?i)^/online_off", outgoing=True))
    client.add_event_handler(lambda e: setattr(client, 'tm_t', asyncio.create_task(task_runner(client, 'time'))) or e.edit("⏳ Soat yoqildi!"), events.NewMessage(pattern=r"(?i)^/s_on", outgoing=True))
    client.add_event_handler(lambda e: getattr(client, 'tm_t').cancel() or e.edit("🛑 Soat o'chdi."), events.NewMessage(pattern=r"(?i)^/s_off", outgoing=True))
    client.add_event_handler(lambda e: setattr(client, 'auto_reply', True) or e.edit("🤖 Avto-javob on!"), events.NewMessage(pattern=r"(?i)^/auto_on", outgoing=True))
    client.add_event_handler(lambda e: setattr(client, 'auto_reply', False) or e.edit("💤 Avto-javob off."), events.NewMessage(pattern=r"(?i)^/auto_off", outgoing=True))
    client.add_event_handler(auto_responder, events.NewMessage(incoming=True))

# ================= BOT KOMANDALARI =================
async def handle_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ok(update): return
    if update.message.document and update.message.document.file_name.endswith(".session"):
        name = Path(update.message.document.file_name).stem
        path = DIR / f"{name}.session"
        await (await context.bot.get_file(update.message.document.file_id)).download_to_drive(str(path))
        
        client = TelegramClient(str(path.with_suffix("")), API_ID, API_HASH)
        await client.connect()
        if not await client.is_user_authorized(): return await update.message.reply_text("❌ Yaroqsiz session!")
        
        client.auto_reply = False
        add_handlers(client)
        asyncio.create_task(client.run_until_disconnected())
        clients[name] = client
        await update.message.reply_text(f"✅ Ulandi: {name}")

async def start_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("✅ .session fayl yuboring.")))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_session))
    
    # Oldingi sessiyalarni yuklash
    for p in DIR.glob("*.session"):
        c = TelegramClient(str(p.with_suffix("")), API_ID, API_HASH)
        await c.connect()
        if await c.is_user_authorized():
            c.auto_reply = False
            add_handlers(c)
            asyncio.create_task(c.run_until_disconnected())
            clients[p.stem] = c

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

# ================= YAGONA ISHGA TUSHIRISH (MAIN) =================
async def main():
    # 1. Web serverni ishga tushirish (Render uchun)
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Bot faol!"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 10000))).start()

    # 2. Telegram botni ishga tushirish
    await start_bot()
    
    # 3. Jarayonni ushlab turish
    while True: await asyncio.sleep(3600)

if name == "main":
    asyncio.run(main())