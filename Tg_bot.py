#!/usr/bin/env python3

"""
Telegram Utility Bot
Features:
- Get user ID
- Get chat ID
- Get chat info
- Whois lookup
- Welcome users
- Set welcome message
- Broadcast (admin only)
- Pin messages (admin only)
"""

import json
import logging
import os
from typing import List

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Chat,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler,
)

# ------------------ CONFIG ------------------
BOT_TOKEN = "8558266388:AAE5satgzoNQwxrcOZCMqhOedgCYIIsn11Q"
ADMIN_IDS: List[int] = [8202939953]   # Your admin ID

DATA_FILE = "data.json"
# ------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def load_data():
    if not os.path.exists(DATA_FILE):
        return {"welcome": {}, "groups": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


DATA = load_data()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ------------------ COMMANDS ------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("Show My ID", callback_data="my_id")],
        [InlineKeyboardButton("Show Chat ID", callback_data="chat_id")],
    ]
    await update.message.reply_text(
        f"Hello {user.first_name}! 👋\nUse /help to see commands.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - welcome menu\n"
        "/id - show your ID\n"
        "/chatinfo - show chat details\n"
        "/whois - info about a user\n"
        "/setwelcome <text> - set welcome msg (admin)\n"
        "/broadcast <text> - send to all groups (admin)\n"
        "/pin - pin replied message (admin)\n"
    )


async def button_handler(update, context):
    q = update.callback_query
    await q.answer()
    chat = q.message.chat
    user = q.from_user

    if q.data == "my_id":
        await q.edit_message_text(
            f"Your ID: `{user.id}`\nUsername: @{user.username or '—'}",
            parse_mode="Markdown"
        )
    elif q.data == "chat_id":
        await q.edit_message_text(
            f"Chat ID: `{chat.id}`\nChat type: {chat.type}",
            parse_mode="Markdown"
        )


async def id_cmd(update, context):
    user = update.effective_user
    chat = update.effective_chat
    await update.message.reply_text(
        f"Your ID: `{user.id}`\nChat ID: `{chat.id}`",
        parse_mode="Markdown"
    )


async def chatinfo_cmd(update, context):
    chat = update.effective_chat
    text = (
        f"Chat ID: `{chat.id}`\n"
        f"Chat Type: {chat.type}\n"
        f"Title: {chat.title or chat.full_name}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def whois_cmd(update, context):
    msg = update.message
    if msg.reply_to_message:
        user = msg.reply_to_message.from_user
    else:
        return await msg.reply_text("Reply to a user or use an ID/username.")

    info = (
        f"Name: {user.full_name}\n"
        f"User ID: `{user.id}`\n"
        f"Username: @{user.username or '—'}"
    )
    await msg.reply_text(info, parse_mode="Markdown")


async def setwelcome_cmd(update, context):
    user = update.effective_user
    chat = update.effective_chat

    if not is_admin(user.id):
        return await update.message.reply_text("Admin only!")

    text = " ".join(context.args)
    if not text:
        return await update.message.reply_text("Usage: /setwelcome <text>")

    DATA["welcome"][str(chat.id)] = text
    save_data(DATA)
    await update.message.reply_text("Welcome message updated!")


async def welcome(update, context):
    chat = update.effective_chat
    msg = update.message
    new_users = msg.new_chat_members
    template = DATA["welcome"].get(str(chat.id), "Welcome {name}!")

    for user in new_users:
        txt = template.replace("{name}", user.first_name)
        await msg.reply_text(txt)


async def broadcast_cmd(update, context):
    user = update.effective_user
    if not is_admin(user.id):
        return await update.message.reply_text("Admin only!")

    text = " ".join(context.args)
    if not text:
        return await update.message.reply_text("Usage: /broadcast <text>")

    groups = DATA.get("groups", [])
    success = 0
    for gid in groups:
        try:
            await context.bot.send_message(gid, text)
            success += 1
        except:
            pass

    await update.message.reply_text(f"Broadcast sent to {success} chats.")


async def track_groups(update, context):
    chat = update.effective_chat
    if chat.type in ("group", "supergroup"):
        groups = set(DATA.get("groups", []))
        if chat.id not in groups:
            groups.add(chat.id)
            DATA["groups"] = list(groups)
            save_data(DATA)


async def pin_cmd(update, context):
    user = update.effective_user
    msg = update.message

    if not is_admin(user.id):
        return await msg.reply_text("Admin only!")

    if not msg.reply_to_message:
        return await msg.reply_text("Reply to a message to pin it!")

    await context.bot.pin_chat_message(msg.chat.id, msg.reply_to_message.message_id)
    await msg.reply_text("Pinned!")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("id", id_cmd))
    app.add_handler(CommandHandler("chatinfo", chatinfo_cmd))
    app.add_handler(CommandHandler("whois", whois_cmd))
    app.add_handler(CommandHandler("setwelcome", setwelcome_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CommandHandler("pin", pin_cmd))

    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS, track_groups))

    app.run_polling()


if __name__ == "__main__":
    main()
