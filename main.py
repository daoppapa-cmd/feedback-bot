import os
import logging
import threading
import asyncio
from flask import Flask
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# --- CONFIGURATION ---
# ត្រូវប្រាកដថាបានដាក់ TOKEN និង ADMIN_GROUP_ID ក្នុង Render Environment Variables
TOKEN = os.getenv("TOKEN")
# ADMIN_GROUP_ID អាចជាលេខ Group (មានសញ្ញា -) ឬលេខ Account ផ្ទាល់ខ្លួន (អត់សញ្ញា -)
try:
    ADMIN_ID = int(os.getenv("ADMIN_GROUP_ID"))
except (TypeError, ValueError):
    print("⚠️ Error: សូមពិនិត្យមើល ADMIN_GROUP_ID នៅក្នុង Render របស់អ្នក។")
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
    return "Bot is running perfectly!"

def run_flask():
    # Run port 10000 for Render
    app.run(host="0.0.0.0", port=10000)

# --- BOT LOGIC ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ឆ្លើយតបតែជាមួយ User ធម្មតាប៉ុណ្ណោះ (មិនមែន Admin)
    if update.effective_chat.id != ADMIN_ID:
        await update.message.reply_text("ជម្រាបសួរ🙏! តើលោកអ្នកមានអ្វីឱ្យខ្ញុំជួយបានទេ?")

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. ពិនិត្យ៖ ត្រូវតែជាសារមកពី User (មិនមែនមកពី Admin)
    # និងត្រូវតែជា Private Chat
    if update.effective_chat.id == ADMIN_ID:
        return # បើ Admin ផ្ញើខ្លួនឯង កុំធ្វើអីទាំងអស់ (ទុកឱ្យមុខងារ Reply ធ្វើការ)

    if update.effective_chat.type == "private":
        try:
            # 2. ដាក់ Reaction ❤️ ភ្លាមៗ
            try:
                await update.message.set_reaction(reaction="❤️")
            except Exception as e:
                logging.warning(f"Reaction failed (Ignore): {e}")

            # 3. ប្រមូលព័ត៌មាន User (ចាប់យកត្រង់នេះទើបត្រឹមត្រូវ ១០០%)
            user = update.effective_user
            user_info = (
                f"📩 **សារថ្មីពី User:**\n"
                f"👤 ឈ្មោះ: {user.first_name} {user.last_name or ''}\n"
                f"🆔 ID: `{user.id}`\n"
                f"🔗 Username: @{user.username if user.username else 'គ្មាន'}"
            )

            # 4. Forward សារទៅ Admin (មិនថា Group ឬ Personal ទេ ឱ្យតែត្រូវ ID)
            forwarded_msg = await context.bot.forward_message(
                chat_id=ADMIN_ID,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )

            # 5. ផ្ញើសារព័ត៌មាន User ទៅបន្ទាប់ពី Forward
            # នេះជាគន្លឹះ! Admin អាច Reply លើសារនេះបាន បើសារ Forward ជាប់ Privacy
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=user_info,
                reply_to_message_id=forwarded_msg.message_id,
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            logging.error(f"Error handling user message: {e}")

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. ពិនិត្យ៖ ត្រូវតែជាសាររបស់ Admin និងមានការ Reply
    if update.effective_chat.id != ADMIN_ID or not update.message.reply_to_message:
        return

    original_msg = update.message.reply_to_message
    target_user_id = None

    try:
        # វិធីទី ១: រក ID ពីសារដែលបាន Forward (User ធម្មតា)
        if original_msg.forward_from:
            target_user_id = original_msg.forward_from.id
        
        # វិធីទី ២: រក ID ពីសារព័ត៌មាន User (ដែល Bot ផ្ញើទៅភ្ជាប់ជាមួយ Forward)
        # បើ Admin Reply លើសារដែលមានអក្សរ "ID: 123456" Bot នឹងចាប់យកលេខនោះ
        elif original_msg.text and "ID:" in original_msg.text:
            lines = original_msg.text.split('\n')
            for line in lines:
                if "ID:" in line:
                    # កាត់យកលេខ ID ចេញពីចន្លោះ `...`
                    try:
                        target_user_id = int(line.split('`')[1])
                    except:
                        pass
        
        # វិធីទី ៣: សម្រាប់ Telegram ជំនាន់ថ្មី (Forward Origin)
        elif hasattr(original_msg, 'forward_origin') and original_msg.forward_origin:
             if hasattr(original_msg.forward_origin, 'sender_user'):
                 target_user_id = original_msg.forward_origin.sender_user.id

        # --- ការផ្ញើសារត្រឡប់ទៅ User ---
        if target_user_id:
            # Copy គ្រប់យ៉ាង (Text, Photo, Video...) ទៅ User វិញ
            await context.bot.copy_message(
                chat_id=target_user_id,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
            # ដាក់ Reaction 👍 ឱ្យ Admin ដឹងថាបានសម្រេច
            try:
                await update.message.set_reaction(reaction="👍")
            except:
                pass
        else:
            # បើរកមិនឃើញ ID (ករណី User បិទ Privacy ខ្លាំងពេក ហើយ Admin Reply លើ Forward ផ្ទាល់)
            await update.message.reply_text(
                "⚠️ **មិនអាចផ្ញើបាន!**\n"
                "ដោយសារ User នេះបិទ Privacy, Bot រក ID មិនឃើញពីសារ Forward ទេ។\n\n"
                "👉 **ដំណោះស្រាយ:** សូម Admin ជួយ Reply លើសារដែលមានសរសេរ **ID: ...** នៅខាងក្រោមសារនោះវិញ ទើបផ្ញើបាន។"
            )

    except Exception as e:
        logging.error(f"Error replying: {e}")
        await update.message.reply_text(f"❌ Error: {e}")

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    
    if not TOKEN or not ADMIN_ID:
        print("🚨 Error: សូមដាក់ TOKEN និង ADMIN_GROUP_ID ឱ្យបានត្រឹមត្រូវ!")
    else:
        application = ApplicationBuilder().token(TOKEN).build()

        # Handler 1: Start (សម្រាប់តែ User)
        application.add_handler(CommandHandler("start", start_command))

        # Handler 2: Admin Reply (សំខាន់ត្រូវដាក់មុន User Handler ដើម្បីកុំឱ្យជាន់គ្នា)
        # filters.Chat(ADMIN_ID) មានន័យថាឱ្យតែជា Chat របស់ Admin (មិនថា Group ឬ Personal)
        admin_reply_handler = MessageHandler(filters.Chat(ADMIN_ID) & filters.REPLY, handle_admin_reply)
        application.add_handler(admin_reply_handler)

        # Handler 3: User Message (ចាប់យកគ្រប់យ៉ាងពី User ធម្មតា)
        user_handler = MessageHandler(filters.ChatType.PRIVATE & (~filters.Chat(ADMIN_ID)), handle_user_message)
        application.add_handler(user_handler)

        print(f"🤖 Bot is running... Admin ID: {ADMIN_ID}")
        application.run_polling()
