import os
import logging
from dotenv import load_dotenv
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from pymongo import MongoClient

# Load env vars
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection
MONGO_URI = os.getenv('MONGO_URI')
mongo_client = MongoClient(MONGO_URI)
db = mongo_client['telegram_userbot']
users_collection = db['users']

# Telegram credentials
api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')
session_string = os.getenv('SESSION_STRING')
OWNER_ID = int(os.getenv('OWNER_ID'))

# Initialize client
telegram_client = TelegramClient(StringSession(session_string), api_id, api_hash)

# --- Main message handler ---
@telegram_client.on(events.NewMessage(incoming=True))
async def handler(event):
    if event.is_group or event.is_channel:
        return

    sender = event.sender_id
    user = users_collection.find_one({"_id": sender})

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
                    await event.delete()
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
                    await event.delete()
            else:
                users_collection.update_one({"_id": sender}, {"$inc": {"messages": 1}})
        else:
            await event.reply("You are blocked for sending unsupported content!")
            users_collection.update_one({"_id": sender}, {"$set": {"approved": False, "banned": True}})
            await event.delete()

async def send_warning(event, sender, remaining_warnings):
    await event.reply(f"Warning {5 - remaining_warnings}/5: You have {remaining_warnings} warnings left.")
    users_collection.update_one({"_id": sender}, {"$set": {"warnings": remaining_warnings}})

# --- Admin commands ---
@telegram_client.on(events.NewMessage(pattern='/approve'))
async def approve_user(event):
    if event.sender_id != OWNER_ID:
        return
    users_collection.update_one({"_id": event.sender_id}, {"$set": {"approved": True, "banned": False}})
    await event.reply(f"User {event.sender_id} approved.")

@telegram_client.on(events.NewMessage(pattern='/unapprove'))
async def unapprove_user(event):
    if event.sender_id != OWNER_ID:
        return
    users_collection.update_one({"_id": event.sender_id}, {"$set": {"approved": False}})
    await event.reply(f"User {event.sender_id} unapproved.")

@telegram_client.on(events.NewMessage(pattern='/ban'))
async def ban_user(event):
    if event.sender_id != OWNER_ID:
        return
    users_collection.update_one({"_id": event.sender_id}, {"$set": {"approved": False, "banned": True}})
    await event.reply(f"User {event.sender_id} has been banned.")

# --- Unban Command ---
@telegram_client.on(events.NewMessage(pattern=r'/unban(?:\s+(.+))?'))
async def unban_user(event):
    if event.sender_id != OWNER_ID:
        return

    args = event.pattern_match.group(1)
    if not args:
        await event.reply("Usage: `/unban <username or user_id>`", parse_mode="md")
        return

    try:
        if args.isdigit():
            user_id = int(args)
        else:
            user = await telegram_client.get_entity(args)
            user_id = user.id

        result = users_collection.update_one({"_id": user_id}, {"$set": {"banned": False}})
        if result.modified_count:
            await event.reply(f"✅ User `{user_id}` has been unbanned.", parse_mode="md")
        else:
            await event.reply(f"No banned user found with ID `{user_id}`.", parse_mode="md")

    except Exception as e:
        await event.reply(f"Error: {str(e)}")

# --- Status menu and buttons ---
@telegram_client.on(events.NewMessage(pattern='/status'))
async def status_menu(event):
    if event.sender_id != OWNER_ID:
        return
    buttons = [
        [Button.inline("✅ Approved", data=b"approved")],
        [Button.inline("❌ Unapproved", data=b"unapproved")],
        [Button.inline("⛔ Banned", data=b"banned")]
    ]
    await event.respond("Select a category to view users:", buttons=buttons)

@telegram_client.on(events.CallbackQuery)
async def handle_callback(event):
    data = event.data.decode("utf-8")
    if event.sender_id != OWNER_ID:
        await event.answer("You're not allowed.", alert=True)
        return

    if data == "approved":
        users = users_collection.find({"approved": True})
        text = "\n".join([f"`{u['_id']}`" for u in users]) or "No approved users."
        await event.edit(f"✅ **Approved Users:**\n{text}")

    elif data == "unapproved":
        users = users_collection.find({"approved": False, "banned": {"$ne": True}})
        text = "\n".join([f"`{u['_id']}`" for u in users]) or "No unapproved users."
        await event.edit(f"❌ **Unapproved Users:**\n{text}")

    elif data == "banned":
        users = users_collection.find({"banned": True})
        text = "\n".join([f"`{u['_id']}`" for u in users]) or "No banned users."
        await event.edit(f"⛔ **Banned Users:**\n{text}")

# --- Start bot ---
logger.info("Starting userbot...")
telegram_client.start()
telegram_client.run_until_disconnected()
