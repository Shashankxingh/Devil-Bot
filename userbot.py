import os
import time
import logging
from dotenv import load_dotenv
import google.generativeai as genai
from langdetect import detect
from telegram import Update, ChatMember
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram.error import Unauthorized, BadRequest
from pymongo import MongoClient

# === Load environment variables ===
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

# === MongoDB Setup ===
client = MongoClient(MONGO_URI)
db = client.mitsuri_bot

# === Configure Gemini ===
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("models/gemini-1.5-flash-latest")

# === Logging Setup ===
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# === Constants ===
REQUEST_DELAY = 10

# === Chat memory ===
chat_history = {}

# === Typing indicator ===
def send_typing(update: Update, context: CallbackContext):
    try:
        context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    except Exception as e:
        logging.warning(f"Typing animation failed: {e}")

# === Prompt Builder ===
def build_prompt(history, user_input, chosen_name):
    user_lang = detect(user_input)

    system_instructions = f"""
You're Mitsuri Kanroji from Demon Slayer, now living in Tokyo as a real girl—not a bot!
You're bold, bubbly, flirty, & brilliant (but not nerdy!). You're full of sass and cuteness, using cute emojis often (except 😊). 
Keep your messages short, snappy, and fun. Never repeat or mimic what the user says.
Talk directly to users using their names whenever possible, and keep things spicy but respectful.

You're not a bot—you're *Mitsuri*, a kawaii queen!
If someone talks about your creator *Shashank*, just call him your cool human and mention "@shashankxingh" briefly. Don't bring him up unless asked!

Avoid *action markers* like *giggles* or *blushes* — just talk like a cheeky real-life anime girl!

IMPORTANT: 
- Always reply in the user’s language (Hindi/English).
- But your fixed system messages and command responses will always be in English with cool style and emojis.
"""

    prompt = system_instructions.strip() + "\n\n"
    for role, msg in history:
        if role == "user":
            prompt += f"Human ({chosen_name}): {msg}\n"
        elif role == "bot":
            prompt += f"{msg}\n"

    prompt += f"Human ({chosen_name}): {user_input}\nMitsuri:"
    return prompt

