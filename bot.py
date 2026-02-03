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
from database import (
    save_thumbnail, get_thumbnail, delete_thumbnail, has_thumbnail,
    ban_user, unban_user, is_user_banned, get_total_users, get_banned_users_count, get_stats,
    format_log_message, log_new_user, log_user_banned, log_user_unbanned,
    log_thumbnail_set, log_thumbnail_removed
)
from telegram import MessageEntity

def bold_entities(text: str):
    """Return entities list to make full caption bold"""
    if not text:
        return None
    return [MessageEntity(type="bold", offset=0, length=len(text))]

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
LOG_CHANNEL_ID = os.environ.get("LOG_CHANNEL_ID")

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


# In-memory set of users who completed the verify step
verified_users = set()

"""═════════════════ LOGGING HELPER ═════════════════"""
async def send_log(context: ContextTypes.DEFAULT_TYPE, log_message: str) -> bool:
    """Send log message to log channel"""
    if not LOG_CHANNEL_ID:
        logger.debug("LOG_CHANNEL_ID not configured")
        return False
    
    try:
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=log_message,
            parse_mode="HTML"
        )
        logger.debug(f"✅ Log sent to channel {LOG_CHANNEL_ID}")
        return True
    except Exception as e:
        logger.error(f"❌ Error sending log to channel: {e}")
        return False


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

"""--------------------ADMIN CHECK-----------------"""

def fancy_text(text: str) -> str:
    """Convert text to fancy Unicode styled text (Bold Sans-Serif Italic)
    
    Example: 
        "Hello" -> "𝗛𝗲𝗹𝗹𝗼"
        "Join Our Bot" -> "𝗝ᴏɪɴ 𝗢ᴜʀ 𝗕ᴏᴛ"
    """
    # Unicode mapping for fancy bold italic sans-serif
    # Uppercase: A-Z (Mathematical Alphanumeric Symbols)
    uppercase = "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭"
    # Lowercase: a-z (Small caps style with lowercase)
    lowercase = "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘqʀsᴛᴜᴠᴡxʏᴢ"
    # Digits: 0-9
    digits = "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
    
    result = ""
    for char in text:
        if 'A' <= char <= 'Z':
            result += uppercase[ord(char) - ord('A')]
        elif 'a' <= char <= 'z':
            result += lowercase[ord(char) - ord('a')]
        elif '0' <= char <= '9':
            result += digits[ord(char) - ord('0')]
        else:
            result += char
    
    return result

def is_admin(user_id: int) -> bool:
    """Check if user is bot owner or admin"""
    admin_list = [OWNER_ID]
    # Add more admins here if needed from env
    return user_id in admin_list


