import telebot
import json
import os
from telebot import types
from telebot.apihelper import ApiTelegramException

TOKEN = "8321820205:AAHLoqoby6gKL2z7ZGsvT-0d3kQOO-n1pwQ"
ADMIN_CHAT_ID = -1003184522262  # chat id адмін-чату або твій приватний чат (int)

bot = telebot.TeleBot(TOKEN)
forward_map = {}
BANNED_FILE = "banned.json"

def load_banned():
    if os.path.exists(BANNED_FILE):
        with open(BANNED_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_banned(banned_set):
    with open(BANNED_FILE, "w", encoding="utf-8") as f:
        json.dump(list(banned_set), f, ensure_ascii=False)

banned = load_banned()

def esc(s):
    if not s:
        return ""
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;"))

def user_display(user):
    username = f"@{user.username}" if user.username else "—"
    fullname = user.first_name or ""
    if user.last_name:
        fullname += f" " + user.last_name
    return esc(fullname.strip()), esc(username)

def make_header(user):
    fullname, username = user_display(user)
    return f"Повідомлення від {fullname} ({username}) (id: <code>{user.id}</code>)"

def make_buttons_for_user(user_id):
    kb = types.InlineKeyboardMarkup()
    if user_id in banned:
        kb.add(types.InlineKeyboardButton("Розбанити", callback_data=f"unban:{user_id}"))
    else:
        kb.add(types.InlineKeyboardButton("Забанити", callback_data=f"ban:{user_id}"))
    return kb

def ban_user_by_id(uid):
    if uid not in banned:
        banned.add(uid)
        save_banned(banned)
    try:
        bot.send_message(uid, "На жаль вас було забанено в боті")
    except ApiTelegramException:
        pass
    bot.send_message(ADMIN_CHAT_ID, f"Користувач {uid} забанений")

def unban_user_by_id(uid):
    if uid in banned:
        banned.remove(uid)
        save_banned(banned)
    try:
        bot.send_message(uid, "Вітаємо, ви отримали розбан")
    except ApiTelegramException:
        pass
    bot.send_message(ADMIN_CHAT_ID, f"Користувач {uid} розбанений")

@bot.message_handler(commands=["start"])
def handle_start(message):
    if message.chat.id in banned:
        try:
            bot.send_message(message.chat.id, "На жаль, ви забанені і не можете користуватись ботом.")
        except ApiTelegramException:
            pass
        return
    fullname, username = user_display(message.from_user)
    admin_text = f"Користувач {fullname} ({username}) (id: <code>{message.from_user.id}</code>) запустив бота"
    try:
        bot.send_message(ADMIN_CHAT_ID, admin_text, parse_mode="HTML")
    except ApiTelegramException:
        pass
    reply_text = "Вітаю в тех. підтримці INM, опишіть свою проблему і через певний час наші працівники з вами зв'яжуться"
    try:
        bot.send_message(message.chat.id, reply_text)
    except ApiTelegramException:
        pass

@bot.message_handler(func=lambda m: m.chat.id != ADMIN_CHAT_ID, content_types=["text", "photo", "document", "audio", "voice", "video", "sticker", "location", "contact", "video_note", "animation"])
def handle_user_message(message):
    if message.chat.id in banned:
        try:
            bot.send_message(message.chat.id, "На жаль, ви забанені і не можете писати в техпідтримку.")
        except ApiTelegramException:
            pass
        return
    header = make_header(message.from_user)
    sent = None
    try:
        if message.content_type == "text":
            combined = f"{header}\n\n{esc(message.text)}"
            sent = bot.send_message(ADMIN_CHAT_ID, combined, parse_mode="HTML", reply_markup=make_buttons_for_user(message.chat.id))
        elif message.content_type == "photo":
            file_id = message.photo[-1].file_id
            caption = header
            if message.caption:
                caption += "\n\n" + esc(message.caption)
            sent = bot.send_photo(ADMIN_CHAT_ID, file_id, caption=caption, parse_mode="HTML", reply_markup=make_buttons_for_user(message.chat.id))
        elif message.content_type == "document":
            file_id = message.document.file_id
            caption = header
            if message.caption:
                caption += "\n\n" + esc(message.caption)
            sent = bot.send_document(ADMIN_CHAT_ID, file_id, caption=caption, parse_mode="HTML", reply_markup=make_buttons_for_user(message.chat.id))
        elif message.content_type == "audio":
            file_id = message.audio.file_id
            caption = header
            sent = bot.send_audio(ADMIN_CHAT_ID, file_id, caption=caption, parse_mode="HTML", reply_markup=make_buttons_for_user(message.chat.id))
        elif message.content_type == "voice":
            file_id = message.voice.file_id
            # voice doesn't support long captions reliably; use send_voice
            sent = bot.send_voice(ADMIN_CHAT_ID, file_id, caption=header, parse_mode="HTML", reply_markup=make_buttons_for_user(message.chat.id))
        elif message.content_type == "video":
            file_id = message.video.file_id
            caption = header
            if message.caption:
                caption += "\n\n" + esc(message.caption)
            sent = bot.send_video(ADMIN_CHAT_ID, file_id, caption=caption, parse_mode="HTML", reply_markup=make_buttons_for_user(message.chat.id))
        elif message.content_type == "animation":
            file_id = message.animation.file_id
            caption = header
            if message.caption:
                caption += "\n\n" + esc(message.caption)
            sent = bot.send_animation(ADMIN_CHAT_ID, file_id, caption=caption, parse_mode="HTML", reply_markup=make_buttons_for_user(message.chat.id))
        elif message.content_type == "video_note":
            file_id = message.video_note.file_id
            # video_note doesn't take caption -> send header then video_note
            sent_header = bot.send_message(ADMIN_CHAT_ID, header, parse_mode="HTML", reply_markup=make_buttons_for_user(message.chat.id))
            sent = bot.send_video_note(ADMIN_CHAT_ID, file_id)
            if sent_header:
                forward_map[sent_header.message_id] = message.chat.id
        elif message.content_type == "sticker":
            file_id = message.sticker.file_id
            # stickers don't have caption
            sent_header = bot.send_message(ADMIN_CHAT_ID, header, parse_mode="HTML", reply_markup=make_buttons_for_user(message.chat.id))
            sent = bot.send_sticker(ADMIN_CHAT_ID, file_id)
            if sent_header:
                forward_map[sent_header.message_id] = message.chat.id
        elif message.content_type == "location":
            sent_header = bot.send_message(ADMIN_CHAT_ID, header, parse_mode="HTML", reply_markup=make_buttons_for_user(message.chat.id))
            sent = bot.send_location(ADMIN_CHAT_ID, message.location.latitude, message.location.longitude)
            if sent_header:
                forward_map[sent_header.message_id] = message.chat.id
        elif message.content_type == "contact":
            sent_header = bot.send_message(ADMIN_CHAT_ID, header, parse_mode="HTML", reply_markup=make_buttons_for_user(message.chat.id))
            sent = bot.send_contact(ADMIN_CHAT_ID, message.contact.phone_number, message.contact.first_name)
            if sent_header:
                forward_map[sent_header.message_id] = message.chat.id
    except ApiTelegramException:
        sent = None

    if sent:
        forward_map[sent.message_id] = message.chat.id

@bot.callback_query_handler(func=lambda call: call.message and call.message.chat.id == ADMIN_CHAT_ID)
def callback_handler(call):
    data = call.data or ""
    if ":" not in data:
        bot.answer_callback_query(call.id, "Невідома дія")
        return
    action, raw_id = data.split(":", 1)
    try:
        uid = int(raw_id)
    except ValueError:
        bot.answer_callback_query(call.id, "Невірний ID")
        return
    if action == "ban":
        ban_user_by_id(uid)
        bot.answer_callback_query(call.id, "Користувача забанено")
        # змінити кнопку на Розбанити
        try:
            bot.edit_message_reply_markup(ADMIN_CHAT_ID, call.message.message_id, reply_markup=make_buttons_for_user(uid))
        except ApiTelegramException:
            pass
    elif action == "unban":
        unban_user_by_id(uid)
        bot.answer_callback_query(call.id, "Користувача розбанено")
        try:
            bot.edit_message_reply_markup(ADMIN_CHAT_ID, call.message.message_id, reply_markup=make_buttons_for_user(uid))
        except ApiTelegramException:
            pass
    else:
        bot.answer_callback_query(call.id, "Невідома дія")

@bot.message_handler(func=lambda m: m.chat.id == ADMIN_CHAT_ID, content_types=["text", "photo", "document", "audio", "voice", "video", "sticker", "location", "contact", "video_note", "animation"])
def handle_admin_message(message):
    text = message.text or ""
    parts = text.split()

    if parts:
        cmd = parts[0].lower()
        if cmd in ("/ban", "/unban"):
            if len(parts) >= 2:
                try:
                    target_id = int(parts[1])
                    if cmd == "/ban":
                        ban_user_by_id(target_id)
                    else:
                        unban_user_by_id(target_id)
                    return
                except ValueError:
                    bot.send_message(ADMIN_CHAT_ID, "Невірний ID. Використай /ban <id> або reply + /ban.")
                    return
            if message.reply_to_message:
                replied_id = message.reply_to_message.message_id
                user_id = forward_map.get(replied_id)
                if user_id:
                    if cmd == "/ban":
                        ban_user_by_id(user_id)
                    else:
                        unban_user_by_id(user_id)
                else:
                    bot.send_message(ADMIN_CHAT_ID, "Не вдалось визначити користувача для цієї команди (мапа не має цього повідомлення).")
                return

    if message.reply_to_message:
        replied_id = message.reply_to_message.message_id
        user_id = forward_map.get(replied_id)
        if user_id:
            try:
                if message.content_type == "text":
                    bot.send_message(user_id, message.text)
                elif message.content_type == "photo":
                    file_id = message.photo[-1].file_id
                    bot.send_photo(user_id, file_id, caption=message.caption if message.caption else None)
                elif message.content_type == "document":
                    bot.send_document(user_id, message.document.file_id, caption=message.caption if message.caption else None)
                elif message.content_type == "audio":
                    bot.send_audio(user_id, message.audio.file_id, caption=message.caption if message.caption else None)
                elif message.content_type == "voice":
                    bot.send_voice(user_id, message.voice.file_id, caption=message.caption if message.caption else None)
                elif message.content_type == "video":
                    bot.send_video(user_id, message.video.file_id, caption=message.caption if message.caption else None)
                elif message.content_type == "sticker":
                    bot.send_sticker(user_id, message.sticker.file_id)
                elif message.content_type == "location":
                    bot.send_location(user_id, message.location.latitude, message.location.longitude)
                elif message.content_type == "contact":
                    bot.send_contact(user_id, message.contact.phone_number, message.contact.first_name)
                elif message.content_type == "video_note":
                    bot.send_video_note(user_id, message.video_note.file_id)
                elif message.content_type == "animation":
                    bot.send_animation(user_id, message.animation.file_id, caption=message.caption if message.caption else None)
                bot.send_message(ADMIN_CHAT_ID, "✅ Відправлено користувачу")
            except ApiTelegramException as e:
                bot.send_message(ADMIN_CHAT_ID, f"❌ Помилка при відправці: {e}")
            return

    bot.send_message(ADMIN_CHAT_ID, "Щоб відповісти користувачу — Reply на повідомлення; для бан/розбан — використай /ban або /unban як reply або /ban <id> /unban <id>")

if __name__ == "__main__":
    bot.infinity_polling()
