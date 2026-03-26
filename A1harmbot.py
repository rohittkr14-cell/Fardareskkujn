from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from telegram.constants import ParseMode
import html

# ================= CONFIG =================
TOKEN = "8743013698:AAHbatOmi4eRNShDcBBZIPa4VwskGZPTz4s"

ADMIN_IDS = [7691071175, 6587658540]

CHANNEL_ID = -1003344628533
GC_IDS = [-1003730637965]

STATE = {}

# ================= UTILS =================
def reset(uid):
    STATE.pop(uid, None)

def esc(text):
    return html.escape(str(text))

def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("➕ Create Report")]],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Choose an option..."
    )

def report_type_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🚨 IMP REPORT")],
            [KeyboardButton("⚠️ SCM REPORT")],
            [KeyboardButton("❌ Cancel")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Select report type..."
    )

def cancel_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("❌ Cancel")]],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Type your answer..."
    )

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type != "private":
        return

    uid = update.effective_user.id
    reset(uid)

    await update.message.reply_text(
        "<b>👋 Welcome</b>\n\n"
        "<b>Use the keyboard below to create a report.</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard()
    )

# ================= CREATE REPORT =================
async def create_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type != "private":
        return

    uid = update.effective_user.id
    reset(uid)

    await update.message.reply_text(
        "<b>Select report type:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=report_type_keyboard()
    )

# ================= SEND TO ADMINS =================
async def send_admin(uid, context):
    d = STATE[uid]

    if d["type"] == "SCM":
        text = (
            "<b>🚨 SCAM REPORT</b>\n\n"
            f"<b>❌ Username:</b> {esc(d['scm_username'])}\n"
            f"<b>🆔 User ID:</b> <code>{esc(d['scm_id'])}</code>\n"
            f"<b>💰 Amount:</b> <code>{esc(d['amount'])}</code>\n"
            f"<b>📝 Statement:</b>\n{esc(d['statement'])}\n\n"
            f"<b>🔗 Proof:</b> {esc(d['proof'])}"
        )
    else:
        text = (
            "<b>🚨 IMP REPORT</b>\n\n"
            f"<b>❌ Fake Username:</b> {esc(d['fake_username'])}\n"
            f"<b>🆔 Fake ID:</b> <code>{esc(d['fake_id'])}</code>\n\n"
            f"<b>✅ Real Username:</b> {esc(d['real_username'])}\n"
            f"<b>🆔 Real ID:</b> <code>{esc(d['real_id'])}</code>"
        )

    kb = [[
        InlineKeyboardButton("✅ Approve", callback_data=f"approve_{uid}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{uid}")
    ]]

    for admin in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(kb),
                disable_web_page_preview=True
            )
        except Exception as e:
            print(f"Admin send error to {admin}: {e}")

