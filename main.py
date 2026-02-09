import os
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# --- CONFIGURATION ---
TOKEN = os.getenv("TOKEN")
ADMIN_GROUP_ID = os.getenv("ADMIN_GROUP_ID")

# --- LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- WEB SERVER (Keep Render Awake) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running perfectly!"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

# --- BOT LOGIC ---

# 1. មុខងារសម្រាប់ពាក្យ /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ឆ្លើយតបសារស្វាគមន៍ភ្លាមៗ
    await update.message.reply_text("ជម្រាបសួរ🙏! តើលោកអ្នកមានអ្វីឱ្យខ្ញុំជួយបានទេ? ")

# 2. មុខងារសម្រាប់ USER (ដំណើរការតែក្នុង Private Chat)
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ធ្វើការតែជាមួយ Private Chat (១ ទល់ ១)
    if update.effective_chat.type == "private":
        try:
            # ជំហានទី ១: ដាក់ Reaction បេះដូង ❤️ លើសារ User
            await update.message.set_reaction(reaction="❤️")
            
            # ជំហានទី ២: Forward សារនោះទៅកាន់ Admin Group
            await context.bot.forward_message(
                chat_id=ADMIN_GROUP_ID,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
        except Exception as e:
            logging.error(f"Error handling user message: {e}")

# 3. មុខងារសម្រាប់ ADMIN (ដំណើរការតែក្នុង Group)
async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ពិនិត្យមើល៖ ត្រូវតែនៅក្នុង Group Admin + មានការ Reply + Reply ដាក់សារ Bot
    if str(update.effective_chat.id) == str(ADMIN_GROUP_ID) and update.message.reply_to_message:
        
        # ការពារកុំឱ្យ Bot Reply ដាក់ខ្លួនឯង ឬដាក់ User ផ្សេងក្នុង Group
        original_msg = update.message.reply_to_message
        if original_msg.from_user.id != context.bot.id:
            return

        try:
            user_id = None
            # ព្យាយាមរក User ID ពីសារដែលបាន Forward
            if original_msg.forward_from:
                user_id = original_msg.forward_from.id
            elif original_msg.forward_origin:
                if hasattr(original_msg.forward_origin, 'sender_user'):
                    user_id = original_msg.forward_origin.sender_user.id

            # បើរកឃើញ User ID -> Copy សារ Admin ផ្ញើទៅ User វិញ
            if user_id:
                await context.bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=update.effective_chat.id,
                    message_id=update.message.message_id
                )
            else:
                await update.message.reply_text("⚠️ រក User ID មិនឃើញ (គាត់បិទ Privacy Forward)។")

        except Exception as e:
            logging.error(f"Error replying to user: {e}")

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    
    if not TOKEN or not ADMIN_GROUP_ID:
        print("Error: Please set TOKEN and ADMIN_GROUP_ID")
    else:
        application = ApplicationBuilder().token(TOKEN).build()

        # --- HANDLERS ---
        
        # 1. Start Command Handler (ដាក់មុនគេ)
        start_handler = CommandHandler("start", start_command)
        application.add_handler(start_handler)

        # 2. User Message Handler (Private Only, No Commands)
        # filters.ALL = ចាប់យកគ្រប់យ៉ាង (Text, Photo, Video, Voice...)
        user_filter = filters.ChatType.PRIVATE & (~filters.COMMAND)
        user_handler = MessageHandler(user_filter, handle_user_message)
        application.add_handler(user_handler)

        # 3. Admin Reply Handler (Group Only)
        admin_filter = filters.ChatType.GROUPS & filters.REPLY
        admin_handler = MessageHandler(admin_filter, handle_admin_reply)
        application.add_handler(admin_handler)

        print("Bot started with Heart Reaction & Start Message...")
        application.run_polling()
