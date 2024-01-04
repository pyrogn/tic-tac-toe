"""Helpers for main code of a bot.

This includes formatting and common operations with data strctures.
And some text
"""

from telegram import User
from telegram.ext import (
    ContextTypes,
)

from tic_tac_toe.multiplayer import ChatId

GAME_RULES = r"""*1\. You play 1 step at a time
2\. X plays first
3\. Player who joined multiplayer before an opponent plays first as X*"""


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
