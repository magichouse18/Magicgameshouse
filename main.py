#!/usr/bin/env python3
import os
import time
import logging
import sqlite3
import threading
from flask import Flask
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackQueryHandler,
    ConversationHandler,
    CallbackContext
)

# ─── LOGGING ────────────────────────────────────────────────────
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── STATI CONVERSATION ────────────────────────────────────────
USERNAME, GAME = range(2)

# ─── DB ─────────────────────────────────────────────────────────
DB_PATH = 'scores.db'
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            username TEXT,
            score     INTEGER,
            timestamp REAL
        )
    ''')
    conn.commit()
    conn.close()

def save_score(username: str, score: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO scores VALUES (?, ?, ?)', (username, score, time.time()))
    conn.commit()
    conn.close()

def get_leaderboard(limit: int = 10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT username, score FROM scores ORDER BY score DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

# ─── FLASK PER KEEP‑ALIVE ──────────────────────────────────────
app = Flask('')
@app.route('/')
def alive():
    return 'OK'

# ─── HANDLER DEL BOT ────────────────────────────────────────────
def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "👋 Benvenuto in *MagicGamesHouse*! Inviami il tuo username:",
        parse_mode=ParseMode.MARKDOWN
    )
    return USERNAME

def username_received(update: Update, context: CallbackContext) -> int:
    uname = update.message.text.strip()
    context.user_data['username'] = uname
    update.message.reply_text(f"Perfetto, *{uname}*! 🎮", parse_mode=ParseMode.MARKDOWN)
    kb = [[InlineKeyboardButton("Inizia partita 🪓", callback_data='start_game')]]
    update.message.reply_text("Sei pronto?", reply_markup=InlineKeyboardMarkup(kb))
    return GAME

def start_game_callback(update: Update, context: CallbackContext) -> int:
    query = update.callback_query; query.answer()
    context.user_data['score'] = 0
    context.user_data['game_active'] = True

    msg = query.message.reply_text(
        "⏱️ *Partita iniziata!* Clicca 🪓 il più velocemente possibile in 10 sec!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🪓", callback_data='chop')]])
    )
    context.user_data['game_chat_id'] = msg.chat_id
    context.user_data['game_msg_id']  = msg.message_id

    context.job_queue.run_once(
        end_game, when=10,
        context={'chat_id': update.effective_chat.id, 'user_id': update.effective_user.id}
    )
    return GAME

def chop_callback(update: Update, context: CallbackContext) -> int:
    query = update.callback_query; query.answer()
    if not context.user_data.get('game_active'): return GAME
    context.user_data['score'] += 1
    try:
        context.bot.edit_message_text(
            chat_id=context.user_data['game_chat_id'],
            message_id=context.user_data['game_msg_id'],
            text=f"⏱️ *In corso!* Punteggio: *{context.user_data['score']}* 🪓",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🪓", callback_data='chop')]])
        )
    except: pass
    return GAME

def end_game(context: CallbackContext):
    job = context.job; data = job.context
    chat_id, user_id = data['chat_id'], data['user_id']
    ud = context.dispatcher.user_data.get(user_id, {})
    username, score = ud.get('username','Anonimo'), ud.get('score',0)
    ud['game_active'] = False

    context.bot.send_message(
        chat_id,
        f"🏁 *Fine!* {username}, hai fatto *{score}* pt.",
        parse_mode=ParseMode.MARKDOWN
    )
    save_score(username, score)

    text = "📊 *Top 10*:\n"
    for i,(u,s) in enumerate(get_leaderboard(10),1):
        text += f"{i}. *{u}*: {s} pt\n"
    context.bot.send_message(chat_id, text, parse_mode=ParseMode.MARKDOWN)

def leaderboard(update: Update, context: CallbackContext):
    rows = get_leaderboard(10)
    text = "📊 *Top 10*:\n" + "\n".join(f"{i}. *{u}*: {s} pt"
                                       for i,(u,s) in enumerate(rows,1))
    update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

def error(update: Update, context: CallbackContext):
    logger.error(f"Update {update} errore {context.error}")

# ─── MAIN ────────────────────────────────────────────────────────
def main():
    load_dotenv()
    init_db()

    token = os.getenv('BOT_TOKEN')
    if not token:
        logger.error("BOT_TOKEN mancante"); return

    # prendi PORT da Railway o usa 3000 come fallback
    port = int(os.environ.get("PORT", 3000))
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port)).start()

    updater = Updater(token, use_context=True)
    dp = updater.dispatcher
    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            USERNAME: [MessageHandler(Filters.text & ~Filters.command, username_received)],
            GAME: [
                CallbackQueryHandler(start_game_callback, pattern='^start_game$'),
                CallbackQueryHandler(chop_callback,       pattern='^chop$'),
            ],
        },
        fallbacks=[CommandHandler('leaderboard', leaderboard)]
    )
    dp.add_handler(conv)
    dp.add_handler(CommandHandler('leaderboard', leaderboard))
    dp.add_error_handler(error)

    updater.start_polling()
    logger.info("Bot avviato. In attesa di comandi…")
    updater.idle()

if __name__ == '__main__':
    main()
