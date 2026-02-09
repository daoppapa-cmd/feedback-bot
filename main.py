import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from flask import Flask
import threading

# --- CONFIGURATION (នឹងទាញពី Render ពេលក្រោយ) ---
TOKEN = os.getenv("TOKEN") 
ADMIN_GROUP_ID = os.getenv("ADMIN_GROUP_ID")

# --- LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- BOT LOGIC ---

# 1. ពេល User ឆាតមក -> Forward ទៅ Admin Group
async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != int(ADMIN_GROUP_ID):
        # Forward សារទៅ Admin Group
        await context.bot.forward_message(
            chat_id=ADMIN_GROUP_ID,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )

# 2. ពេល Admin Reply ក្នុង Group -> Copy ផ្ញើទៅ User វិញ
async def reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ពិនិត្យថាជាការ Reply ក្នុង Group ដែរឬទេ?
    if update.effective_chat.id == int(ADMIN_GROUP_ID) and update.message.reply_to_message:
        try:
            # ចាប់យក User ID ពីសារដើមដែលបាន Forward
            # ចំណាំ: User ខ្លះបិទ Privacy មិនឱ្យឃើញ Forward អាចនឹងបរាជ័យត្រង់នេះ
            original_msg = update.message.reply_to_message
            
            if original_msg.forward_origin:
                 # សម្រាប់ Python-Telegram-Bot v20+
                 if hasattr(original_msg.forward_origin, 'sender_user'):
                    user_id = original_msg.forward_origin.sender_user.id
                    
                    # Copy សាររបស់ Admin ផ្ញើទៅ User វិញ
                    await context.bot.copy_message(
                        chat_id=user_id,
                        from_chat_id=update.effective_chat.id,
                        message_id=update.message.message_id
                    )
            else:
                 pass # បើរក User មិនឃើញ (ដោយសារ Privacy)
                 
        except Exception as e:
            print(f"Error sending message: {e}")

# --- WEB SERVER (ដើម្បីឱ្យ Render ដើររហូត) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    # Run លើ Port 10000 (Render ចូលចិត្ត Port នេះ)
    app.run(host="0.0.0.0", port=10000)

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    # ដំណើរការ Flask ក្នុង Thread មួយផ្សេងទៀត
    threading.Thread(target=run_flask).start()
    
    # ដំណើរការ Bot
    application = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    # ចាប់យកសារទាំងអស់ដែលមិនមែនជា Command
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), forward_to_admin)
    # ចាប់យកការ Reply របស់ Admin
    reply_handler = MessageHandler(filters.Reply, reply_to_user)

    application.add_handler(echo_handler)
    application.add_handler(reply_handler)

    print("Bot started...")
    application.run_polling()
