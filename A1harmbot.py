from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters, ChatMemberHandler
)
from telegram.constants import ParseMode
from telegram.error import TelegramError, BadRequest, Forbidden
import html
import json
import os
import re

# ================= CONFIG =================
TOKEN = "8743013698:AAHbatOmi4eRNShDcBBZIPa4VwskGZPTz4s"

ADMIN_IDS = [7691071175, 6587658540]

CHANNEL_ID = -1003344628533
GC_IDS = [-1003730637965]

STATE = {}
BLACKLIST_FILE = "blacklist.json"

# ================= STORAGE =================
def load_blacklist():
    if not os.path.exists(BLACKLIST_FILE):
        return {}

    try:
        with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            return {}
    except Exception as e:
        print(f"Blacklist load error: {e}")
        return {}

def save_blacklist(data):
    try:
        with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Blacklist save error: {e}")

BLACKLIST = load_blacklist()

def add_to_blacklist(user_id: int, report_type: str, username: str = ""):
    global BLACKLIST
    BLACKLIST[str(user_id)] = {
        "type": report_type,
        "username": username
    }
    save_blacklist(BLACKLIST)

def is_blacklisted(user_id: int):
    return str(user_id) in BLACKLIST

# ================= UTILS =================
def reset(uid):
    STATE.pop(uid, None)

def esc(text):
    return html.escape(str(text))

def clean_username(text):
    text = (text or "").strip()
    if text.startswith("@"):
        text = text[1:]
    return text

def valid_username(text):
    text = clean_username(text)
    return bool(re.fullmatch(r"[A-Za-z0-9_]{5,32}", text))

def username_url(text):
    text = clean_username(text)
    return f"https://t.me/{text}"

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

