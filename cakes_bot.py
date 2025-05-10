#!/usr/bin/env python3
import logging
import os
import re
import html

from telegram import Update, ReplyKeyboardRemove
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# ─── Conversation states ───────────────────────────────────────────────────────
NAME, PHONE, COMMENT = range(3)

# ─── Configuration from env vars ───────────────────────────────────────────────
BOT_TOKEN      = os.environ["BOT_TOKEN"]
GROUP_CHAT_ID  = int(os.environ["GROUP_CHAT_ID"])
PHONE_PATTERN  = re.compile(r"^\+?\d[\d\s\-\(\)]{7,}$")

# ─── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# ─── Handlers ──────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "🍰 Добро пожаловать! Я приму ваш заказ на торт.\n"
        "Как вас зовут? (Имя и фамилия)",
        reply_markup=ReplyKeyboardRemove()
    )
    return NAME

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("📞 Укажите номер телефона (например, +992 900-000-000):")
    return PHONE

async def ask_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone = update.message.text.strip()
    if not PHONE_PATTERN.fullmatch(phone):
        await update.message.reply_text("❗ Телефон некорректен. Попробуйте ещё раз:")
        return PHONE

    context.user_data["phone"] = phone
    await update.message.reply_text(
        "💬 Добавьте комментарий (вкус, вес, дата) или «-», если без комментариев:"
    )
    return COMMENT

async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = context.user_data
    data["comment"] = update.message.text.strip()

    # Экранируем только ввод пользователя
    name    = html.escape(data["name"])
    phone   = html.escape(data["phone"])
    comment = html.escape(data["comment"])

    order_text = (
        "🎂 <b>Новый заказ торта!</b>\n\n"
        f"<b>Имя:</b> {name}\n"
        f"<b>Телефон:</b> {phone}\n"
        f"<b>Комментарий:</b> {comment}"
    )

    try:
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=order_text,
            parse_mode=ParseMode.HTML,
        )
        await update.message.reply_text(
            "Спасибо! 🎉 Ваш заказ отправлен администратору. Мы свяжемся с вами в ближайшее время."
        )
    except Exception:
        logging.exception("Не удалось отправить сообщение в канал")
        await update.message.reply_text(
            "Упс! Что-то пошло не так. Попробуйте позже."
        )

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Заказ отменён. Чтобы начать сначала, отправьте /start."
    )
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error("Ошибка обработки обновления:", exc_info=context.error)


# ─── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    # Команда build-hook от Render автоматически подставит переменную RENDER_EXTERNAL_HOSTNAME
    external_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
    port          = int(os.environ.get("PORT", "8443"))

    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            PHONE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_comment)],
            COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, finish)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv)
    app.add_error_handler(error_handler)

    # Регистрируем webhook в Telegram
    webhook_url = f"https://{external_host}/{BOT_TOKEN}"
    app.bot.set_webhook(webhook_url)
    logging.info("Webhook установлен: %s", webhook_url)

    # Запускаем HTTP-сервер для приёма вебхуков
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN,
    )


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
