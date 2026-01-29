import os
import logging
from dotenv import load_dotenv
from telegram import InputMediaVideo
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Load environment variables
load_dotenv()

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
    """Remove saved thumbnail."""
    user_id = update.message.from_user.id
    if user_id in user_data:
        user_data.pop(user_id, None)
        return await update.message.reply_text(
            "✅ Thumbnail Removed.",
            reply_to_message_id=update.message.message_id
        )
    await update.message.reply_text(
        "⚠️ First Add A Thumbnail.",
        reply_to_message_id=update.message.message_id
    )

async def photo_handler(update, context):
    """Handle photo messages."""
    user_id = update.message.from_user.id
    user_data[user_id] = {"photo_id": update.message.photo[-1].file_id}
    await update.message.reply_text(
        "✅ New Thumbnail Saved.",
        reply_to_message_id=update.message.message_id
    )

async def video_handler(update, context):
    """Handle video messages and add thumbnail."""
    user_id = update.message.from_user.id
    
    if user_id not in user_data or "photo_id" not in user_data[user_id]:
        return await update.message.reply_text(
            "❌ Send A Photo First.",
            reply_to_message_id=update.message.message_id
        )
    
    msg = await update.message.reply_text(
        "🔄 Adding Cover Please Wait...",
        reply_to_message_id=update.message.message_id
    )
    
    try:
        cover = user_data[user_id]["photo_id"]
        video = update.message.video.file_id
        media = InputMediaVideo(
            media=video,
            caption="✅ Cover Added.",
            supports_streaming=True,
            thumbnail=cover
        )
        
        await context.bot.edit_message_media(
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            media=media
        )
    except Exception as e:
        logger.error(f"Error adding cover: {e}")
        await update.message.reply_text(
            f"❌ Failed to send video with cover:\n{str(e)[:100]}"
        )

async def error_handler(update, context):
    """Log the error and send a telegram message to notify the developer."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

def main():
    """Start the bot."""
    logger.info("Starting Thumbnail Bot...")
    
    # Add handlers
    app.add_handler(CommandHandler("start", start_command, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("help", help_command, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("remove", remover, filters=filters.ChatType.PRIVATE))
    app.add_handler(MessageHandler(filters.VIDEO & filters.ChatType.PRIVATE, video_handler))
    app.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, photo_handler))
    
    # Add error handler
    app.add_error_handler(error_handler)
    
    logger.info("Bot is running...")
    app.run_polling(allowed_updates=["message", "edited_channel_post"])

if __name__ == '__main__':
    main()
