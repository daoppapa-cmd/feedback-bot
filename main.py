import os
import logging
import threading
import time          # <--- សម្រាប់រាប់ម៉ោងពេល Restart
import asyncio       # <--- សម្រាប់គ្រប់គ្រង Async Loop
import re
from flask import Flask
from telegram import Update, ReactionTypeEmoji
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# --- CONFIGURATION ---
TOKEN = os.getenv("TOKEN")
try:
    ADMIN_ID = int(os.getenv("ADMIN_GROUP_ID"))
except (TypeError, ValueError):
    print("⚠️ Error: សូមពិនិត្យមើល ADMIN_GROUP_ID នៅក្នុង Render")
    ADMIN_ID = None

# --- LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.ERROR # <--- ប្តូរទៅ ERROR ដើម្បីកុំឱ្យ Log ពេញអេក្រង់ពេក
)

# --- WEB SERVER (Keep Render Awake) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running with Auto-Restart enabled!"

def run_flask():
    # Run port 10000 for Render
    app.run(host="0.0.0.0", port=10000)

# --- BOT LOGIC (HANDLERS) ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_ID:
        await update.message.reply_text("ជម្រាបសួរ🙏! តើលោកអ្នកមានអ្វីឱ្យខ្ញុំជួយបានទេ?")

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == ADMIN_ID:
        return 

    if update.effective_chat.type == "private":
        try:
            # 1. Reaction ❤️
            try: 
                await context.bot.set_message_reaction(
                    chat_id=update.effective_chat.id,
                    message_id=update.message.message_id,
                    reaction=[ReactionTypeEmoji("❤️")]
                )
            except: pass

            # 2. User Info
            user = update.effective_user
            user_link = f"https://t.me/{user.username}" if user.username else f"tg://user?id={user.id}"
            
            info_text = (
                f"📩 **សារថ្មីពី User:**\n"
                f"👤 ឈ្មោះ: {user.first_name}\n"
                f"🆔 ID: `{user.id}`\n"
                f"🔗 Link: [Click Here]({user_link})\n\n"
                f"👇 **សូម Reply លើសារនេះ ដើម្បីតបទៅគាត់វិញ!**"
            )

            # 3. Forward
            forwarded_msg = await context.bot.forward_message(
                chat_id=ADMIN_ID,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )

            # 4. Info Message
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=info_text,
                reply_to_message_id=forwarded_msg.message_id, 
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )

        except Exception as e:
            logging.error(f"User Handler Error: {e}")

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_ID or not update.message.reply_to_message:
        return

    original_msg = update.message.reply_to_message
    target_user_id = None

    try:
        # Find ID
        if original_msg.text and "ID:" in original_msg.text:
            match = re.search(r"ID:\s*`?(\d+)`?", original_msg.text)
            if match:
                target_user_id = int(match.group(1))

        if not target_user_id and original_msg.forward_from:
            target_user_id = original_msg.forward_from.id

        # Send & React
        if target_user_id:
            try:
                await context.bot.copy_message(
                    chat_id=target_user_id,
                    from_chat_id=update.effective_chat.id,
                    message_id=update.message.message_id
                )
                # Reaction ❤️ on Admin's messages
                try:
                    await context.bot.set_message_reaction(
                        chat_id=ADMIN_ID,
                        message_id=original_msg.message_id,
                        reaction=[ReactionTypeEmoji("❤️")]
                    )
                except: pass
                
                if original_msg.reply_to_message:
                    try:
                        await context.bot.set_message_reaction(
                            chat_id=ADMIN_ID,
                            message_id=original_msg.reply_to_message.message_id,
                            reaction=[ReactionTypeEmoji("❤️")]
                        )
                    except: pass
                
            except Exception as send_error:
                await update.message.reply_text(f"❌ ផ្ញើមិនបាន: {send_error}")
        else:
            await update.message.reply_text("⚠️ **រក User ID មិនឃើញ!** Reply លើសារដែលមាន ID ទើបបាន។")

    except Exception as e:
        logging.error(f"Reply Error: {e}")

# --- MAIN EXECUTION WITH AUTO-RESTART ---
def main_bot():
    """ មុខងារបង្កើត និងដំណើរការ Bot """
    if not TOKEN or not ADMIN_ID:
        print("🚨 Error: ភ្លេចដាក់ TOKEN ឬ ADMIN_GROUP_ID")
        return

    application = ApplicationBuilder().token(TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.Chat(chat_id=ADMIN_ID) & filters.REPLY, handle_admin_reply))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & (~filters.Chat(chat_id=ADMIN_ID)), handle_user_message))

    print("✅ Bot is starting...")
    # run_polling នឹងដំណើរការរហូតទាល់តែមាន Error
    application.run_polling()

if __name__ == '__main__':
    # 1. ដំណើរការ Web Server (ដាច់ដោយឡែក)
    threading.Thread(target=run_flask).start()
    
    # 2. ដំណើរការ Bot ក្នុងរង្វង់អមតៈ (Infinite Loop)
    print("🚀 System started with Auto-Restart Protection")
    
    while True:
        try:
            main_bot() # ហៅ Bot មកប្រើ
        except Exception as e:
            # បើ Bot គាំង (Crash), កូដនឹងធ្លាក់មកដល់ត្រង់នេះ
            print(f"⚠️ Bot Crashed! Error: {e}")
            print("🔄 Restarting in 5 seconds...")
            time.sleep(5) # សម្រាក ៥ វិនាទី
            # បន្ទាប់មកវានឹងវិលទៅលើ ហើយ Start Bot ម្ដងទៀត
        except KeyboardInterrupt:
            print("🛑 Bot stopped by user.")
            break
