import os
import sys
import logging
import subprocess
from dotenv import load_dotenv, dotenv_values
from telegram import InputMediaVideo
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from pymongo import MongoClient

# Load environment variables
load_dotenv()

# Support optional config.env (matches snippet provided)
if os.path.exists("config.env"):
    # override with config.env values if present
    for k, v in dotenv_values("config.env").items():
        if v is not None:
            os.environ.setdefault(k, v)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get token from environment
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables!")

# Application setup
app = Application.builder().token(TOKEN).build()

# User data store
user_data = {}

# Admin / owner configuration
# Provide OWNER_ID (single) or ADMIN_IDS (comma-separated) in env
OWNER_ID = os.getenv("OWNER_ID")
ADMIN_IDS = os.getenv("ADMIN_IDS", "")
if OWNER_ID and OWNER_ID.isdigit():
    ADMIN_SET = {int(OWNER_ID)}
else:
    ADMIN_SET = set()
for a in [x.strip() for x in ADMIN_IDS.split(",") if x.strip()]:
    if a.isdigit():
        ADMIN_SET.add(int(a))

# Upstream repo settings
UPSTREAM_REPO = os.getenv("UPSTREAM_REPO", "") or None
UPSTREAM_BRANCH = os.getenv("UPSTREAM_BRANCH", "master") or "master"

# Optional database-driven config (DATABASE_URL)
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    try:
        conn = MongoClient(DATABASE_URL)
        db = conn.get_database()
        bot_id = TOKEN.split(":", 1)[0]
        old_config = db.settings.deployConfig.find_one({"_id": bot_id})
        config_dict = db.settings.config.find_one({"_id": bot_id})
        if config_dict is not None:
            UPSTREAM_REPO = config_dict.get("UPSTREAM_REPO", UPSTREAM_REPO)
            UPSTREAM_BRANCH = config_dict.get("UPSTREAM_BRANCH", UPSTREAM_BRANCH)
            # allow override of admin ids from DB (optional)
            if config_dict.get("ADMIN_IDS"):
                ADMIN_IDS = config_dict.get("ADMIN_IDS")
                for a in [x.strip() for x in ADMIN_IDS.split(",") if x.strip()]:
                    if a.isdigit():
                        ADMIN_SET.add(int(a))
    except Exception as e:
        logger.warning(f"Could not read config from DB: {e}")

async def start_command(update, context):
    """Send a message when the command /start is issued."""
    welcome_message = """
🤖 *Thumbnail Bot*

Welcome! I can help you add custom thumbnails to your videos.

**Commands:**
• Send a photo → I'll save it as your thumbnail
• Send a video → I'll add the saved thumbnail as cover
• /remove → Delete your saved thumbnail

**Note:** This bot only works in private chats.
"""
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def help_command(update, context):
    """Send a message when the command /help is issued."""
    help_message = """
*How to use:*

1️⃣ Send a photo/image
2️⃣ Send a video
3️⃣ I'll add the photo as thumbnail to your video

Use /remove to delete saved thumbnail.
"""
    await update.message.reply_text(help_message, parse_mode='Markdown')

async def remover(update, context):
    user_id = update.message.from_user.id
    if user_id in user_data:
        user_data.pop(user_id, None)
        return await update.message.reply_text("✅ Thumbnail Removed.", reply_to_message_id=update.message.message_id)
    await update.message.reply_text("⚠️ First Add A Thumbnail.", reply_to_message_id=update.message.message_id)

async def photo_handler(update, context):
    user_id = update.message.from_user.id
    user_data[user_id] = {"photo_id": update.message.photo[-1].file_id}
    await update.message.reply_text("✅ New Thumbnail Saved.", reply_to_message_id=update.message.message_id)

async def video_handler(update, context):
    user_id = update.message.from_user.id
    if user_id not in user_data or "photo_id" not in user_data[user_id]:
        return await update.message.reply_text("❌ Send A Photo First.", reply_to_message_id=update.message.message_id)
    msg = await update.message.reply_text("🔄 Adding Cover Please Wait...", reply_to_message_id=update.message.message_id)
    
    cover = user_data[user_id]["photo_id"]
    video = update.message.video.file_id
    media = InputMediaVideo(media=video, caption="✅ Cover Added.", supports_streaming=True, cover=cover)
    
    try:
        await context.bot.edit_message_media(chat_id=update.effective_chat.id, message_id=msg.message_id, media=media)
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to send video with cover:\n{e}")
        
def perform_update(repo: str, branch: str) -> bool:
    """If UPSTREAM_REPO is set, attempt to fetch and reset local code to that branch."""
    if not repo:
        return False
    try:
        # remove git folder to avoid conflicts, then re-init and reset
        if os.path.exists(".git"):
            try:
                import shutil

                shutil.rmtree(".git")
            except Exception:
                pass

        cmd = (
            f"git init -q && git config --global user.email 'dev@local' "
            f"&& git config --global user.name 'bot' "
            f"&& git add . && git commit -sm update -q || true "
            f"&& git remote add origin {repo} || git remote set-url origin {repo} "
            f"&& git fetch origin -q && git reset --hard origin/{branch} -q"
        )
        res = subprocess.run(cmd, shell=True)
        return res.returncode == 0
    except Exception as e:
        logger.error(f"Update failed: {e}")
        return False


async def restart_command(update, context):
    """Admin-only command to update from upstream (if configured) and restart the process."""
    user = update.effective_user
    user_id = getattr(user, "id", None)
    if user_id not in ADMIN_SET:
        return await update.message.reply_text("❌ You are not authorized to run this command.")

    await update.message.reply_text("🔄 Update requested. Running update (if configured)...")
    if UPSTREAM_REPO:
        ok = perform_update(UPSTREAM_REPO, UPSTREAM_BRANCH)
        if ok:
            await update.message.reply_text("✅ Updated code from upstream.")
        else:
            await update.message.reply_text("⚠️ Failed to update from upstream. Proceeding to restart anyway.")

    await update.message.reply_text("♻️ Restarting bot now...")
    python = sys.executable
    os.execv(python, [python] + sys.argv)

def main():
    """Start the bot."""
    logger.info("Starting Thumbnail Bot...")
    # If UPSTREAM_REPO configured, try to update at startup
    if UPSTREAM_REPO:
        try:
            ok = perform_update(UPSTREAM_REPO, UPSTREAM_BRANCH)
            if ok:
                logger.info("Successfully updated code from upstream at startup.")
            else:
                logger.warning("Failed to update from upstream at startup.")
        except Exception as e:
            logger.warning(f"Startup update check failed: {e}")
    
    # Add handlers
    app.add_handler(CommandHandler("start", start_command, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("help", help_command, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("remove", remover, filters=filters.ChatType.PRIVATE))
    app.add_handler(MessageHandler(filters.VIDEO & filters.ChatType.PRIVATE, video_handler))
    app.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, photo_handler))
    
    # Add error handler
    app.add_error_handler(error_handler)

    # Add admin-only restart command
    app.add_handler(CommandHandler("restart", restart_command))
    
    logger.info("Bot is running...")
    app.run_polling(allowed_updates=["message", "edited_channel_post"])

if __name__ == '__main__':
    main()
