import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes
import sqlite3

TOKEN = os.environ.get("TOKEN")

NAME, AGE, GENDER, AREA, LOOKING_FOR, PHOTO, BIO = range(7)

conn = sqlite3.connect("hyd_dating.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    name TEXT, age INTEGER, gender TEXT,
    area TEXT, looking_for TEXT,
    photo_id TEXT, bio TEXT, username TEXT
)""")
cur.execute("""CREATE TABLE IF NOT EXISTS likes(
    from_id INTEGER, to_id INTEGER, UNIQUE(from_id, to_id)
)""")
conn.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to Hyd Dates ❤️\n\nFind people near you in Hyderabad.\n\nLet's create your profile.\n\nWhat's your name / nickname?")
    return NAME

async def get_name(update, context):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Your age? (Must be 18+, just send number like 25)")
    return AGE

async def get_age(update, context):
    try:
        age = int(update.message.text)
        if age < 18:
            await update.message.reply_text("Sorry, 18+ only. Send /start to try again.")
            return ConversationHandler.END
        context.user_data['age'] = age
    except:
        await update.message.reply_text("Send age as number only, e.g. 25")
        return AGE
    await update.message.reply_text("Your gender? Type: Male / Female / Other")
    return GENDER

async def get_gender(update, context):
    context.user_data['gender'] = update.message.text
    await update.message.reply_text("Which area? Type one:\nKondapur, Hitech City, Madhapur, Banjara Hills, Jubilee Hills, Gachibowli, Kukatpally, Secunderabad, Uppal, Manikonda")
    return AREA

async def get_area(update, context):
    context.user_data['area'] = update.message.text
    await update.message.reply_text("What are you looking for? Type: Dating / Friendship / Serious / Casual Chat")
    return LOOKING_FOR

async def get_looking(update, context):
    context.user_data['looking_for'] = update.message.text
    await update.message.reply_text("Send 1 photo for your profile.")
    return PHOTO

async def get_photo(update, context):
    context.user_data['photo_id'] = update.message.photo[-1].file_id
    await update.message.reply_text("Last step - write a short bio, e.g. Coffee lover from Kondapur")
    return BIO

async def get_bio(update, context):
    u = update.message.from_user
    d = context.user_data
    cur.execute("INSERT OR REPLACE INTO users VALUES (?,?,?,?,?,?,?,?)",
        (u.id, d['name'], d['age'], d['gender'], d['area'], d['looking_for'], d['photo_id'], update.message.text, u.username))
    conn.commit()
    await update.message.reply_text("Profile done! 🎉\n\nNow send /browse to see people.")
    return ConversationHandler.END

async def browse(update, context):
    user_id = update.message.from_user.id
    cur.execute("SELECT * FROM users WHERE user_id != ? ORDER BY RANDOM() LIMIT 1", (user_id,))
    person = cur.fetchone()
    if not person:
        await update.message.reply_text("No other profiles yet. Ask a friend to join @Hyddates_bot")
        return
    caption = f"{person[1]}, {person[2]} • {person[4]}\nLooking for: {person[5]}\n\n{person[7]}\n\nTo like this person, send: /like_{person[0]}\nTo see next, send /browse again"
    await update.message.reply_photo(person[6], caption=caption)

async def like_cmd(update, context):
    try:
        liked_id = int(update.message.text.split("_")[1])
    except:
        await update.message.reply_text("Use /browse first")
        return
    my_id = update.message.from_user.id
    cur.execute("INSERT OR IGNORE INTO likes VALUES (?,?)", (my_id, liked_id))
    conn.commit()
    cur.execute("SELECT * FROM likes WHERE from_id=? AND to_id=?", (liked_id, my_id))
    if cur.fetchone():
        await update.message.reply_text("It's a MATCH! 🎉 You both liked each other!")
        try:
            await context.bot.send_message(liked_id, "It's a MATCH! 🎉 Someone you liked also liked you back!")
        except: pass
    else:
        await update.message.reply_text("Liked! If they like you back, it's a match. Send /browse for more.")

def main():
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)],
            AREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_area)],
            LOOKING_FOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_looking)],
            PHOTO: [MessageHandler(filters.PHOTO, get_photo)],
            BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bio)],
        },
        fallbacks=[]
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("browse", browse))
    app.add_handler(MessageHandler(filters.Regex(r"^/like_\d+$"), like_cmd))
    print("Bot running on Render...")
    app.run_polling()

if __name__ == "__main__":
    main()
