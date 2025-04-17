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

@telegram_client.on(events.NewMessage(pattern='/approve'))
async def approve_user(event):
    if event.sender_id != OWNER_ID or event.is_group or event.is_channel:
        return
    if event.is_reply:
        user_id = (await event.get_reply_message()).sender_id
        users_collection.update_one({"_id": user_id}, {"$set": {"approved": True, "banned": False, "warnings": 5, "messages": 0}})
        await event.reply(f"✅ User `{user_id}` approved.", parse_mode="md")
    else:
        await event.reply("Reply to a message to approve.")

@telegram_client.on(events.NewMessage(pattern='/unapprove'))
async def unapprove_user(event):
    if event.sender_id != OWNER_ID or event.is_group or event.is_channel:
        return
    if event.is_reply:
        user_id = (await event.get_reply_message()).sender_id
        users_collection.update_one({"_id": user_id}, {"$set": {"approved": False}})
        await event.reply(f"❌ User `{user_id}` unapproved.", parse_mode="md")

@telegram_client.on(events.NewMessage(pattern='/ban'))
async def ban_user(event):
    if event.sender_id != OWNER_ID or event.is_group or event.is_channel:
        return
    if event.is_reply:
        user_id = (await event.get_reply_message()).sender_id
        users_collection.update_one({"_id": user_id}, {"$set": {"approved": False, "banned": True}})
        await event.reply(f"⛔ User `{user_id}` banned.", parse_mode="md")

@telegram_client.on(events.NewMessage(pattern=r'/unban(?:\s+(.+))?'))
async def unban_user(event):
    if event.sender_id != OWNER_ID or event.is_group or event.is_channel:
        return
    args = event.pattern_match.group(1)
    if not args:
        await event.reply("Usage: `/unban <user_id or username>`", parse_mode="md")
        return
    try:
        user_id = int(args) if args.isdigit() else (await telegram_client.get_entity(args)).id
        users_collection.update_one({"_id": user_id}, {"$set": {"banned": False}})
        await event.reply(f"✅ User `{user_id}` unbanned.", parse_mode="md")
    except Exception as e:
        await event.reply(f"Error: {str(e)}")

@telegram_client.on(events.NewMessage(pattern='/status'))
async def status_menu(event):
    if event.sender_id != OWNER_ID or event.is_group or event.is_channel:
        return
    buttons = [
        [Button.inline("✅ Approved", data=b"approved")],
        [Button.inline("❌ Unapproved", data=b"unapproved")],
        [Button.inline("⛔ Banned", data=b"banned")]
    ]
    await event.respond("Select a category to view users:", buttons=buttons)

@telegram_client.on(events.CallbackQuery)
async def handle_callback(event):
    if event.sender_id != OWNER_ID:
        await event.answer("Unauthorized.", alert=True)
        return

    data = event.data.decode("utf-8")
    query_map = {
        "approved": {"approved": True},
        "unapproved": {"approved": False, "banned": {"$ne": True}},
        "banned": {"banned": True}
    }
    users = users_collection.find(query_map[data])
    text = "\n".join([f"`{u['_id']}`" for u in users]) or "No users found."
    await event.edit(f"**{data.capitalize()} Users:**\n{text}")

@telegram_client.on(events.NewMessage(pattern='/help'))
async def help_command(event):
    if event.sender_id != OWNER_ID or event.is_group or event.is_channel:
        return
    await event.reply("""
**UserBot Admin Help**
Available commands:
/approve – Reply to approve a user.
/unapprove – Reply to unapprove a user.
/ban – Reply to ban a user.
/unban <id or username> – Unban a user.
/status – View all user statuses.
/help – This message.
    """.strip(), parse_mode="md")

# Start
logger.info("Starting userbot...")
telegram_client.start()
telegram_client.run_until_disconnected()