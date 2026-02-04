
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all inline button callbacks"""
    try:
        query = update.callback_query
        data = query.data
        user_id = update.effective_user.id
        
        await query.answer()
        
        # ═══════════ Menu Callbacks (menu_*) ═══════════
        if data.startswith("menu_"):
            key = data.split("menu_")[1]
            
            # Back to home
            if key == "back":
                await open_home(update, context)
                return
            
            # Help menu
            elif key == "help":
                text = (
                    "ℹ️ <b>Help Menu</b>\n\n"
                    "1️⃣ Send A <b>Photo</b> → Thumbnail Saved\n"
                    "2️⃣ Send A <b>Video</b> → Cover Applied\n\n"
                    "<b>Commands:</b>\n"
                    "/remove – Remove Saved Thumbnail\n"
                    "/settings – View Bot Settings\n"
                    "/about – About This Bot"
                )
            
            # About menu
            elif key == "about":
                text = (
                    "🤖 <b>Instant Video Cover Bot</b>\n\n"
                    "✨ Features:\n"
                    "• Instant Thumbnail Apply\n"
                    "• One Thumbnail Per User\n"
                    "• Fast & Simple\n\n"
                    "🛠 Powered By Python-Telegram-Bot"
                )
            
            # Settings menu
            elif key == "settings":
                text = (
                    "⚙️ <b>Settings</b>\n\n"
                    "Choose What You Want To Manage:"
                )
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
            
            # Developer info
            elif key == "developer":
                dev_contact = f"https://t.me/{OWNER_ID}" if OWNER_ID else "Contact Admin"
                text = (
                    "👨‍💻 <b>Developer</b>\n\n"
                    f"Contact: {dev_contact}\n"
                    "If You Need Help, Reach Out To The Developer."
                )
            
            else:
                text = "ℹ️ <b>Info</b>\n\nNo Information Available."
            
            # Add back button
            if key != "settings":
                back_kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back", callback_data="menu_back")]
                ])
                try:
                    msg = query.message
                    if getattr(msg, "photo", None):
                        await msg.edit_caption(text, reply_markup=back_kb, parse_mode="HTML")
                    else:
                        await msg.edit_text(text, reply_markup=back_kb, parse_mode="HTML")
                except Exception as e:
                    logger.debug(f"Menu edit error: {e}")
            return
        
        # ═══════════ Thumbnail Submenu ═══════════
        if data == "submenu_thumbnails":
            thumb_status = "✅ Saved" if has_thumbnail(user_id) else "❌ Not Saved"
            text = (
                "🖼️ <b>Thumbnail Manager</b>\n\n"
                f"<b>Current Status:</b> {thumb_status}\n\n"
                "📚 <b>Available Actions:</b>\n\n"
                "💾 Save Thumbnail - Upload A New Photo\n"
                "👁️ Show Thumbnail - Preview Your Cover\n"
                "🗑️ Delete Thumbnail - Remove Your Cover"
            )
            thumb_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("💾 Save", callback_data="thumb_save_info"),
                 InlineKeyboardButton("👁️ Show", callback_data="thumb_show")],
                [InlineKeyboardButton("🗑️ Delete", callback_data="thumb_delete"),
                 InlineKeyboardButton("⬅️ Back", callback_data="menu_settings")]
            ])
            try:
                msg = query.message
                if getattr(msg, "photo", None):
                    await msg.edit_caption(text, reply_markup=thumb_kb, parse_mode="HTML")
                else:
                    await msg.edit_text(text, reply_markup=thumb_kb, parse_mode="HTML")
            except Exception as e:
                logger.debug(f"Thumbnails submenu error: {e}")
            return
        
        # ═══════════ Thumbnail Operations ═══════════
        if data == "thumb_save_info":
            text = (
                "💾 <b>Save Your Thumbnail</b>\n\n"
                "<b>📸 How It Works:</b>\n\n"
                "Step 1️⃣: Send A Photo\n"
                "Go Back And Send Any Photo To The Bot\n\n"
                "Step 2️⃣: Automatic Save\n"
                "The Thumbnail Is Saved Automatically\n\n"
                "Step 3️⃣: Ready To Use\n"
                "Send Any Video And Cover Applies!\n\n"
                "💡 <b>Tips:</b>\n"
                "• Use High-Resolution Images\n"
                "• Max 5MB File Size\n\n"
                "Ready? Send Your Photo Now! 📸"
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
            context.user_data['waiting_for_thumb'] = True
            return
        
        if data == "thumb_show":
            photo_id = get_thumbnail(user_id)
            if photo_id:
                text = "👁️ <b>Your Current Thumbnail</b>\n\nThis Is The Photo That Will Be Applied To Your Videos."
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
                text = "❌ <b>No Thumbnail Saved Yet</b>\n\nYou Haven't Uploaded A Thumbnail. Send A Photo To The Bot To Create One!"
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
        
        if data == "thumb_delete":
            if delete_thumbnail(user_id):
                text = "✅ <b>Thumbnail Deleted Successfully</b>\n\nYour Saved Thumbnail Has Been Removed."
            else:
                text = "⚠️ <b>No Thumbnail Found</b>\n\nYou Don't Have A Saved Thumbnail Yet."
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
        
       
