import os
import logging
import pandas as pd
from datetime import datetime, time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler, JobQueue

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# States
CATEGORIES = [
    "Каркас здания", "Устройство пола", "Кирпичная кладка", "Монтаж лифта", "Отделка",
    "ОВ ВК", "Монтаж оконных проемов", "Монтаж металлоконструкции", "Кровля",
    "Фасад", "Электрооборудования", "Система связи",
    "Оператор автокрана", "Оператор петушок", "Оператор экскаватора/погрузчика",
    "Петушок", "Автокран", "Экскаватор", "Самосвал"
]
MAX_VALUES = {
    "Каркас здания": 3, "Устройство пола": 2, "Кирпичная кладка": 10, "Монтаж лифта": 4,
    "Отделка": 8, "ОВ ВК": 7, "Монтаж оконных проемов": 2, "Монтаж металлоконструкции": 7,
    "Кровля": 6, "Фасад": 6, "Электрооборудования": 4, "Система связи": 6,
    "Оператор автокрана": 2, "Оператор петушок": 1, "Оператор экскаватора/погрузчика": 2,
    "Петушок": 1, "Автокран": 3, "Экскаватор": 1, "Самосвал": 1
}

STATE_INDEX = 0
EXCEL_FILE = "daily_headcount.xlsx"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['index'] = 0
    await update.message.reply_text(f"Введите количество для: {CATEGORIES[0]} (макс. {MAX_VALUES[CATEGORIES[0]]})")
    return STATE_INDEX

async def collect_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    index = context.user_data.get('index', 0)
    try:
        val = int(update.message.text)
        max_val = MAX_VALUES[CATEGORIES[index]]
        if 0 <= val <= max_val:
            context.user_data[CATEGORIES[index]] = val
        else:
            await update.message.reply_text(f"❗ Введите число от 0 до {max_val} для {CATEGORIES[index]}.")
            return STATE_INDEX
    except ValueError:
        await update.message.reply_text("❗ Пожалуйста, введите целое число.")
        return STATE_INDEX

    index += 1
    if index < len(CATEGORIES):
        context.user_data['index'] = index
        await update.message.reply_text(f"Введите количество для: {CATEGORIES[index]} (макс. {MAX_VALUES[CATEGORIES[index]]})")
        return STATE_INDEX
    else:
        summary = "📋 Отчёт по рабочим:\n"
        data = {"Дата": [datetime.now().strftime("%Y-%m-%d %H:%M")]}  # Initialize data for Excel
        for cat in CATEGORIES:
            val = context.user_data.get(cat, 0)
            summary += f"{cat}: {val}\n"
            data[cat] = [val]

        await update.message.reply_text(summary + "\n✅ Спасибо! Данные приняты.")

        # Append data to Excel
        try:
            df_new = pd.DataFrame(data)
            try:
                df_existing = pd.read_excel(EXCEL_FILE)
                df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            except FileNotFoundError:
                df_combined = df_new
            df_combined.to_excel(EXCEL_FILE, index=False)
        except Exception as e:
            logger.error(f"Ошибка при записи в Excel: {e}")

        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Ввод отменён.")
    return ConversationHandler.END

async def daily_reminder(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=916091427, text="⏰ Пожалуйста, введите количество рабочих на площадке. Напишите /start")

async def echo_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Ваш chat_id: {update.effective_chat.id}")

if __name__ == '__main__':
    application = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            STATE_INDEX: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_input)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('id', echo_id))

    job_queue = application.job_queue
    job_queue.run_daily(daily_reminder, time(hour=9, minute=0))
    job_queue.run_daily(daily_reminder, time(hour=14, minute=30))

    application.run_polling()
