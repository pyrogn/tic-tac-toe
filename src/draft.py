#!/usr/bin/env python

"""
Bot for playing tic tac toe game with multiple CallbackQueryHandlers.
"""
import asyncio
from copy import deepcopy
import logging
from typing import Optional, Union
import random

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

PLAYERS_TURN, OPPONENTS_TURN = range(2)

FREE_SPACE = "."
CROSS = "X"
ZERO = "O"


DEFAULT_STATE = [[FREE_SPACE for _ in range(3)] for _ in range(3)]


def get_default_state():
    """Helper function to get default state of the game"""
    return deepcopy(DEFAULT_STATE)


def generate_keyboard(state: list[list[str]]) -> list[list[InlineKeyboardButton]]:
    """Generate tic tac toe keyboard 3x3 (telegram buttons)"""
    return [
        [InlineKeyboardButton(state[r][c], callback_data=f"{r}{c}") for r in range(3)]
        for c in range(3)
    ]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send message on `/start`."""
    context.user_data["keyboard_state"] = get_default_state()
    keyboard = generate_keyboard(context.user_data["keyboard_state"])
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.user_data["steps_played"] = 0
    await update.message.reply_text(
        f"X (your) turn! Please, put X to the free place", reply_markup=reply_markup
    )
    return PLAYERS_TURN


async def move_judge(
    step: tuple[int, int],
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    mark: str,
) -> int:
    """Checks if it is legal move, if so - registers it and returns new state
    Might throw an error
    And end the game
    Useful for user, opponent, bot. Is it??? Because opponent will be user itself.
    """
    grid = context.user_data["keyboard_state"]
    context.user_data["steps_played"] += 1
    r, c = step
    if not any([j == FREE_SPACE for i in grid for j in i]):
        return True, True
    if grid[r][c] == FREE_SPACE:
        is_valid = True
        is_end = False
        grid[r][c] = mark

    # if won(grid): # print something nice
    #     return True, True

    # if draw return not valid
    return is_valid, is_end


async def bot_turn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    grid = context.user_data["keyboard_state"]
    step = bot_response(grid)
    # write text that machine is thinking
    await asyncio.sleep(0.5)
    # write text that it is your turn with actual move
    is_valid, is_end = await move_judge(step, update, context, ZERO)
    # while not is_valid: make move? I think just throw an error
    if is_end:
        return await end(update, context)
    return PLAYERS_TURN
    # return PLAYERS_TURN


def bot_response(grid):
    available_moves = []
    for i in range(3):
        for j in range(3):
            if grid[i][j] == FREE_SPACE:
                available_moves.append((i, j))
    if not available_moves:
        raise ValueError("no available moves for a bot")
    selected_idx = random.randint(0, len(available_moves) - 1)
    return available_moves[selected_idx]


async def game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Main processing of the game"""
    # PLACE YOUR CODE HERE
    upd = update.callback_query.data
    r, c = int(upd[0]), int(upd[1])
    # print(r, c)
    context.user_data["keyboard_state"][r][c] = CROSS
    context.user_data["steps_played"] += 1
    if context.user_data["steps_played"] == 9:
        return OPPONENTS_TURN
    r, c = bot_response(context.user_data["keyboard_state"])
    context.user_data["keyboard_state"][r][c] = ZERO
    context.user_data["steps_played"] += 1

    if context.user_data["steps_played"] == 9:
        return OPPONENTS_TURN
    keyboard = generate_keyboard(context.user_data["keyboard_state"])
    reply_markup = InlineKeyboardMarkup(keyboard)
    query = update.callback_query

    if won(context.user_data["keyboard_state"]):
        # print("yay finish")
        # print(context.user_data["keyboard_state"])
        text = "YOU WON"
        # TODO: add here game map and next instructions using emoji
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text=text)

        return ConversationHandler.END
    await context.bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text="Someones turn",
        reply_markup=reply_markup,
    )

    return PLAYERS_TURN


# def won(fields: list[str]) -> bool:
#     """Check if crosses or zeros have won the game"""
#     # PLACE YOUR CODE HERE
def won(fields):
    if all([i == CROSS for i in fields[0]]):
        return True
    return False


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns `ConversationHandler.END`, which tells the
    ConversationHandler that the conversation is over.
    """
    # reset state to default so you can play again with /start
    # context.user_data["keyboard_state"] = get_default_state()

    # make it work, remove keyboard if someone is won
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Bye")
    return ConversationHandler.END


async def first_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send message on `/start`."""
    await context.bot.send_message(
        context._chat_id,
        text='If you want to play, just type "/start" command',
    )


async def inplay_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await context.bot.send_message(
        context._chat_id,
        text="You have an active game, if dont want to continue, type some command."
        "Or start to play again",
    )


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
                # HandlerOnFinish(end)
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