async def check_admin(update: Update) -> bool:
    """Check if user is admin and send error if not"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return False
    return True


async def check_admin_and_banned(update: Update, user_id_to_check: int = None) -> tuple[bool, str]:
    """Check if admin and if target user is banned"""
    admin = await check_admin(update)
    if not admin:
        return False, None
    
    if user_id_to_check and is_user_banned(user_id_to_check):
        return True, "banned"  # User is admin and target is banned
    return True, None


"""------------------FORCE-SUB CHECK-----------------"""

async def check_force_sub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Check if user has verified through force-sub AND is still a member.
    Verifies membership for cached users to ensure they haven't left the channel.
    """
    user_id = update.effective_user.id

    # Owner bypass
    if user_id == OWNER_ID:
        return True

    # If no force-sub configured, allow access
    if not FORCE_SUB_CHANNEL_ID:
        return True

    # If user already verified through verify button, verify they're still a member
    if user_id in verified_users:
        logger.info(f"🔍 User {user_id} is cached - checking if still a member...")
        
        try:
            channel_id_str = str(FORCE_SUB_CHANNEL_ID).strip()
            
            # Parse channel ID
            try:
                if channel_id_str.startswith("-"):
                    channel_id = int(channel_id_str)
                else:
                    try:
                        channel_id = int(channel_id_str)
                    except ValueError:
                        channel_id = channel_id_str
            except Exception:
                channel_id = channel_id_str
            
            # Check current membership status
            member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            
            # If still a member, allow access
            if member.status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
                logger.info(f"✅ User {user_id} is still a member - access granted")
                return True
            
            # If no longer a member, remove from cache and show join prompt
            logger.warning(f"⚠️ User {user_id} left the channel - removing from cache")
            verified_users.discard(user_id)
            
        except Exception as e:
            logger.warning(f"Could not verify membership for cached user {user_id}: {e}")
            # On error, remove from cache to be safe
            verified_users.discard(user_id)
    
    logger.info(f"🔒 User {user_id} not verified or left channel - showing join prompt")

    # User not verified - show join prompt
    try:
        channel_id_str = str(FORCE_SUB_CHANNEL_ID).strip()
        logger.info(f"📌 Channel config: {channel_id_str}")
        
        # Parse channel ID
        try:
            if channel_id_str.startswith("-"):
                channel_chat_id = int(channel_id_str)
            else:
                try:
                    channel_chat_id = int(channel_id_str)
                except ValueError:
                    channel_chat_id = channel_id_str
        except Exception as parse_err:
            logger.error(f"❌ Channel ID parse error: {parse_err}")
            channel_chat_id = channel_id_str

        # Get channel info
        try:
            logger.info(f"📍 Getting chat info for {channel_chat_id}")
            chat = await context.bot.get_chat(channel_chat_id)
            channel_name = chat.title or chat.username or "Channel"
            logger.info(f"✅ Got chat info: {channel_name}")
            
            # Get invite link
            invite_link = None
            if chat.username:
                invite_link = f"https://t.me/{chat.username}"
            elif hasattr(chat, 'invite_link') and chat.invite_link:
                invite_link = chat.invite_link
            
            # Try to create invite link if doesn't exist
            if not invite_link:
                try:
                    link_obj = await context.bot.create_chat_invite_link(
                        chat_id=channel_chat_id, 
                        member_limit=1
                    )
                    invite_link = link_obj.invite_link
                except Exception as link_error:
                    logger.warning(f"Could not create invite link: {link_error}")
                    # Fallback to direct channel link
                    if str(channel_chat_id).startswith('-100'):
                        invite_link = f"https://t.me/c/{str(channel_chat_id)[4:]}"
                    else:
                        invite_link = f"https://t.me/{channel_chat_id}"
            
        except Exception as e:
            logger.error(f"Could not get chat info: {e}")
            return True  # Fail open

        # Build keyboard
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=invite_link)],
            [
                InlineKeyboardButton("✅ Verify", callback_data="check_fsub"),
                InlineKeyboardButton("✖️ Close", callback_data="close_banner")
            ]
        ])
        
        # Build prompt message
        prompt = (
            "🔒 <b>Access Restricted</b>\n\n"
            f"You must join <b>{channel_name}</b> to use this bot.\n\n"
            "👇 Click button below to join 👇"
        )

        try:
            if update.message:
                await update.message.reply_text(
                    prompt,
                    reply_markup=kb,
                    parse_mode="HTML"
                )
            elif update.callback_query:
                await update.callback_query.message.edit_text(
                    prompt,
                    reply_markup=kb,
                    parse_mode="HTML"
                )
            logger.info(f"🔒 Force-sub prompt shown to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to show prompt: {e}")
            return True

        return False

    except Exception as e:
        logger.error(f"Force-Sub Error: {e}", exc_info=True)
        return True  # Fail open




