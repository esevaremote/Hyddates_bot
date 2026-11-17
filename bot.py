import os
import threading
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = os.environ.get("TOKEN")
NAME, AGE, GENDER, AREA, LOOKING, PHOTO, BIO = range(7)
AREAS = ["Kondapur","Hitech City","Madhapur","Banjara Hills","Jubilee Hills","Gachibowli","Kukatpally","Secunderabad","Uppal","Manikonda","LB Nagar","Dilsukhnagar"]
profiles = {}

app = Flask(__name__)
@app.route('/')
def home():
    return "Hyd Dates Bot is Live!"
def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
threading.Thread(target=run_web, daemon=True).start()

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
    p = profiles[uid]
    await update.message.reply_text(f"✅ Profile Created!\n\n👤 {p['name']}, {p['age']}\n{p['gender']} | {p['area']}\nLooking for: {p['looking']}\nBio: {p['bio']}\n\nNow you can browse!", reply_markup=ReplyKeyboardMarkup([["🔍 Browse Profiles","👤 My Profile"],["🗑️ Delete Profile"]], resize_keyboard=True))
    return ConversationHandler.END
async def browse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    others = [v for k,v in profiles.items() if k != uid]
    if not others:
        await update.message.reply_text("No other profiles yet. Share @Hyddates_bot with friends in Hyderabad!")
        return
    for p in others:
        await update.message.reply_photo(photo=p['photo'], caption=f"👤 {p['name']}, {p['age']}\n{p['gender']} | {p['area']}\nLooking for: {p['looking']}\nBio: {p['bio']}")
async def myprofile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in profiles:
        await update.message.reply_text("No profile yet. Type /start")
        return
    p = profiles[uid]
    await update.message.reply_photo(photo=p['photo'], caption=f"Your Profile:\n👤 {p['name']}, {p['age']}\n{p['gender']} | {p['area']}\nLooking for: {p['looking']}\nBio: {p['bio']}")
async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    profiles.pop(update.effective_user.id, None)
    await update.message.reply_text("Profile deleted. Type /start to create again.")
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled. Type /start to begin again.")
    return ConversationHandler.END
def main():
    app_bot = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler(entry_points=[CommandHandler("start", start)], states={NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)], AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)], GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)], AREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_area)], LOOKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_looking)], PHOTO: [MessageHandler(filters.PHOTO, get_photo)], BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bio)]}, fallbacks=[CommandHandler("cancel", cancel)])
    app_bot.add_handler(conv)
    app_bot.add_handler(MessageHandler(filters.Regex("🔍 Browse Profiles"), browse))
    app_bot.add_handler(MessageHandler(filters.Regex("👤 My Profile"), myprofile))
    app_bot.add_handler(MessageHandler(filters.Regex("🗑️ Delete Profile"), delete))
    app_bot.add_handler(CommandHandler("browse", browse))
    print("Bot started...")
    app_bot.run_polling()
if __name__ == "__main__":
    main()
