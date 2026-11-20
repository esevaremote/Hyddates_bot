import os
import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())
import threading
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler

TOKEN = os.environ.get("TOKEN")
NAME, AGE, GENDER, AREA, LOOKING, PHOTO, BIO = range(7)
AREAS = ["Kondapur","Hitech City","Madhapur","Banjara Hills","Jubilee Hills","Gachibowli","Kukatpally","Secunderabad","Uppal","Manikonda","LB Nagar","Dilsukhnagar"]

profiles = {}
likes = {}  # uid -> set of uids they liked
active_chats = {}  # uid -> partner uid
seen = {}  # uid -> set of profile ids already shown

MAIN_MENU = ReplyKeyboardMarkup([["🔍 Browse Profiles","👤 My Profile"],["🗑️ Delete Profile","💬 My Matches"]], resize_keyboard=True)

app = Flask(__name__)
@app.route('/')
def home():
    return "Hyd Dates Bot is Live!"
def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)
threading.Thread(target=run_web, daemon=True).start()

# ---------- SIGNUP (same as before) ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to Hyd Dates ❤️\nHyderabad Dating for 18+\n\nWhat's your name?")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Your age? (18+)")
    return AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text)
        if age < 18:
            await update.message.reply_text("Sorry, 18+ only. Enter age again:")
            return AGE
    except:
        await update.message.reply_text("Please type age in numbers, e.g. 25")
        return AGE
    context.user_data['age'] = age
    await update.message.reply_text("Gender? Type: Male / Female / Other", reply_markup=ReplyKeyboardMarkup([["Male","Female","Other"]], one_time_keyboard=True, resize_keyboard=True))
    return GENDER

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gender'] = update.message.text
    await update.message.reply_text("Your area? Choose:", reply_markup=ReplyKeyboardMarkup([AREAS[i:i+3] for i in range(0, len(AREAS), 3)], one_time_keyboard=True, resize_keyboard=True))
    return AREA

async def get_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['area'] = update.message.text
    await update.message.reply_text("What are you looking for? Type: Dating / Friendship / Serious / Casual Chat", reply_markup=ReplyKeyboardMarkup([["Dating","Friendship"],["Serious","Casual Chat"]], one_time_keyboard=True, resize_keyboard=True))
    return LOOKING

async def get_looking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['looking'] = update.message.text
    await update.message.reply_text("Send 1 photo for your profile.")
    return PHOTO

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        context.user_data['photo'] = update.message.photo[-1].file_id
        await update.message.reply_text("Last step - write a short bio, e.g. Coffee lover from Kondapur")
        return BIO
    await update.message.reply_text("Please send a photo.")
    return PHOTO

async def get_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['bio'] = update.message.text
    uid = update.effective_user.id
    profiles[uid] = dict(context.user_data)
    profiles[uid]['uid'] = uid
    profiles[uid]['chat_id'] = update.effective_chat.id
    p = profiles[uid]
    await update.message.reply_text(f"✅ Profile Created!\n\n👤 {p['name']}, {p['age']}\n{p['gender']} | {p['area']}\nLooking for: {p['looking']}\nBio: {p['bio']}\n\nNow you can browse!", reply_markup=MAIN_MENU)
    return ConversationHandler.END

# ---------- BROWSE + LIKE ----------
async def browse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_next_profile(update.effective_chat.id, update.effective_user.id, context, update)

async def show_next_profile(chat_id, uid, context, update=None):
    if uid not in profiles:
        await context.bot.send_message(chat_id, "Create profile first. Type /start", reply_markup=MAIN_MENU)
        return
    seen.setdefault(uid, set())
    others = [v for k,v in profiles.items() if k != uid and k not in seen[uid]]
    if not others:
        await context.bot.send_message(chat_id, "No more new profiles. Share @Hyddates_bot with friends in Hyderabad!\n\nTap Browse again for new people.", reply_markup=MAIN_MENU)
        return
    p = others[0]
    seen[uid].add(p['uid'])
    context.user_data['current_id'] = p['uid']
    keyboard = [
        [InlineKeyboardButton("❤️ Like", callback_data=f"like_{p['uid']}"),
         InlineKeyboardButton("❌ Pass", callback_data=f"pass_{p['uid']}")],
        [InlineKeyboardButton("⏭️ Next", callback_data=f"pass_{p['uid']}")]
    ]
    await context.bot.send_photo(chat_id=chat_id, photo=p['photo'],
        caption=f"👤 {p['name']}, {p['age']}\n{p['gender']} | {p['area']}\nLooking for: {p['looking']}\nBio: {p['bio']}",
        reply_markup=InlineKeyboardMarkup(keyboard))

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    me = query.from_user.id
    data = query.data
    if data.startswith("like_"):
        other_id = int(data.split("_")[1])
        likes.setdefault(me, set()).add(other_id)
        # Mutual like?
        if me in likes.get(other_id, set()):
            active_chats[me] = other_id
            active_chats[other_id] = me
            await query.message.reply_text("❤️ It's a MATCH! You can now chat. Just type a message or send a photo here.\n\nType /stop to end chat.", reply_markup=MAIN_MENU)
            # notify other person
            other_chat = profiles.get(other_id, {}).get('chat_id')
            if other_chat:
                try:
                    await context.bot.send_message(other_chat, f"❤️ It's a MATCH with {profiles[me]['name']}! You can now chat. Just type here.\n\nType /stop to end chat.", reply_markup=MAIN_MENU)
                except: pass
        else:
            await query.message.reply_text("Liked ❤️ Waiting for them to like you back...")
    elif data.startswith("pass_"):
        await query.message.reply_text("Passed ➡️ Showing next...")
    await show_next_profile(query.message.chat_id, me, context)

