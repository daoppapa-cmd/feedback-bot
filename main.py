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

# 1. ពេល User ចុច /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ជម្រាបសួរ🙏! តើលោកអ្នកមានអ្វីឱ្យខ្ញុំជួយបានទេ?")

# 2. ពេល USER ឆាតមក (Private Chat)
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        try:
            # ១. ដាក់ Reaction បេះដូង ❤️
            try:
                await update.message.set_reaction(reaction="❤️")
            except Exception:
                pass # បើដាក់មិនបាន (អ៊ិនធឺណិតគាំង) កុំឱ្យ Error

            # ២. ទាញយកព័ត៌មាន User
            user = update.effective_user
            user_info_text = (
                f"👤 **Name:** {user.first_name} {user.last_name or ''}\n"
                f"🆔 **ID:** `{user.id}`\n"
                f"🔗 **Username:** @{user.username if user.username else 'None'}"
            )

            # ៣. Forward សារទៅ Admin Group
            forwarded_msg = await context.bot.forward_message(
                chat_id=ADMIN_GROUP_ID,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )

            # ៤. Reply លើសារដែលបាន Forward នោះ ដើម្បីប្រាប់ព័ត៌មាន User (ជួយ Admin ងាយស្រួលមើល)
            await context.bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=user_info_text,
                reply_to_message_id=forwarded_msg.message_id,
                parse_mode="Markdown"
            )

        except Exception as e:
            logging.error(f"Error handling user message: {e}")

# 3. ពេល ADMIN Reply (Group Only)
async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # លក្ខខណ្ឌ៖ ក្នុង Group + មាន Reply
    if str(update.effective_chat.id) == str(ADMIN_GROUP_ID) and update.message.reply_to_message:
        
        original_msg = update.message.reply_to_message
        
        # សំខាន់៖ យើងត្រូវ Reply ទៅកាន់សារដែល Bot ជាអ្នកផ្ញើ (Forward)
        if original_msg.from_user.id != context.bot.id:
            return

        try:
            user_id = None
            
            # វិធីទី ១: រក ID តាមរយៈ Forward Header (User ធម្មតា)
            if original_msg.forward_from:
                user_id = original_msg.forward_from.id
            
            # វិធីទី ២: រកតាមរយៈ Forward Origin (សម្រាប់ Telegram ថ្មី)
            elif original_msg.forward_origin:
                if hasattr(original_msg.forward_origin, 'sender_user'):
                    user_id = original_msg.forward_origin.sender_user.id
            
            # វិធីទី ៣ (ពិសេស): បើ Admin ច្រឡំទៅ Reply លើសារ "User Info" ដែល Bot ផ្ញើ
            # យើងអាចចាប់យក ID ពីអត្ថបទសារនោះបាន (ត្រង់កន្លែង `123456`)
            if not user_id and original_msg.text and "ID:" in original_msg.text:
                # នេះជាវិធីសាស្រ្តចាប់យក ID ពីអត្ថបទ (Backup)
                try:
                    lines = original_msg.text.split('\n')
                    for line in lines:
                        if "ID:" in line:
                            user_id = int(line.split('`')[1]) # ទាញយកលេខក្នុងសញ្ញា `...`
                except:
                    pass

            # ផ្ញើសារទៅ User វិញ
            if user_id:
                await context.bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=update.effective_chat.id,
                    message_id=update.message.message_id
                )
                # ដាក់ Reaction ដៃមេ 👍 ឱ្យ Admin ដឹងថាផ្ញើចេញហើយ
                try:
                    await update.message.set_reaction(reaction="👍")
                except:
                    pass
            else:
                await update.message.reply_text(
                    "⚠️ **មិនអាចផ្ញើបាន!**\n"
                    "រកមិនឃើញ User ID (គាត់ប្រហែលជាបិទ Privacy)។"
                )

        except Exception as e:
            logging.error(f"Error replying to user: {e}")

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    
    if not TOKEN or not ADMIN_GROUP_ID:
        print("Error: Please set TOKEN and ADMIN_GROUP_ID")
    else:
        application = ApplicationBuilder().token(TOKEN).build()

        # Handlers
        start_handler = CommandHandler("start", start_command)
        
        # User Handler (Private)
        user_handler = MessageHandler(filters.ChatType.PRIVATE & (~filters.COMMAND), handle_user_message)
        
        # Admin Handler (Group + Reply)
        admin_handler = MessageHandler(filters.ChatType.GROUPS & filters.REPLY, handle_admin_reply)

        application.add_handler(start_handler)
        application.add_handler(user_handler)
        application.add_handler(admin_handler)

        print("Bot started with Reaction, User Info & Admin Reply Fix...")
        application.run_polling()