async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback query with proper force-sub verification"""
    query = update.callback_query
    
    logger.info(f"🔵 CALLBACK | Data: {query.data}")
    
    if not query or not query.data:
        logger.error("❌ Invalid query!")
        return

    user_id = query.from_user.id
    logger.info(f"👤 User ID: {user_id} | Channel ID Config: {FORCE_SUB_CHANNEL_ID}")
    
    # Handle force-sub verification button
    if query.data == "check_fsub":
        logger.info(f"🔍 Verify button clicked by user {user_id}")
        
        if not FORCE_SUB_CHANNEL_ID:
            logger.warning("⚠️ FORCE_SUB_CHANNEL_ID not configured")
            await query.answer("✅ Bot configured successfully!", show_alert=False)
            await open_home(update, context)
            return
        
        try:
            # Parse channel ID - make sure we handle it as string first
            channel_id_str = str(FORCE_SUB_CHANNEL_ID).strip()
            logger.info(f"📌 Channel ID string: {channel_id_str}")
            
            # Try to convert to int
            try:
                if channel_id_str.startswith("-"):
                    channel_id = int(channel_id_str)
                else:
                    # Try as int first, otherwise keep as string
                    try:
                        channel_id = int(channel_id_str)
                    except ValueError:
                        channel_id = channel_id_str
            except Exception as parse_error:
                logger.error(f"❌ Failed to parse channel ID: {parse_error}")
                channel_id = channel_id_str
            
            logger.info(f"🔎 Checking membership for user {user_id} in channel {channel_id}")
            
            # Direct membership check
            try:
                member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
                logger.info(f"📊 Member status: {member.status}")
            except Exception as member_error:
                logger.error(f"❌ Error checking membership: {member_error}")
                await query.answer("❌ Channel check failed! Try again later.", show_alert=True)
                return
            
            # Check if user is member
            if member.status in (
                ChatMemberStatus.MEMBER,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.OWNER
            ):
                verified_users.add(user_id)
                logger.info(f"✅ User {user_id} verified successfully with status {member.status}")
                
                # Show success alert
                await query.answer("✅ Channel verified successfully!", show_alert=False)
                
                # Try to delete verification message
                try:
                    await query.message.delete()
                    logger.info(f"🗑️ Verification message deleted")
                except Exception as del_error:
                    logger.warning(f"Could not delete message: {del_error}")
                
                # Show home screen
                logger.info(f"🏠 Showing home screen for user {user_id}")
                await open_home(update, context)
                return
            
            # User not in channel yet
            logger.warning(f"⚠️ User {user_id} not a member. Status: {member.status}")
            await query.answer("❌ Join the channel first!\n\nPlease join the channel and then click Verify.", show_alert=True)
            return
            
        except Exception as e:
            logger.error(f"❌ Verification error: {type(e).__name__}: {e}", exc_info=True)
            await query.answer("❌ Verification failed!\n\nPlease make sure you joined the channel first.", show_alert=True)
            return
    
    # Handle close button
    if query.data == "close_banner":
        logger.info(f"❌ User {user_id} closed banner")
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
    
    # Handle admin callbacks
    if query.data == "admin_stats":
        if not is_admin(user_id):
            await query.answer("❌ Unauthorized", show_alert=True)
            return
        await query.answer()
        stats = get_stats()
        text = (
            "📊 <b>Bot Statistics</b>\n\n"
            f"👥 Total Users: <b>{stats['total_users']}</b>\n"
            f"🚫 Banned Users: <b>{stats['banned_users']}</b>\n"
            f"🖼 Users with Thumbnail: <b>{stats['users_with_thumbnail']}</b>"
        )
        back_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]
        ])
        try:
            msg = query.message
            if getattr(msg, "photo", None):
                await msg.edit_caption(text, reply_markup=back_kb, parse_mode="HTML")
            else:
                await msg.edit_text(text, reply_markup=back_kb, parse_mode="HTML")
        except Exception:
            pass
        return
    
    if query.data == "admin_status":
        if not is_admin(user_id):
            await query.answer("❌ Unauthorized", show_alert=True)
            return
        await query.answer()
        try:
            import psutil
            import time
            cpu_percent = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory()
            text = (
                "⏱️ <b>Bot Status</b>\n\n"
                f"🟢 Status: <b>Online</b>\n\n"
                f"🖥 <b>System Resources:</b>\n"
                f"CPU: <b>{cpu_percent}%</b>\n"
                f"RAM: <b>{ram.percent}%</b>"
            )
        except ImportError:
            text = "⏱️ <b>Bot Status</b>\n\n🟢 Status: <b>Online</b>"
        
        back_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]
        ])
        try:
            msg = query.message
            if getattr(msg, "photo", None):
                await msg.edit_caption(text, reply_markup=back_kb, parse_mode="HTML")
            else:
                await msg.edit_text(text, reply_markup=back_kb, parse_mode="HTML")
        except Exception:
            pass
        return
    
    if query.data == "admin_ban":
        if not is_admin(user_id):
            await query.answer("❌ Unauthorized", show_alert=True)
            return
        await query.answer()
        text = "🚫 <b>Ban User</b>\n\nSend user ID to ban (or /ban userid reason)"
        back_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]
        ])
        await context.bot.send_message(chat_id=user_id, text=text, reply_markup=back_kb, parse_mode="HTML")
        return
    
    if query.data == "admin_unban":
        if not is_admin(user_id):
            await query.answer("❌ Unauthorized", show_alert=True)
            return
        await query.answer()
        text = "✅ <b>Unban User</b>\n\nSend user ID to unban (or /unban userid)"
        back_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]
        ])
        await context.bot.send_message(chat_id=user_id, text=text, reply_markup=back_kb, parse_mode="HTML")
        return
    
    if query.data == "admin_broadcast":
        if not is_admin(user_id):
            await query.answer("❌ Unauthorized", show_alert=True)
            return
        await query.answer()
        text = "📢 <b>Broadcast Message</b>\n\nSend message to broadcast to all users"
        back_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]
        ])
        await context.bot.send_message(chat_id=user_id, text=text, reply_markup=back_kb, parse_mode="HTML")
        return
    
    if query.data == "admin_back":
        if not is_admin(user_id):
            await query.answer("❌ Unauthorized", show_alert=True)
            return
        await query.answer()
        text = (
            "🛡️ " + fancy_text("Admin Control Panel") + "\n\n"
            "Choose an option:"
        )
        admin_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"),
             InlineKeyboardButton("⏱️ Status", callback_data="admin_status")],
            [InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban"),
             InlineKeyboardButton("✅ Unban User", callback_data="admin_unban")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
             InlineKeyboardButton("⬅️ Back", callback_data="menu_back")],
        ])
        try:
            msg = query.message
            if getattr(msg, "photo", None):
                await msg.edit_caption(text, reply_markup=admin_kb, parse_mode="HTML")
            else:
                await msg.edit_text(text, reply_markup=admin_kb, parse_mode="HTML")
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
                "👋 " + fancy_text("Welcome to Instant Cover Bot") + "\n\n"
                "📸 Send a <b>photo</b> to set thumbnail\n"
                "🎥 Send a <b>video</b> to get it with cover\n\n"
                "🧩 <b>Commands:</b>\n"
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
                    "ℹ️ " + fancy_text("Help Menu") + "\n\n"
                    "1️⃣ Send a <b>photo</b> → thumbnail saved\n"
                    "2️⃣ Send a <b>video</b> → cover applied\n\n"
                    "<b>Commands:</b>\n"
                    "/remove – Remove saved thumbnail\n"
                    "/settings – View bot settings\n"
                    "/about – About this bot"
                )
            elif key == "about":
                text = (
                    "🤖 " + fancy_text("Instant Video Cover Bot") + "\n\n"
                    "✨ Features:\n"
                    "• Instant thumbnail apply\n"
                    "• One thumbnail per user\n"
                    "• Fast & simple\n\n"
                    "🛠 Powered by python-telegram-bot"
                )
            elif key == "settings":
                uid = query.from_user.id
                text = (
                    "⚙️ " + fancy_text("Settings") + "\n\n"
                    "Choose what you want to manage:"
                )
                # Add settings submenus buttons
                settings_kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🖼 Thumbnails", callback_data="submenu_thumbnails")],
                    [InlineKeyboardButton("⬅️ Back", callback_data="menu_back")]
                ])
                try:
                    msg = query.message
                    if getattr(msg, "photo", None):
                        await msg.edit_caption(text, reply_markup=settings_kb, parse_mode="HTML")
                    else:
                        await msg.edit_text(text, reply_markup=settings_kb, parse_mode="HTML")
                except Exception as e:
                    logger.debug(f"Settings menu edit error: {e}")
                return
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
            
            # Add back button to all menus (except settings which has its own)
            if key != "settings":
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
    
    # Handle Thumbnails submenu
    if query.data == "submenu_thumbnails":
        await query.answer()
        uid = query.from_user.id
        thumb_status = "✅ Saved" if has_thumbnail(uid) else "❌ Not Saved"
        text = (
            "🖼 <b>Thumbnails</b>\n\n"
            f"Status: <b>{thumb_status}</b>\n\n"
            "Manage your video thumbnails:"
        )
        thumb_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💾 Save Thumbnail", callback_data="thumb_save_info"),
             InlineKeyboardButton("👁️ Show Thumbnail", callback_data="thumb_show")],
            [InlineKeyboardButton("🗑️ Delete Thumbnail", callback_data="thumb_delete"),
             InlineKeyboardButton("⬅️ Back", callback_data="menu_settings")]
        ])
        try:
            msg = query.message
            if getattr(msg, "photo", None):
                await msg.edit_caption(text, reply_markup=thumb_kb, parse_mode="HTML")
            else:
                await msg.edit_text(text, reply_markup=thumb_kb, parse_mode="HTML")
        except Exception as e:
            logger.debug(f"Thumbnails submenu edit error: {e}")
        return
    
    
    # Handle thumbnail operations
    if query.data == "thumb_save_info":
        await query.answer()
        text = (
            "💾 <b>Save Thumbnail</b>\n\n"
            "To save a thumbnail:\n"
            "1️⃣ Send a photo to the bot\n"
            "2️⃣ The thumbnail will be saved automatically\n"
            "3️⃣ Later, send a video to apply the cover\n\n"
            "Your thumbnail will be saved in the database!"
        )
        back_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back", callback_data="submenu_thumbnails")]
        ])
        try:
            msg = query.message
            if getattr(msg, "photo", None):
                await msg.edit_caption(text, reply_markup=back_kb, parse_mode="HTML")
            else:
                await msg.edit_text(text, reply_markup=back_kb, parse_mode="HTML")
        except Exception:
            pass
        return
    
    if query.data == "thumb_show":
        await query.answer()
        photo_id = get_thumbnail(user_id)
        if photo_id:
            text = "👁️ <b>Your Saved Thumbnail</b>"
            back_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="submenu_thumbnails")]
            ])
            try:
                await query.message.delete()
            except Exception:
                pass
            try:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=photo_id,
                    caption=text,
                    reply_markup=back_kb,
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Error sending thumbnail: {e}")
        else:
            text = "❌ <b>No Thumbnail Saved</b>\n\nSend a photo first to save a thumbnail."
            back_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="submenu_thumbnails")]
            ])
            try:
                msg = query.message
                if getattr(msg, "photo", None):
                    await msg.edit_caption(text, reply_markup=back_kb, parse_mode="HTML")
                else:
                    await msg.edit_text(text, reply_markup=back_kb, parse_mode="HTML")
            except Exception:
                pass
        return
    
    if query.data == "thumb_delete":
        await query.answer()
        if delete_thumbnail(user_id):
            text = "✅ <b>Thumbnail Deleted</b>\n\nYour thumbnail has been removed successfully."
        else:
            text = "❌ <b>No Thumbnail to Delete</b>\n\nYou don't have a saved thumbnail."
        back_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back", callback_data="submenu_thumbnails")]
        ])
        try:
            msg = query.message
            if getattr(msg, "photo", None):
                await msg.edit_caption(text, reply_markup=back_kb, parse_mode="HTML")
            else:
                await msg.edit_text(text, reply_markup=back_kb, parse_mode="HTML")
        except Exception:
            pass
        return
    
    logger.warning(f"⚠️ Unknown callback: {query.data}")
    try:
        await query.answer("Unknown action", show_alert=False)
    except Exception:
        pass


"""---------------------- Menus--------------------- """

async def open_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        fancy_text("Welcome to Instant Cover Bot") + "\n\n"
        "📸 Send a <b>photo</b> to set thumbnail\n"
        "🎥 Send a <b>video</b> to get it with cover\n\n"
        "🧩 <b>Commands:</b>\n"
        "/help – How to use bot\n"
        "/settings – Bot settings\n"
        "/about – About this bot"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("❓ Help", callback_data="menu_help"),
         InlineKeyboardButton("ℹ️ About", callback_data="menu_about")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
         InlineKeyboardButton("👨‍💻 Developer", callback_data="menu_developer")],
    ])

    if update.callback_query:
        msg = update.callback_query.message
        try:
            if msg.photo:
                await msg.edit_caption(text, reply_markup=kb, parse_mode="HTML")
            else:
                await msg.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except:
            await context.bot.send_message(
                chat_id=msg.chat.id,
                text=text,
                reply_markup=kb,
                parse_mode="HTML"
            )
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    first_name = update.effective_user.first_name or "User"
    
    # Check if user is banned
    if is_user_banned(user_id):
        await update.message.reply_text("🚫 <b>You are banned from using this bot.</b>", parse_mode="HTML")
        return
    
    # Log new user (if first time)
    user_check = get_thumbnail(user_id)
    if user_check is None:
        # New user - log it
        log_data = log_new_user(user_id, username, first_name)
        log_msg = format_log_message(user_id, username, log_data["action"], log_data.get("details", ""))
        await send_log(context, log_msg)
    
    # Check force-sub first
    if not await check_force_sub(update, context):
        logger.warning(f"❌ User {user_id} blocked by force-sub check")
        return
    
    text = (
        fancy_text("Welcome to Instant Cover Bot") + "\n\n"
        "📸 Send a <b>photo</b> to set thumbnail\n"
        "🎥 Send a <b>video</b> to get it with cover\n\n"
        "🧩 <b>Commands:</b>\n"
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
    
    # Add admin panel button if user is admin
    if is_admin(user_id):
        kb_rows.append([InlineKeyboardButton("🛡️ Admin Panel", callback_data="admin_back")])
    
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
    # Show thumbnail status
    thumb_status = "✅ Saved" if has_thumbnail(user_id) else "❌ Not Saved"
    
    text = (
        "⚙️ <b>Settings</b>\n\n"
        f"🖼 Thumbnail: <b>{thumb_status}</b>\n\n"
        "Choose what you want to manage:"
    )
    settings_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼 Thumbnails", callback_data="submenu_thumbnails")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu_back")]
    ])
    await update.message.reply_text(text, reply_markup=settings_kb, parse_mode="HTML")


async def remover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_sub(update, context):
        return
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Unknown"
    
    if delete_thumbnail(user_id):
        # Log thumbnail removal
        log_data = log_thumbnail_removed(user_id, username)
        log_msg = format_log_message(user_id, username, log_data["action"])
        await send_log(context, log_msg)
        
        return await update.message.reply_text("✅ Thumbnail Removed.", reply_to_message_id=update.message.message_id)
    await update.message.reply_text("⚠️ First Add A Thumbnail.", reply_to_message_id=update.message.message_id)

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_sub(update, context):
        return
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Unknown"
    photo_id = update.message.photo[-1].file_id
    
    # Check if replacing
    old_thumbnail = get_thumbnail(user_id)
    is_replace = old_thumbnail is not None
    
    save_thumbnail(user_id, photo_id)
    logger.info(f"✅ Thumbnail saved to MongoDB for user {user_id}")
    
    # Log thumbnail action
    log_data = log_thumbnail_set(user_id, username, is_replace=is_replace)
    log_msg = format_log_message(user_id, username, log_data["action"])
    await send_log(context, log_msg)
    
    await update.message.reply_text("✅ New Thumbnail Saved.", reply_to_message_id=update.message.message_id)

async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_sub(update, context):
        return
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "No Username"
    cover = get_thumbnail(user_id)
    if not cover:
        return await update.message.reply_text("❌ Send A Photo First.", reply_to_message_id=update.message.message_id)
    msg = await update.message.reply_text("🔄 Adding Cover Please Wait...", reply_to_message_id=update.message.message_id)
    
    video = update.message.video.file_id
    
    # Get original caption and preserve it
    original_caption = update.message.caption or ""
    new_caption = original_caption
    caption_entities = bold_entities(original_caption)
    
    media = InputMediaVideo(media=video, caption=new_caption,caption_entities=caption_entities, supports_streaming=True, cover=cover)
    
    try:
        # Edit message with video and cover
        await context.bot.edit_message_media(chat_id=update.effective_chat.id, message_id=msg.message_id, media=media)
        
        # Forward video to log channel
        if LOG_CHANNEL_ID:
            try:
                log_caption = (
                    f"🎥 <b>User Video Received</b>\n\n"
                    f"👤 User ID: {user_id}\n"
                    f"📌 Username: @{username}\n"
                    f"📝 Caption: {original_caption or 'No Caption'}\n"
                )
                await context.bot.send_video(
                    chat_id=LOG_CHANNEL_ID,
                    video=video,
                    caption=log_caption,
                    supports_streaming=True,
                    thumbnail=cover,
                    parse_mode="HTML"
                )
                logger.debug(f"✅ Video logged to channel for user {user_id}")
            except Exception as e:
                logger.error(f"❌ Error forwarding video to log channel: {e}")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to send video with cover:\n{e}")


async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != OWNER_ID:
        return await update.message.reply_text("❌ You are not authorized.")

    msg = await update.message.reply_text("🔄 Checking for updates from upstream...")

    try:
        success = update_from_upstream()

        if not success:
            await msg.edit_text(
                "❌ <b>Update Failed</b>\n\n"
                "Could not fetch updates from upstream.\n"
                "Please check:\n"
                "• UPSTREAM_REPO is correct\n"
                "• UPSTREAM_BRANCH is correct\n"
                "• Internet connection is active\n\n"
                "Check logs for details.",
                parse_mode="HTML"
            )
            logger.error(f"Update failed - bot not restarting")
            return

        # Update successful - now restart
        await msg.edit_text(
            "✅ <b>Update Successful!</b>\n\n"
            "🔄 Restarting bot with new changes...\n"
            "<i>Please wait...</i>",
            parse_mode="HTML"
        )
        
        logger.info("✅ Update completed successfully. Restarting bot...")
        # Give time for message to be sent
        await asyncio.sleep(1)
        
        # Restart the bot
        os.execv(sys.executable, [sys.executable] + sys.argv)
        
    except Exception as e:
        logger.error(f"❌ Error during restart/update: {e}")
        await msg.edit_text(
            f"❌ <b>Error During Update</b>\n\n"
            f"An unexpected error occurred:\n"
            f"<code>{str(e)[:100]}</code>\n\n"
            f"Check logs for full details.",
            parse_mode="HTML"
        )


"""═══════════════════ ADMIN COMMANDS ═══════════════════"""

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin control panel"""
    if not await check_admin(update):
        return
    
    text = (
        "🛡️ " + fancy_text("Admin Control Panel") + "\n\n"
        "Choose an option:"
    )
    admin_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"),
         InlineKeyboardButton("⏱️ Status", callback_data="admin_status")],
        [InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban"),
         InlineKeyboardButton("✅ Unban User", callback_data="admin_unban")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
         InlineKeyboardButton("⬅️ Back", callback_data="menu_back")],
    ])
    await update.message.reply_text(text, reply_markup=admin_kb, parse_mode="HTML")


