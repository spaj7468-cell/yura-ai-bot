import os
import asyncio

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.constants import ChatType

from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    filters,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler
)

from openai import OpenAI


# =========================
# КЛЮЧИ
# =========================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

if not TELEGRAM_TOKEN or not OPENROUTER_API_KEY:
    raise RuntimeError(
        "Укажи TELEGRAM_TOKEN и OPENROUTER_API_KEY в переменных окружения."
    )


# =========================
# OPENROUTER
# =========================

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)


# =========================
# ИГРЫ
# =========================

active_games = {}


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [
            InlineKeyboardButton(
                "🚀 Запустить бота",
                callback_data="start_ai"
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 Привет, как дела?\n\n"
        "Нажми кнопку ниже чтобы подключить ИИ.",
        reply_markup=reply_markup
    )


# =========================
# ПРИВЕТСТВИЕ ГРУППЫ
# =========================

async def welcome_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    chat = update.effective_chat

    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:

        await update.message.reply_text(
            "👋 Всем привет! Я Юра AI 🤖\n\n"
            "Я рад быть в этой группе.\n\n"
            "Чтобы говорить со мной:\n"
            "Юра ...\n\n"
            "🎮 Команды:\n"
            "Юра играть\n"
            "Юра стоп"
        )


# =========================
# КНОПКИ
# =========================

async def button_click(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    if query.data == "start_ai":

        await query.edit_message_text(
            "✅ ИИ подключен к тебе.\n\n"
            "Теперь отправь сообщение ✨"
        )

    elif query.data == "guess_yes":

        await query.edit_message_text(
            "😎 Ура! Я угадал персонажа!"
        )

        chat_id = query.message.chat.id

        if chat_id in active_games:
            del active_games[chat_id]

    elif query.data == "guess_no":

        await query.edit_message_text(
            "🙂 Жаль, что не угадал."
        )

        chat_id = query.message.chat.id

        if chat_id in active_games:
            del active_games[chat_id]


# =========================
# ЧАТ
# =========================

async def chat(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        user_message = update.message.text

        chat_type = update.message.chat.type

        user_id = update.effective_user.id

        chat_id = update.effective_chat.id

        # =========================
        # ГРУППЫ
        # =========================

        if chat_type in ["group", "supergroup"]:

            if not user_message.lower().startswith("юра"):
                return

            user_message = user_message[4:].strip()

            # =========================
            # ИГРА
            # =========================

            if user_message.lower() == "играть":

                if chat_id in active_games:

                    if active_games[chat_id] != user_id:

                        await update.message.reply_text(
                            "❌ Уже играет другой пользователь."
                        )

                        return

                active_games[chat_id] = user_id

                await update.message.reply_text(
                    "🎮 Игра началась!\n\n"
                    "Загадай персонажа 😎"
                )

                return

            if user_message.lower() == "стоп":

                if chat_id not in active_games:

                    await update.message.reply_text(
                        "❌ Сейчас никто не играет."
                    )

                    return

                if active_games[chat_id] != user_id:

                    await update.message.reply_text(
                        "❌ Игру начал другой пользователь."
                    )

                    return

                del active_games[chat_id]

                await update.message.reply_text(
                    "🛑 Игра остановлена."
                )

                return

            # Игра идет
            if chat_id in active_games:

                if active_games[chat_id] != user_id:
                    return

                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "✅ Да",
                            callback_data="guess_yes"
                        ),

                        InlineKeyboardButton(
                            "❌ Нет",
                            callback_data="guess_no"
                        )
                    ]
                ])

                await update.message.reply_text(
                    "🤔 Я угадал персонажа?",
                    reply_markup=keyboard
                )

                return

        # =========================
        # AI
        # =========================

        response = await asyncio.to_thread(
            client.chat.completions.create,

            model="mistralai/mistral-7b-instruct:free",

            messages=[
                {
                    "role": "system",
                    "content":
                    "Ты AI помощник Юра. "
                    "Отвечай коротко и дружелюбно."
                },

                {
                    "role": "user",
                    "content": user_message
                }
            ]
            )

        answer = response.choices[0].message.content

        await update.message.reply_text(answer)

    except Exception as e:

        print(f"Ошибка обработки сообщения: {type(e).__name__}: {e}")
        await update.message.reply_text(
            "❌ Не удалось обработать сообщение. Проверь настройки API и попробуй ещё раз."
        )


# =========================
# ЗАПУСК
# =========================

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()


app.add_handler(
    MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        welcome_group
    )
)

app.add_handler(
    CommandHandler(
        "start",
        start
    )
)

app.add_handler(
    CallbackQueryHandler(
        button_click
    )
)

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        chat
    )
)

print("🤖 Юра AI запущен...")

app.run_polling()
