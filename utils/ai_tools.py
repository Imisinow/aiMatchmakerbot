import requests
import os

GEMINI_KEY = os.getenv("GEMINI_KEY")

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

    response = requests.post(GEMINI_URL, json=payload)

    data = response.json()

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "AI response unavailable."


def compatibility(bio1, bio2):

    prompt = f"""
Compare these two people.

User A bio: {bio1}

User B bio: {bio2}

Return compatibility score 1-100 and one reason.
"""

    return ask_gemini(prompt)


def flirt(message):

    prompt = f"""
You are a charming dating assistant.

Reply romantically to this message:

{message}
"""

    return ask_gemini(prompt)
