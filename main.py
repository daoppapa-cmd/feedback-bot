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

# --- WEB SERVER (Keep Render Awake) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running perfectly!"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

# --- BOT LOGIC ---

# 1. ផ្នែក User ផ្ញើមក (Support គ្រប់ប្រភេទ file)
async def handle_incoming_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # តែងតែ Forward គ្រប់យ៉ាងដែល User ផ្ញើមក (មិនថាអក្សរ រូប ឬសំឡេង)
    # ឆែកមើលថាជា Private Chat (User ឆាតមក Bot) ឬអត់?
    if update.effective_chat.type == "private":
        try:
            await context.bot.forward_message(
                chat_id=ADMIN_GROUP_ID,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
        except Exception as e:
            logging.error(f"Error forwarding message: {e}")

# 2. ផ្នែក Admin Reply ទៅវិញ (Support គ្រប់ប្រភេទ file)
async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ធ្វើការតែនៅពេល៖ នៅក្នុង Group Admin + មានការ Reply
    if str(update.effective_chat.id) == str(ADMIN_GROUP_ID) and update.message.reply_to_message:
        try:
            # ជំហានទី ១: រកមើល User ID របស់ម្ចាស់សារដើម
            original_msg = update.message.reply_to_message
            user_id = None

            # ករណីទី ១: ធម្មតា (ឃើញ ID)
            if original_msg.forward_from:
                user_id = original_msg.forward_from.id
            
            # ករណីទី ២: បើប្រើ Library ថ្មី ឬ Telegram update ថ្មី (Hidden User)
            elif original_msg.forward_origin:
                # ព្យាយាមទាញយក ID ពី forward_origin
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
                await update.message.reply_text(
                    "⚠️ **មិនអាច Reply បានទេ!**\n\n"
                    "User នេះបានកំណត់ Privacy បិទមិនឱ្យគេឃើញ Profile របស់គាត់ពេល Forward។\n"
                    "ដំណោះស្រាយ៖ សូមប្រាប់ User ឱ្យឆាតមកម្ដងទៀត ហើយបើក Privacy ជា Public សិន។"
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

        # Handler សម្រាប់ User (ចាប់យកគ្រប់យ៉ាង មិនមែនតែ Text ទេ)
        # filters.ALL មានន័យថាចាប់ទាំងរូប ទាំងសំឡេង ទាំងអក្សរ
        user_handler = MessageHandler(filters.ChatType.PRIVATE & (~filters.COMMAND), handle_incoming_message)
        
        # Handler សម្រាប់ Admin Reply (ប្រើ filters.REPLY អក្សរធំ)
        admin_reply_handler = MessageHandler(filters.ChatType.GROUPS & filters.REPLY, handle_admin_reply)

        application.add_handler(user_handler)
        application.add_handler(admin_reply_handler)

        print("Bot started...")
        application.run_polling()
