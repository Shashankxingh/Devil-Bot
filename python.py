import random
import os
from dotenv import load_dotenv
from telegram import Update, ChatMemberOwner, ChatMemberAdministrator
from telegram.ext import Application, CommandHandler, CallbackContext

load_dotenv()

# 🚨 Keep this token secret! If leaked, regenerate via @BotFather 🚨
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing from .env file!")

# 🔥 Overlord’s Responses 🔥

PROMOTE_MESSAGES = [
    "You have been granted a mere fraction of my power. Serve well, or vanish.",
    "Consider yourself fortunate. Authority is a gift, but it can be taken.",
    "Even the weak may rise… but do not mistake this for mercy.",
    "This power is temporary. Fail, and you will be erased."
]

DEMOTE_MESSAGES = [
    "You have failed. Your title is stripped, and your worth is gone.",
    "I have no use for the weak. Step aside.",
    "Disappointing. You were given a chance, and yet, you fell.",
    "Power is not for everyone. You are proof of that."
]

DENIED_MESSAGES = [
    "You… a mere insect… believe you can command me? How amusing.",
    "You hold no authority here. Do not speak of things beyond your reach.",
    "Pathetic. You lack power, yet you dare to order me?",
    "You are unworthy. Do not waste my time with your foolishness."
]

MISSING_REPLY_MESSAGES = [
    "Did your tiny mind forget to mention who should receive this power?",
    "I cannot promote a ghost. Speak properly, or not at all.",
    "Fool. If you cannot name a subordinate, how do you expect to command anyone?",
    "Your incompetence is irritating. Mention the one who shall receive power."
]

MISSING_REPLY_DEMOTE = [
    "Who am I to demote? Speak clearly, or remain silent forever.",
    "Are you too weak to even point out your failure? Name them, or be gone.",
    "I do not play games. If you cannot follow simple commands, do not waste my time.",
    "You wish to strip someone of their title, yet you hesitate? Pathetic."
]

RANDOM_TITLES = [
    "Shadow Enforcer",
    "Harbinger of Order",
    "The Unseen Hand",
    "Master of the Dominion",
    "Keeper of Silence"
]

async def is_admin_with_promotion_rights(context: CallbackContext, chat_id: int, user_id: int) -> bool:
    """Check if the mortal is worthy of power... or doomed to servitude."""
    member = await context.bot.get_chat_member(chat_id, user_id)
    return isinstance(member, ChatMemberOwner) or (isinstance(member, ChatMemberAdministrator) and member.can_promote_members)

async def promote(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.message.from_user.id  

    if not await is_admin_with_promotion_rights(context, chat_id, user_id):  
        await update.message.reply_text(random.choice(DENIED_MESSAGES))
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(random.choice(MISSING_REPLY_MESSAGES))
        return

    target_user_id = update.message.reply_to_message.from_user.id
    title = " ".join(context.args) if context.args else random.choice(RANDOM_TITLES)  

    try:
        await context.bot.promote_chat_member(
            chat_id,
            target_user_id,
            can_manage_chat=True,
            can_delete_messages=True,
            can_restrict_members=True,
            can_promote_members=False
        )
        await context.bot.set_chat_administrator_custom_title(chat_id, target_user_id, title)
        
        await update.message.reply_text(random.choice(PROMOTE_MESSAGES))
    except Exception as e:
        print(f"Promotion Error: {e}")
        await update.message.reply_text("Something interferes… but nothing escapes my grasp forever. This failure will be corrected.")

async def demote(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.message.from_user.id  

    if not await is_admin_with_promotion_rights(context, chat_id, user_id):  
        await update.message.reply_text(random.choice(DENIED_MESSAGES))
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(random.choice(MISSING_REPLY_DEMOTE))
        return

    target_user_id = update.message.reply_to_message.from_user.id
    
    try:
        await context.bot.promote_chat_member(
            chat_id,
            target_user_id,
            can_manage_chat=False,
            can_delete_messages=False,
            can_restrict_members=False,
            can_promote_members=False
        )
        await update.message.reply_text(random.choice(DEMOTE_MESSAGES))
    except Exception as e:
        print(f"Demotion Error: {e}")
        await update.message.reply_text("A disturbance… but ultimately meaningless. Your power has been revoked.")

def main():
    app = Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()

    app.add_handler(CommandHandler("promote", promote))
    app.add_handler(CommandHandler("demote", demote))
    
    print("👁️ The unseen force has awakened… 👁️")
    app.run_polling()

if __name__ == "__main__":
    main()
