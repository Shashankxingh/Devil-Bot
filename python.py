import os
from dotenv import load_dotenv
from telegram import Update, ChatMemberOwner, ChatMemberAdministrator
from telegram.ext import Application, CommandHandler, CallbackContext

# Load environment variables (for local testing, ignored in Koyeb)
load_dotenv()

# 🔥 Fetch bot token securely from environment variables 🔥
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("🔥 BOT_TOKEN is missing! Check your Koyeb environment variables. 🔥")

async def is_admin_with_promotion_rights(context: CallbackContext, chat_id: int, user_id: int) -> bool:
    """Check if the mortal is worthy of power... or doomed to servitude."""
    member = await context.bot.get_chat_member(chat_id, user_id)
    
    if isinstance(member, ChatMemberOwner):
        return True
    elif isinstance(member, ChatMemberAdministrator) and member.can_promote_members:
        return True
    return False

async def promote(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.message.from_user.id  # The fool who dared summon me

    if not await is_admin_with_promotion_rights(context, chat_id, user_id):  
        await update.message.reply_text("🤣 You dare command me? Insolent worm!")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Hah! Even you are confused in my domain! 😈")
        return

    target_user_id = update.message.reply_to_message.from_user.id
    title = " ".join(context.args) if context.args else "Demonic Underling"
    
    try:
        # 🔥 Grant them cursed power 🔥
        await context.bot.promote_chat_member(
            chat_id,
            target_user_id,
            can_manage_chat=True,
            can_delete_messages=True,
            can_restrict_members=True,
            can_promote_members=False
        )
        
        # 🔥 Mark them with a devilish title 🔥
        await context.bot.set_chat_administrator_custom_title(chat_id, target_user_id, title)
        
        await update.message.reply_text(f"Ah, {update.message.reply_to_message.from_user.first_name}... You have escaped my torment... for now. 🔥😈")
    except Exception as e:
        await update.message.reply_text(f"Tch... The ritual failed! 🩸 {e}")

async def demote(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.message.from_user.id  

    if not await is_admin_with_promotion_rights(context, chat_id, user_id):  
        await update.message.reply_text("Foolish mortal! You have no power here! 🤡")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Lost already? Weakling. 😏")
        return

    target_user_id = update.message.reply_to_message.from_user.id
    
    try:
        # 🔥 Strip them of their unholy power 🔥
        await context.bot.promote_chat_member(
            chat_id,
            target_user_id,
            can_manage_chat=False,
            can_delete_messages=False,
            can_restrict_members=False,
            can_promote_members=False
        )
        await update.message.reply_text(f"Pathetic {update.message.reply_to_message.from_user.first_name}... You thought you were safe? Now, you are mine again. 😈")
    except Exception as e:
        await update.message.reply_text(f"Something interferes... a holy force? ⚡ {e}")

def main():
    app = Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()  # Faster than your soul's descent into hell

    app.add_handler(CommandHandler("promote", promote))
    app.add_handler(CommandHandler("demote", demote))
    
    print("🔥 The devil awakens... 🔥")
    app.run_polling()

if __name__ == "__main__":
    main()