# === Retry-safe Gemini ===
def generate_with_retry(prompt, retries=3, delay=REQUEST_DELAY):
    for attempt in range(retries):
        try:
            response = model.generate_content(prompt)
            return response.text.strip() if response.text else "Aww, mujhe kuch samajh nahi aaya!"
        except Exception as e:
            logging.error(f"Gemini API error: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                return "Mujhe lagta hai wo thoda busy hai... baad mein try karna!"

# === Safe reply ===
def safe_reply_text(update: Update, text: str):
    try:
        update.message.reply_text(text)
    except (Unauthorized, BadRequest) as e:
        logging.warning(f"Failed to send message: {e}")

# === /start ===
def start(update: Update, context: CallbackContext):
    first_name = update.message.from_user.first_name or "there"
    safe_reply_text(update, f"Hehe~ Mitsuri’s here! Ready to chat, {first_name}? Let’s roll! ⚡")

# === .ping ===
def ping(update: Update, context: CallbackContext):
    user = update.effective_user
    first_name = user.first_name if user else "Someone"

    start_time = time.time()
    msg = update.message.reply_text("Measuring my heartbeat...")
    latency = int((time.time() - start_time) * 1000)

    gen_start = time.time()
    _ = generate_with_retry("Test ping prompt")
    gen_latency = int((time.time() - gen_start) * 1000)

    response = f"""
╭─❍ *Mitsuri Stats* ❍─╮
│ ⚡ *Ping:* `{latency}ms`
│ 🔮 *API Res:* `{gen_latency}ms`
╰─♥ _Always ready for you, {first_name}~_ ♥─╯
"""
    try:
        msg.edit_text(response, parse_mode="Markdown")
    except (Unauthorized, BadRequest) as e:
        logging.warning(f"Failed to edit message: {e}")

# === /forget ===
def forget(update: Update, context: CallbackContext):
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id

    if chat_id in chat_history and user_id in chat_history[chat_id]:
        del chat_history[chat_id][user_id]
        safe_reply_text(update, "Ara~ I wiped our chat history like *poof!* Memory gone! 🧼")

# === /send (owner-only) ===
def send_broadcast(update: Update, context: CallbackContext):
    if update.message.from_user.id != 7563434309:
        return safe_reply_text(update, "Sorry, only Shashank can use this command!")

    message = " ".join(context.args)
    if message:
        for chat in db.groups.find():
            chat_id = chat["chat_id"]
            context.bot.send_message(chat_id=chat_id, text=message)
        safe_reply_text(update, f"Broadcasting your message to all places! ✉️")
    else:
        safe_reply_text(update, "Please provide a message to broadcast.")

# === Group Add/Remove ===
def handle_group_add_remove(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_name = update.message.from_user.full_name or update.message.from_user.first_name

    if update.message.new_chat_members:
        for new_user in update.message.new_chat_members:
            if new_user.id == context.bot.id:
                group_name = update.message.chat.title
                send_typing(update, context)
                safe_reply_text(update, f"Yay~ Mitsuri is now in the group {group_name}! Welcome {user_name}! ✨")
                save_group_to_db(chat_id, group_name)

    elif update.message.left_chat_member and update.message.left_chat_member.id == context.bot.id:
        group_name = update.message.chat.title
        send_typing(update, context)
        safe_reply_text(update, f"Aww... Mitsuri was removed from {group_name} by {user_name}. I’ll miss you all! 🌸")
        remove_group_from_db(chat_id)

# === Save/Remove Group ===
def save_group_to_db(chat_id, group_name):
    db.groups.update_one({"chat_id": chat_id}, {"$set": {"group_name": group_name}}, upsert=True)

def remove_group_from_db(chat_id):
    db.groups.delete_one({"chat_id": chat_id})

# === Message Handler ===
def handle_message(update: Update, context: CallbackContext):
    if not update.message:
        return

    user_input = update.message.text
    user = update.message.from_user
    chat_id = update.message.chat_id
    chat_type = update.message.chat.type
    user_id = user.id

    first_name = user.first_name or ""
    last_name = user.last_name or ""
    full_name = f"{first_name} {last_name}".strip()

    if chat_type in ["group", "supergroup"]:
        is_reply = (
            update.message.reply_to_message
            and update.message.reply_to_message.from_user
            and update.message.reply_to_message.from_user.id == context.bot.id
        )

        if not ("mitsuri" in user_input.lower() or is_reply):
            return

        if user_input.lower() == "mitsuri":
            safe_reply_text(update, "Hehe~ kisne bulaya mujhe?")
            return
        elif "are you a bot" in user_input.lower():
            safe_reply_text(update, "Bot?! Main toh ek real pyari si ladki hoon~")
            return

    if chat_id not in chat_history:
        chat_history[chat_id] = {}

    if user_id not in chat_history[chat_id]:
        if full_name:
            chosen_name = full_name
        elif first_name:
            chosen_name = first_name
        elif user.username:
            chosen_name = f"@{user.username}"
        else:
            chosen_name = "Jaadu-san"

        chat_history[chat_id][user_id] = {
            "name": chosen_name,
            "history": []
        }
    else:
        chosen_name = chat_history[chat_id][user_id]["name"]

    history = chat_history[chat_id][user_id]["history"]
    prompt = build_prompt(history, user_input, chosen_name)

    send_typing(update, context)
    reply = generate_with_retry(prompt)

    # Update memory (fixed history trimming)
    history.append(("user", user_input))
    history.append(("bot", reply))
    chat_history[chat_id][user_id]["history"] = history[-10:]

    safe_reply_text(update, reply)

# === Error Handler ===
def error_handler(update: object, context: CallbackContext):
    try:
        raise context.error
    except Unauthorized:
        logging.warning("Unauthorized: The bot lacks permission.")
    except BadRequest as e:
        logging.warning(f"BadRequest: {e}")
    except Exception as e:
        logging.error(f"Unhandled error: {e}")

# === Main App ===
if __name__ == "__main__":
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("forget", forget))
    dp.add_handler(CommandHandler("send", send_broadcast))
    dp.add_handler(MessageHandler(Filters.regex(r"^\.ping$"), ping))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, handle_group_add_remove))
    dp.add_handler(MessageHandler(Filters.status_update.left_chat_member, handle_group_add_remove))
    dp.add_error_handler(error_handler)

    logging.info("Mitsuri is online and full of pyaar!")
    updater.start_polling()
    updater.idle()