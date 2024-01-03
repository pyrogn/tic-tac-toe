"""Helpers for main code of a bot.

This includes formatting and common operations with data strctures"""

from telegram import User
from telegram.ext import (
    ContextTypes,
)

from tic_tac_toe.multiplayer import ChatId


def wide_message(msg):
    msg += " "
    return f"{msg:_<50}"


def get_full_user_name(user: User):
    user_name = user.first_name
    if user.last_name:
        user_name += " " + user.last_name
    if user.username:  # who doesn't have it?
        user_name += " @" + user.username
    return user_name


def get_message(context: ContextTypes.DEFAULT_TYPE, chat_id: ChatId):
    try:
        return context.bot_data["bot_message"][chat_id]
    except KeyError:
        return context.user_data["bot_message"][chat_id]


def edit_message():
    ...


def two_players_edit():
    ...