# ================= ADMIN ACTION =================
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return

    await q.answer()

    if q.from_user.id not in ADMIN_IDS:
        return

    try:
        action, uid = q.data.split("_")
        uid = int(uid)
    except:
        await q.message.edit_text(
            "<b>❌ Invalid action.</b>",
            parse_mode=ParseMode.HTML
        )
        return

    if uid not in STATE:
        await q.message.edit_text(
            "<b>❌ Report expired or already processed.</b>",
            parse_mode=ParseMode.HTML
        )
        return

    d = STATE[uid]

    if action == "approve":
        target_id = int(d["scm_id"] if d["type"] == "SCM" else d["fake_id"])

        # -------- BAN + GROUP MESSAGE --------
        for gc in GC_IDS:
            try:
                await context.bot.ban_chat_member(gc, target_id)

                if d["type"] == "SCM":
                    gc_text = (
                        "<b>🚫 USER BANNED</b>\n\n"
                        f"<b>User ID:</b> <code>{target_id}</code>\n"
                        "<b>Reason:</b> <b>Scammer Report Approved</b>"
                    )
                else:
                    gc_text = (
                        "<b>🚫 USER BANNED</b>\n\n"
                        f"<b>User ID:</b> <code>{target_id}</code>\n"
                        "<b>Reason:</b> <b>Impersonation Report Approved</b>"
                    )

                await context.bot.send_message(
                    chat_id=gc,
                    text=gc_text,
                    parse_mode=ParseMode.HTML
                )

            except Exception as e:
                print(f"GC ban/send error in {gc}: {e}")

        # -------- CHANNEL POST --------
        if d["type"] == "SCM":
            caption = (
                "<b>🚨 SCAMMER FLAGGED</b>\n\n"
                f"<b>❌ Username:</b> {esc(d['scm_username'])}\n"
                f"<b>🆔 Telegram ID:</b> <code>{esc(d['scm_id'])}</code>\n"
                f"<b>💰 Amount:</b> <code>{esc(d['amount'])}</code>\n\n"
                "<b>⚠️ Stay Alert & Avoid Deals Without Verification</b>"
            )

            kb = [[
                InlineKeyboardButton(
                    "View Profile",
                    url=f"tg://user?id={d['scm_id']}"
                ),
                InlineKeyboardButton(
                    "View Proof",
                    url=d["proof"]
                )
            ]]

        else:
            caption = (
                "<b>🚨 IMPERSONATOR FLAGGED</b>\n\n"
                f"<b>❌ Fake:</b> {esc(d['fake_username'])} (<code>{esc(d['fake_id'])}</code>)\n"
                f"<b>✅ Real:</b> {esc(d['real_username'])} (<code>{esc(d['real_id'])}</code>)\n\n"
                "<b>⚠️ Stay Safe From Fake Accounts</b>"
            )

            kb = [[
                InlineKeyboardButton(
                    "View Real Profile",
                    url=f"tg://user?id={d['real_id']}"
                ),
                InlineKeyboardButton(
                    "View Fake Profile",
                    url=f"tg://user?id={d['fake_id']}"
                )
            ]]

        try:
            with open("pfp.jpg", "rb") as photo:
                await context.bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=photo,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(kb)
                )
        except Exception as e:
            print(f"Photo send error: {e}")
            try:
                await context.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(kb)
                )
            except Exception as e2:
                print(f"Channel text send error: {e2}")

        await q.message.edit_text(
            "<b>✅ Approved successfully.</b>",
            parse_mode=ParseMode.HTML
        )
        reset(uid)

    elif action == "reject":
        await q.message.edit_text(
            "<b>❌ Report rejected.</b>",
            parse_mode=ParseMode.HTML
        )
        reset(uid)

