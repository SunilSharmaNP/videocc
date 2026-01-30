import os
import logging
from telegram import InputMediaVideo, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from config import config
import sys
from updater import update_from_upstream
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.error import BadRequest
from telegram.ext import CallbackQueryHandler

# Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Token from config or environment
TOKEN = getattr(config, "BOT_TOKEN", None) or os.environ.get("BOT_TOKEN")
if not TOKEN:
    logger.error("BOT_TOKEN not set in config or environment (config.env).")
    raise SystemExit("BOT_TOKEN not set")

OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
FORCE_SUB_CHANNEL_ID = os.environ.get("FORCE_SUB_CHANNEL_ID")
FORCE_SUB_BANNER_URL = os.environ.get("FORCE_SUB_BANNER_URL")


# In-memory per-user thumbnail storage (keeps only file_ids)
user_data = {}

"""--------------------HELPER FUNCTIONS--------------------"""
async def send_or_edit(update: Update, text, reply_markup=None, force_banner=None):
    if update.callback_query:
        try:
            await update.callback_query.message.edit_text(
                text,
                reply_markup=reply_markup,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        except BadRequest:
            pass
    else:
        if force_banner:
            await update.message.reply_photo(
                photo=force_banner,
                caption=text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=reply_markup,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )

"""------------------FORCE-SUB CHECK-----------------"""

async def check_force_sub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user has joined the required channel"""
    if update.effective_user.id == OWNER_ID:
        return True
    if not FORCE_SUB_CHANNEL_ID:
        return True

    user_id = update.effective_user.id

    try:
        chat_id = int(FORCE_SUB_CHANNEL_ID) if FORCE_SUB_CHANNEL_ID.isdigit() else FORCE_SUB_CHANNEL_ID
        
        # Check user's membership status
        try:
            member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status in ("left", "kicked", "restricted", None):
                raise Exception("User not a member")
        except Exception as e:
            # User is not a member or bot can't check
            logger.info(f"User {user_id} is not a member of channel {chat_id}: {e}")
            
            # Get invite link
            try:
                link_obj = await context.bot.create_chat_invite_link(chat_id=chat_id, member_limit=1)
                invite_link = link_obj.invite_link
            except Exception as e:
                logger.error(f"Error creating invite link: {e}")
                try:
                    chat = await context.bot.get_chat(chat_id)
                    invite_link = chat.invite_link if chat.invite_link else f"https://t.me/{chat.username}"
                except Exception as e:
                    logger.error(f"Error getting chat info: {e}")
                    return True  # Fail-safe

            # Show force-sub message
            text = (
                "🔒 <b>Access Restricted</b>\n\n"
                "To use this bot, you must join our updates channel.\n\n"
                "👇 Join first, then click Verify 👇"
            )

            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Updates Channel", url=invite_link)],
                [InlineKeyboardButton("✅ Verify Access", callback_data="check_fsub")]
            ])

            await send_or_edit(update, text, kb, FORCE_SUB_BANNER_URL)
            return False

        # User is a member
        return True

    except Exception as e:
        logger.error(f"❌ Force-Sub Error: {e}")
        return True  # Allow access on error


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback query for force-sub verification"""
    query = update.callback_query
    if not query or query.data != "check_fsub":
        return

    # Answer the callback immediately
    await query.answer()

    user_id = query.from_user.id
    
    # Check membership
    if not FORCE_SUB_CHANNEL_ID:
        await query.message.delete()
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="✅ <b>Access Granted</b>\n\nYou can now use the bot.",
            parse_mode="HTML"
        )
        return

    try:
        chat_id = int(FORCE_SUB_CHANNEL_ID) if FORCE_SUB_CHANNEL_ID.isdigit() else FORCE_SUB_CHANNEL_ID
        
        try:
            member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status in ("left", "kicked", "restricted", None):
                raise Exception("Still not a member")
        except Exception as e:
            logger.info(f"User {user_id} still not a member: {e}")
            await query.answer("❌ You haven't joined the channel yet!", show_alert=True)
            return

        # User has joined - delete old message and send success
        try:
            await query.message.delete()
        except Exception as e:
            logger.error(f"Error deleting message: {e}")

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                "✅ <b>Access Verified</b>\n\n"
                "You have successfully joined the channel.\n\n"
                "You can now use the bot commands."
            ),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"❌ Callback Error: {e}")
        await query.answer("❌ An error occurred. Please try again.", show_alert=True)


