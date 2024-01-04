"""Helpers for main code of a bot.

This includes formatting and common operations with data strctures.
And some text for user.
"""

import inspect
from typing import Final

from telegram import User
from telegram.helpers import escape_markdown

from tic_tac_toe.game import GameConductor, Mark, get_winner

GAME_RULES: Final = inspect.cleandoc(
    r"""
    *1\. You play 1 step at a time
    2\. X plays first
    3\. Player who joined multiplayer before an opponent plays first as X*"""
)


def wide_message(msg: str, escape: bool = False) -> str:
    """Add right padding with underscore so InlineKeyboard extends across full width"""
    max_width = 60
    add_symbols = max_width - len(msg)
    if add_symbols <= 0:
        return msg

    underscores = "_" * add_symbols
    if escape:
        underscores = escape_markdown(underscores, version=2)

    return msg + " " + underscores


def get_full_user_name(user: User) -> str:
    """Get name and username from telegram user and return as string"""
    user_name = user.first_name
    if user.last_name:
        user_name += " " + user.last_name
    if user.username:
        user_name += " @" + user.username
    return user_name


def render_message_at_game_end(
    gc: GameConductor,
    mark: Mark,
) -> str:
    """Get final message after the game to replace InlineKeyboard."""
    winner = get_winner(gc.grid) or "Дружба"
    if winner != "Дружба":
        if winner == mark:
            first_line = r"You won!"
            emoji = "\N{Smiling Face with Sunglasses}"
        else:
            first_line = "You lost..."
            emoji = "\N{Melting Face}"
    else:
        emoji = "\N{Face with Finger Covering Closed Lips}"
        first_line = "It's a draw!"

    rendered_grid = str(gc)
    text = (
        first_line
        + "\n"
        + rendered_grid
        + "\n"
        + emoji
        + f"\nWinner in this game: {winner}.\nThanks for playing"
    )
    return text
