from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import OPENAI_API_KEY, UPLOADS_DIR
from database import SessionLocal
from services.dish_service import (
    add_component,
    add_ingredient,
    create_dish,
    delete_dish,
    get_component,
    get_dish,
    get_user_dishes,
    update_dish_text,
    set_dish_photo,
)
from services.html_service import generate_dish_html
from services.image_service import ImageProcessingError, process_dish_photo
from services.speech_service import SpeechError, transcribe_audio

logger = logging.getLogger(__name__)

(
    MENU,
    CREATE_TITLE,
    CREATE_YIELD,
    DISH_MENU,
    WAIT_PHOTO,
    WAIT_VOICE,
    WAIT_VOICE_EDIT,
    WAIT_COMMENT,
    COMPONENT_NAME,
    COMPONENT_PORTION,
    COMPONENT_YIELD,
    COMPONENT_PREP,
    ING_NAME,
    ING_AMOUNT,
    EDIT_FIELD,
) = range(15)

MAIN_MENU_KB = ReplyKeyboardMarkup(
    [["Создать блюдо", "Мои блюда"], ["Помощь"]], resize_keyboard=True
)

DISH_MENU_KB = ReplyKeyboardMarkup(
    [
        ["Загрузить фото", "Загрузить голос"],
        ["Добавить компонент", "Предпросмотр"],
        ["Сформировать HTML", "Редактировать блюдо"],
        ["Удалить блюдо", "Назад"],
    ],
    resize_keyboard=True,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "Привет! Я помогу собрать технологическую карту блюда. Выберите действие:",
        reply_markup=MAIN_MENU_KB,
    )
    return MENU


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (
        "Как работать с ботом:\n"
        "1) Создайте блюдо (название + выход).\n"
        "2) Загрузите фото блюда и голосовое описание.\n"
        "3) Проверьте/исправьте распознанный текст.\n"
        "4) Добавьте компоненты и ингредиенты вручную.\n"
        "5) Сформируйте HTML и распечатайте."
    )
    await update.message.reply_text(text, reply_markup=MAIN_MENU_KB)
    return MENU


async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text == "Создать блюдо":
        await update.message.reply_text("Введите название блюда:", reply_markup=ReplyKeyboardRemove())
        return CREATE_TITLE
    if text == "Мои блюда":
        return await list_dishes(update, context)
    if text == "Помощь":
        return await help_cmd(update, context)

    await update.message.reply_text("Пожалуйста, используйте кнопки меню.", reply_markup=MAIN_MENU_KB)
    return MENU


async def create_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    title = (update.message.text or "").strip()
    if not title:
        await update.message.reply_text("Название не может быть пустым. Введите снова:")
        return CREATE_TITLE
    context.user_data["new_title"] = title
    await update.message.reply_text("Укажите итоговый выход блюда (например, 350 г):")
    return CREATE_YIELD


