import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)
import yt_dlp

# ==========================
# Variables Fly.io
# ==========================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")  # On récupère le token depuis les variables d'env
NUM_RESULTS = 10  # nombre de résultats à afficher
DOWNLOAD_DIR = "downloads"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ==========================
# Logging
# ==========================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

user_state = {}

# ==========================
# Commande /start
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_state:
        user_state[user_id] = {'lang': 'fr', 'history': []}

    keyboard = [
        [InlineKeyboardButton("🇫🇷 Français", callback_data='fr')],
        [InlineKeyboardButton("🇬🇧 English", callback_data='en')]
    ]
    await update.message.reply_text(
        "Choisissez votre langue / Choose your language :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==========================
# Choix de langue
# ==========================
async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = query.data
    user_state[query.from_user.id] = {'lang': lang, 'history': []}
    await query.answer()
    await go_menu(query, lang=lang)

# ==========================
# Menu principal
# ==========================
async def go_menu(query, lang=None):
    if lang is None:
        user_id = query.from_user.id
        lang = user_state.get(user_id, {}).get('lang', 'fr')

    keyboard = [
        [InlineKeyboardButton("🎵 Audio", callback_data='audio')],
        [InlineKeyboardButton("🎥 Vidéo", callback_data='video')],
        [InlineKeyboardButton("📜 Historique", callback_data='history')]
    ]
    msg = "Que voulez-vous faire ?" if lang == 'fr' else "What would you like to do?"
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

# ==========================
# Gestion des boutons
# ==========================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    state = user_state.get(user_id, {})

    data = query.data
    if data == 'menu':
        await go_menu(query)
        return
    if data == 'history':
        await show_history(query, state)
        return
    if data.startswith('select_'):
        index = int(data.split('_')[1])
        if 'search_results' in state and index < len(state['search_results']):
            state['query'] = state['search_results'][index]['webpage_url']
            user_state[user_id] = state
            await handle_message_after_search(query, state)
        return

    # Mode audio/video
    state['mode'] = data
    user_state[user_id] = state
    msg = {
        'audio': "Entrez le titre ou l’artiste 🎶 :" if state.get('lang', 'fr') == 'fr' else "Enter title or artist 🎶:",
        'video': "Entrez le lien, titre ou nom de vidéo 🎬 :" if state.get('lang', 'fr') == 'fr' else "Enter link, title or name 🎬:"
    }
    if data in ['audio', 'video']:
        await query.edit_message_text(msg[data])

# ==========================
# Historique
# ==========================
async def show_history(query, state):
    history = state.get('history', [])
    if not history:
        msg = "Aucun téléchargement pour le moment." if state.get('lang') == 'fr' else "No downloads yet."
    else:
        msg_lines = []
        for i, h in enumerate(history, 1):
            msg_lines.append(f"{i}. [{h['title']}]({h['url']}) ({h['type']})")
        msg = "\n".join(msg_lines)
    await query.edit_message_text(msg, parse_mode='Markdown')

# ==========================
# Gestion des messages
# ==========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    state = user_state.get(user_id, {})
    state['query'] = update.message.text
    user_state[user_id] = state

    if update.message.text.startswith("http://") or update.message.text.startswith("https://"):
        await handle_message_after_search(update.message, state)
    else:
        await do_search(update.message, state)

# ==========================
# Recherche YouTube
# ==========================
async def do_search(message, state):
    query_text = state['query']
    ydl_opts = {
        'quiet': True,
        'noplaylist': True,
        'default_search': f'ytsearch{NUM_RESULTS}',
        'nocheckcertificate': True,
        'cachedir': False
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{NUM_RESULTS}:{query_text}", download=False)
            if not info or 'entries' not in info or len(info['entries']) == 0:
                await message.reply_text("Aucun résultat trouvé pour cette recherche.")
                return
            videos = info['entries'][:NUM_RESULTS]
            user_id = message.from_user.id
            state['search_results'] = videos
            user_state[user_id] = state
            keyboard = []
            for i, v in enumerate(videos):
                title = v.get('title', 'No title')
                keyboard.append([InlineKeyboardButton(f"{i+1}. {title[:50]}", callback_data=f'select_{i}')])
            keyboard.append([InlineKeyboardButton("⬅️ Menu", callback_data='menu')])
            text = "Résultats trouvés : choisissez la vidéo :" if state.get('lang') == 'fr' else "Results found: choose the video:"
            await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        await message.reply_text("Erreur lors de la recherche : " + str(e))

# ==========================
# Boutons qualité
# ==========================
async def handle_message_after_search(obj, state):
    mode = state.get('mode')
    user_id = obj.from_user.id if hasattr(obj, 'from_user') else obj.message.from_user.id
    if mode == 'audio':
        buttons = [[InlineKeyboardButton("MP3", callback_data='bestaudio')]]
    else:
        buttons = [[
            InlineKeyboardButton("Best", callback_data='best'),
            InlineKeyboardButton("360p", callback_data='360p'),
            InlineKeyboardButton("144p", callback_data='144p')
        ]]
    buttons.append([InlineKeyboardButton("⬅️ Menu", callback_data='menu')])
    text = "Choisissez la qualité :" if state.get('lang', 'fr') == 'fr' else "Choose quality:"
    if hasattr(obj, 'reply_text'):
        await obj.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await obj.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

# ==========================
# Téléchargement selon qualité
# ==========================
async def quality_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    state = user_state.get(user_id, {})
    query_text = state.get('query')
    quality = query.data
    mode = state.get('mode')

    # Map qualité → format MP4 forcé
    format_map = {
        'best': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
        '360p': 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]',
        '144p': 'bestvideo[height<=144][ext=mp4]+bestaudio[ext=m4a]/best[height<=144][ext=mp4]',
        'bestaudio': 'bestaudio'
    }

    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_DIR}/%(title).50s.%(ext)s',
        'format': format_map.get(quality, 'best'),
        'merge_output_format': 'mp4' if mode == 'video' else None,
        'noplaylist': True,
        'quiet': True,
    }

    if mode == 'audio':
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query_text, download=True)
            filename = ydl.prepare_filename(info)
            if mode == 'audio':
                filename = filename.rsplit('.', 1)[0] + ".mp3"

            # Historique
            history = state.get('history', [])
            history.append({
                'title': info.get('title', 'No title'),
                'url': info.get('webpage_url', query_text),
                'type': mode
            })
            state['history'] = history
            user_state[user_id] = state

        if mode == 'audio':
            with open(filename, 'rb') as f:
                await query.message.reply_document(f)
        else:
            with open(filename, 'rb') as f:
                await query.message.reply_video(f)

    except Exception as e:
        await query.message.reply_text("Erreur : " + str(e))

# ==========================
# MAIN
# ==========================
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(set_language, pattern='^(fr|en)$'))
    app.add_handler(CallbackQueryHandler(button, pattern='^(audio|video|history|menu|select_\\d)$'))
    app.add_handler(CallbackQueryHandler(quality_choice, pattern='^(best|360p|144p|bestaudio)$'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot démarré... tape /start dans Telegram")
    app.run_polling()

if __name__ == "__main__":
    main()