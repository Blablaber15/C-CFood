import telebot
import config
import re
from telebot import types
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.apihelper import ApiTelegramException

bot = telebot.TeleBot(config.token)

# Раздельные словари для хранения выборов на каждом этапе
user_selections = {
    "open": {},
    "work": {},
    "finish": {}
}

# Хранилище для текстовых данных (например, для Расхода мяса)
user_inputs = {}

user_data = {}

OPTIONS_open = {
    "menu": "Актуальность меню проверена",
    "uniform": "Рабочая форма чистая",
    "hands": "Руки вымыты, перчатки готовы",
    "workspace": "Рабочее место чистое",
    "fridge": "Холодильник в порядке: температура проверена",
    "ingredients": "Все ингредиенты на месте",
    "meat": "Мясо / заготовки в наличии",
    "sauces": "Соусы заправлены",
    "tools": "Инвентарь готов к работе",
    "equipment": "Проверка оборудования"
}

OPTIONS_work = {
    "grammage": "Сборка строго по граммовке и техкарте",
    "meat_control": "Мясо не перерасходуется",
    "speed": "Очередь не стоит — соблюдаем скорость",
    "upsell": "Предлагаем допы каждому клиенту (сыр/мясо/напиток)",
    "cleanliness": "Чистота поддерживается постоянно",
    "display_case": "Гастроёмкости и витрина выглядят аккуратно",
    "marking": "Заготовки промаркированы, сроки контролируются",
    "idle_time": "При отсутствии гостей: уборка, подготовка места"
}

OPTIONS_finish = {
    "leftovers": "Остатки продуктов зафиксированы",
    "write_offs": "Списания зафиксированы",
    "meat_storage": "Мясо и заготовки убраны и промаркированы",
    "containers": "Гастроёмкости закрыты / убраны",
    "sauces_clean": "Соусы убраны, линия очищена",
    "tools_wash": "Оборудование и инвентарь вымыты",
    "disinfection": "Поверхности продезинфицированы",
    "fridge_close": "Холодильники проверены, температура записана",
    "trash": "Мусор вынесен",
    "cash_register": "Касса закрыта и сверена",
    "floor_clean": "Пол и рабочая зона убраны",
    "power_off": "Необходимое оборудование выключено",
    "meat_consumption": "Расход мяса (план-факт)"  # Перенесено в конец смены
}


# --- ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ФОРМИРОВАНИЯ ТЕКСТА О ТЧЕТА ---

def get_user_info_text(user_id, stage_title):
    info = user_data.get(user_id, {})
    name = info.get("name", "Не указано")
    date = info.get("date", "Не указана")
    shift = info.get("shift", "Не указана")
    
    return f"📌 **{stage_title}**\n\n👤 **Сотрудник:** {name}\n📅 **Дата:** {date}\n🔢 **Смена:** №{shift}"


# --- СТАРТ И ВВОД ДАННЫХ ---

