import os
import logging
import threading
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
    level=logging.INFO
)

# --- WEB SERVER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running..."

def run_flask():
    app.run(host="0.0.0.0", port=10000)

# --- BOT LOGIC ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_ID:
        await update.message.reply_text("ជម្រាបសួរ🙏! តើលោកអ្នកមានអ្វីឱ្យខ្ញុំជួយបានទេ?")

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == ADMIN_ID:
        return 

    if update.effective_chat.type == "private":
        try:
            # 1. Reaction ❤️ លើសារ User (ក្នុង Private Chat)
            try: 
                await context.bot.set_message_reaction(
                    chat_id=update.effective_chat.id,
                    message_id=update.message.message_id,
                    reaction=[ReactionTypeEmoji("❤️")]
                )
            except: pass

            # 2. បង្កើតអត្ថបទ User Info
            user = update.effective_user
            user_link = f"https://t.me/{user.username}" if user.username else f"tg://user?id={user.id}"
            
            info_text = (
                f"📩 **សារថ្មីពី User:**\n"
                f"👤 ឈ្មោះ: {user.first_name}\n"
                f"🆔 ID: `{user.id}`\n"
                f"🔗 Link: [Click Here]({user_link})\n\n"
                f"👇 **សូម Reply លើសារនេះ ដើម្បីតបទៅគាត់វិញ!**"
            )

            # 3. Forward សារដើមទៅ Admin
            forwarded_msg = await context.bot.forward_message(
                chat_id=ADMIN_ID,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )

            # 4. ផ្ញើ Info ទៅតាមក្រោយ (Reply ជាប់ជាមួយ Forward)
            # សំខាន់៖ ការដាក់ reply_to_message_id នៅទីនេះ ជួយឱ្យយើងរកសារដើមឃើញពេលក្រោយ
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
        # --- រក USER ID ---
        # 1. ពីអត្ថបទ (ID: ...)
        if original_msg.text and "ID:" in original_msg.text:
            match = re.search(r"ID:\s*`?(\d+)`?", original_msg.text)
            if match:
                target_user_id = int(match.group(1))

        # 2. ពី Forward Header
        if not target_user_id and original_msg.forward_from:
            target_user_id = original_msg.forward_from.id

        # --- ផ្ញើចេញ និង ដាក់ REACTION ---
        if target_user_id:
            try:
                # A. Copy សារផ្ញើទៅ User
                await context.bot.copy_message(
                    chat_id=target_user_id,
                    from_chat_id=update.effective_chat.id,
                    message_id=update.message.message_id
                )

                # B. ដាក់ Reaction ❤️ លើសារដែល Admin បាន Reply (សារ Info)
                try:
                    await context.bot.set_message_reaction(
                        chat_id=ADMIN_ID,
                        message_id=original_msg.message_id,
                        reaction=[ReactionTypeEmoji("❤️")]
                    )
                except: pass

                # C. ដាក់ Reaction ❤️ លើសារដើម (Forwarded Message) ផងដែរ
                # ដោយសារយើងបាន Link សារ Info ជាមួយ Forward (Reply chain) យើងអាចរកសារដើមបាន
                if original_msg.reply_to_message:
                    try:
                        await context.bot.set_message_reaction(
                            chat_id=ADMIN_ID,
                            message_id=original_msg.reply_to_message.message_id,
                            reaction=[ReactionTypeEmoji("❤️")]
                        )
                    except: pass
                
            except Exception as send_error:
                await update.message.reply_text(f"❌ ផ្ញើមិនបាន (User Block Bot): {send_error}")
        else:
            await update.message.reply_text(
                "⚠️ **រក User ID មិនឃើញ!**\n"
                "សូម Reply លើសារដែលមានសរសេរថា **'ID: ...'**"
            )

    except Exception as e:
        logging.error(f"Reply Error: {e}")

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    
    if not TOKEN or not ADMIN_ID:
        print("🚨 Error: ភ្លេចដាក់ TOKEN ឬ ADMIN_GROUP_ID")
    else:
        application = ApplicationBuilder().token(TOKEN).build()
        application.add_handler(CommandHandler("start", start_command))
        
        # Admin Handler
        admin_handler = MessageHandler(filters.Chat(chat_id=ADMIN_ID) & filters.REPLY, handle_admin_reply)
        application.add_handler(admin_handler)

        # User Handler
        user_handler = MessageHandler(filters.ChatType.PRIVATE & (~filters.Chat(chat_id=ADMIN_ID)), handle_user_message)
        application.add_handler(user_handler)

        print("Bot started...")
        application.run_polling()
