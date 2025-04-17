import os
import logging
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from pymongo import MongoClient
from threading import Thread
from keep_alive import run as keep_alive

# Load env vars
load_dotenv()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB
MONGO_URI = os.getenv('MONGO_URI')
mongo_client = MongoClient(MONGO_URI)
db = mongo_client['telegram_userbot']
users_collection = db['users']

# Telegram creds
api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')
session_string = os.getenv('SESSION_STRING')
OWNER_ID = int(os.getenv('OWNER_ID'))

# Telethon client
telegram_client = TelegramClient(StringSession(session_string), api_id, api_hash)

# Keep alive server
Thread(target=keep_alive).start()

# Handlers
@telegram_client.on(events.NewMessage(incoming=True))
async def handler(event):
    if event.is_group or event.is_channel or event.sender_id == OWNER_ID:
        return

    sender = event.sender_id
    user = users_collection.find_one({"_id": sender})

    if user and user.get("banned"):
        await event.reply("⟶ 𝘠𝘰𝘶 𝘢𝘳𝘦 𝘣𝘢𝘯𝘯𝘦𝘥 𝘧𝘳𝘰𝘮 𝘮𝘦𝘴𝘴𝘢𝘨𝘪𝘯𝘨 𝘵𝘩𝘪𝘴 𝘢𝘤𝘤𝘰𝘶𝘯𝘵.")
        return

    if not user:
        users_collection.insert_one({"_id": sender, "messages": 1, "warnings": 5, "approved": False})
        await event.reply("⟶ 𝘠𝘰𝘶'𝘷𝘦 𝘴𝘦𝘯𝘵 𝘺𝘰𝘶𝘳 𝘧𝘪𝘳𝘴𝘵 𝘮𝘦𝘴𝘴𝘢𝘨𝘦. 𝘗𝘭𝘦𝘢𝘴𝘦 𝘸𝘢𝘪𝘵 𝘧𝘰𝘳 𝘢𝘱𝘱𝘳𝘰𝘷𝘢𝘭.")
    elif not user["approved"]:
        if event.is_reply:
            return
        if event.text:
            if user["messages"] > 1:
                await event.delete()
                if user["warnings"] > 1:
                    await send_warning(event, sender, user["warnings"] - 1)
                else:
                    await event.reply("⟶ 𝘠𝘰𝘶 𝘢𝘳𝘦 𝘯𝘰𝘸 𝘣𝘭𝘰𝘤𝘬𝘦𝘥 𝘧𝘰𝘳 𝘴𝘱𝘢𝘮.")
                    users_collection.update_one({"_id": sender}, {"$set": {"approved": False, "banned": True}})
            else:
                users_collection.update_one({"_id": sender}, {"$inc": {"messages": 1}})
        elif event.sticker:
            if user["messages"] > 2:
                await event.delete()
                if user["warnings"] > 1:
                    await send_warning(event, sender, user["warnings"] - 1)
                else:
                    await event.reply("⟶ 𝘠𝘰𝘶 𝘢𝘳𝘦 𝘯𝘰𝘸 𝘣𝘭𝘰𝘤𝘬𝘦𝘥 𝘧𝘰𝘳 𝘴𝘵𝘪𝘤𝘬𝘦𝘳 𝘴𝘱𝘢𝘮.")
                    users_collection.update_one({"_id": sender}, {"$set": {"approved": False, "banned": True}})
            else:
                users_collection.update_one({"_id": sender}, {"$inc": {"messages": 1}})
        else:
            await event.reply("⟶ 𝘜𝘯𝘴𝘶𝘱𝘱𝘰𝘳𝘵𝘦𝘥 𝘤𝘰𝘯𝘵𝘦𝘯𝘵. 𝘠𝘰𝘶 𝘢𝘳𝘦 𝘣𝘢𝘯𝘯𝘦𝘥.")
            users_collection.update_one({"_id": sender}, {"$set": {"approved": False, "banned": True}})

async def send_warning(event, sender, remaining):
    await event.reply(f"⟶ 𝘞𝘢𝘳𝘯𝘪𝘯𝘨 {5 - remaining}/5: {remaining} 𝘸𝘢𝘳𝘯𝘪𝘯𝘨𝘴 𝘭𝘦𝘧𝘵.")
    users_collection.update_one({"_id": sender}, {"$set": {"warnings": remaining}})

# Admin Commands
@telegram_client.on(events.NewMessage(pattern=r'\.approve'))
async def approve_user(event):
    if event.sender_id != OWNER_ID or event.is_group or event.is_channel:
        return
    user_id = event.chat_id
    users_collection.update_one(
        {"_id": user_id},
        {"$set": {"approved": True, "banned": False, "warnings": 5, "messages": 0}},
        upsert=True
    )
    await event.reply(f"⟶ 𝘜𝘴𝘦𝘳 `{user_id}` 𝘩𝘢𝘴 𝘣𝘦𝘦𝘯 𝘢𝘱𝘱𝘳𝘰𝘷𝘦𝘥.", parse_mode="md")

