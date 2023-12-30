#!/usr/bin/env python

"""
Bot for playing tic tac toe game with multiple CallbackQueryHandlers.
"""
import asyncio
from copy import deepcopy
import logging
from typing import Optional, Union
import random
from tic_tac_toe.game import (
    DEFAULT_STATE,
    get_default_state,
    Cell,
    Grid,
    Move,
    FREE_SPACE,
    CROSS,
    ZERO,
    select_cell,
    n_empty_cells,
    is_game_over,
    make_move,
    get_winner,
    set_cell,
    random_available_move,
    is_move_legal,
    GameConductor,
)


from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    BaseHandler,
    ConversationHandler,
    filters,
)
import os
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning

filterwarnings(
    action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# get token using BotFather
TOKEN = os.getenv("TIC_TAC_TOE_TOKEN_TG")  # I put it in zsh config
assert TOKEN, "Token not found in env vars"

PLAYERS_TURN, OPPONENTS_TURN = range(2)

FREE_SPACE = "."
CROSS = "X"
ZERO = "O"


DEFAULT_STATE = [[FREE_SPACE for _ in range(3)] for _ in range(3)]


def generate_keyboard(state: Grid) -> list[list[InlineKeyboardButton]]:
    """Generate tic tac toe keyboard 3x3 (telegram buttons)"""
    return [
        [InlineKeyboardButton(state[r][c], callback_data=f"{r}{c}") for r in range(3)]
        for c in range(3)
    ]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send message on `/start`."""
    # assert context.user_data
    assert update.message

    context.user_data["keyboard_state"] = get_default_state()
    keyboard = generate_keyboard(context.user_data["keyboard_state"])
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.user_data["GameConductor"] = GameConductor()
    context.user_data["handle1"] = context.user_data["GameConductor"].get_handler(CROSS)
    context.user_data["handle2"] = context.user_data["GameConductor"].get_handler(ZERO)
    await update.message.reply_text(
        f"X (your) turn! Please, put X to the free place", reply_markup=reply_markup
    )
    return PLAYERS_TURN


async def bot_turn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    grid = context.user_data["keyboard_state"]
    gc = context.user_data["GameConductor"]
    move = random_available_move(grid)

    assert is_move_legal(grid, move), "Bot move is illegal"

    handle = context.user_data["handle2"]
    handle(move)
    # print(move)

    # write text that machine is thinking
    await asyncio.sleep(0.5)
    # write text that it is your turn with actual move
    # while not is_valid: make move? I think just throw an error
    keyboard = generate_keyboard(gc.grid)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(reply_markup=reply_markup, text="Player's turn")
    gc: GameConductor = context.user_data["GameConductor"]
    if gc.is_game_over:
        return await end(update, context)
    return PLAYERS_TURN


async def game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Main processing of the game"""
    # PLACE YOUR CODE HERE
    query = update.callback_query
    assert query, "query is None, not good..."
    # coords_keyboard = await query.answer()
    coords_keyboard = query.data
    assert coords_keyboard

    grid = context.user_data["keyboard_state"]
    move = int(coords_keyboard[0]), int(coords_keyboard[1])

    if not is_move_legal(grid, move):
        return PLAYERS_TURN

    handle = context.user_data["handle1"]
    handle(move)

    gc: GameConductor = context.user_data["GameConductor"]
    keyboard = generate_keyboard(gc.grid)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(reply_markup=reply_markup, text="Opponent's turn")

    if gc.is_game_over:
        return await end(update, context)
    return await bot_turn(update, context)
    return OPPONENTS_TURN


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns `ConversationHandler.END`, which tells the
    ConversationHandler that the conversation is over.
    """
    # reset state to default so you can play again with /start
    # context.user_data["keyboard_state"] = get_default_state()

    # make it work, remove keyboard if someone is won
    query = update.callback_query
    assert query, "Query is None. Message was deleted?"

    gc: GameConductor = context.user_data["GameConductor"]
    winner = gc.result or "Draw"
    text = f"Winner in this game: {winner}. Thanks for playing"
    await query.answer()
    await query.edit_message_text(text=text)
    return ConversationHandler.END


async def first_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send message on `/start`."""
    await context.bot.send_message(
        context._chat_id,
        text='If you want to play, just type "/start" command',
    )


async def inplay_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await context.bot.send_message(
        context._chat_id,  # something else?
        text="You have an active game, if dont want to continue, type some command."
        "Or start to play again",
    )
    return PLAYERS_TURN


class HandlerOpponent(BaseHandler):
    # https://docs.python-telegram-bot.org/en/v20.7/telegram.ext.basehandler.html
    def check_update(self, update: object) -> bool | object | None:
        return True


def main() -> None:
    """Run the bot"""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()

    # Setup conversation handler with the states CONTINUE_GAME and FINISH_GAME
    # Use the pattern parameter to pass CallbackQueries with specific
    # data pattern to the corresponding handlers.
    # ^ means "start of line/string"
    # $ means "end of line/string"
    # So ^ABC$ will only allow 'ABC'
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.ALL, first_message),
        ],
        states={
            PLAYERS_TURN: [
                CallbackQueryHandler(game, pattern="^" + f"{r}{c}" + "$")
                for r in range(3)
                for c in range(3)
            ],
            # Aren't used for now, maybe will be with multiplayer
            OPPONENTS_TURN: [
                HandlerOpponent(bot_turn)
                # CallbackQueryHandler(end, pattern="^" + f"{r}{c}" + "$")
                # for r in range(3)
                # for c in range(3)
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            MessageHandler(filters.ALL, inplay_message),
        ],
        per_message=False,
    )

    # Add ConversationHandler to application that will be used for handling updates
    application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
