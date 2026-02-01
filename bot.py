import os
import logging
import asyncio
from telegram import InputMediaVideo, Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
)
from config import config
import sys
from updater import update_from_upstream
from telegram.error import BadRequest, RetryAfter
import random

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
OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "")

# Fallback: collect images from ./ui/ and pick randomly when showing banner
FALLBACK_BANNER = None
UI_BANNERS = []
try:
    ui_dir = os.path.join(os.path.dirname(__file__), "ui")
    if os.path.isdir(ui_dir):
        UI_BANNERS = [os.path.join(ui_dir, f) for f in os.listdir(ui_dir) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
        if UI_BANNERS:
            FALLBACK_BANNER = UI_BANNERS[0]
except Exception:
    UI_BANNERS = []
    FALLBACK_BANNER = None

# Final banner env value (may be URL) or local fallback
FORCE_SUB_BANNER = FORCE_SUB_BANNER_URL or FALLBACK_BANNER


def get_force_banner():
    """Return a banner URL or local file path. Prefer env URL; else pick random local image."""
    if FORCE_SUB_BANNER_URL:
        return FORCE_SUB_BANNER_URL
    try:
        if UI_BANNERS:
            return random.choice(UI_BANNERS)
    except Exception:
        pass
    return FALLBACK_BANNER


# In-memory per-user thumbnail storage (keeps only file_ids)
user_data = {}
# In-memory set of users who completed the verify step
verified_users = set()

"""--------------------HELPER FUNCTIONS--------------------"""
async def send_or_edit(update: Update, text, reply_markup=None, force_banner=None):
    if update.callback_query:
        try:
            # If original message contains a photo, edit the caption instead
            msg = update.callback_query.message
            if getattr(msg, "photo", None):
                await msg.edit_caption(
                    text,
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )
            else:
                await msg.edit_text(
                    text,
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
        except BadRequest:
            pass
    else:
        if force_banner:
            # Support local file paths in addition to URLs
            try:
                if isinstance(force_banner, str) and os.path.isfile(force_banner):
                    photo = InputFile(force_banner)
                else:
                    photo = force_banner
            except Exception:
                photo = force_banner

            await update.message.reply_photo(
                photo=photo,
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


async def get_invite_link(bot, chat_id):
    """Create or return a chat invite link with rate-limit retry handling."""
    try:
        link_obj = await bot.create_chat_invite_link(chat_id=chat_id, member_limit=1)
        # Different objects may expose either 'invite_link' attribute or be a string
        return getattr(link_obj, "invite_link", link_obj)
    except RetryAfter as e:
        # python-telegram-bot RetryAfter provides `retry_after` in seconds
        secs = getattr(e, "retry_after", None) or 30
        logger.info(f"Rate limited while creating invite link: sleeping {secs}s")
        await asyncio.sleep(secs)
        return await get_invite_link(bot, chat_id)
    except Exception as e:
        logger.error(f"get_invite_link failed: {e}")
        return None

"""------------------FORCE-SUB CHECK-----------------"""

async def check_force_sub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user has joined the required channel (FileStreamBot pattern: auto-verify + auto-delete)"""
    user_id = update.effective_user.id

    # Owner bypass
    if user_id == OWNER_ID:
        return True

    # If no force-sub configured, allow access
    if not FORCE_SUB_CHANNEL_ID:
        return True

    # If user already completed the verify step, allow access
    if user_id in verified_users:
        return True

    # Parse channel ID
    try:
        chat_id = int(FORCE_SUB_CHANNEL_ID) if str(FORCE_SUB_CHANNEL_ID).isdigit() else FORCE_SUB_CHANNEL_ID
    except Exception:
        logger.error(f"Invalid FORCE_SUB_CHANNEL_ID: {FORCE_SUB_CHANNEL_ID}")
        return True  # Fail open

    try:
        # Check if user is already a member
        try:
            member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            # Check status - use both OWNER and CREATOR for compatibility
            allowed_statuses = (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR)
            # Try to add OWNER or CREATOR if they exist
            try:
                allowed_statuses = allowed_statuses + (ChatMemberStatus.OWNER,)
            except AttributeError:
                try:
                    allowed_statuses = allowed_statuses + (ChatMemberStatus.CREATOR,)
                except AttributeError:
                    pass
            
            if member.status in allowed_statuses:
                verified_users.add(user_id)
                return True
            # User is restricted, left, or kicked
            if member.status == ChatMemberStatus.KICKED:
                await send_or_edit(update, "🚫 <b>Blocked</b>\n\nYou are blocked from this channel.", parse_mode="HTML")
                return False
        except Exception as e:
            logger.debug(f"Member check initial failed: {e}")

        # User not in channel — show join prompt
        invite_link = await get_invite_link(context.bot, chat_id)
        if not invite_link:
            # Fallback to public link
            try:
                chat = await context.bot.get_chat(chat_id)
                invite_link = getattr(chat, "invite_link", None) or (f"https://t.me/{getattr(chat, 'username', '')}" if getattr(chat, 'username', None) else None)
            except Exception:
                invite_link = None

        # Build keyboard
        kb_rows = []
        kb_rows.append([InlineKeyboardButton("📢 Join Updates Channel", url=invite_link if invite_link else "https://t.me/")])
        kb_rows.append([
            InlineKeyboardButton("✅ Verify Access", callback_data="check_fsub"),
            InlineKeyboardButton("✖️ Close", callback_data="close_banner")
        ])
        if OWNER_USERNAME:
            kb_rows.append([InlineKeyboardButton("📞 Contact Owner", url=f"https://t.me/{OWNER_USERNAME}")])

        kb = InlineKeyboardMarkup(kb_rows)
        prompt = (
            "🔒 <b>Access Restricted</b>\n\n"
            "To use this bot, you must join our updates channel.\n\n"
            "👇 Join the channel first 👇"
        )

        msg = await send_or_edit(update, prompt, kb, get_force_banner())

        # Wait 30 seconds (FileStreamBot pattern)
        await asyncio.sleep(30)

        # Try to delete the prompt message
        try:
            if update.callback_query and msg:
                await msg.delete()
            elif update.message:
                await update.message.delete()
        except Exception:
            pass

        # Auto-recheck membership after 30s
        try:
            member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            # Check status - use both OWNER and CREATOR for compatibility
            allowed_statuses = (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR)
            # Try to add OWNER or CREATOR if they exist
            try:
                allowed_statuses = allowed_statuses + (ChatMemberStatus.OWNER,)
            except AttributeError:
                try:
                    allowed_statuses = allowed_statuses + (ChatMemberStatus.CREATOR,)
                except AttributeError:
                    pass
            
            if member.status in allowed_statuses:
                verified_users.add(user_id)
                return True
        except Exception as e:
            logger.debug(f"Auto-recheck after 30s failed: {e}")

        return False

    except Exception as e:
        logger.error(f"❌ Force-Sub Error: {e}")
        return True  # Fail open


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback query for force-sub verification"""
    query = update.callback_query
    
    logger.info(f"🔵 CALLBACK HANDLER TRIGGERED | Query Data: {query.data if query else 'NO QUERY'}")
    
    if not query:
        logger.error("❌ Query is None!")
        return
    
    if not query.data:
        logger.error("❌ Query data is None!")
        return

    user_id = query.from_user.id
    
    # Handle explicit verify button click
    if query.data == "check_fsub":
        logger.info(f"🔍 Processing verify button for user {user_id}")
        
        # Answer callback IMMEDIATELY to prevent timeout
        try:
            await query.answer()
        except Exception as e:
            logger.debug(f"Early callback answer error (okay): {e}")
        
        try:
            chat_id = int(FORCE_SUB_CHANNEL_ID) if str(FORCE_SUB_CHANNEL_ID).isdigit() else FORCE_SUB_CHANNEL_ID
        except Exception:
            logger.error(f"Invalid FORCE_SUB_CHANNEL_ID: {FORCE_SUB_CHANNEL_ID}")
            verified_users.add(user_id)
            await start(update, context)
            return

        try:
            member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            logger.info(f"✅ Member status: {member.status}")
            
            # Check if user is member, admin, or owner
            allowed_statuses = (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR)
            try:
                allowed_statuses = allowed_statuses + (ChatMemberStatus.OWNER,)
            except AttributeError:
                try:
                    allowed_statuses = allowed_statuses + (ChatMemberStatus.CREATOR,)
                except AttributeError:
                    pass
            
            if member.status in allowed_statuses:
                # User joined! Verify instantly and show home menu
                verified_users.add(user_id)
                logger.info(f"✅ User {user_id} verified, opening home menu instantly")
                await start(update, context)
                return
            else:
                # User not member - send error message
                msg = query.message
                error_text = (
                    "❌ <b>You haven't joined yet!</b>\n\n"
                    "Join our channel using the button below, then click Verify again."
                )
                try:
                    if getattr(msg, "photo", None):
                        await msg.edit_caption(error_text, parse_mode="HTML")
                    else:
                        await msg.edit_text(error_text, parse_mode="HTML")
                except Exception:
                    pass
                logger.warning(f"❌ User {user_id} not member. Status: {member.status}")
                return
        except Exception as e:
            logger.error(f"❌ Verify button check error: {e}", exc_info=True)
            # Fail open
            verified_users.add(user_id)
            await start(update, context)
            return
    
    # Handle other callback actions first
    if query.data == "close_banner":
        logger.info(f"❌ Close banner for user {user_id}")
        try:
            await query.answer()
            await query.message.delete()
        except Exception as e:
            logger.error(f"Close error: {e}")
            try:
                await query.message.edit_text("Closed", parse_mode="HTML")
            except Exception:
                pass
        return

    if query.data == "contact_owner":
        logger.info(f"📞 Contact owner for user {user_id}")
        try:
            await query.answer()
            if OWNER_USERNAME:
                await context.bot.send_message(chat_id=query.message.chat_id, text=f"Contact owner: https://t.me/{OWNER_USERNAME}")
            else:
                await context.bot.send_message(chat_id=query.message.chat_id, text="Owner contact not configured.")
        except Exception as e:
            logger.error(f"Contact error: {e}")
        return

    # Menu callbacks: show help/about/settings/developer inline
    if query.data.startswith("menu_"):
        key = query.data.split("menu_")[1]
        logger.info(f"📋 Menu callback: {key} for user {user_id}")
        await query.answer()
        
        # Handle back button - return to home menu
        if key == "back":
            text = (
                "👋 <b>Welcome to Instant Cover Bot</b>\n\n"
                "📸 Send a <b>photo</b> to set thumbnail\n"
                "🎥 Send a <b>video</b> to get it with cover\n\n"
                "🧩 Commands:\n"
                "/help – How to use bot\n"
                "/settings – Bot settings\n"
                "/about – About this bot"
            )
            kb_rows = [
                [InlineKeyboardButton("❓ Help", callback_data="menu_help"),
                 InlineKeyboardButton("ℹ️ About", callback_data="menu_about")],
                [InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
                 InlineKeyboardButton("👨‍💻 Developer", callback_data="menu_developer")],
            ]
            kb = InlineKeyboardMarkup(kb_rows)
            try:
                msg = query.message
                if getattr(msg, "photo", None):
                    await msg.edit_caption(text, reply_markup=kb, parse_mode="HTML")
                else:
                    await msg.edit_text(text, reply_markup=kb, parse_mode="HTML")
            except Exception as e:
                logger.debug(f"Back button message edit error: {e}")
            return
        
        try:
            if key == "help":
                text = (
                    "ℹ️ <b>Help Menu</b>\n\n"
                    "1️⃣ Send a <b>photo</b> → thumbnail saved\n"
                    "2️⃣ Send a <b>video</b> → cover applied\n\n"
                    "<b>Commands:</b>\n"
                    "/remove – Remove saved thumbnail\n"
                    "/settings – View bot settings\n"
                    "/about – About this bot"
                )
            elif key == "about":
                text = (
                    "🤖 <b>Instant Video Cover Bot</b>\n\n"
                    "✨ Features:\n"
                    "• Instant thumbnail apply\n"
                    "• One thumbnail per user\n"
                    "• Fast & simple\n\n"
                    "🛠 Powered by python-telegram-bot"
                )
            elif key == "settings":
                uid = query.from_user.id
                thumb_status = "✅ Set" if uid in user_data else "❌ Not Set"
                text = (
                    "⚙️ <b>Settings</b>\n\n"
                    f"🖼 Thumbnail: <b>{thumb_status}</b>\n\n"
                    "Use /remove to delete thumbnail"
                )
            elif key == "developer":
                dev_contact = f"https://t.me/{OWNER_USERNAME}" if OWNER_USERNAME else f"tg://user?id={OWNER_ID}"
                text = (
                    "👨‍💻 <b>Developer</b>\n\n"
                    f"Contact: {dev_contact}\n"
                    "If you need help, reach out to the developer."
                )
            else:
                text = (
                    "ℹ️ <b>Info</b>\n\n"
                    "No information available for this menu."
                )
            
            # Add back button to all menus
            back_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="menu_back")]
            ])
            
            # Try to edit original message's caption/text first
            try:
                msg = query.message
                if getattr(msg, "photo", None):
                    await msg.edit_caption(text, reply_markup=back_kb, parse_mode="HTML")
                else:
                    await msg.edit_text(text, reply_markup=back_kb, parse_mode="HTML")
            except Exception as e:
                logger.debug(f"Menu edit error: {e}")
                await context.bot.send_message(chat_id=query.message.chat.id, text=text, reply_markup=back_kb, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Menu error: {e}", exc_info=True)
        return

    logger.warning(f"⚠️ Unknown callback: {query.data}")
    try:
        await query.answer("Unknown action", show_alert=False)
    except Exception:
        pass


"""---------------------- Menus--------------------- """

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check force-sub first
    if not await check_force_sub(update, context):
        logger.warning(f"❌ User {update.effective_user.id} blocked by force-sub check")
        return
    
    text = (
        "👋 <b>Welcome to Instant Cover Bot</b>\n\n"
        "📸 Send a <b>photo</b> to set thumbnail\n"
        "🎥 Send a <b>video</b> to get it with cover\n\n"
        "🧩 Commands:\n"
        "/help – How to use bot\n"
        "/settings – Bot settings\n"
        "/about – About this bot"
    )
    # Build home menu with all buttons
    kb_rows = [
        [InlineKeyboardButton("❓ Help", callback_data="menu_help"),
         InlineKeyboardButton("ℹ️ About", callback_data="menu_about")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
         InlineKeyboardButton("👨‍💻 Developer", callback_data="menu_developer")],
    ]
    kb = InlineKeyboardMarkup(kb_rows)
    banner = get_force_banner() if 'get_force_banner' in globals() else None
    
    # Handle both callback_query and regular message
    if update.callback_query:
        msg = update.callback_query.message
        if banner:
            try:
                if isinstance(banner, str) and os.path.isfile(banner):
                    photo = InputFile(banner)
                else:
                    photo = banner
                if getattr(msg, "photo", None):
                    await msg.edit_caption(caption=text, reply_markup=kb, parse_mode="HTML")
                else:
                    try:
                        await msg.delete()
                    except Exception:
                        pass
                    await msg.chat.send_photo(photo=photo, caption=text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                await msg.edit_text(text, reply_markup=kb, parse_mode="HTML")
        else:
            await msg.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        if banner:
            try:
                if isinstance(banner, str) and os.path.isfile(banner):
                    await update.message.reply_photo(photo=InputFile(banner), caption=text, reply_markup=kb, parse_mode="HTML")
                else:
                    await update.message.reply_photo(photo=banner, caption=text, reply_markup=kb, parse_mode="HTML")
                return
            except Exception:
                pass
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_sub(update, context):
        return
    text = (
        "ℹ️ <b>Help Menu</b>\n\n"
        "1️⃣ Send a <b>photo</b> → thumbnail saved\n"
        "2️⃣ Send a <b>video</b> → cover applied\n\n"
        "<b>Commands:</b>\n"
        "/remove – Remove saved thumbnail\n"
        "/settings – View bot settings\n"
        "/about – About this bot"
    )
    banner = get_force_banner() if 'get_force_banner' in globals() else None
    if banner:
        try:
            if isinstance(banner, str) and os.path.isfile(banner):
                await update.message.reply_photo(photo=InputFile(banner), caption=text, parse_mode="HTML")
            else:
                await update.message.reply_photo(photo=banner, caption=text, parse_mode="HTML")
            return
        except Exception:
            pass
    await update.message.reply_text(text, parse_mode="HTML")
async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_sub(update, context):
        return
    text = (
        "🤖 <b>Instant Video Cover Bot</b>\n\n"
        "✨ Features:\n"
        "• Instant thumbnail apply\n"
        "• One thumbnail per user\n"
        "• Fast & simple\n\n"
        "🛠 Powered by python-telegram-bot"
    )
    banner = get_force_banner() if 'get_force_banner' in globals() else None
    if banner:
        try:
            if isinstance(banner, str) and os.path.isfile(banner):
                await update.message.reply_photo(photo=InputFile(banner), caption=text, parse_mode="HTML")
            else:
                await update.message.reply_photo(photo=banner, caption=text, parse_mode="HTML")
            return
        except Exception:
            pass
    await update.message.reply_text(text, parse_mode="HTML")
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
    
    # Get original caption and preserve it
    original_caption = update.message.caption or ""
    if original_caption:
        new_caption = f"{original_caption}"
    else:
        new_caption = "✅ Cover Added."
    
    media = InputMediaVideo(media=video, caption=new_caption, supports_streaming=True, cover=cover, parse_mode="HTML")
    
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

    # Global error handler
    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Log all errors"""
        logger.error(f"🔴 ERROR: {context.error}", exc_info=context.error)

    app.add_error_handler(error_handler)

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
    
    # Register a general callback handler (handles verify, close, contact, etc.)
    # IMPORTANT: This should be registered LAST before error handler
    app.add_handler(CallbackQueryHandler(callback_handler))

    logger.info("✅ All handlers registered")
    logger.info("Bot starting (polling)")
    app.run_polling(
        allowed_updates=[
            "message",
            "callback_query",
        ],
        close_loop=False,
    )


if __name__ == "__main__":
    main()