@telegram_client.on(events.NewMessage(pattern=r'\.unapprove'))
async def unapprove_user(event):
    if event.sender_id != OWNER_ID or event.is_group or event.is_channel:
        return
    user_id = event.chat_id
    users_collection.update_one({"_id": user_id}, {"$set": {"approved": False}})
    await event.reply(f"⟶ 𝘜𝘴𝘦𝘳 `{user_id}` 𝘩𝘢𝘴 𝘣𝘦𝘦𝘯 𝘶𝘯𝘢𝘱𝘱𝘳𝘰𝘷𝘦𝘥.", parse_mode="md")

@telegram_client.on(events.NewMessage(pattern=r'\.ban'))
async def ban_user(event):
    if event.sender_id != OWNER_ID or event.is_group or event.is_channel:
        return
    user_id = event.chat_id
    users_collection.update_one({"_id": user_id}, {"$set": {"approved": False, "banned": True}})
    await event.reply(f"⟶ 𝘜𝘴𝘦𝘳 `{user_id}` 𝘩𝘢𝘴 𝘣𝘦𝘦𝘯 𝘣𝘢𝘯𝘯𝘦𝘥.", parse_mode="md")

@telegram_client.on(events.NewMessage(pattern=r'\.unban'))
async def unban_user(event):
    if event.sender_id != OWNER_ID or event.is_group or event.is_channel:
        return
    user_id = event.chat_id
    users_collection.update_one({"_id": user_id}, {"$set": {"banned": False}})
    await event.reply(f"⟶ 𝘜𝘴𝘦𝘳 `{user_id}` 𝘩𝘢𝘴 𝘣𝘦𝘦𝘯 𝘶𝘯𝘣𝘢𝘯𝘯𝘦𝘥.", parse_mode="md")

@telegram_client.on(events.NewMessage(pattern=r'\.astat'))
async def approved_users(event):
    if event.sender_id != OWNER_ID or event.is_group or event.is_channel:
        return
    users = users_collection.find({"approved": True})
    text = "\n".join([f"`{u['_id']}`" for u in users]) or "⟶ 𝘕𝘰 𝘢𝘱𝘱𝘳𝘰𝘷𝘦𝘥 𝘶𝘴𝘦𝘳𝘴."
    await event.reply(f"**⟶ 𝘈𝘱𝘱𝘳𝘰𝘷𝘦𝘥 𝘜𝘴𝘦𝘳𝘴:**\n{text}", parse_mode="md")

@telegram_client.on(events.NewMessage(pattern=r'\.bstat'))
async def banned_users(event):
    if event.sender_id != OWNER_ID or event.is_group or event.is_channel:
        return
    users = users_collection.find({"banned": True})
    text = "\n".join([f"`{u['_id']}`" for u in users]) or "⟶ 𝘕𝘰 𝘣𝘢𝘯𝘯𝘦𝘥 𝘶𝘴𝘦𝘳𝘴."
    await event.reply(f"**⟶ 𝘉𝘢𝘯𝘯𝘦𝘥 𝘜𝘴𝘦𝘳𝘴:**\n{text}", parse_mode="md")

@telegram_client.on(events.NewMessage(pattern=r'\.help'))
async def help_command(event):
    if event.sender_id != OWNER_ID or event.is_group or event.is_channel:
        return
    await event.reply("""
**⟶ 𝘈𝘥𝘮𝘪𝘯 𝘊𝘰𝘮𝘮𝘢𝘯𝘥𝘴**
• `.approve` – 𝘈𝘱𝘱𝘳𝘰𝘷𝘦 𝘤𝘶𝘳𝘳𝘦𝘯𝘵 𝘶𝘴𝘦𝘳.
• `.unapprove` – 𝘜𝘯𝘢𝘱𝘱𝘳𝘰𝘷𝘦 𝘤𝘶𝘳𝘳𝘦𝘯𝘵 𝘶𝘴𝘦𝘳.
• `.ban` – 𝘉𝘢𝘯 𝘤𝘶𝘳𝘳𝘦𝘯𝘵 𝘶𝘴𝘦𝘳.
• `.unban` – 𝘜𝘯𝘣𝘢𝘯 𝘤𝘶𝘳𝘳𝘦𝘯𝘵 𝘶𝘴𝘦𝘳.
• `.astat` – 𝘚𝘩𝘰𝘸 𝘢𝘭𝘭 𝘢𝘱𝘱𝘳𝘰𝘷𝘦𝘥 𝘶𝘴𝘦𝘳𝘴.
• `.bstat` – 𝘚𝘩𝘰𝘸 𝘢𝘭𝘭 𝘣𝘢𝘯𝘯𝘦𝘥 𝘶𝘴𝘦𝘳𝘴.
• `.help` – 𝘚𝘩𝘰𝘸 𝘩𝘦𝘭𝘱 𝘮𝘦𝘯𝘶.
    """, parse_mode="md")

# Start
logger.info("Starting userbot...")
telegram_client.start()
telegram_client.run_until_disconnected()