async def myprofile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in profiles:
        await update.message.reply_text("No profile yet. Type /start")
        return
    p = profiles[uid]
    await update.message.reply_photo(photo=p['photo'], caption=f"Your Profile:\n👤 {p['name']}, {p['age']}\n{p['gender']} | {p['area']}\nLooking for: {p['looking']}\nBio: {p['bio']}", reply_markup=MAIN_MENU)

async def mymatches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    partner = active_chats.get(uid)
    if not partner:
        await update.message.reply_text("No matches yet. Tap 🔍 Browse Profiles and Like people.", reply_markup=MAIN_MENU)
        return
    p = profiles.get(partner)
    if p:
        await update.message.reply_text(f"Your current chat: {p['name']}, {p['age']} from {p['area']}\nJust type here to chat. /stop to end.", reply_markup=MAIN_MENU)

async def stop_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    partner = active_chats.pop(uid, None)
    if partner:
        active_chats.pop(partner, None)
        await update.message.reply_text("Chat ended. Tap Browse for new people.", reply_markup=MAIN_MENU)
        try:
            await context.bot.send_message(profiles[partner]['chat_id'], "Your match ended the chat.", reply_markup=MAIN_MENU)
        except: pass
    else:
        await update.message.reply_text("You are not in a chat.", reply_markup=MAIN_MENU)

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    profiles.pop(uid, None)
    likes.pop(uid, None)
    if uid in active_chats:
        partner = active_chats.pop(uid)
        active_chats.pop(partner, None)
    seen.pop(uid, None)
    await update.message.reply_text("Profile deleted. Type /start to create again.", reply_markup=MAIN_MENU)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled. Type /start to begin again.")
    return ConversationHandler.END

# ---------- CHAT RELAY - TEXT + PHOTO ----------
async def relay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    partner = active_chats.get(uid)
    if not partner:
        return  # not in chat, ignore - let other handlers work
    # Don't relay menu buttons
    if update.message.text in ["🔍 Browse Profiles","👤 My Profile","🗑️ Delete Profile","💬 My Matches"]:
        return
    partner_chat = profiles.get(partner, {}).get('chat_id')
    if not partner_chat:
        return
    try:
        if update.message.text:
            await context.bot.send_message(partner_chat, f"💬 {update.message.text}")
        elif update.message.photo:
            await context.bot.send_photo(partner_chat, photo=update.message.photo[-1].file_id, caption=update.message.caption or "")
        elif update.message.voice:
            await context.bot.send_voice(partner_chat, voice=update.message.voice.file_id)
        elif update.message.video:
            await context.bot.send_video(partner_chat, video=update.message.video.file_id, caption=update.message.caption or "")
        elif update.message.sticker:
            await context.bot.send_sticker(partner_chat, sticker=update.message.sticker.file_id)
    except Exception as e:
        await update.message.reply_text("Could not deliver. They may have blocked the bot.")

def main():
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    app_bot = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler(entry_points=[CommandHandler("start", start)], states={NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)], AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)], GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)], AREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_area)], LOOKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_looking)], PHOTO: [MessageHandler(filters.PHOTO, get_photo)], BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bio)]}, fallbacks=[CommandHandler("cancel", cancel)])
    app_bot.add_handler(conv)
    app_bot.add_handler(CallbackQueryHandler(button_click))
    app_bot.add_handler(MessageHandler(filters.Regex("🔍 Browse Profiles"), browse))
    app_bot.add_handler(MessageHandler(filters.Regex("👤 My Profile"), myprofile))
    app_bot.add_handler(MessageHandler(filters.Regex("🗑️ Delete Profile"), delete))
    app_bot.add_handler(MessageHandler(filters.Regex("💬 My Matches"), mymatches))
    app_bot.add_handler(CommandHandler("browse", browse))
    app_bot.add_handler(CommandHandler("matches", mymatches))
    app_bot.add_handler(CommandHandler("stop", stop_chat))
    # Relay MUST be last - it only works if user is in active_chats
    app_bot.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.VOICE | filters.VIDEO | filters.Sticker.ALL, relay), group=1)
    print("Bot started...", flush=True)
    app_bot.run_polling()

if __name__ == "__main__":
    main()