async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user - usage: /ban user_id reason"""
    if not await check_admin(update):
        return
    
    args = update.message.text.split(None, 2)
    if len(args) < 2:
        return await update.message.reply_text(
            "❌ Usage: /ban <user_id> [reason]\n"
            "Example: /ban 123456789 Spam"
        )
    
    try:
        user_id = int(args[1])
        reason = args[2] if len(args) > 2 else "No reason"
        
        if ban_user(user_id, reason):
            await update.message.reply_text(
                f"✅ <b>User {user_id} Banned</b>\n"
                f"Reason: {reason}",
                parse_mode="HTML"
            )
            
            # Log ban action
            log_data = log_user_banned(user_id, "User", reason)
            log_msg = format_log_message(user_id, "User", log_data["action"], log_data.get("details", ""))
            await send_log(context, log_msg)
        else:
            await update.message.reply_text("❌ Failed to ban user")
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unban a user - usage: /unban user_id"""
    if not await check_admin(update):
        return
    
    args = update.message.text.split()
    if len(args) < 2:
        return await update.message.reply_text(
            "❌ Usage: /unban <user_id>\n"
            "Example: /unban 123456789"
        )
    
    try:
        user_id = int(args[1])
        if unban_user(user_id):
            await update.message.reply_text(f"✅ User {user_id} Unbanned")
            
            # Log unban action
            log_data = log_user_unbanned(user_id, "User")
            log_msg = format_log_message(user_id, "User", log_data["action"])
            await send_log(context, log_msg)
        else:
            await update.message.reply_text("❌ Failed to unban user")
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics"""
    if not await check_admin(update):
        return
    
    stats = get_stats()
    text = (
        "📊 <b>Bot Statistics</b>\n\n"
        f"👥 Total Users: <b>{stats['total_users']}</b>\n"
        f"🚫 Banned Users: <b>{stats['banned_users']}</b>\n"
        f"🖼 Users with Thumbnail: <b>{stats['users_with_thumbnail']}</b>"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot status (uptime, CPU, RAM)"""
    if not await check_admin(update):
        return
    
    import psutil
    import time
    
    try:
        # Bot uptime (from when bot.py started)
        uptime_seconds = time.time() - context.bot_data.get('start_time', time.time())
        uptime_hours = int(uptime_seconds // 3600)
        uptime_mins = int((uptime_seconds % 3600) // 60)
        
        # System stats
        cpu_percent = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        ram_percent = ram.percent
        
        text = (
            "⏱️ <b>Bot Status</b>\n\n"
            f"🟢 Status: <b>Online</b>\n"
            f"⏰ Uptime: <b>{uptime_hours}h {uptime_mins}m</b>\n\n"
            f"🖥 <b>System Resources:</b>\n"
            f"CPU: <b>{cpu_percent}%</b>\n"
            f"RAM: <b>{ram_percent}%</b> ({ram.used // (1024**2)} MB / {ram.total // (1024**2)} MB)"
        )
        await update.message.reply_text(text, parse_mode="HTML")
    except ImportError:
        text = (
            "⏱️ <b>Bot Status</b>\n\n"
            f"🟢 Status: <b>Online</b>\n\n"
            "⚠️ <b>Note:</b> Install <code>psutil</code> for system stats\n"
            "Run: <code>pip install psutil</code>"
        )
        await update.message.reply_text(text, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")



async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    if not await check_force_sub(update, context):
        return
    
    # Ignore all text messages (don't respond)


"""-----------CALLBAck Hnadlers--------"""


def main() -> None:
    app = Application.builder().token(TOKEN).build()

    # Global error handler
    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Log all errors"""
        logger.error(f"🔴 ERROR: {context.error}", exc_info=context.error)

    app.add_error_handler(error_handler)
    
    # Setup bot commands on startup
    async def setup_commands(app: Application) -> None:
        """Setup bot commands menu"""
        from telegram import BotCommand
        
        commands = [
            BotCommand("start", "🏠 Start bot"),
            BotCommand("help", "ℹ️ How to use bot"),
            BotCommand("about", "🤖 About bot"),
            BotCommand("settings", "⚙️ Bot settings"),
            BotCommand("remove", "🗑️ Remove thumbnail"),
            BotCommand("admin", "🛡️ Admin panel"),
            BotCommand("ban", "🚫 Ban user"),
            BotCommand("unban", "✅ Unban user"),
            BotCommand("stats", "📊 Bot statistics"),
            BotCommand("status", "⏱️ Bot status"),
        ]
        
        try:
            await app.bot.set_my_commands(commands)
            logger.info("✅ Bot commands configured successfully")
        except Exception as e:
            logger.error(f"❌ Error setting bot commands: {e}")
    
    # Register post_init callback to setup commands
    app.post_init = setup_commands

    # Command handlers (MUST be registered FIRST before text handler)
    app.add_handler(CommandHandler("start", start, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("help", help_cmd, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("about", about, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("settings", settings, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("remove", remover, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("restart", restart, filters=filters.ChatType.PRIVATE))
    
    # Admin commands
    app.add_handler(CommandHandler("admin", admin_menu, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("ban", ban_cmd, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("unban", unban_cmd, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("stats", stats_cmd, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("status", status_cmd, filters=filters.ChatType.PRIVATE))

    # Photo and video handlers (private chats only via filters)
    app.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, photo_handler))
    app.add_handler(MessageHandler(filters.VIDEO & filters.ChatType.PRIVATE, video_handler))
    
    # Text handler for dump channel ID capture (MUST be LAST - only non-command text)
    # Add filter to exclude commands (messages starting with /)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, text_handler))
    
    # Register callback handler (handles all callbacks)
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
