import os
import random
import string
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from supabase import create_client
import google.generativeai as genai

# -----------------------
# ENV VARIABLES
# -----------------------

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")
PAYSTACK_SECRET = os.getenv("PAYSTACK_SECRET")
BOT_USERNAME = os.getenv("BOT_USERNAME")

# -----------------------
# SERVICES
# -----------------------

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# -----------------------
# UTILITIES
# -----------------------

def generate_referral():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def ai_flirt(message):

    prompt = f"""
You are a charming dating assistant.

Reply romantically to this message:

{message}
"""

    res = model.generate_content(prompt)

    return res.text


def ai_compatibility(a, b):

    prompt = f"""
User A Bio: {a}
User B Bio: {b}

Rate compatibility 1-100 and explain shortly.
"""

    res = model.generate_content(prompt)

    return res.text


# -----------------------
# START + REFERRAL
# -----------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    args = context.args

    referral = generate_referral()

    referred_by = None

    if args:
        referred_by = args[0]

    supabase.table("profiles").upsert({
        "id": user.id,
        "username": user.username,
        "referral_code": referral,
        "referred_by": referred_by
    }).execute()

    if referred_by:
        supabase.table("referrals").insert({
            "referrer": referred_by,
            "referred": user.id
        }).execute()

    await update.message.reply_text(
        "Welcome ❤️\n\n"
        "Commands:\n"
        "/bio\n"
        "/interests\n"
        "/find\n"
        "/flirt\n"
        "/premium\n"
        "/referral"
    )


# -----------------------
# PROFILE SETUP
# -----------------------

async def bio(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = " ".join(context.args)

    supabase.table("profiles").update({
        "bio": text
    }).eq("id", update.effective_user.id).execute()

    await update.message.reply_text("Bio saved.")


async def interests(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = " ".join(context.args)

    supabase.table("profiles").update({
        "interests": text
    }).eq("id", update.effective_user.id).execute()

    await update.message.reply_text("Interests saved.")


# -----------------------
# MATCH SYSTEM
# -----------------------

async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    user = supabase.table("profiles").select("*").eq("id", user_id).single().execute().data

    match = supabase.table("profiles")\
        .select("*")\
        .eq("is_searching", True)\
        .neq("id", user_id)\
        .limit(1)\
        .execute()

    if not match.data:

        await update.message.reply_text("Searching for partner...")
        return

    partner = match.data[0]

    result = ai_compatibility(user["bio"], partner["bio"])

    supabase.table("profiles").update({
        "is_taken": True,
        "current_partner_id": partner["id"]
    }).eq("id", user_id).execute()

    supabase.table("profiles").update({
        "is_taken": True,
        "current_partner_id": user_id
    }).eq("id", partner["id"]).execute()

    await update.message.reply_text(f"Match ❤️\n{result}")

    await context.bot.send_message(
        chat_id=partner["id"],
        text=f"You have a match ❤️\n{result}"
    )


# -----------------------
# AI FLIRTING ASSISTANT
# -----------------------

async def flirt(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = " ".join(context.args)

    response = ai_flirt(text)

    await update.message.reply_text(response)


# -----------------------
# PREMIUM SYSTEM
# -----------------------

async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    data = {
        "email": f"user{user_id}@bot.com",
        "amount": 200000
    }

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET}"
    }

    r = requests.post(
        "https://api.paystack.co/transaction/initialize",
        json=data,
        headers=headers
    )

    link = r.json()["data"]["authorization_url"]

    await update.message.reply_text(
        f"Upgrade to premium:\n{link}"
    )


# -----------------------
# REFERRAL SYSTEM
# -----------------------

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = supabase.table("profiles").select("*").eq("id", update.effective_user.id).single().execute().data

    code = user["referral_code"]

    link = f"https://t.me/{BOT_USERNAME}?start={code}"

    await update.message.reply_text(
        f"Invite friends and earn rewards\n\n{link}"
    )


# -----------------------
# AUTO MARKETING
# -----------------------

async def broadcast(context: ContextTypes.DEFAULT_TYPE):

    users = supabase.table("profiles").select("id").execute()

    for u in users.data:

        try:
            await context.bot.send_message(
                chat_id=u["id"],
                text="🔥 New matches waiting! Use /find now."
            )
        except:
            pass


# -----------------------
# BOT MAIN
# -----------------------

def main():

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bio", bio))
    app.add_handler(CommandHandler("interests", interests))
    app.add_handler(CommandHandler("find", find))
    app.add_handler(CommandHandler("flirt", flirt))
    app.add_handler(CommandHandler("premium", premium))
    app.add_handler(CommandHandler("referral", referral))

    app.job_queue.run_repeating(broadcast, interval=43200)

    print("Bot running...")

    app.run_polling()


if __name__ == "__main__":
    main()