"""---------------------- Menus--------------------- """

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_sub(update, context):
        return
    await update.message.reply_text(
        "👋 <b>Welcome to Instant Cover Bot</b>\n\n"
        "📸 Send a <b>photo</b> to set thumbnail\n"
        "🎥 Send a <b>video</b> to get it with cover\n\n"
        "🧩 Commands:\n"
        "/help – How to use bot\n"
        "/settings – Bot settings\n"
        "/about – About this bot",
        parse_mode="HTML"
    )
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_sub(update, context):
        return
    await update.message.reply_text(
        "ℹ️ <b>Help Menu</b>\n\n"
        "1️⃣ Send a <b>photo</b> → thumbnail saved\n"
        "2️⃣ Send a <b>video</b> → cover applied\n\n"
        "<b>Commands:</b>\n"
        "/remove – Remove saved thumbnail\n"
        "/settings – View bot settings\n"
        "/about – About this bot",
        parse_mode="HTML"
    )
async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_sub(update, context):
        return
    await update.message.reply_text(
        "🤖 <b>Instant Video Cover Bot</b>\n\n"
        "✨ Features:\n"
        "• Instant thumbnail apply\n"
        "• One thumbnail per user\n"
        "• Fast & simple\n\n"
        "🛠 Powered by python-telegram-bot",
        parse_mode="HTML"
    )
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_sub(update, context):
        return
    user_id = update.message.from_user.id
    thumb_status = "✅ Set" if user_id in user_data else "❌ Not Set"
    await update.message.reply_text(
        "⚙️ <b>Settings</b>\n\n"
        f"🖼 Thumbnail: <b>{thumb_status}</b>\n\n"
        "Use /remove to delete thumbnail",
        parse_mode="HTML"
    )


async def remover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_sub(update, context):
        return
    user_id = update.message.from_user.id
    if user_id in user_data:
        user_data.pop(user_id, None)
        return await update.message.reply_text("✅ Thumbnail Removed.", reply_to_message_id=update.message.message_id)
    await update.message.reply_text("⚠️ First Add A Thumbnail.", reply_to_message_id=update.message.message_id)

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_sub(update, context):
        return
    user_id = update.message.from_user.id
    user_data[user_id] = {"photo_id": update.message.photo[-1].file_id}
    await update.message.reply_text("✅ New Thumbnail Saved.", reply_to_message_id=update.message.message_id)

async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_sub(update, context):
        return
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


async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != OWNER_ID:
        return await update.message.reply_text("❌ You are not authorized.")

    msg = await update.message.reply_text("🔄 Updating from upstream...")

    success = update_from_upstream()

    if not success:
        return await msg.edit_text("❌ Update failed. Check logs.")

    await msg.edit_text("✅ Updated successfully.\n♻️ Restarting bot...")
    os.execv(sys.executable, [sys.executable] + sys.argv)


"""-----------CALLBAck Hnadlers--------"""


def main() -> None:
    app = Application.builder().token(TOKEN).build()

    # Command to remove stored thumbnail
    app.add_handler(CommandHandler("remove", remover, filters=filters.ChatType.PRIVATE))

    # Photo and video handlers (private chats only via filters)
    app.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, photo_handler))
    app.add_handler(MessageHandler(filters.VIDEO & filters.ChatType.PRIVATE, video_handler))

    app.add_handler(CommandHandler("start", start, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("help", help_cmd, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("about", about, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("settings", settings, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("restart", restart, filters=filters.ChatType.PRIVATE))
    
    app.add_handler(CallbackQueryHandler(callback_handler, pattern="^check_fsub$"))



    logger.info("Bot starting (polling)")
    app.run_polling()


if __name__ == "__main__":
    main()