@bot.message_handler(commands=["start"])
def start(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = KeyboardButton("✅ Открыть смену")
    markup.add(button)

    bot.send_message(
        message.chat.id,
        "✅ Доброе утро! Чтобы открыть смену, нажмите ниже ⬇️",
        reply_markup=markup
    )


@bot.message_handler(func=lambda message: message.text == "✅ Открыть смену")
def open_shift(message):
    markup = InlineKeyboardMarkup()
    button = InlineKeyboardButton(text="Ваш чек-лист", callback_data="run_cheklist")
    markup.add(button)

    bot.send_message(
        message.chat.id,
        "Смена открыта! ✅ Нажмите кнопку ниже для заполнения данных:",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == "run_cheklist")
def handle_cheklist(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "📅 **Шаг 1/3:** Введите дату смены в формате **ДД.ММ.ГГГГ** (например, 03.09.2026):",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_date_step)


def process_date_step(message):
    user_id = message.from_user.id
    date_pattern = r"^\d{2}\.\d{2}\.\d{4}$"

    if not message.text or not re.match(date_pattern, message.text):
        msg = bot.send_message(
            message.chat.id,
            "❌ **Неверный формат даты!** Пожалуйста, введите дату строго в формате **ДД.ММ.ГГГГ** (например, 25.10.2026):",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_date_step)
        return

    user_data[user_id] = {"date": message.text}

    msg = bot.send_message(
        message.chat.id,
        "🔢 **Шаг 2/3:** Введите **номер смены** (только число, например: 1 или 2):",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_shift_step)


def process_shift_step(message):
    user_id = message.from_user.id

    if not message.text or not message.text.isdigit():
        msg = bot.send_message(
            message.chat.id,
            "❌ **Ошибка!** Нужно ввести **только число**. Пожалуйста, укажите номер смены цифрами:",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_shift_step)
        return

    if user_id in user_data:
        user_data[user_id]["shift"] = message.text

    msg = bot.send_message(
        message.chat.id,
        "👤 **Шаг 3/3:** Введите **Имя и Фамилию** сотрудника (текст):",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_name_step)


def process_name_step(message):
    user_id = message.from_user.id

    if message.content_type != 'text':
        msg = bot.send_message(
            message.chat.id,
            "❌ **Ошибка!** Отправьте имя обычным текстом:",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_name_step)
        return

    if user_id in user_data:
        user_data[user_id]["name"] = message.text

    bot.send_message(
        message.chat.id,
        f"📋 **Данные приняты!**\n"
        f"Сотрудник: {user_data[user_id]['name']}\n"
        f"Дата: {user_data[user_id]['date']}\n"
        f"Смена: №{user_data[user_id]['shift']}\n\n"
        f"Теперь отметьте галочками выполненные пункты:",
        reply_markup=get_checkbox_keyboard(user_id, "open", OPTIONS_open, "toggle_open:", "finish_open"),
        parse_mode="Markdown"
    )


# --- ГЕНЕРАТОР КЛАВИАТУР ДЛЯ ЧЕК-ЛИСТОВ ---

def get_checkbox_keyboard(user_id, stage, options, toggle_prefix, finish_callback):
    selected = user_selections[stage].get(user_id, set())
    markup = InlineKeyboardMarkup()

    for item_id, label in options.items():
        status_emoji = "✅" if item_id in selected else "⬜️"
        
        # Динамическая подстановка введенных пользователем данных
        if item_id == "meat_consumption" and user_id in user_inputs and "meat_consumption" in user_inputs[user_id]:
            button_text = f"{status_emoji} {label}: {user_inputs[user_id]['meat_consumption']}"
        else:
            button_text = f"{status_emoji} {label}"

        callback_data = f"{toggle_prefix}{item_id}"
        markup.add(InlineKeyboardButton(text=button_text, callback_data=callback_data))

    completed_count = len(selected)
    total_count = len(options)
    finish_text = f"📥 Завершить отчет ({completed_count}/{total_count})"

    markup.add(InlineKeyboardButton(text=finish_text, callback_data=finish_callback))
    return markup


# --- 1. ЭТАП: ОТКРЫТИЕ СМЕНЫ ---

@bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_open:"))
def process_checkbox_open(call):
    user_id = call.from_user.id
    item_id = call.data.split(":")[1]

    if user_id not in user_selections["open"]:
        user_selections["open"][user_id] = set()

    if item_id in user_selections["open"][user_id]:
        user_selections["open"][user_id].remove(item_id)
    else:
        user_selections["open"][user_id].add(item_id)

    bot.answer_callback_query(call.id)
    
    try:
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=get_checkbox_keyboard(user_id, "open", OPTIONS_open, "toggle_open:", "finish_open")
        )
    except ApiTelegramException as e:
        if "message is not modified" not in e.description:
            raise e


@bot.callback_query_handler(func=lambda call: call.data == "finish_open")
def process_finish_open(call):
    user_id = call.from_user.id
    selected = user_selections["open"].get(user_id, set())

    if len(selected) < len(OPTIONS_open):
        bot.answer_callback_query(
            call.id,
            text=f"Вы выполнили не все пункты! Заполнено только {len(selected)} из {len(OPTIONS_open)}.",
            show_alert=True
        )
        return

    bot.answer_callback_query(call.id)
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)

    msg = bot.send_message(
        call.message.chat.id,
        "🎉 Отлично! Все пункты чек-листа выполнены.\n\n"
        "📸 Теперь, пожалуйста, **отправьте фотоотчет** (одну фотографию вашего рабочего места):",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, save_photo_report_open)


