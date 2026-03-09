import os
import requests
import random
import string
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from supabase import create_client

# ==============================
# ENV VARIABLES
# ==============================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")
PAYSTACK_SECRET = os.getenv("PAYSTACK_SECRET")

# ==============================
# DATABASE
# ==============================

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==============================
# GEMINI REST API
# ==============================

GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"


def ask_gemini(prompt):

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        r = requests.post(GEMINI_URL, json=payload)
        data = r.json()

        return data["candidates"][0]["content"]["parts"][0]["text"]

    except Exception:
        return "AI response unavailable."


def compatibility(bio1, bio2):

    prompt = f"""
Compare these two users.

User A bio: {bio1}

User B bio: {bio2}

Give compatibility score from 1 to 100 and one reason.
"""

    return ask_gemini(prompt)


def flirt(message):

    prompt = f"""
You are a charming dating assistant.

Reply romantically to this message:

{message}
"""

    return ask_gemini(prompt)


# ==============================
# UTILITIES
# ==============================

def generate_code():

    return ''.join(
        random.choices(
            string.ascii_uppercase + string.digits,
            k=6
        )
    )


# ==============================
# COMMANDS
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    code = generate_code()

    supabase.table("profiles").upsert({
        "id": user.id,
        "username": user.username,
        "referral_code": code
    }).execute()

    await update.message.reply_text(
        "Welcome ❤️\n\nUse /bio to set your profile."
    )


async def bio(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = " ".join(context.args)

    supabase.table("profiles").update({
        "bio": text
    }).eq("id", update.effective_user.id).execute()

    await update.message.reply_text("Bio saved.")


async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    user = supabase.table("profiles")\
        .select("*")\
        .eq("id", user_id)\
        .single()\
        .execute().data

    match = supabase.table("profiles")\
        .select("*")\
        .neq("id", user_id)\
        .limit(1)\
        .execute()

    if not match.data:
        await update.message.reply_text("Searching for a partner...")
        return

    partner = match.data[0]

    result = compatibility(user.get("bio", ""), partner.get("bio", ""))

    await update.message.reply_text(
        f"❤️ Match Found\n\n{result}"
    )


async def flirt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = " ".join(context.args)

    response = flirt(text)

    await update.message.reply_text(response)


async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET}"
    }

    data = {
        "email": f"user{user_id}@bot.com",
        "amount": 200000
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


# ==============================
# MAIN
# ==============================

def main():

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bio", bio))
    app.add_handler(CommandHandler("find", find))
    app.add_handler(CommandHandler("flirt", flirt_command))
    app.add_handler(CommandHandler("premium", premium))

    print("Bot running...")

    app.run_polling()


if __name__ == "__main__":
    main()
