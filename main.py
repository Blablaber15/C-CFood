import telebot
import os
import re
from telebot import types
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.apihelper import ApiTelegramException

try:
    import config
    BOT_TOKEN = config.BOT_TOKEN
    GROUP_ID = config.GROUP_ID
    ADMIN_USER_IDS = {config.ADMIN_USER_ID}
except ImportError:
    BOT_TOKEN = os.environ["BOT_TOKEN"]
    GROUP_ID = os.environ["GROUP_ID"]
    ADMIN_USER_IDS = {
        int(user_id.strip())
        for user_id in os.environ.get("ADMIN_USER_IDS", "").split(",")
        if user_id.strip()
    }
bot = telebot.TeleBot(BOT_TOKEN)

# --- НАСТРОЙКА ОБЯЗАТЕЛЬНЫХ ФОТО ДЛЯ ПУНКТОВ ---
# True — бот потребует фото. False — пункт отмечается просто кликом.
REQUIRES_PHOTO_OPEN = {
    "menu": False,
    "uniform": True,
    "hands": False,
    "workspace": True,
    "fridge": True,
    "ingredients": True,
    "meat": True,
    "sauces": True,
    "tools": True,
    "equipment": False
}

REQUIRES_PHOTO_WORK = {
    "grammage": False,
    "meat_control": False,
    "speed": False,
    "upsell": False,
    "cleanliness": True,
    "display_case": True,
    "marking": True,
    "idle_time": False
}

REQUIRES_PHOTO_FINISH = {
    "leftovers": True,
    "write_offs": True,
    "meat_storage": True,
    "containers": True,
    "sauces_clean": True,
    "tools_wash": True,
    "disinfection": False,
    "fridge_close": True,
    "trash": True,
    "cash_register": True,
    "floor_clean": True,
    "power_off": False,
    "meat_consumption": False  # Для этого пункта используется текстовый ввод
}

# Раздельные словари для хранения выборов на каждом этапе
user_selections = {
    "open": {},
    "work": {},
    "finish": {}
}

# Хранилище сданных за сегодня отчетов для блокировки повторных кликов
submitted_reports = {
    "open": set(),
    "work": set(),
    "finish": set()
}

godmode_users = set()

STAGE_PREREQUISITES = {
    "open": (),
    "work": ("open",),
    "finish": ("open", "work")
}

# Хранилище для текстовых данных и состояний сессии
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
    "meat_consumption": "Расход мяса (план-факт)"
}
def get_user_info_text(user_id, stage_title):
    info = user_data.get(user_id, {})
    name = info.get("name", "Не указано")
    date = info.get("date", "Не указана")
    shift = info.get("shift", "Не указана")
    return f"📌 **{stage_title}**\n\n👤 **Сотрудник:** {name}\n📅 **Дата:** {date}\n🔢 **Смена:** {shift}"

def get_stages_keyboard(user_id):
    markup = InlineKeyboardMarkup()
    open_text = "🌅 Открытие смены (СДАНО)" if user_id in submitted_reports["open"] else "🌅 Открытие смены"
    work_text = "☀️ Отчет в середине дня (СДАНО)" if user_id in submitted_reports["work"] else "☀️ Отчет в середине дня"
    finish_text = "🌌 Закрытие смены (СДАНО)" if user_id in submitted_reports["finish"] else "🌌 Закрытие смены"
    
    markup.add(InlineKeyboardButton(text=open_text, callback_data="start_stage_open"))
    markup.add(InlineKeyboardButton(text=work_text, callback_data="start_stage_work"))
    markup.add(InlineKeyboardButton(text=finish_text, callback_data="start_stage_finish"))
    return markup

# --- СТАРТ И ВВОД ДАННЫХ ---

