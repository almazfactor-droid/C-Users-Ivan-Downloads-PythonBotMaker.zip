import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import telebot

# ----- Логи для Render -----
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ----- Переменные окружения -----
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL = os.environ.get("TELEGRAM_CHANNEL_ID")  # пример: @poputiksebe26

if not TOKEN or not CHANNEL:
    raise RuntimeError("Нет TELEGRAM_BOT_TOKEN или TELEGRAM_CHANNEL_ID")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
bot.delete_webhook(drop_pending_updates=True)

# ----- Генерация текста -----
def build_post(time_label: str) -> str:
    now_msk = datetime.now(ZoneInfo("Europe/Moscow")).strftime("%d.%m.%Y, %H:%M")
    title = {
        "morning": "<b>АПЛ — утренний бриф ☕</b>",
        "day":     "<b>АПЛ — дневной апдейт ⚽</b>",
        "now":     "<b>АПЛ — свежий апдейт 🔔</b>",
    }.get(time_label, "<b>АПЛ — апдейт</b>")

    # Здесь можно вставить свой текст или автоматическую сводку
    return (
        f"{title}\n"
        f"📅 {now_msk} (МСК)\n\n"
        "Манчестер Юнайтед — фокус на прессинг и баланс в центре.\n"
        "Ливерпуль — Слот пробует вариации полузащиты.\n"
        "Ман Сити — Холанд и Родри в порядке, темп высокий.\n"
        "Арсенал — стабильная серия, ротация по флангам.\n\n"
        "#АПЛ #новости"
    )

# ----- Публикация в канал -----
def send_post(time_label: str):
    text = build_post(time_label)
    logging.info(f"Отправляю пост ({time_label}) в канал {CHANNEL}...")
    bot.send_message(CHANNEL, text)
    logging.info("✅ Пост отправлен.")

# ===== Telegram-команды =====
@bot.message_handler(commands=["start"])
def on_start(m):
    bot.reply_to(
        m,
        "Привет! Я автопостер для канала.\n"
        "Команды:\n"
        "• /now — сразу публикую свежий пост в канал\n"
        "Планово публикую в 08:00 и 14:00 (МСК)."
    )

@bot.message_handler(commands=["now"])
def on_now(m):
    try:
        send_post("now")
        bot.reply_to(m, "✅ Отправил пост в канал.")
    except Exception as e:
        logging.exception("Ошибка при /now")
        bot.reply_to(m, f"⚠️ Ошибка: {e}")

# ===== Запуск планировщика + polling =====
if __name__ == "__main__":
    # Сбрасываем активный вебхук, чтобы polling не конфликтовал
    try:
        # удаляем вебхук и отбрасываем накопившиеся апдейты
        bot.delete_webhook(drop_pending_updates=True)
        # или так (в некоторых версиях): bot.remove_webhook()
        logging.info("Webhook удалён, запускаю планировщик и polling.")
    except Exception as e:
        logging.exception(f"Не удалось удалить webhook: {e}")

    # Планировщик (08:00 и 14:00 МСК)
    sched = BackgroundScheduler(timezone=ZoneInfo("Europe/Moscow"))
    sched.add_job(send_post, CronTrigger(hour=8, minute=0), args=["morning"])
    sched.add_job(send_post, CronTrigger(hour=14, minute=0), args=["day"])
    sched.start()
    logging.info("Бот запущен. План: 08:00 и 14:00 (МСК). Команда /now активна.")

    # Приём команд
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except KeyboardInterrupt:
        logging.info("Остановка.")

