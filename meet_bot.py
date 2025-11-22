import os
import logging
import telebot
from telebot import types
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from flask import Flask, request
import uuid

logging.basicConfig(level=logging.INFO)

SCOPES = ['https://www.googleapis.com/auth/meetings.space.created']
TOKEN_FILE = 'token.json'

def get_meet_client():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())
    return build('meet', 'v2', credentials=creds,
                 discoveryServiceUrl='https://meet.googleapis.com/$discovery/rest?version=v2')

# Bot setup
token = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(token)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Instant Meet Bot\nUse /meet or @yourbot meet in any chat!")

@bot.message_handler(commands=['meet'])
def meet(message):
    try:
        client = get_meet_client()
        response = client.spaces().create(
            body={
                "config": {
                    "accessType": "OPEN",  # No knocking—anyone with link joins directly
                    "entryPointAccess": "OPEN"  # Direct entry via link, no approval
                }
            }
        ).execute()
        link = response['meetingUri']
        bot.reply_to(message, f"Instant Meet (fully open—no approval needed!)\nJoin → {link}")
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

@bot.inline_handler(lambda query: 'meet' in query.query.lower() or not query.query)
def inline_query(query):
    try:
        client = get_meet_client()
        response = client.spaces().create(
            body={
                "config": {
                    "accessType": "OPEN",
                    "entryPointAccess": "OPEN"
                }
            }
        ).execute()
        link = response['meetingUri']
        r = types.InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title="Instant Open Google Meet",
            description="Anyone can join and speak—no host approval!",
            input_message_content=types.InputTextMessageContent(f"Open Meet → {link}")
        )
        bot.answer_inline_query(query.id, [r], cache_time=0)
    except Exception as e:
        pass

# Flask webhook
app = Flask(__name__)

@app.route(f"/{token}", methods=["POST"])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        abort(403)

@app.route("/")
def health():
    return "Bot alive!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