@bot.message_handler(commands=["start"])
def start(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    button = KeyboardButton("✅ Открыть смену")
    markup.add(button)
    bot.send_message(message.chat.id, "✅ Добрый день! Чтобы начать, нажмите кнопку ниже ⬇️", reply_markup=markup)

@bot.message_handler(commands=["reset_reports"])
def reset_reports(message):
    user_id = message.from_user.id
    for stage in submitted_reports:
        submitted_reports[stage].discard(user_id)
        user_selections[stage].pop(user_id, None)
    user_inputs.pop(user_id, None)
    user_data.pop(user_id, None)
    bot.send_message(message.chat.id, "♻️ Ваши отчеты сброшены. Теперь можно начать с открытия смены.")

@bot.message_handler(commands=["godmode"])
def enable_godmode(message):
    if message.from_user.id not in ADMIN_USER_IDS:
        bot.send_message(message.chat.id, "⛔ Эта команда доступна только администратору.")
        return
    godmode_users.add(message.from_user.id)
    bot.send_message(message.chat.id, "🛠 Godmode включен.")

@bot.message_handler(commands=["godmodeexit"])
def disable_godmode(message):
    godmode_users.discard(message.from_user.id)
    bot.send_message(message.chat.id, "🔒 Godmode выключен.")

@bot.message_handler(func=lambda message: message.text == "✅ Открыть смену")
def open_shift(message):
    user_id = message.from_user.id
    bot.send_message(message.chat.id, "Выберите чек-лист, который хотите заполнить:", reply_markup=get_stages_keyboard(user_id))

@bot.callback_query_handler(func=lambda call: call.data.startswith("start_stage_"))
def handle_stage_selection(call):
    stage = call.data.split("_")[2]  # Получаем open, work, или finish
    user_id = call.from_user.id
    
    if user_id in submitted_reports[stage] and user_id not in godmode_users:
        bot.answer_callback_query(call.id, text="❌ Эта смена уже закрыта и отправлена!", show_alert=True)
        return

    missing_stages = [] if user_id in godmode_users else [
        required_stage
        for required_stage in STAGE_PREREQUISITES[stage]
        if user_id not in submitted_reports[required_stage]
    ]
    if missing_stages:
        stage_names = {
            "open": "открытие смены",
            "work": "отчет в середине дня"
        }
        missing_text = " и ".join(stage_names[item] for item in missing_stages)
        bot.answer_callback_query(
            call.id,
            text=f"Сначала завершите: {missing_text}.",
            show_alert=True
        )
        return

    bot.answer_callback_query(call.id)
    
    if user_id not in user_inputs:
        user_inputs[user_id] = {}
    user_inputs[user_id]["target_stage"] = stage
    
    if user_id in user_data and "name" in user_data[user_id] and "date" in user_data[user_id]:
        launch_checklist_instantly(call.message.chat.id, user_id, stage)
    else:
        msg = bot.send_message(call.message.chat.id, "📅 **Шаг 1/3:** Введите дату в формате **ДД.ММ.ГГГГ** (например, 07.09.2026):", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_date_step)
def process_date_step(message):
    if message.text == "/start":
        start(message)
        return
        
    user_id = message.from_user.id
    date_pattern = r"^\d{2}\.\d{2}\.\d{4}$"
    if not message.text or not re.match(date_pattern, message.text):
        msg = bot.send_message(message.chat.id, "❌ **Неверный формат даты!** Пожалуйста, введите дату строго в формате **ДД.ММ.ГГГГ**:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_date_step)
        return
    
    user_data[user_id] = {"date": message.text}
    msg = bot.send_message(message.chat.id, "🔢 **Шаг 2/3:** Введите название или номер смены (например: 1, Вечер, Смена А):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_shift_step)

def process_shift_step(message):
    if message.text == "/start":
        start(message)
        return
        
    user_id = message.from_user.id
    if not message.text:
        msg = bot.send_message(message.chat.id, "❌ **Ошибка!** Введите название или номер смены:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_shift_step)
        return
    if user_id in user_data:
        user_data[user_id]["shift"] = message.text
    msg = bot.send_message(message.chat.id, "👤 **Шаг 3/3:** Введите **Имя и Фамилию** сотрудника (текст):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_name_step)

def process_name_step(message):
    if message.text == "/start":
        start(message)
        return
        
    user_id = message.from_user.id
    if message.content_type != 'text':
        msg = bot.send_message(message.chat.id, "❌ **Ошибка!** Отправьте имя обычным текстом:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_name_step)
        return
        
    if user_id in user_data:
        user_data[user_id]["name"] = message.text

    stage = user_inputs.get(user_id, {}).get("target_stage", "open")
    launch_checklist_instantly(message.chat.id, user_id, stage)

def launch_checklist_instantly(chat_id, user_id, stage):
    if stage == "open":
        reply_markup = get_checkbox_keyboard(user_id, "open", OPTIONS_open, "toggle_open:", "finish_open")
        title = "Открытие смены"
    elif stage == "work":
        reply_markup = get_checkbox_keyboard(user_id, "work", OPTIONS_work, "toggle_work:", "finish_work")
        title = "Отчет в середине дня"
    else:
        reply_markup = get_checkbox_keyboard(user_id, "finish", OPTIONS_finish, "toggle_finish:", "finish_finish")
        title = "Закрытие смены"

    bot.send_message(
        chat_id,
        f"📋 **Чек-лист: {title}**\nСотрудник: {user_data[user_id]['name']}\nДата: {user_data[user_id]['date']}\nСмена: {user_data[user_id]['shift']}\n\nОтметьте выполненные пункты:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

def get_checkbox_keyboard(user_id, stage, options, toggle_prefix, finish_callback):
    selected = user_selections[stage].get(user_id, set())
    markup = InlineKeyboardMarkup()
    for item_id, label in options.items():
        status_emoji = "✅" if item_id in selected else "⬜️"
        
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
        bot.answer_callback_query(call.id)
        update_keyboard_safe(call, user_id, "open", OPTIONS_open, "toggle_open:", "finish_open")
    else:
        if REQUIRES_PHOTO_OPEN.get(item_id, False):
            bot.answer_callback_query(call.id)
            msg = bot.send_message(
                call.message.chat.id, 
                f"📸 Для пункта **«{OPTIONS_open[item_id]}»** необходимо отправить фото-подтверждение:", 
                parse_mode="Markdown"
            )
            bot.register_next_step_handler(msg, save_photo_and_toggle, "open", item_id, OPTIONS_open, "toggle_open:", "finish_open", call.message.message_id)
        else:
            user_selections["open"][user_id].add(item_id)
            bot.answer_callback_query(call.id)
            update_keyboard_safe(call, user_id, "open", OPTIONS_open, "toggle_open:", "finish_open")
# --- 2. ЭТАП: ОТЧЕТ В СЕРЕДИНЕ ДНЯ ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_work:"))
def process_checkbox_work(call):
    user_id = call.from_user.id
    item_id = call.data.split(":")[1]
    if user_id not in user_selections["work"]:
        user_selections["work"][user_id] = set()
    if item_id in user_selections["work"][user_id]:
        user_selections["work"][user_id].remove(item_id)
        bot.answer_callback_query(call.id)
        update_keyboard_safe(call, user_id, "work", OPTIONS_work, "toggle_work:", "finish_work")
    else:
        if REQUIRES_PHOTO_WORK.get(item_id, False):
            bot.answer_callback_query(call.id)
            msg = bot.send_message(
                call.message.chat.id, 
                f"📸 Для пункта **«{OPTIONS_work[item_id]}»** необходимо отправить фото-подтверждение:", 
                parse_mode="Markdown"
            )
            bot.register_next_step_handler(msg, save_photo_and_toggle, "work", item_id, OPTIONS_work, "toggle_work:", "finish_work", call.message.message_id)
        else:
            user_selections["work"][user_id].add(item_id)
            bot.answer_callback_query(call.id)
            update_keyboard_safe(call, user_id, "work", OPTIONS_work, "toggle_work:", "finish_work")

# --- 3. ЭТАП: ЗАКРЫТИЕ СМЕНЫ ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_finish:"))
def process_checkbox_finish(call):
    user_id = call.from_user.id
    item_id = call.data.split(":")[1]
    if user_id not in user_selections["finish"]:
        user_selections["finish"][user_id] = set()
        
    if item_id in user_selections["finish"][user_id]:
        if item_id == "meat_consumption":
            if user_id in user_inputs and "meat_consumption" in user_inputs[user_id]:
                del user_inputs[user_id]["meat_consumption"]
        user_selections["finish"][user_id].remove(item_id)
        bot.answer_callback_query(call.id)
        update_keyboard_safe(call, user_id, "finish", OPTIONS_finish, "toggle_finish:", "finish_finish")
    else:
        if item_id == "meat_consumption":
            bot.answer_callback_query(call.id)
            msg = bot.send_message(
                call.message.chat.id, 
                "🥩 Введите данные по **расходу мяса (план-факт)** текстом или числами:", 
                parse_mode="Markdown"
            )
            bot.register_next_step_handler(msg, save_meat_input, call.message.message_id)
        elif REQUIRES_PHOTO_FINISH.get(item_id, False):
            bot.answer_callback_query(call.id)
            msg = bot.send_message(
                call.message.chat.id, 
                f"📸 Для пункта **«{OPTIONS_finish[item_id]}»** необходимо отправить фото-подтверждение:", 
                parse_mode="Markdown"
            )
            bot.register_next_step_handler(msg, save_photo_and_toggle, "finish", item_id, OPTIONS_finish, "toggle_finish:", "finish_finish", call.message.message_id)
        else:
            user_selections["finish"][user_id].add(item_id)
            bot.answer_callback_query(call.id)
            update_keyboard_safe(call, user_id, "finish", OPTIONS_finish, "toggle_finish:", "finish_finish")

# --- ВВОД ТЕКСТА ДЛЯ РАСХОДА МЯСА ---
def save_meat_input(message, menu_message_id):
    if message.text == "/start":
        start(message)
        return
        
    user_id = message.from_user.id
    if not message.text:
        msg = bot.send_message(message.chat.id, "❌ **Ошибка!** Отправьте данные текстом или цифрами:")
        bot.register_next_step_handler(msg, save_meat_input, menu_message_id)
        return
        
    if user_id not in user_inputs:
        user_inputs[user_id] = {}
    user_inputs[user_id]["meat_consumption"] = message.text
    
    if user_id not in user_selections["finish"]:
        user_selections["finish"][user_id] = set()
    user_selections["finish"][user_id].add("meat_consumption")
    
    bot.send_message(message.chat.id, "✅ Данные по расходу мяса успешно записаны!")
    
    # Отправляем НОВОЕ меню чек-листа взамен сломанного edit_message
    launch_checklist_instantly(message.chat.id, user_id, "finish")

# --- ИСПРАВЛЕННЫЙ ОБРАБОТЧИК ФОТО-ПОДТВЕРЖДЕНИЙ ---
def save_photo_and_toggle(message, stage, item_id, options, toggle_prefix, finish_callback, menu_message_id):
    if message.text == "/start":
        start(message)
        return
        
    user_id = message.from_user.id
    if message.content_type != 'photo':
        msg = bot.send_message(message.chat.id, "❌ **Ошибка!** Нужно отправить именно **фотографию**. Попробуйте еще раз:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, save_photo_and_toggle, stage, item_id, options, toggle_prefix, finish_callback, menu_message_id)
        return
        
    photo_id = message.photo[-1].file_id
    stage_titles = {"open": "Открытие смены", "work": "Середина дня", "finish": "Закрытие смены"}
    info_text = get_user_info_text(user_id, stage_titles.get(stage, "Отчет"))
    caption_text = f"{info_text}\n\n📷 **Фото-подтверждение для пункта:**\n«{options[item_id]}»"
    
    try:
        bot.send_photo(chat_id=GROUP_ID, photo=photo_id, caption=caption_text, parse_mode="Markdown")
    except Exception as e:
        print(f"Ошибка отправки фото: {e}")
        
    if user_id not in user_selections[stage]:
        user_selections[stage][user_id] = set()
    user_selections[stage][user_id].add(item_id)
    
    bot.send_message(message.chat.id, f"✅ Фото для пункта «{options[item_id]}» принято!")
    
    # ИСПРАВЛЕНО: Вместо edit_message принудительно отправляем НОВОЕ меню с галочками
    launch_checklist_instantly(message.chat.id, user_id, stage)

# --- ОБРАБОТЧИКИ ЗАВЕРШЕНИЯ ОТЧЕТОВ ---
@bot.callback_query_handler(func=lambda call: call.data == "finish_open")
def finish_open_report(call):
    user_id = call.from_user.id
    selected = user_selections["open"].get(user_id, set())
    info_text = get_user_info_text(user_id, "Отчет по открытию смены")
    report_lines = [f"{'✅' if i in selected else '❌'} {l}" for i, l in OPTIONS_open.items()]
    full_report = f"{info_text}\n\n" + "\n".join(report_lines)
    try:
        bot.send_message(chat_id=GROUP_ID, text=full_report, parse_mode="Markdown")
        submitted_reports["open"].add(user_id)
        bot.answer_callback_query(call.id, text="🚀 Отчет по открытию смены отправлен!", show_alert=True)
        bot.send_message(call.message.chat.id, "✨ Отчет успешно отправлен руководству! Выберите следующий чек-лист для заполнения:", reply_markup=get_stages_keyboard(user_id))
        user_selections["open"][user_id] = set()
    except Exception as e:
        bot.answer_callback_query(call.id, text="⚠️ Ошибка отправки в группу.")

@bot.callback_query_handler(func=lambda call: call.data == "finish_work")
def finish_work_report(call):
    user_id = call.from_user.id
    selected = user_selections["work"].get(user_id, set())
    info_text = get_user_info_text(user_id, "Отчет за середину дня")
    report_lines = [f"{'✅' if i in selected else '❌'} {l}" for i, l in OPTIONS_work.items()]
    full_report = f"{info_text}\n\n" + "\n".join(report_lines)
    try:
        bot.send_message(chat_id=GROUP_ID, text=full_report, parse_mode="Markdown")
        submitted_reports["work"].add(user_id)
        bot.answer_callback_query(call.id, text="🚀 Дневной отчет успешно отправлен!", show_alert=True)
        bot.send_message(call.message.chat.id, "✨ Отчет успешно отправлен руководству! Выберите следующий чек-лист для заполнения:", reply_markup=get_stages_keyboard(user_id))
        user_selections["work"][user_id] = set()
    except Exception as e:
        bot.answer_callback_query(call.id, text="⚠️ Ошибка отправки.")

@bot.callback_query_handler(func=lambda call: call.data == "finish_finish")
def finish_final_report(call):
    user_id = call.from_user.id
    selected = user_selections["finish"].get(user_id, set())
    info_text = get_user_info_text(user_id, "Отчет по закрытию смены")
    report_lines = []
    for item_id, label in OPTIONS_finish.items():
        status = "✅" if item_id in selected else "❌"
        if item_id == "meat_consumption" and user_id in user_inputs and "meat_consumption" in user_inputs[user_id]:
            report_lines.append(f"{status} {label}: {user_inputs[user_id]['meat_consumption']}")
        else:
            report_lines.append(f"{status} {label}")
    full_report = f"{info_text}\n\n" + "\n".join(report_lines)
    try:
        bot.send_message(chat_id=GROUP_ID, text=full_report, parse_mode="Markdown")
        submitted_reports["finish"].add(user_id)
        bot.answer_callback_query(call.id, text="🚀 Отчет по закрытию отправлен!", show_alert=True)
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
        markup.add(KeyboardButton("✅ Открыть смену"))
        bot.send_message(
            call.message.chat.id,
            "✅ Вечерняя смена успешно закрыта. Все отчеты зарегистрированы!",
            reply_markup=markup
        )
        user_selections["finish"][user_id] = set()
    except Exception as e:
        bot.answer_callback_query(call.id, text="⚠️ Ошибка отправки.")

def update_keyboard_safe(call, user_id, stage, options, toggle_prefix, finish_callback):
    try:
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id, 
            reply_markup=get_checkbox_keyboard(user_id, stage, options, toggle_prefix, finish_callback)
        )
    except ApiTelegramException:
        pass

bot.polling(non_stop=True)