def save_photo_report_open(message):
    user_id = message.from_user.id

    if message.content_type == "photo":
        # Пересылка фотографии в целевую группу
        if hasattr(config, "GROUP_CHAT_ID") and config.GROUP_CHAT_ID:
            photo_id = message.photo[-1].file_id
            caption = get_user_info_text(user_id, "Открытие смены 🟢")
            try:
                bot.send_photo(config.GROUP_CHAT_ID, photo_id, caption=caption, parse_mode="Markdown")
            except Exception as e:
                print(f"❌ Ошибка отправки фото в группу (Открытие): {e}")

        user_selections["open"][user_id] = set()

        markup = InlineKeyboardMarkup()
        button = InlineKeyboardButton(text="📋 Отчет в середине дня", callback_data="run_work_checklist")
        markup.add(button)

        bot.send_message(
            message.chat.id,
            "✅ Фотоотчет открытия смены принят!\n\n"
            "Смена успешно зарегистрирована.\n"
            "Когда будете готовы сдать отчет в середине дня, нажмите кнопку ниже:",
            reply_markup=markup
        )
    else:
        msg = bot.send_message(
            message.chat.id,
            "❌ Ошибка. Нужна именно **фотография**. Пожалуйста, отправьте фото вашего рабочего места еще раз:",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, save_photo_report_open)


# --- 2. ЭТАП: СЕРЕДИНА ДНЯ ---

@bot.callback_query_handler(func=lambda call: call.data == "run_work_checklist")
def run_work_checklist(call):
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "📋 **Чек-лист середины дня.** Отметьте выполненные пункты:",
        reply_markup=get_checkbox_keyboard(call.from_user.id, "work", OPTIONS_work, "toggle_work:", "finish_work"),
        parse_mode="Markdown"
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_work:"))
def process_checkbox_work(call):
    user_id = call.from_user.id
    item_id = call.data.split(":")[1]

    if user_id not in user_selections["work"]:
        user_selections["work"][user_id] = set()

    if item_id in user_selections["work"][user_id]:
        user_selections["work"][user_id].remove(item_id)
    else:
        user_selections["work"][user_id].add(item_id)

    bot.answer_callback_query(call.id)
    
    try:
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=get_checkbox_keyboard(user_id, "work", OPTIONS_work, "toggle_work:", "finish_work")
        )
    except ApiTelegramException as e:
        if "message is not modified" not in e.description:
            raise e


@bot.callback_query_handler(func=lambda call: call.data == "finish_work")
def process_finish_work(call):
    user_id = call.from_user.id
    selected = user_selections["work"].get(user_id, set())

    if len(selected) < len(OPTIONS_work):
        bot.answer_callback_query(
            call.id,
            text=f"Вы выполнили не все пункты! Заполнено только {len(selected)} из {len(OPTIONS_work)}.",
            show_alert=True
        )
        return

    bot.answer_callback_query(call.id)
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)

    msg = bot.send_message(
        call.message.chat.id,
        "🎉 Отлично! Все пункты чек-листа выполнены.\n\n"
        "📸 Теперь, пожалуйста, **отправьте фотоотчет** (одну фотографию вашего рабочего места):",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, save_photo_report_work)


def save_photo_report_work(message):
    user_id = message.from_user.id

    if message.content_type == "photo":
        # Пересылка фотографии в целевую группу
        if hasattr(config, "GROUP_CHAT_ID") and config.GROUP_CHAT_ID:
            photo_id = message.photo[-1].file_id
            caption = get_user_info_text(user_id, "Середина дня 🟡")
            try:
                bot.send_photo(int(config.GROUP_CHAT_ID), photo_id, caption=caption, parse_mode="Markdown")
            except Exception as e:
                print(f"❌ Ошибка отправки фото в группу (Середина): {e}")

        user_selections["work"][user_id] = set()

        markup = InlineKeyboardMarkup()
        button = InlineKeyboardButton(text="🔒 Закрыть смену", callback_data="run_finish_checklist")
        markup.add(button)

        bot.send_message(
            message.chat.id,
            "✅ Фотоотчет середины дня принят!\n\n"
            "Отчет успешно зарегистрирован.\n"
            "Когда будете готовы закрыть смену, нажмите кнопку ниже:",
            reply_markup=markup
        )
    else:
        msg = bot.send_message(
            message.chat.id,
            "❌ Ошибка. Нужна именно **фотография**. Пожалуйста, отправьте фото вашего рабочего места еще раз:",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, save_photo_report_work)


# --- 3. ЭТАП: ЗАКРЫТИЕ СМЕНЫ ---

