import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, ApplicationBuilder
from gigachat import GigaChat

TG_TOKEN = '8549207829:AAG00pVRjNQCSKiPeDgreI6rEzpJxSPuFj4'
GIGACHAT_AUTH_TOKEN = "MDE5YzE0ZjAtZWY3My03NDIwLThjMzUtZWFiMjIzMjVjZjY0OjFkYWQyYjhjLWM2ZGYtNDFlYS05NDBjLTkzNzcyMThmMDY4MA=="
GIGACHAT_SCOPE = "GIGACHAT_API_PERS"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

gigachat = GigaChat(credentials=GIGACHAT_AUTH_TOKEN, scope=GIGACHAT_SCOPE, verify_ssl_certs=False)

# Состояния для ConversationHandler
OUTLINE, STYLE = range(2)

STYLES = {
    "научный": "Научный стиль (академический, с терминологией, строгий)",
    "деловой": "Официально-деловой стиль (для документов, отчетов, писем)",
    "художественный": "Художественный стиль (образный, эмоциональный, литературный)",
    "разговорный": "Разговорный стиль (простой, дружеский, как в общении с друзьями)",
    "рекламный": "Рекламный стиль (продающий, цепляющий, с призывами к действию)",
    "публицистический": "Публицистический стиль (для статей, блогов, постов в соцсетях)"
}

style_keyboard = ReplyKeyboardMarkup(
    [[style] for style in STYLES.keys()],
    one_time_keyboard=True,
    resize_keyboard=True
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запуск диалога - просим прислать конспект."""
    await update.message.reply_text(
        "Привет! Я помогу тебе написать текст на основе краткого конспекта.\n\n"
        "📝 **Шаг 1 из 2:** Пришли мне краткий конспект (план, тезисы, ключевые мысли) того, "
        "что должен содержать будущий текст.\n\n"
        "Например:\n"
        "• Солнце - звезда\n"
        "• Состоит из водорода и гелия\n"
        "• Температура поверхности 5500°C\n"
        "• Влияет на климат Земли",
        parse_mode='Markdown'
    )
    return OUTLINE


async def handle_outline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохраняем конспект и просим выбрать стиль."""
    user_outline = update.message.text

    if len(user_outline.split()) < 3:
        await update.message.reply_text(
            "Конспект слишком короткий. Пожалуйста, напиши хотя бы 3-4 тезиса или ключевых мысли, "
            "чтобы я мог сгенерировать хороший текст."
        )
        return OUTLINE


    context.user_data['outline'] = user_outline

    await update.message.reply_text(
        "📝 **Шаг 2 из 2:** Теперь выбери стиль, в котором нужно написать текст:",
        reply_markup=style_keyboard,
        parse_mode='Markdown'
    )
    return STYLE


async def handle_style(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получаем стиль, генерируем текст и отправляем результат."""
    chosen_style = update.message.text.lower()

    if chosen_style not in STYLES:
        await update.message.reply_text(
            "Пожалуйста, выбери стиль из предложенных на клавиатуре.",
            reply_markup=style_keyboard
        )
        return STYLE

    user_outline = context.user_data.get('outline', '')

    processing_msg = await update.message.reply_text(
        "⏳ Генерирую текст... Это может занять несколько секунд.",
        reply_markup=ReplyKeyboardRemove()
    )

    try:
        generated_text = generate_text_from_outline(user_outline, chosen_style)

        if not generated_text:
            raise ValueError("Пустой ответ от нейросети")

        result_message = (
            f"✅ **Готово!**\n\n"
            f"**Сгенерированный текст:**\n{generated_text}"
        )

        await update.message.reply_text(result_message, parse_mode='Markdown')

        await processing_msg.delete()

    except Exception as e:
        logger.error(f"Ошибка при работе с GigaChat: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при генерации текста. Попробуй ещё раз или измени конспект.",
            reply_markup=ReplyKeyboardRemove()
        )

    context.user_data.clear()

    return ConversationHandler.END


def generate_text_from_outline(outline: str, style: str) -> str:
    """Генерирует развернутый текст на основе конспекта и выбранного стиля."""

    style_description = STYLES.get(style, style)

    prompt = (
        "Ты — профессиональный писатель и копирайтер. Твоя задача — написать связный, интересный и логичный текст, "
        "строго следуя предоставленному конспекту (кратким тезисам) и придав тексту заданный стиль.\n\n"

        "ПРАВИЛА:\n"
        "1. Внимательно изучи конспект. Раскрой КАЖДУЮ мысль из конспекта, превратив её в одно или несколько предложений.\n"
        "2. Добавь необходимые логические связки между предложениями и абзацами, чтобы текст читался плавно.\n"
        "3. Строго соблюдай заданный стиль: используй соответствующую лексику, интонацию и манеру изложения.\n"
        "4. НЕ добавляй информации, которой нет в конспекте, если она не требуется для связности текста.\n"
        "5. Объем итогового текста должен быть в 3-5 раз больше объема конспекта (примерно 1 абзац на 1 тезис).\n"
        "6. НЕ используй маркированные списки в ответе, пиши сплошным текстом с абзацами.\n"
        "7. НЕ добавляй никаких пояснений, заголовков или комментариев — только готовый текст.\n\n"

        "ИСХОДНЫЙ КОНСПЕКТ (основные идеи):\n"
        f"{outline}\n\n"

        "ТРЕБУЕМЫЙ СТИЛЬ:\n"
        f"{style_description}\n\n"

        "ГОТОВЫЙ ТЕКСТ (только текст, без пояснений):"
    )

    try:
        response = gigachat.chat(prompt)
        if response.choices and response.choices[0].message.content:
            return response.choices[0].message.content.strip()
        else:
            raise ValueError("GigaChat вернул пустой ответ")
    except Exception as e:
        logger.error(f"Ошибка при вызове GigaChat: {e}")
        raise


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет диалог."""
    await update.message.reply_text(
        "Диалог отменён. Чтобы начать заново, отправь /start",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет справочную информацию."""
    help_text = (
        "📚 **Как пользоваться ботом:**\n\n"
        "1. Отправь команду /start\n"
        "2. Пришли краткий конспект (план, тезисы, ключевые мысли)\n"
        "3. Выбери нужный стиль из списка\n"
        "4. Получи готовый текст!\n\n"
        "**Доступные стили:**\n"
        "• научный - академический, с терминологией\n"
        "• деловой - для документов и отчетов\n"
        "• художественный - литературный, образный\n"
        "• разговорный - простой, дружеский\n"
        "• рекламный - продающий, цепляющий\n"
        "• публицистический - для статей и блогов\n\n"
        "Для отмены диалога отправь /cancel"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')


def main() -> None:
    """Запускает бота."""
    proxy_url='socks5://157.245.155.242:6350'
    application = (Application.builder().token(TG_TOKEN).proxy(proxy_url).get_updates_proxy(proxy_url).build())

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            OUTLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_outline)],
            STYLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_style)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', help_command))

    logger.info("Бот запущен. Ожидание сообщений...")
    application.run_polling()


if __name__ == "__main__":
    main()