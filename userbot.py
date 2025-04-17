import os
import logging
from dotenv import load_dotenv
from telethon import TelegramClient, events, Button
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
    if event.is_group or event.is_channel:
        return

    sender = event.sender_id
    user = users_collection.find_one({"_id": sender})

    if user and user.get("banned"):
        await event.reply("You are banned from messaging this account.")
        return

    if not user:
        users_collection.insert_one({"_id": sender, "messages": 1, "warnings": 5, "approved": False})
        await event.reply("You've sent your first message. I need your approval to continue.")
    elif not user["approved"]:
        if event.is_reply:
            return
        if event.text:
            if user["messages"] > 1:
                await event.delete()
                if user["warnings"] > 1:
                    await send_warning(event, sender, user["warnings"] - 1)
                else:
                    await event.reply("You are blocked for violating the message limit!")
                    users_collection.update_one({"_id": sender}, {"$set": {"approved": False, "banned": True}})
            else:
                users_collection.update_one({"_id": sender}, {"$inc": {"messages": 1}})
        elif event.sticker:
            if user["messages"] > 2:
                await event.delete()
                if user["warnings"] > 1:
                    await send_warning(event, sender, user["warnings"] - 1)
                else:
                    await event.reply("You are blocked for violating the sticker limit!")
                    users_collection.update_one({"_id": sender}, {"$set": {"approved": False, "banned": True}})
            else:
                users_collection.update_one({"_id": sender}, {"$inc": {"messages": 1}})
        else:
            await event.reply("You are blocked for sending unsupported content!")
            users_collection.update_one({"_id": sender}, {"$set": {"approved": False, "banned": True}})

async def send_warning(event, sender, remaining):
    await event.reply(f"Warning {5 - remaining}/5: {remaining} warnings left.")
    users_collection.update_one({"_id": sender}, {"$set": {"warnings": remaining}})

@telegram_client.on(events.NewMessage(pattern=r'\.approve'))
async def approve_user(event):
    if event.sender_id != OWNER_ID or event.is_group or event.is_channel:
        return
    if event.is_reply:
        user_id = (await event.get_reply_message()).sender_id
        users_collection.update_one({"_id": user_id}, {"$set": {"approved": True, "banned": False, "warnings": 5, "messages": 0}})
        await event.reply(f"✅ User `{user_id}` approved.", parse_mode="md")
    else:
        await event.reply("Reply to a message to approve.")

@telegram_client.on(events.NewMessage(pattern=r'\.unapprove'))
async def unapprove_user(event):
    if event.sender_id != OWNER_ID or event.is_group or event.is_channel:
        return
    if event.is_reply:
        user_id = (await event.get_reply_message()).sender_id
        users_collection.update_one({"_id": user_id}, {"$set": {"approved": False}})
        await event.reply(f"❌ User `{user_id}` unapproved.", parse_mode="md")
    else:
        users_collection.update_many({"approved": True}, {"$set": {"approved": False}})
        await event.reply("✅ All users unapproved.", parse_mode="md")

@telegram_client.on(events.NewMessage(pattern=r'\.ban'))
async def ban_user(event):
    if event.sender_id != OWNER_ID or event.is_group or event.is_channel:
        return
    if event.is_reply:
        user_id = (await event.get_reply_message()).sender_id
        users_collection.update_one({"_id": user_id}, {"$set": {"approved": False, "banned": True}})
        await event.reply(f"⛔ User `{user_id}` banned.", parse_mode="md")
    else:
        users_collection.update_many({"approved": True}, {"$set": {"approved": False, "banned": True}})
        await event.reply("✅ All users banned.", parse_mode="md")

@telegram_client.on(events.NewMessage(pattern=r'\.unban'))
async def unban_user(event):
    if event.sender_id != OWNER_ID or event.is_group or event.is_channel:
        return
    if event.is_reply:
        user_id = (await event.get_reply_message()).sender_id
        users_collection.update_one({"_id": user_id}, {"$set": {"banned": False}})
        await event.reply(f"✅ User `{user_id}` unbanned.", parse_mode="md")
    else:
        args = event.pattern_match.group(1)
        try:
            user_id = int(args) if args.isdigit() else (await telegram_client.get_entity(args)).id
            users_collection.update_one({"_id": user_id}, {"$set": {"banned": False}})
            await event.reply(f"✅ User `{user_id}` unbanned.", parse_mode="md")
        except Exception as e:
            await event.reply(f"Error: {str(e)}")

@telegram_client.on(events.NewMessage(pattern=r'\.astat'))
async def approved_users(event):
    if event.sender_id != OWNER_ID or event.is_group or event.is_channel:
        return
    users = users_collection.find({"approved": True})
    text = "\n".join([f"`{u['_id']}`" for u in users]) or "No approved users found."
    await event.reply(f"**Approved Users:**\n{text}")

@telegram_client.on(events.NewMessage(pattern=r'\.bstat'))
async def banned_users(event):
    if event.sender_id != OWNER_ID or event.is_group or event.is_channel:
        return
    users = users_collection.find({"banned": True})
    text = "\n".join([f"`{u['_id']}`" for u in users]) or "No banned users found."
    await event.reply(f"**Banned Users:**\n{text}")

@telegram_client.on(events.NewMessage(pattern=r'\.help'))
async def help_command(event):
    if event.sender_id != OWNER_ID or event.is_group or event.is_channel:
        return
    await event.reply("""
**UserBot Admin Help**
Available commands:
.approve – Reply to approve a user.
.unapprove – Reply to unapprove a user or unapprove everyone.
.ban – Reply to ban a user or ban everyone.
.unban <id or username> – Unban a user.
.astat – View all approved users.
.bstat – View all banned users.
.help – This message.
    """, parse_mode="md")

# Start
logger.info("Starting userbot...")
telegram_client.start()
telegram_client.run_until_disconnected()