async def create_yield(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    final_yield = (update.message.text or "").strip()
    if not final_yield:
        await update.message.reply_text("Выход не может быть пустым. Введите снова:")
        return CREATE_YIELD

    user_id = update.effective_user.id
    with SessionLocal() as session:
        dish = create_dish(session, user_id=user_id, title=context.user_data["new_title"], final_yield=final_yield)

    context.user_data["dish_id"] = dish.id
    await update.message.reply_text(
        f"Блюдо «{dish.title}» создано. Теперь можно добавить фото, голос и компоненты.",
        reply_markup=DISH_MENU_KB,
    )
    return DISH_MENU


async def list_dishes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    with SessionLocal() as session:
        dishes = get_user_dishes(session, user_id)

    if not dishes:
        await update.message.reply_text("У вас пока нет блюд.", reply_markup=MAIN_MENU_KB)
        return MENU

    buttons = [[InlineKeyboardButton(f"#{d.id} {d.title}", callback_data=f"open_dish:{d.id}")] for d in dishes]
    await update.message.reply_text("Ваши блюда:", reply_markup=InlineKeyboardMarkup(buttons))
    return MENU


async def open_dish_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    dish_id = int(query.data.split(":", 1)[1])

    with SessionLocal() as session:
        dish = get_dish(session, dish_id=dish_id, user_id=update.effective_user.id)
    if not dish:
        await query.message.reply_text("Блюдо не найдено.")
        return MENU

    context.user_data["dish_id"] = dish.id
    await query.message.reply_text(f"Открыто блюдо: {dish.title}", reply_markup=DISH_MENU_KB)
    return DISH_MENU


def _get_current_dish(user_id: int, dish_id: int):
    with SessionLocal() as session:
        return get_dish(session, dish_id=dish_id, user_id=user_id)


async def dish_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    dish_id = context.user_data.get("dish_id")
    if not dish_id:
        await update.message.reply_text("Сначала выберите блюдо.", reply_markup=MAIN_MENU_KB)
        return MENU

    text = (update.message.text or "").strip()
    if text == "Загрузить фото":
        await update.message.reply_text("Пришлите фото блюда одним изображением.")
        return WAIT_PHOTO
    if text == "Загрузить голос":
        if not OPENAI_API_KEY:
            await update.message.reply_text("OPENAI_API_KEY не задан. Расшифровка голоса недоступна.")
            return DISH_MENU
        await update.message.reply_text("Пришлите voice или audio файл.")
        return WAIT_VOICE
    if text == "Добавить компонент":
        context.user_data["component_data"] = {}
        await update.message.reply_text("Название компонента/п/ф:")
        return COMPONENT_NAME
    if text == "Предпросмотр":
        return await preview_dish(update, context)
    if text == "Сформировать HTML":
        return await export_html(update, context)
    if text == "Редактировать блюдо":
        await update.message.reply_text(
            "Что редактировать? (название / выход / комментарий)", reply_markup=ReplyKeyboardRemove()
        )
        return EDIT_FIELD
    if text == "Удалить блюдо":
        return await remove_dish(update, context)
    if text == "Назад":
        await update.message.reply_text("Главное меню.", reply_markup=MAIN_MENU_KB)
        return MENU

    await update.message.reply_text("Используйте кнопки меню блюда.", reply_markup=DISH_MENU_KB)
    return DISH_MENU


async def wait_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message.photo:
        await update.message.reply_text("Пожалуйста, отправьте именно фото.")
        return WAIT_PHOTO

    dish_id = context.user_data.get("dish_id")
    user_id = update.effective_user.id

    photo = update.message.photo[-1]
    tg_file = await context.bot.get_file(photo.file_id)

    original_path = UPLOADS_DIR / f"dish_{dish_id}_{uuid4().hex}.jpg"
    await tg_file.download_to_drive(str(original_path))

    processed_path = UPLOADS_DIR / f"dish_{dish_id}_{uuid4().hex}_processed.jpg"
    message = "Фото сохранено."
    processed_saved = ""
    try:
        processed_saved = process_dish_photo(str(original_path), str(processed_path))
        message += " Фон очищен, подготовлена версия на белом фоне."
    except ImageProcessingError as exc:
        logger.warning("Image processing failed: %s", exc)
        message += " Не удалось обработать фон, будет использовано исходное фото."

    with SessionLocal() as session:
        dish = get_dish(session, dish_id=dish_id, user_id=user_id)
        if dish:
            set_dish_photo(session, dish, str(original_path), processed_saved)

    await update.message.reply_text(message, reply_markup=DISH_MENU_KB)
    return DISH_MENU


async def wait_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    media = msg.voice or msg.audio
    if not media:
        await msg.reply_text("Пришлите voice или audio файл.")
        return WAIT_VOICE

    dish_id = context.user_data.get("dish_id")
    user_id = update.effective_user.id
    tg_file = await context.bot.get_file(media.file_id)

    ext = ".ogg" if msg.voice else Path((msg.audio.file_name or "audio.mp3")).suffix or ".mp3"
    audio_path = UPLOADS_DIR / f"dish_{dish_id}_{uuid4().hex}{ext}"
    await tg_file.download_to_drive(str(audio_path))

    await msg.reply_text("Расшифровываю аудио, подождите...")
    try:
        text = transcribe_audio(str(audio_path))
    except SpeechError as exc:
        await msg.reply_text(f"Не удалось расшифровать аудио: {exc}")
        return DISH_MENU

    context.user_data["voice_text_candidate"] = text
    await msg.reply_text(
        f"Результат распознавания:\n\n{text}\n\n"
        "Ответьте:\n"
        "- 'подтвердить' чтобы сохранить\n"
        "- 'ввести заново' чтобы прислать новое аудио\n"
        "- или отправьте исправленный текст вручную"
    )
    return WAIT_VOICE_EDIT


async def wait_voice_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    answer = (update.message.text or "").strip()
    dish_id = context.user_data.get("dish_id")
    user_id = update.effective_user.id

    if answer.lower() == "ввести заново":
        await update.message.reply_text("Хорошо, пришлите новое voice/audio.")
        return WAIT_VOICE

    text_to_save = context.user_data.get("voice_text_candidate", "")
    if answer.lower() != "подтвердить":
        text_to_save = answer

    if not text_to_save:
        await update.message.reply_text("Текст пустой. Пришлите исправленный текст или 'ввести заново'.")
        return WAIT_VOICE_EDIT

    with SessionLocal() as session:
        dish = get_dish(session, dish_id=dish_id, user_id=user_id)
        if dish:
            update_dish_text(session, dish, "voice_text", text_to_save)

    await update.message.reply_text("Текст голосового описания сохранен.", reply_markup=DISH_MENU_KB)
    return DISH_MENU


async def component_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = (update.message.text or "").strip()
    if not name:
        await update.message.reply_text("Название компонента не может быть пустым.")
        return COMPONENT_NAME
    context.user_data["component_data"]["name"] = name
    await update.message.reply_text("Количество на порцию (например, 1 шт / 120 г):")
    return COMPONENT_PORTION


async def component_portion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["component_data"]["portion_amount"] = (update.message.text or "").strip()
    await update.message.reply_text("Выход компонента:")
    return COMPONENT_YIELD


async def component_yield(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["component_data"]["component_yield"] = (update.message.text or "").strip()
    await update.message.reply_text("Описание приготовления компонента:")
    return COMPONENT_PREP


async def component_prep(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = context.user_data["component_data"]
    data["preparation_text"] = (update.message.text or "").strip()

    dish_id = context.user_data.get("dish_id")
    user_id = update.effective_user.id
    with SessionLocal() as session:
        dish = get_dish(session, dish_id=dish_id, user_id=user_id)
        if not dish:
            await update.message.reply_text("Блюдо не найдено.", reply_markup=MAIN_MENU_KB)
            return MENU
        component = add_component(
            session,
            dish,
            portion_amount=data["portion_amount"],
            name=data["name"],
            component_yield=data["component_yield"],
            preparation_text=data["preparation_text"],
        )

    context.user_data["component_id"] = component.id
    await update.message.reply_text(
        "Компонент добавлен. Теперь можно добавить ингредиент.\n"
        "Введите название ингредиента или напишите 'пропустить'."
    )
    return ING_NAME


async def ingredient_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = (update.message.text or "").strip()
    if name.lower() == "пропустить":
        await update.message.reply_text("Готово.", reply_markup=DISH_MENU_KB)
        return DISH_MENU

    if not name:
        await update.message.reply_text("Название ингредиента не может быть пустым.")
        return ING_NAME

    context.user_data["ingredient_name"] = name
    await update.message.reply_text("Граммовка/количество (число):")
    return ING_AMOUNT


async def ingredient_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw_amount = (update.message.text or "").replace(",", ".").strip()
    try:
        amount = float(raw_amount)
    except ValueError:
        await update.message.reply_text("Введите число, например 25 или 12.5")
        return ING_AMOUNT

    dish_id = context.user_data.get("dish_id")
    component_id = context.user_data.get("component_id")
    user_id = update.effective_user.id

    with SessionLocal() as session:
        dish = get_dish(session, dish_id=dish_id, user_id=user_id)
        if not dish:
            await update.message.reply_text("Блюдо не найдено.", reply_markup=MAIN_MENU_KB)
            return MENU
        component = get_component(session, component_id=component_id, dish_id=dish.id)
        if not component:
            await update.message.reply_text("Компонент не найден.", reply_markup=DISH_MENU_KB)
            return DISH_MENU
        add_ingredient(session, component, name=context.user_data["ingredient_name"], amount=amount)

    await update.message.reply_text(
        "Ингредиент добавлен. Введите следующий ингредиент или 'пропустить'."
    )
    return ING_NAME


async def preview_dish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    dish_id = context.user_data.get("dish_id")
    user_id = update.effective_user.id

    with SessionLocal() as session:
        dish = get_dish(session, dish_id=dish_id, user_id=user_id)

    if not dish:
        await update.message.reply_text("Блюдо не найдено.", reply_markup=MAIN_MENU_KB)
        return MENU

    lines = [
        f"Блюдо: {dish.title}",
        f"Выход: {dish.final_yield}",
        f"Комментарий: {dish.comment or '—'}",
        f"Голосовое описание: {'есть' if dish.voice_text else 'нет'}",
        f"Фото: {'есть' if dish.photo_path else 'нет'}",
        "",
        "Компоненты:",
    ]
    if not dish.components:
        lines.append("— нет компонентов")

    for i, comp in enumerate(dish.components, start=1):
        lines.append(f"{i}. {comp.name} ({comp.portion_amount}, выход: {comp.component_yield})")
        lines.append(f"   Описание: {comp.preparation_text or '—'}")
        if not comp.ingredients:
            lines.append("   Ингредиенты: —")
        for ing in comp.ingredients:
            lines.append(f"   - {ing.name}: {ing.amount:g}")

    await update.message.reply_text("\n".join(lines), reply_markup=DISH_MENU_KB)
    return DISH_MENU


async def edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    field = (update.message.text or "").strip().lower()
    if field not in {"название", "выход", "комментарий"}:
        await update.message.reply_text("Доступно: название / выход / комментарий")
        return EDIT_FIELD

    context.user_data["edit_field"] = field
    await update.message.reply_text(f"Введите новое значение для поля: {field}")
    return WAIT_COMMENT


async def edit_field_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip()
    field_map = {"название": "title", "выход": "final_yield", "комментарий": "comment"}

    field = field_map[context.user_data["edit_field"]]
    dish_id = context.user_data.get("dish_id")
    user_id = update.effective_user.id

    with SessionLocal() as session:
        dish = get_dish(session, dish_id=dish_id, user_id=user_id)
        if dish:
            update_dish_text(session, dish, field, value)

    await update.message.reply_text("Данные блюда обновлены.", reply_markup=DISH_MENU_KB)
    return DISH_MENU


async def remove_dish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    dish_id = context.user_data.get("dish_id")
    user_id = update.effective_user.id

    with SessionLocal() as session:
        dish = get_dish(session, dish_id=dish_id, user_id=user_id)
        if not dish:
            await update.message.reply_text("Блюдо не найдено.", reply_markup=MAIN_MENU_KB)
            return MENU
        delete_dish(session, dish)

    context.user_data.pop("dish_id", None)
    await update.message.reply_text("Блюдо удалено.", reply_markup=MAIN_MENU_KB)
    return MENU


async def export_html(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    dish_id = context.user_data.get("dish_id")
    user_id = update.effective_user.id

    with SessionLocal() as session:
        dish = get_dish(session, dish_id=dish_id, user_id=user_id)
        if not dish:
            await update.message.reply_text("Блюдо не найдено.", reply_markup=MAIN_MENU_KB)
            return MENU
        export_path = generate_dish_html(dish)

    await update.message.reply_document(document=Path(export_path).open("rb"), filename=Path(export_path).name)
    await update.message.reply_text("HTML-файл сформирован и отправлен.", reply_markup=DISH_MENU_KB)
    return DISH_MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Действие отменено.", reply_markup=MAIN_MENU_KB)
    return MENU


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Не понял формат сообщения. Используйте кнопки меню или /start.")


def build_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, menu_router),
                CallbackQueryHandler(open_dish_callback, pattern=r"^open_dish:\d+$"),
            ],
            CREATE_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_title)],
            CREATE_YIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_yield)],
            DISH_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, dish_menu_router)],
            WAIT_PHOTO: [MessageHandler(filters.PHOTO, wait_photo), MessageHandler(filters.ALL, wait_photo)],
            WAIT_VOICE: [
                MessageHandler(filters.VOICE | filters.AUDIO, wait_voice),
                MessageHandler(filters.ALL, wait_voice),
            ],
            WAIT_VOICE_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, wait_voice_edit)],
            COMPONENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, component_name)],
            COMPONENT_PORTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, component_portion)],
            COMPONENT_YIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, component_yield)],
            COMPONENT_PREP: [MessageHandler(filters.TEXT & ~filters.COMMAND, component_prep)],
            ING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ingredient_name)],
            ING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ingredient_amount)],
            EDIT_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_field)],
            WAIT_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_field_value)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("help", help_cmd)],
        allow_reentry=True,
    )


def register_handlers(application: Application) -> None:
    application.add_handler(build_conversation_handler())
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(MessageHandler(filters.ALL, unknown_message))