# ================= USER INPUT =================
async def user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type != "private":
        return

    uid = update.effective_user.id
    text = (update.message.text or "").strip()

    # -------- CANCEL --------
    if text == "❌ Cancel":
        reset(uid)
        return await update.message.reply_text(
            "<b>❌ Report cancelled.</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_keyboard()
        )

    # -------- MAIN MENU --------
    if text == "➕ Create Report":
        return await create_report(update, context)

    # -------- REPORT TYPE --------
    if text == "⚠️ SCM REPORT":
        STATE[uid] = {"type": "SCM", "step": "scm_username"}
        return await update.message.reply_text(
            "<b>❌ Send scammer username</b>\n\n"
            "<b>Example:</b> <code>@username</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=cancel_keyboard()
        )

    if text == "🚨 IMP REPORT":
        STATE[uid] = {"type": "IMP", "step": "imp_fake_username"}
        return await update.message.reply_text(
            "<b>❌ Send fake (impersonator) username</b>\n\n"
            "<b>Example:</b> <code>@username</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=cancel_keyboard()
        )

    # -------- NO ACTIVE FLOW --------
    if uid not in STATE:
        return await update.message.reply_text(
            "<b>Please use the keyboard below.</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_keyboard()
        )

    step = STATE[uid]["step"]

    # ================= SCM FLOW =================
    if step == "scm_username":
        STATE[uid]["scm_username"] = text
        STATE[uid]["step"] = "scm_id"
        return await update.message.reply_text(
            "<b>🆔 Send scammer Telegram ID</b>\n\n"
            "<b>Numbers only</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=cancel_keyboard()
        )

    if step == "scm_id":
        if not text.isdigit():
            return await update.message.reply_text(
                "<b>❌ Invalid ID</b>\n\n"
                "<b>Send numbers only.</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=cancel_keyboard()
            )

        STATE[uid]["scm_id"] = text
        STATE[uid]["step"] = "scm_statement"
        return await update.message.reply_text(
            "<b>📝 Send statement</b>\n\n"
            "<b>Explain what happened.</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=cancel_keyboard()
        )

    if step == "scm_statement":
        STATE[uid]["statement"] = text
        STATE[uid]["step"] = "scm_amount"
        return await update.message.reply_text(
            "<b>💰 Send amount</b>\n\n"
            "<b>Numbers only</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=cancel_keyboard()
        )

    if step == "scm_amount":
        if not text.isdigit():
            return await update.message.reply_text(
                "<b>❌ Invalid amount</b>\n\n"
                "<b>Send numbers only.</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=cancel_keyboard()
            )

        STATE[uid]["amount"] = text
        STATE[uid]["step"] = "scm_proof"
        return await update.message.reply_text(
            "<b>🔗 Send proof channel/post link</b>\n\n"
            "<b>Example:</b> <code>https://t.me/...</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=cancel_keyboard()
        )

    if step == "scm_proof":
        if not text.startswith("https://t.me/"):
            return await update.message.reply_text(
                "<b>❌ Invalid Telegram link</b>\n\n"
                "<b>Send a valid</b> <code>https://t.me/...</code> <b>link.</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=cancel_keyboard()
            )

        STATE[uid]["proof"] = text
        await send_admin(uid, context)

        return await update.message.reply_text(
            "<b>✅ Report submitted successfully</b>\n\n"
            "<b>Please wait for admin approval.</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_keyboard()
        )

    # ================= IMP FLOW =================
    if step == "imp_fake_username":
        STATE[uid]["fake_username"] = text
        STATE[uid]["step"] = "imp_fake_id"
        return await update.message.reply_text(
            "<b>🆔 Send fake account Telegram ID</b>\n\n"
            "<b>Numbers only</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=cancel_keyboard()
        )

    if step == "imp_fake_id":
        if not text.isdigit():
            return await update.message.reply_text(
                "<b>❌ Invalid ID</b>\n\n"
                "<b>Send numbers only.</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=cancel_keyboard()
            )

        STATE[uid]["fake_id"] = text
        STATE[uid]["step"] = "imp_real_username"
        return await update.message.reply_text(
            "<b>✅ Send real user username</b>\n\n"
            "<b>Example:</b> <code>@username</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=cancel_keyboard()
        )

    if step == "imp_real_username":
        STATE[uid]["real_username"] = text
        STATE[uid]["step"] = "imp_real_id"
        return await update.message.reply_text(
            "<b>🆔 Send real user Telegram ID</b>\n\n"
            "<b>Numbers only</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=cancel_keyboard()
        )

    if step == "imp_real_id":
        if not text.isdigit():
            return await update.message.reply_text(
                "<b>❌ Invalid ID</b>\n\n"
                "<b>Send numbers only.</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=cancel_keyboard()
            )

        STATE[uid]["real_id"] = text
        await send_admin(uid, context)

        return await update.message.reply_text(
            "<b>✅ Report submitted successfully</b>\n\n"
            "<b>Please wait for admin approval.</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_keyboard()
        )

# ================= ERROR HANDLER =================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"Error: {context.error}")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(admin_action, pattern="^(approve|reject)_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_input))

    app.add_error_handler(error_handler)

    print("🤖 Bot running smoothly...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