@bot.callback_query_handler(func=lambda call: call.data == "run_finish_checklist")
def run_finish_checklist(call):
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "🔒 **Чек-лист закрытия смены.** Отметьте выполненные пункты:",
        reply_markup=get_checkbox_keyboard(call.from_user.id, "finish", OPTIONS_finish, "toggle_finish:", "finish_finish"),
        parse_mode="Markdown"
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_finish:"))
def process_checkbox_finish(call):
    user_id = call.from_user.id
    item_id = call.data.split(":")[1]

    if user_id not in user_selections["finish"]:
        user_selections["finish"][user_id] = set()

    # Перехват клика по пункту Расход мяса (в конце смены)
    if item_id == "meat_consumption":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(
            call.message.chat.id,
            "🥩 Введите **Расход мяса (план-факт)** текстом\n(например: *10 кг / 9.5 кг* или *15/14*):",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_meat_input, call.message.message_id)
        return

    if item_id in user_selections["finish"][user_id]:
        user_selections["finish"][user_id].remove(item_id)
    else:
        user_selections["finish"][user_id].add(item_id)

    bot.answer_callback_query(call.id)
    
    try:
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=get_checkbox_keyboard(user_id, "finish", OPTIONS_finish, "toggle_finish:", "finish_finish")
        )
    except ApiTelegramException as e:
        if "message is not modified" not in e.description:
            raise e


# Функция приема ввода данных для Расхода мяса при закрытии смены
def process_meat_input(message, checklist_msg_id):
    user_id = message.from_user.id

    if not message.text:
        msg = bot.send_message(
            message.chat.id,
            "❌ **Ошибка!** Отправьте значения текстом (например: 10/9.5):",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_meat_input, checklist_msg_id)
        return

    # Сохраняем значение пользователя
    if user_id not in user_inputs:
        user_inputs[user_id] = {}
    user_inputs[user_id]["meat_consumption"] = message.text

    # Проставляем галочку в чек-листе закрытия смены
    if user_id not in user_selections["finish"]:
        user_selections["finish"][user_id] = set()
    user_selections["finish"][user_id].add("meat_consumption")

    bot.send_message(
        message.chat.id,
        f"✅ Значение *«{message.text}»* сохранено!",
        parse_mode="Markdown"
    )

    # Обновляем клавиатуру у сообщения с чек-листом закрытия смены
    try:
        bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=checklist_msg_id,
            reply_markup=get_checkbox_keyboard(user_id, "finish", OPTIONS_finish, "toggle_finish:", "finish_finish")
        )
    except ApiTelegramException:
        pass


@bot.callback_query_handler(func=lambda call: call.data == "finish_finish")
def process_finish_finish(call):
    user_id = call.from_user.id
    selected = user_selections["finish"].get(user_id, set())

    if len(selected) < len(OPTIONS_finish):
        bot.answer_callback_query(
            call.id,
            text=f"Вы выполнили не все пункты! Заполнено только {len(selected)} из {len(OPTIONS_finish)}.",
            show_alert=True
        )
        return

    bot.answer_callback_query(call.id)
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)

    msg = bot.send_message(
        call.message.chat.id,
        "🎉 Отлично! Все пункты чек-листа выполнены.\n\n"
        "📸 Теперь, пожалуйста, **отправьте фотоотчет** (одну фотографию вашего рабочего места):",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, save_photo_report_finish)


def save_photo_report_finish(message):
    user_id = message.from_user.id

    if message.content_type == "photo":
        # Пересылка фотографии в целевую группу
        if hasattr(config, "GROUP_CHAT_ID") and config.GROUP_CHAT_ID:
            photo_id = message.photo[-1].file_id
            caption = get_user_info_text(user_id, "Закрытие смены 🔴")
            
            meat_val = user_inputs.get(user_id, {}).get("meat_consumption")
            if meat_val:
                caption += f"\n🥩 **Расход мяса (план-факт):** {meat_val}"

            try:
                bot.send_photo(int(config.GROUP_CHAT_ID), photo_id, caption=caption, parse_mode="Markdown")
            except Exception as e:
                print(f"❌ Ошибка отправки фото в группу (Закрытие): {e}")

        # Очищаем временные данные пользователя по окончании смены
        user_selections["finish"][user_id] = set()
        if user_id in user_inputs:
            del user_inputs[user_id]
        if user_id in user_data:
            del user_data[user_id]

        bot.send_message(
            message.chat.id,
            "✅ Финальный фотоотчет принят!\n\n"
            "🔒 **Смена успешно закрыта.**\n"
            "Все отчеты зарегистрированы. Хорошего дня!",
            parse_mode="Markdown"
        )
    else:
        msg = bot.send_message(
            message.chat.id,
            "❌ Ошибка. Нужна именно **фотография**. Пожалуйста, отправьте фото вашего рабочего места еще раз:",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, save_photo_report_finish)


bot.polling(none_stop=True)