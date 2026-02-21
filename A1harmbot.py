from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

TOKEN = "8465045827:AAGB-7KLce05TY2Xb5ToTdU7oBTsd2vzPmY"

# 🔑 2 ADMINS
ADMIN_IDS = [7659864091, 6587658540]   # second admin id yahan daal do

CHANNEL_ID = -1003344628533
GC_IDS = [-1003692774580, -1003382668169]

STATE = {}

# ---------------- UTILS ----------------
def reset(uid):
    STATE.pop(uid, None)

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ❗ sirf DM me kaam kare
    if update.message.chat.type != "private":
        return

    kb = [[InlineKeyboardButton("➕ Create Report", callback_data="create")]]
    await update.message.reply_text(
        "👋 Welcome\nReport banane ke liye niche click karo",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ---------------- CREATE ----------------
async def create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    kb = [
        [InlineKeyboardButton("🚨 IMP REPORT", callback_data="type_IMP")],
        [InlineKeyboardButton("⚠️ SCM REPORT", callback_data="type_SCM")]
    ]
    await q.message.reply_text(
        "Report type select karo:",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ---------------- SET TYPE ----------------
async def set_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    rtype = q.data.split("_")[1]
    STATE[uid] = {"type": rtype}

    if rtype == "SCM":
        STATE[uid]["step"] = "scm_username"
        await q.message.reply_text("❌ Scammer ka username bhejo (@username)")
    else:
        STATE[uid]["step"] = "imp_fake_username"
        await q.message.reply_text("❌ Fake (IMP) username bhejo (@username)")

# ---------------- MESSAGE HANDLER ----------------
async def user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ❗ sirf DM me input allow
    if update.message.chat.type != "private":
        return

    uid = update.effective_user.id
    text = update.message.text.strip()

    if uid not in STATE:
        return

    step = STATE[uid]["step"]

    # ===== SCM FLOW =====
    if step == "scm_username":
        STATE[uid]["scm_username"] = text
        STATE[uid]["step"] = "scm_id"
        return await update.message.reply_text("🆔 Scammer Telegram ID bhejo (sirf number)")

    if step == "scm_id":
        if not text.isdigit():
            return await update.message.reply_text("❌ Galat ID\nSirf number bhejo")
        STATE[uid]["scm_id"] = text
        STATE[uid]["step"] = "scm_statement"
        return await update.message.reply_text("📝 Statement likho (kya hua)")

    if step == "scm_statement":
        STATE[uid]["statement"] = text
        STATE[uid]["step"] = "scm_amount"
        return await update.message.reply_text("💰 Amount bhejo (sirf number)")

    if step == "scm_amount":
        if not text.isdigit():
            return await update.message.reply_text("❌ Sirf number bhejo")
        STATE[uid]["amount"] = text
        STATE[uid]["step"] = "scm_proof"
        return await update.message.reply_text("🔗 Proof channel link bhejo (https://t.me/...)")

    if step == "scm_proof":
        if not text.startswith("https://t.me/"):
            return await update.message.reply_text("❌ Valid Telegram link bhejo")
        STATE[uid]["proof"] = text
        await send_admin(uid, context)
        await update.message.reply_text("✅ Report submit ho gayi\nAdmin approval ka wait karo")
        return

    # ===== IMP FLOW =====
    if step == "imp_fake_username":
        STATE[uid]["fake_username"] = text
        STATE[uid]["step"] = "imp_fake_id"
        return await update.message.reply_text("🆔 Fake account ka Telegram ID bhejo")

    if step == "imp_fake_id":
        if not text.isdigit():
            return await update.message.reply_text("❌ Sirf number bhejo")
        STATE[uid]["fake_id"] = text
        STATE[uid]["step"] = "imp_real_username"
        return await update.message.reply_text("✅ Real user ka username bhejo (@username)")

    if step == "imp_real_username":
        STATE[uid]["real_username"] = text
        STATE[uid]["step"] = "imp_real_id"
        return await update.message.reply_text("🆔 Real user ka Telegram ID bhejo")

    if step == "imp_real_id":
        if not text.isdigit():
            return await update.message.reply_text("❌ Sirf number bhejo")
        STATE[uid]["real_id"] = text
        await send_admin(uid, context)
        await update.message.reply_text("✅ Report submit ho gayi\nAdmin approval ka wait karo")
        return

# ---------------- SEND TO ADMINS (DM ONLY) ----------------
async def send_admin(uid, context):
    d = STATE[uid]

    if d["type"] == "SCM":
        text = (
            "🚨 SCAM REPORT\n\n"
            f"❌ User: {d['scm_username']} ({d['scm_id']})\n"
            f"💰 Amount: {d['amount']}\n"
            f"📝 Statement:\n{d['statement']}\n"
            f"🔗 Proof: {d['proof']}"
        )
    else:
        text = (
            "🚨 IMP REPORT\n\n"
            f"❌ Fake: {d['fake_username']} ({d['fake_id']})\n"
            f"✅ Real: {d['real_username']} ({d['real_id']})"
        )

    kb = [[
        InlineKeyboardButton("✅ Approve", callback_data=f"approve_{uid}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{uid}")
    ]]

    for admin in ADMIN_IDS:
        await context.bot.send_message(
            chat_id=admin,
            text=text,
            reply_markup=InlineKeyboardMarkup(kb)
        )

# ---------------- ADMIN ACTION ----------------
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    # ❗ sirf admins
    if q.from_user.id not in ADMIN_IDS:
        return

    action, uid = q.data.split("_")
    uid = int(uid)

    if uid not in STATE:
        await q.message.edit_text("❌ Report expired")
        return

    d = STATE[uid]

    if action == "approve":
        target_id = int(d["scm_id"] if d["type"] == "SCM" else d["fake_id"])

        # 🔇 GC me sirf BAN (no message)
        for gc in GC_IDS:
            try:
                await context.bot.ban_chat_member(gc, target_id)
            except:
                pass

        # 📢 Channel post allowed
        if d["type"] == "SCM":
            caption = f"❌ User {d['scm_username']} (Telegram ID: {d['scm_id']}) flagged"
            kb = [[
                InlineKeyboardButton("View Profile", url=f"https://t.me/{d['scm_username'].replace('@','')}"),
                InlineKeyboardButton("View Proof", url=d["proof"])
            ]]
        else:
            caption = (
                f"❌ Impersonator: {d['fake_username']} ({d['fake_id']})\n"
                f"✅ Real User: {d['real_username']} ({d['real_id']})"
            )
            kb = [[
                InlineKeyboardButton("View Real Profile", url=f"https://t.me/{d['real_username'].replace('@','')}"),
                InlineKeyboardButton("View Fake Profile", url=f"https://t.me/{d['fake_username'].replace('@','')}")
            ]]

        with open("pfp.jpg", "rb") as photo:
            await context.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=photo,
                caption=caption,
                reply_markup=InlineKeyboardMarkup(kb)
            )

        await q.message.edit_text("✅ Approved")
        reset(uid)

    else:
        await q.message.edit_text("❌ Rejected")
        reset(uid)

# ---------------- MAIN ----------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(create, pattern="^create$"))
app.add_handler(CallbackQueryHandler(set_type, pattern="^type_"))
app.add_handler(CallbackQueryHandler(admin_action, pattern="^(approve|reject)_"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_input))

print("🤖 Bot running...")
app.run_polling()