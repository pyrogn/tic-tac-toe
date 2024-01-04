"""Helpers for main code of a bot.

This includes formatting and common operations with data structures.
And some text for user.
"""

import inspect
from typing import Final

from telegram import User
from telegram.helpers import escape_markdown

from tic_tac_toe.game import GameConductor, Mark, get_opposite_mark, get_winner

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
    username_mark: dict[Mark, str],
) -> str:
    """Get final message with results after the game to replace InlineKeyboard.

    Parameters:
        gc: GameConductor
        mark: mark of the player
        username_mark: dictionary with mark and user name to congratulate personally!
    """
    winner = get_winner(gc.grid)
    if winner:
        if winner == mark:
            first_line = "You won!"
            emoji = "\N{Smiling Face with Sunglasses}"
            winner_username = username_mark[mark]
        else:
            first_line = "You lost..."
            emoji = "\N{Melting Face}"
            winner_username = username_mark[get_opposite_mark(mark)]
        winner = f"{winner_username} ({winner})"  # username + mark
    else:
        winner = "Дружба 😻"
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
