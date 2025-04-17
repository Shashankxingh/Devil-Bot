import os
from dotenv import load_dotenv
from telethon import TelegramClient, events
from pymongo import MongoClient

# Load environment variables from .env file
load_dotenv()

# MongoDB connection setup
MONGO_URI = os.getenv('MONGO_URI')
client = MongoClient(MONGO_URI)
db = client['telegram_userbot']
users_collection = db['users']

# Telegram credentials from .env file
api_id = int(os.getenv('API_ID'))  # Replace with your API ID from Telegram Developer Portal
api_hash = os.getenv('API_HASH')  # Replace with your API Hash from Telegram Developer Portal

# Initialize the Telegram client (Userbot)
telegram_client = TelegramClient('userbot', api_id, api_hash)

# Helper function to send warnings
async def send_warning(event, sender, remaining_warnings):
    await event.reply(f"Warning {5 - remaining_warnings}/5: You have {remaining_warnings} warnings left.")
    users_collection.update_one({"_id": sender}, {"$set": {"warnings": remaining_warnings}})

# Function to handle new messages
@telegram_client.on(events.NewMessage(incoming=True))
async def handler(event):
    sender = event.sender_id
    user = users_collection.find_one({"_id": sender})

    # If the user is not found in the database (unknown user)
    if not user:
        users_collection.insert_one({"_id": sender, "messages": 1, "warnings": 5, "approved": False})
        await event.reply("You've sent your first message. I need your approval to continue.")
    else:
        if user["approved"]:
            # User is approved, allow them to send unlimited messages
            pass
        else:
            # Check if the user sent a sticker or text message
            if event.is_reply:
                return  # Ignore replies to messages, as these are not new messages.

            if event.text:  # Regular text message
                if user["messages"] > 1:
                    await event.delete()
                    remaining_warnings = user["warnings"]
                    if remaining_warnings > 1:
                        await send_warning(event, sender, remaining_warnings - 1)
                    else:
                        # Block the user if they exceed the warning limit
                        await event.reply("You are blocked for violating the message limit!")
                        users_collection.update_one({"_id": sender}, {"$set": {"approved": False}})
                        await event.delete()
                else:
                    # Update the number of messages the user sent
                    users_collection.update_one({"_id": sender}, {"$set": {"messages": user["messages"] + 1}})

            elif event.sticker:  # Sticker message
                if user["messages"] > 2:
                    await event.delete()
                    remaining_warnings = user["warnings"]
                    if remaining_warnings > 1:
                        await send_warning(event, sender, remaining_warnings - 1)
                    else:
                        # Block the user if they exceed the warning limit
                        await event.reply("You are blocked for violating the sticker limit!")
                        users_collection.update_one({"_id": sender}, {"$set": {"approved": False}})
                        await event.delete()
                else:
                    # Update the number of messages the user sent
                    users_collection.update_one({"_id": sender}, {"$set": {"messages": user["messages"] + 1}})

            else:  # If the message is neither text nor a sticker (e.g., photo, link)
                await event.delete()
                await event.reply("You are blocked for sending unsupported content!")
                users_collection.update_one({"_id": sender}, {"$set": {"approved": False}})
                await event.delete()

# Command to approve the user
@telegram_client.on(events.NewMessage(pattern='/approve'))
async def approve_user(event):
    sender = event.sender_id
    user = users_collection.find_one({"_id": sender})

    if user:
        users_collection.update_one({"_id": sender}, {"$set": {"approved": True}})
        await event.reply(f"User {sender} has been approved.")
    else:
        await event.reply(f"No such user {sender} to approve!")

# Command to unapprove the user
@telegram_client.on(events.NewMessage(pattern='/unapprove'))
async def unapprove_user(event):
    sender = event.sender_id
    user = users_collection.find_one({"_id": sender})

    if user:
        users_collection.update_one({"_id": sender}, {"$set": {"approved": False}})
        await event.reply(f"User {sender} has been unapproved.")
    else:
        await event.reply(f"No such user {sender} to unapprove!")

# Command to ban the user
@telegram_client.on(events.NewMessage(pattern='/ban'))
async def ban_user(event):
    sender = event.sender_id
    user = users_collection.find_one({"_id": sender})

    if user:
        users_collection.update_one({"_id": sender}, {"$set": {"approved": False}})
        await event.reply(f"User {sender} has been banned and will no longer be able to message.")
    else:
        await event.reply(f"No such user {sender} to ban!")

# Start the bot
telegram_client.start()  # This will handle phone number and OTP prompt automatically on first run
telegram_client.run_until_disconnected()