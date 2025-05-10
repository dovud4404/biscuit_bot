#!/usr/bin/env python3
import logging
import os
import re
import html

from telegram import Update, ReplyKeyboardRemove
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# ────────────── CONFIG ──────────────
BOT_TOKEN       = os.environ["BOT_TOKEN"]
GROUP_CHAT_ID   = int(os.environ["GROUP_CHAT_ID"])
EXTERNAL_URL    = os.environ["RENDER_EXTERNAL_URL"].rstrip("/")  # https://*.onrender.com
PORT            = int(os.environ.get("PORT", "8443"))

PHONE_RE = re.compile(r"^\+?\d[\d\s\-\(\)]{7,}$")
NAME, PHONE, COMMENT = range(3)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# ────────────── HANDLERS ──────────────
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
    if not PHONE_RE.fullmatch(phone):
        await update.message.reply_text("❗ Телефон некорректен. Попробуйте ещё раз:")
        return PHONE
    context.user_data["phone"] = phone
    await update.message.reply_text(
        "💬 Добавьте комментарий (вкус, вес, дата) или «-», если без комментариев:"
    )
    return COMMENT

async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    d = context.user_data
    d["comment"] = update.message.text.strip()

    order_text = (
        "🎂 <b>Новый заказ торта!</b>\n\n"
        f"<b>Имя:</b> {html.escape(d['name'])}\n"
        f"<b>Телефон:</b> {html.escape(d['phone'])}\n"
        f"<b>Комментарий:</b> {html.escape(d['comment'])}"
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
    await update.message.reply_text("Заказ отменён. Чтобы начать заново, отправьте /start.")
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error("Ошибка в обработке обновления:", exc_info=context.error)

# ────────────── MAIN ──────────────
def main() -> None:
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

    webhook_url = f"{EXTERNAL_URL}/{BOT_TOKEN}"
    logging.info("Webhook URL → %s", webhook_url)

    # ⬇️ запускаем HTTP-сервер и одновременно регистрируем вебхук
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=webhook_url,   # PTB сам вызовет setWebhook внутри
    )

if __name__ == "__main__":
    main()