# ================= SAFE GROUP ACTION =================
async def safe_group_ban_and_notify(context, target_id: int, reason_text: str):
    results = []

    for gc in GC_IDS:
        ban_ok = False
        ban_error = None

        try:
            await context.bot.ban_chat_member(
                chat_id=gc,
                user_id=target_id,
                revoke_messages=True
            )
            ban_ok = True
        except BadRequest as e:
            ban_error = str(e)
            print(f"BadRequest in {gc}: {e}")
        except Forbidden as e:
            ban_error = str(e)
            print(f"Forbidden in {gc}: {e}")
        except TelegramError as e:
            ban_error = str(e)
            print(f"TelegramError in {gc}: {e}")
        except Exception as e:
            ban_error = str(e)
            print(f"Unknown ban error in {gc}: {e}")

        # GC MSG ALWAYS JAYEGA
        try:
            gc_text = (
                "<b>🚫 USER BANNED</b>\n\n"
                f"<b>User ID:</b> <code>{target_id}</code>\n"
                f"<b>Reason:</b> <b>{esc(reason_text)}</b>\n"
                "<b>Status:</b> <b>Blacklisted Permanently</b>"
            )

            await context.bot.send_message(
                chat_id=gc,
                text=gc_text,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            print(f"GC notify error in {gc}: {e}")

        results.append((gc, ban_ok, ban_error or "OK"))

    return results

# ================= AUTO BAN ON JOIN =================
async def auto_ban_blacklisted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmu = update.chat_member
    if not cmu:
        return

    chat_id = cmu.chat.id
    if chat_id not in GC_IDS:
        return

    new_member = cmu.new_chat_member
    user = new_member.user

    if not user:
        return

    if new_member.status in ["member", "restricted"]:
        uid = user.id

        if is_blacklisted(uid):
            data = BLACKLIST.get(str(uid), {})
            reason_type = data.get("type", "BLACKLISTED")
            username = data.get("username", "")

            try:
                await context.bot.ban_chat_member(
                    chat_id=chat_id,
                    user_id=uid,
                    revoke_messages=True
                )

                msg = (
                    "<b>🚫 AUTO BANNED</b>\n\n"
                    f"<b>User ID:</b> <code>{uid}</code>\n"
                    f"<b>Reason:</b> <b>{esc(reason_type)} Approved Blacklist</b>"
                )

                if username:
                    msg += f"\n<b>Username:</b> {esc(username)}"

                await context.bot.send_message(
                    chat_id=chat_id,
                    text=msg,
                    parse_mode=ParseMode.HTML
                )

                print(f"Auto-banned blacklisted user {uid} in {chat_id}")

            except Exception as e:
                print(f"Auto ban error for {uid} in {chat_id}: {e}")

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

        if d["type"] == "SCM":
            reason_text = "Scammer Report Approved"
            blacklist_username = d.get("scm_username", "")
            blacklist_type = "SCM"
        else:
            reason_text = "Impersonation Report Approved"
            blacklist_username = d.get("fake_username", "")
            blacklist_type = "IMP"

        # -------- SAVE TO BLACKLIST FIRST --------
        add_to_blacklist(target_id, blacklist_type, blacklist_username)

        # -------- TRY BAN + ALWAYS NOTIFY GC --------
        ban_results = await safe_group_ban_and_notify(context, target_id, reason_text)

        # -------- CHANNEL POST (ALWAYS RUN) --------
        if d["type"] == "SCM":
            caption = (
                "<b>❌ {}</b> <b>(Telegram ID: <code>{}</code>) Flagged</b>\n\n"
                "<b>⚠️ Stay Alert & Avoid Deals Without Verification</b>"
            ).format(
                esc(d["scm_username"]),
                esc(d["scm_id"])
            )

            kb = []
            if valid_username(d.get("scm_username", "")):
                kb.append(
                    InlineKeyboardButton(
                        "View Profile",
                        url=username_url(d["scm_username"])
                    )
                )
            kb.append(
                InlineKeyboardButton(
                    "View Proof",
                    url=d["proof"]
                )
            )
            reply_markup = InlineKeyboardMarkup([kb])

        else:
            caption = (
                "<b>❌ {}</b> <b>(Telegram ID: <code>{}</code>) Flagged</b>\n\n"
                "<b>⚠️ Stay Safe From Fake Accounts</b>\n\n"
                f"<b>Real User:</b> {esc(d['real_username'])} "
                f"(<code>{esc(d['real_id'])}</code>)"
            ).format(
                esc(d["fake_username"]),
                esc(d["fake_id"])
            )

            row = []
            if valid_username(d.get("fake_username", "")):
                row.append(
                    InlineKeyboardButton(
                        "View Profile",
                        url=username_url(d["fake_username"])
                    )
                )
            if valid_username(d.get("real_username", "")):
                row.append(
                    InlineKeyboardButton(
                        "Real Profile",
                        url=username_url(d["real_username"])
                    )
                )

            reply_markup = InlineKeyboardMarkup([row]) if row else None

        try:
            with open("pfp.jpg", "rb") as photo:
                await context.bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=photo,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
                print("✅ Channel photo post sent successfully.")
        except Exception as e:
            print(f"Photo send error: {e}")
            try:
                await context.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup,
                    disable_web_page_preview=True
                )
                print("✅ Channel text post sent successfully.")
            except Exception as e2:
                print(f"Channel text send error: {e2}")

        # -------- ADMIN RESULT --------
        api_success_count = sum(1 for _, ok, _ in ban_results if ok)

        result_text = (
            "<b>✅ Approved successfully.</b>\n\n"
            f"<b>Target ID:</b> <code>{target_id}</code>\n"
            f"<b>Blacklist Saved:</b> <b>Yes</b>\n"
            f"<b>Ban Attempted in Groups:</b> <code>{len(GC_IDS)}/{len(GC_IDS)}</code>\n"
            f"<b>Direct Ban API Success:</b> <code>{api_success_count}/{len(GC_IDS)}</code>\n"
            "<b>Future Join Protection:</b> <b>Enabled</b>"
        )

        await q.message.edit_text(
            result_text,
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

    app.app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(admin_action, pattern="^(approve|reject)_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_input))
    app.add_handler(ChatMemberHandler(auto_ban_blacklisted, ChatMemberHandler.CHAT_MEMBER))

    app.add_error_handler(error_handler)

    print("🤖 Bot running smoothly...")
    print(f"📁 Loaded blacklist users: {len(BLACKLIST)}")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
