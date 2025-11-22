import os
import logging
import threading
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, ContextTypes, InlineQueryHandler
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv
import uuid
from flask import Flask

load_dotenv()
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Instant Meet Bot\nUse /meet or @yourbot meet in any chat!")

async def meet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        client = get_meet_client()
        response = client.spaces().create(
            body={
                "config": {
                    "accessType": "OPEN",
                    "entryType": "DIRECT",
                    "requireJoinApproval": False
                }
            }
        ).execute()
        link = response['meetingUri']
        await update.message.reply_text(f"Instant Meet (open to all!)\nJoin → {link}")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.lower()
    if "meet" in query or query == "" or "link" in query or "room" in query:
        try:
            client = get_meet_client()
            response = client.spaces().create(
                body={
                    "config": {
                        "accessType": "OPEN",
                        "entryType": "DIRECT",
                        "requireJoinApproval": False
                    }
                }
            ).execute()
            link = response['meetingUri']

            results = [
                InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title="Instant Open Google Meet",
                    description="Anyone can join instantly — no waiting!",
                    input_message_content=InputTextMessageContent(
                        f"Open Meet — anyone can join!\nJoin → {link}"
                    )
                )
            ]
            await update.inline_query.answer(results, cache_time=1)
        except Exception as e:
            pass

def run_flask():
    app = Flask(__name__)
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):
        return "OK"  # Dummy response for Render health checks
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN not in .env")

    # Start Flask in a thread for health checks
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("meet", meet))
    app.add_handler(InlineQueryHandler(inline_query))

    print("Bot is running with health check! Try /meet")
    app.run_polling()

if __name__ == '__main__':
    main()
