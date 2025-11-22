import os
import logging
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, ContextTypes, InlineQueryHandler
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv
import uuid

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
        response = client.spaces().create(body={}).execute()
        link = response['meetingUri']
        await update.message.reply_text(f"Instant Meet ready!\nJoin → {link}")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

# THIS IS THE INLINE MAGIC
async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.lower()
    if "meet" in query or query == "" or "link" in query or "room" in query:
        try:
            client = get_meet_client()
            response = client.spaces().create(body={}).execute()
            link = response['meetingUri']

            results = [
                InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title="Instant Google Meet",
                    description="Click to send a fresh Meet link",
                    input_message_content=InputTextMessageContent(
                        f"Instant Meet created!\nJoin here → {link}"
                    )
                )
            ]
            await update.inline_query.answer(results, cache_time=1)
        except Exception as e:
            pass  # silently fail if Meet API is slow

def main():
    token = os.getenv("BOT_TOKEN")
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("meet", meet))
    app.add_handler(InlineQueryHandler(inline_query))  # This line enables @bot meet

    print("Bot is running with INLINE MODE! Try @yourbot meet anywhere")
    app.run_polling()

if __name__ == '__main__':
    main()
