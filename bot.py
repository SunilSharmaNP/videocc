import os
from telegram import InputMediaVideo
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import config

# Enhanced logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot
app = Client(
    "Cover_Chnager_Bot",
    TOKEN=config.BOT_TOKEN,
)

TOKEN = ""
app = Application.builder().token(TOKEN).build()

user_data = {}

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
        
app.add_handler(CommandHandler("remove", remover, filters=filters.ChatType.PRIVATE))
app.add_handler(MessageHandler(filters.VIDEO & filters.ChatType.PRIVATE, video_handler))
app.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, photo_handler))
app.run_polling()
