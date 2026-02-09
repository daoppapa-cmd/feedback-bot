import os
import logging
import threading
import re  # ប្រើសម្រាប់ចាប់យកលេខ ID
from flask import Flask
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# --- CONFIGURATION ---
TOKEN = os.getenv("TOKEN")
# ADMIN_GROUP_ID អាចជាលេខ Group (មាន -) ឬ Personal ID (អត់ -)
try:
    ADMIN_ID = int(os.getenv("ADMIN_GROUP_ID"))
except (TypeError, ValueError):
    print("⚠️ Error: សូមពិនិត្យមើល ADMIN_GROUP_ID នៅក្នុង Render")
    ADMIN_ID = None

# --- LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- WEB SERVER (Keep Render Awake) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running..."

def run_flask():
    app.run(host="0.0.0.0", port=10000)

# --- BOT LOGIC ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ឆ្លើយតបតែជាមួយ User ធម្មតា
    if update.effective_chat.id != ADMIN_ID:
        await update.message.reply_text("ជម្រាបសួរ🙏! តើលោកអ្នកមានអ្វីឱ្យខ្ញុំជួយបានទេ?")

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ការពារមិនឱ្យ Bot ឆ្លើយតបសារខ្លួនឯង ឬសារ Admin ក្នុង Group
    if update.effective_chat.id == ADMIN_ID:
        return 

    if update.effective_chat.type == "private":
        try:
            # 1. Reaction ❤️
            try: 
                await update.message.set_reaction(reaction="❤️") 
            except: 
                pass

            # 2. បង្កើតអត្ថបទព័ត៌មាន User (ដាក់ ID ឱ្យច្បាស់ដើម្បីស្រួល Reply)
            user = update.effective_user
            # Link សម្រាប់ចុចចូល Profile គាត់ផ្ទាល់ (បើគាត់មាន Username)
            user_link = f"https://t.me/{user.username}" if user.username else f"tg://user?id={user.id}"
            
            info_text = (
                f"📩 **សារថ្មីពី User:**\n"
                f"👤 ឈ្មោះ: {user.first_name}\n"
                f"🆔 ID: `{user.id}`\n"  # ដាក់ក្នុង `...` ដើម្បីស្រួល Copy
                f"🔗 Link: [Click Here]({user_link})\n\n"
                f"👇 **សូម Reply លើសារនេះ ដើម្បីតបទៅគាត់វិញ!**"
            )

            # 3. Forward សារដើម (រូប/Video...) ទៅ Admin
            await context.bot.forward_message(
                chat_id=ADMIN_ID,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )

            # 4. ផ្ញើសារ Info ទៅតាមក្រោយ
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=info_text,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )

        except Exception as e:
            logging.error(f"User Handler Error: {e}")

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ដំណើរការតែពេល៖ Admin ផ្ញើ + មាន Reply
    if update.effective_chat.id != ADMIN_ID or not update.message.reply_to_message:
        return

    original_msg = update.message.reply_to_message
    target_user_id = None

    try:
        # 🔍 វិធីទី ១ (ល្អបំផុត): រកលេខ ID ពីអត្ថបទសារដែល Admin បាន Reply
        # (ទោះបី User បិទ Privacy ក៏នៅតែអាចផ្ញើបានដែរ តាមវិធីនេះ)
        if original_msg.text and "ID:" in original_msg.text:
            # ប្រើ Regex ដើម្បីចាប់យកលេខនៅពីក្រោយពាក្យ ID:
            match = re.search(r"ID:\s*`?(\d+)`?", original_msg.text)
            if match:
                target_user_id = int(match.group(1))

        # 🔍 វិធីទី ២: បើ Admin Reply លើសារ Forward (ហើយ User មិនបិទ Privacy)
        if not target_user_id and original_msg.forward_from:
            target_user_id = original_msg.forward_from.id

        # --- ចាប់ផ្តើមផ្ញើ ---
        if target_user_id:
            try:
                # Copy សាររបស់ Admin ផ្ញើទៅ User វិញ
                await context.bot.copy_message(
                    chat_id=target_user_id,
                    from_chat_id=update.effective_chat.id,
                    message_id=update.message.message_id
                )
                # ដាក់ Reaction 👍
                await update.message.set_reaction(reaction="👍")
            except Exception as send_error:
                # ករណីផ្ញើមិនចេញ (User Block Bot)
                await update.message.reply_text(f"❌ ផ្ញើមិនបាន: {send_error}")
        else:
            await update.message.reply_text(
                "⚠️ **រក User ID មិនឃើញ!**\n\n"
                "សូមប្រាកដថាអ្នកកំពុង Reply ដាក់សារដែលមានសរសេរថា **'ID: ...'** \n"
                "ព្រោះការ Reply ដាក់សារ Forward ផ្ទាល់ អាចនឹងបរាជ័យបើ User បិទ Privacy។"
            )

    except Exception as e:
        logging.error(f"Reply Error: {e}")
        await update.message.reply_text(f"⚠️ System Error: {e}")

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    
    if not TOKEN or not ADMIN_ID:
        print("🚨 Error: ភ្លេចដាក់ TOKEN ឬ ADMIN_GROUP_ID")
    else:
        application = ApplicationBuilder().token(TOKEN).build()

        # Commands
        application.add_handler(CommandHandler("start", start_command))

        # Admin Reply (ដាក់មុនគេ)
        # filters.Chat(id) ធានាថាដំណើរការទាំង Group និង Personal
        admin_handler = MessageHandler(filters.Chat(chat_id=ADMIN_ID) & filters.REPLY, handle_admin_reply)
        application.add_handler(admin_handler)

        # User Message
        user_handler = MessageHandler(filters.ChatType.PRIVATE & (~filters.Chat(chat_id=ADMIN_ID)), handle_user_message)
        application.add_handler(user_handler)

        print("Bot started...")
        application.run_polling()
