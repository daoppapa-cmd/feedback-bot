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

# --- WEB SERVER (ដើម្បីឱ្យ Render ដើររហូត) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running perfectly!"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

# --- BOT LOGIC ---

# 1. ផ្នែក User ផ្ញើមក (Support គ្រប់ប្រភេទ file)
async def handle_incoming_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # សំខាន់៖ ទទួលយកតែសារដែលផ្ញើពី Private Chat (១ ទល់ ១) ប៉ុណ្ណោះ
    # ដើម្បីកុំឱ្យច្រឡំសាររបស់ Admin ក្នុង Group
    if update.effective_chat.type == "private":
        try:
            # Forward គ្រប់យ៉ាង (Text, Photo, Video...) ទៅកាន់ Admin Group
            await context.bot.forward_message(
                chat_id=ADMIN_GROUP_ID,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
        except Exception as e:
            logging.error(f"Error forwarding message: {e}")

# 2. ផ្នែក Admin Reply ទៅវិញ (Support គ្រប់ប្រភេទ file)
async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ធ្វើការតែនៅពេល៖ នៅក្នុង Group Admin + មានការ Reply លើសារគេ
    if str(update.effective_chat.id) == str(ADMIN_GROUP_ID) and update.message.reply_to_message:
        try:
            # ជំហានទី ១: រកមើល User ID របស់ម្ចាស់សារដើម
            original_msg = update.message.reply_to_message
            user_id = None

            # ករណីទី ១: User ធម្មតា (បើក Privacy ឱ្យឃើញ Profile)
            if original_msg.forward_from:
                user_id = original_msg.forward_from.id
            
            # ករណីទី ២: សាកល្បងរកតាមវិធីថ្មី (សម្រាប់ Telegram update ថ្មី)
            elif original_msg.forward_origin:
                if hasattr(original_msg.forward_origin, 'sender_user'):
                    user_id = original_msg.forward_origin.sender_user.id

            # ជំហានទី ២: ផ្ញើត្រឡប់ទៅ User វិញ
            if user_id:
                # ប្រើ copy_message គឺវាចម្លងទាំងរូប ទាំងសំឡេង ទាំងអក្សរ ដូច Admin ផ្ញើ ១០០%
                await context.bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=update.effective_chat.id,
                    message_id=update.message.message_id
                )
            else:
                # ករណី User បិទ Privacy (Forwarded Messages = Nobody)
                # យើងត្រូវប្រាប់ Admin ឱ្យដឹងថា Reply អត់ទៅទេ
                await update.message.reply_text(
                    "⚠️ **បរាជ័យ!**\n\n"
                    "User ម្នាក់នេះបានបិទ Privacy (Who can see my forwarded messages = Nobody)។\n"
                    "ដូច្នេះ Bot មិនអាចស្គាល់ ID របស់គាត់ដើម្បី Reply ទេ។"
                )

        except Exception as e:
            logging.error(f"Error replying: {e}")

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    # ដំណើរការ Web Server
    threading.Thread(target=run_flask).start()
    
    # ដំណើរការ Bot
    if not TOKEN or not ADMIN_GROUP_ID:
        print("Error: ភ្លេចដាក់ TOKEN ឬ ADMIN_GROUP_ID ក្នុង Environment Variables")
    else:
        application = ApplicationBuilder().token(TOKEN).build()

        # HANDLER 1: សម្រាប់ User (ប្រើ filters.ChatType.PRIVATE សំខាន់ណាស់!)
        # filters.ALL មានន័យថាចាប់យកទាំង Text, Photo, Video, Voice...
        user_handler = MessageHandler(filters.ChatType.PRIVATE & (~filters.COMMAND), handle_incoming_message)
        
        # HANDLER 2: សម្រាប់ Admin Reply ក្នុង Group
        admin_reply_handler = MessageHandler(filters.ChatType.GROUPS & filters.REPLY, handle_admin_reply)

        application.add_handler(user_handler)
        application.add_handler(admin_reply_handler)

        print("Bot started...")
        application.run_polling()
