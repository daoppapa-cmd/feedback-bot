import os
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- CONFIGURATION ---
TOKEN = os.getenv("TOKEN")
ADMIN_GROUP_ID = os.getenv("ADMIN_GROUP_ID")

# --- LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- WEB SERVER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running perfectly!"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

# --- BOT LOGIC ---

# 1. មុខងារសម្រាប់ USER (ដំណើរការតែក្នុង Private Chat ប៉ុណ្ណោះ)
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Logic: គ្រាន់តែ Forward ទៅ Admin Group
    try:
        await context.bot.forward_message(
            chat_id=ADMIN_GROUP_ID,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
    except Exception as e:
        logging.error(f"Error forwarding to admin: {e}")

# 2. មុខងារសម្រាប់ ADMIN (ដំណើរការតែក្នុង Group ប៉ុណ្ណោះ)
async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Logic: ពិនិត្យមើលថាតើ Admin កំពុង Reply ដាក់សាររបស់ Bot ឬអត់?
    
    # Check 1: ត្រូវតែជា Reply
    if not update.message.reply_to_message:
        return

    # Check 2: សារដែល Admin Reply នោះ ត្រូវតែជាសារដែលផ្ញើដោយ Bot (Forwarded Message)
    original_msg = update.message.reply_to_message
    if original_msg.from_user.id != context.bot.id:
        return

    # ចាប់ផ្តើមដំណើរការផ្ញើទៅ User
    try:
        user_id = None

        # ព្យាយាមរក User ID ពីសារដែលបាន Forward
        if original_msg.forward_from:
            user_id = original_msg.forward_from.id
        elif original_msg.forward_origin:
             # សម្រាប់ Telegram Update ថ្មី
            if hasattr(original_msg.forward_origin, 'sender_user'):
                user_id = original_msg.forward_origin.sender_user.id

        # បើរកឃើញ User ID -> Copy សារ Admin ផ្ញើទៅ User នោះ
        if user_id:
            await context.bot.copy_message(
                chat_id=user_id,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
            # (Optional) ដាក់ Reaction ឱ្យ Admin ដឹងថាផ្ញើបានជោគជ័យ
            # await update.message.set_reaction(reaction="👍")
        else:
            # បើ User បិទ Privacy រក ID មិនឃើញ
            await update.message.reply_text("⚠️ រក User ID មិនឃើញ (គាត់បិទ Privacy)។")

    except Exception as e:
        logging.error(f"Error replying to user: {e}")

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    
    if not TOKEN or not ADMIN_GROUP_ID:
        print("Error: Please set TOKEN and ADMIN_GROUP_ID")
    else:
        application = ApplicationBuilder().token(TOKEN).build()

        # --- IMPORTANT: FILTERS (កន្លែងសំខាន់បំផុត) ---
        
        # 1. User Filter: ចាប់យកតែសារ Private Chat (ហាមចាប់ Group)
        # filters.ChatType.PRIVATE = តែសារ ១ ទល់ ១
        user_filter = filters.ChatType.PRIVATE & (~filters.COMMAND)
        user_handler = MessageHandler(user_filter, handle_user_message)

        # 2. Admin Filter: ចាប់យកតែសារក្នុង Group ដែលមាន Reply
        # filters.ChatType.GROUPS = តែក្នុង Group
        admin_filter = filters.ChatType.GROUPS & filters.REPLY
        admin_handler = MessageHandler(admin_filter, handle_admin_reply)

        application.add_handler(user_handler)
        application.add_handler(admin_handler)

        print("Bot started with Strict Filters...")
        application.run_polling()
