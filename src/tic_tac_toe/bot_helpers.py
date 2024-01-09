"""Helpers for main code of a bot.

This includes formatting and common operations with data structures.
And some text for user.
"""

import inspect
from typing import Final

from telegram import User
from telegram.helpers import escape_markdown

from tic_tac_toe.game import Mark, TTTBoard, get_opposite_mark

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


def parse_keyboard_move(data: str) -> tuple[int, int]:
    if len(data) != 2:
        raise ValueError(
            f"length of data from inlinekeyboard should be 2, but it is {len(data)}"
        )
    elif not isinstance(data, str):
        raise ValueError(f"Data has type {type(data)}, but str is required")
    r, c = int(data[0]), int(data[1])
    for dim in (r, c):
        if not 0 <= dim <= 2:
            raise ValueError(f"Some dimension in {r, c} not in range [0, 2]")
    return r, c


def render_message_at_game_end(
    game_board: TTTBoard,
    mark: Mark,
    username_mark: dict[Mark, str],
) -> str:
    """Get final message with results after the game to replace InlineKeyboard.

    Parameters:
        gc: GameConductor
        mark: mark of the player
        username_mark: dictionary with mark and user name to congratulate personally!
    """
    winner = game_board.get_winner()
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
        winner = (
            "Дружба \N{Smiling Cat Face with Heart-Shaped Eyes}"  # это кот Леопольд
        )
        emoji = "\N{Face with Finger Covering Closed Lips}"
        first_line = "It's a draw!"

    rendered_grid = str(game_board)
    text = (
        first_line
        + "\n"
        + rendered_grid
        + "\n"
        + emoji
        + f"\nWinner in this game: {winner}.\nThanks for playing"
    )
    return text
