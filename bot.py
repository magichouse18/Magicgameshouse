import logging
import time
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler,
    MessageHandler, Filters, CallbackContext
)

# ——— CONFIGURAZIONE DI BASE ———
TOKEN = "7287683654:AAEezRGlyOnA4iPWOUqpg5sr104tLjDaq8k"
GAME_DURATION = 30  # secondi

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

game_data = {}  # { chat_id: {username:str, score:int, playing:bool, start_time:float} }
SCORES_FILE = "scores.json"
if not os.path.exists(SCORES_FILE):
    with open(SCORES_FILE, "w") as f:
        json.dump({}, f)

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🎮 Benvenuto in *MagicGamesHouse*! 🎮\n"
        "Per cominciare, inviami il tuo username:",
        parse_mode="Markdown"
    )

def receive_username(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    username = update.message.text.strip()
    if chat_id not in game_data or not game_data[chat_id].get("username"):
        game_data[chat_id] = {"username": username, "playing": False}
        update.message.reply_text(
            f"✅ Username registrato come *{username}*.\nUsa /play per iniziare!",
            parse_mode="Markdown"
        )

def play(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    data = game_data.get(chat_id)
    if not data or not data.get("username"):
        update.message.reply_text("❗ Prima inviami il tuo username (usa /start).")
        return
    if data.get("playing"):
        update.message.reply_text("⚠️ Hai già una partita in corso!")
        return

    data.update(score=0, playing=True, start_time=time.time())
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🪓 Taglia!", callback_data="chop")]])
    update.message.reply_text(
        f"⏱️ Hai {GAME_DURATION} secondi per tagliare legna!\nPremi il bottone:",
        reply_markup=keyboard
    )

def chop_callback(update: Update, context: CallbackContext):
    query = update.callback_query; chat_id = query.message.chat_id
    data = game_data.get(chat_id)
    if not data or not data.get("playing"):
        query.answer("La partita è terminata.")
        return

    elapsed = time.time() - data["start_time"]
    if elapsed > GAME_DURATION:
        end_game(chat_id, context)
        query.answer("⏰ Tempo scaduto!")
    else:
        data["score"] += 1
        query.answer(f"Punteggio: {data['score']}")

def end_game(chat_id, context: CallbackContext):
    data = game_data[chat_id]
    data["playing"] = False
    username, score = data["username"], data["score"]

    with open(SCORES_FILE, "r") as f: all_scores = json.load(f)
    all_scores[username] = score
    with open(SCORES_FILE, "w") as f: json.dump(all_scores, f, indent=2)

    context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"⏰ *Tempo scaduto!* ⏰\n"
            f"{username}, hai totalizzato *{score}* punti!\n"
            "Usa /leaderboard per vedere la classifica."
        ),
        parse_mode="Markdown"
    )

def leaderboard(update: Update, context: CallbackContext):
    with open(SCORES_FILE, "r") as f: all_scores = json.load(f)
    if not all_scores:
        update.message.reply_text("Nessun punteggio registrato.")
        return
    sorted_scores = sorted(all_scores.items(), key=lambda kv: kv[1], reverse=True)
    text = "🏆 *Leaderboard* 🏆\n\n"
    for i, (u, s) in enumerate(sorted_scores[:10], 1):
        text += f"{i}. *{u}* — {s} punti\n"
    update.message.reply_text(text, parse_mode="Markdown")

def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("play", play))
    dp.add_handler(CommandHandler("leaderboard", leaderboard))
    dp.add_handler(CallbackQueryHandler(chop_callback, pattern="^chop$"))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, receive_username))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
