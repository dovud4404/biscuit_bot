import logging
import os
import re
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

NAME, PHONE, COMMENT = range(3)

GROUP_CHAT_ID = -1002697862181
BOT_TOKEN = "8170717877:AAEYlKs6kSheuLRbOlBQ-z4uwdagaR_M2Yk"

PHONE_RE = re.compile(r"^\+?\d[\d\s\-\(\)]{7,}$") 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "🍰 Добро пожаловать! Я приму ваш заказ на торт.\n"
        "Как вас зовут? (Имя и фамилия)",
        reply_markup=ReplyKeyboardRemove()
    )
    return NAME


async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("📞 Укажите номер телефона (например, +992 900‑000‑000):")
    return PHONE


async def ask_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone = update.message.text.strip()
    if not PHONE_RE.fullmatch(phone):
        await update.message.reply_text("❗ Телефон выглядит некорректно. Попробуйте ещё раз:")
        return PHONE

    context.user_data["phone"] = phone
    await update.message.reply_text(
        "💬 Добавьте комментарий (вкус, вес, дата) или напишите «-», если без комментариев:"
    )
    return COMMENT


async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["comment"] = update.message.text.strip()
    d = context.user_data

    order_text = (
        "🎂 *Новый заказ торта!*\n\n"
        f"*Имя:* {escape_markdown(d['name'], version=2)}\n"
        f"*Телефон:* {escape_markdown(d['phone'], version=2)}\n"
        f"*Комментарий:* {escape_markdown(d['comment'], version=2)}"
    )

    try:
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=order_text,
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        await update.message.reply_text(
            "Спасибо! 🎉 Ваш заказ отправлен администратору. Мы свяжемся с вами в ближайшее время."
        )
    except Exception as e:
        logging.exception("Не удалось отправить сообщение в канал: %s", e)
        await update.message.reply_text(
            "Упс! Не получилось отправить заказ. Попробуйте ещё раз позже."
        )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Заказ отменён. Чтобы начать заново, отправьте /start.")
    return ConversationHandler.END


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error("Exception while handling an update:", exc_info=context.error)



def main() -> None:
    if not (BOT_TOKEN and GROUP_CHAT_ID):
        raise RuntimeError("BOT_TOKEN или GROUP_CHAT_ID не заданы в переменных окружения")

    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_comment)],
            COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, finish)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    app.add_error_handler(error_handler)

    logging.info("Bot started…")
    app.run_polling()


if __name__ == "__main__":
    main()
