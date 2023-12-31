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
    get_opposite_mark,
    render_grid,
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
from tic_tac_toe.multiplayer import HandleForPlayer, Multiplayer


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

CONTINUE_GAME, END_STATE = range(2)


DEFAULT_STATE = [[FREE_SPACE for _ in range(3)] for _ in range(3)]


multiplayer = Multiplayer()


def wide_message(msg):
    return f"{msg:_<50}"


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

    user = update.message.from_user
    context.user_data["game"] = f"{user.username}-another player"
    logger.info(
        f"Player {user.first_name or ''} {user.last_name or ''} "
        f"(@{user.username}) has joined"
    )

    context.user_data["keyboard_state"] = get_default_state()
    keyboard = generate_keyboard(context.user_data["keyboard_state"])
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.user_data["GameConductor"] = GameConductor()
    handle = multiplayer.register_player()
    my_mark = CROSS if handle.n == 0 else ZERO
    context.user_data["handle_multiplayer"] = handle
    context.user_data["handle1"] = context.user_data["GameConductor"].get_handler(my_mark)
    context.user_data["handle2"] = context.user_data["GameConductor"].get_handler(get_opposite_mark(my_mark))

    if handle.n == 1:
        text = "Waiting for opponent"
    else:
        text= 'It is your turn, make a move'
    await update.message.reply_text(
        wide_message(text),
        reply_markup=reply_markup,
    )

    logger.info(f"game {context.user_data["game"]} has begun, keyboard rendered")
    if handle.n == 1:
        logger.info(f"{context.user_data["game"]}: waiting for an opponent")
        opponents_move = await handle.pop_value()
        context.user_data["handle2"](opponents_move)
        context.user_data["keyboard_state"] = context.user_data["GameConductor"].grid
        keyboard = generate_keyboard(context.user_data["keyboard_state"])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.edit_text(
            wide_message(f"Your turn! Please, put {my_mark} to the free place"),
            reply_markup=reply_markup,
        )
        logger.info(f"{context.user_data["game"]}: opponent made the first move")
    else:
        logger.info(f"game {context.user_data["game"]}: should make the first move")
    return CONTINUE_GAME


async def game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Main processing of the game"""
    # PLACE YOUR CODE HERE

    game_name = context.user_data['game']
    logger.info(f"{game_name}: entered game coroutine")

    query = update.callback_query
    assert query, "query is None, not good..."
    coords_keyboard = query.data
    assert coords_keyboard

    grid = context.user_data["keyboard_state"]
    move = int(coords_keyboard[0]), int(coords_keyboard[1])
    logger.info(f"player chose move {move}")

    if not is_move_legal(grid, move):
        logger.info(f"move {move} from player is illegal")
        # edit text to warn user or show pop up
        return CONTINUE_GAME

    handle = context.user_data["handle1"]
    if not handle.is_my_turn:
        logger.info(f"Player attempted to make a move not in his time")
        return CONTINUE_GAME

    handle_multiplayer = context.user_data["handle_multiplayer"]

    handle(move)
    handle_multiplayer.push_value(move)
    logger.info(f"Player made move {move}")

    gc: GameConductor = context.user_data["GameConductor"]
    keyboard = generate_keyboard(gc.grid)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        reply_markup=reply_markup, text=wide_message("Opponent's turn")
    )
    logger.info(f"Player made move {move}, message rendered")

    if gc.is_game_over:
        return await end(update, context)

    # wait for reponse
    opponents_move = await handle_multiplayer.pop_value()
    context.user_data["handle2"](opponents_move)
    gc: GameConductor = context.user_data["GameConductor"]
    keyboard = generate_keyboard(gc.grid)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        reply_markup=reply_markup, text=wide_message("Your turn")
    )
    logger.info(f"Opponent made move {move}, message rendered")

    if gc.is_game_over:
        return await end(update, context)

    # return await bot_turn(update, context)
    return CONTINUE_GAME


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns `ConversationHandler.END`, which tells the
    ConversationHandler that the conversation is over.
    """
    # reset state to default so you can play again with /start
    # context.user_data["keyboard_state"] = get_default_state()

    # make it work, remove keyboard if someone is won
    game_name = context.user_data['game']
    logger.info(f"{game_name} has ended")
    query = update.callback_query
    assert query, "Query is None. Message was deleted?"

    gc: GameConductor = context.user_data["GameConductor"]
    winner = gc.result or "Draw"
    rendered_grid = render_grid(gc.grid)
    text = rendered_grid + f"\nWinner in this game: {winner}.\nThanks for playing"
    await query.answer()
    await query.edit_message_text(text=text)
    logger.info(f"{game_name} has ended, message rendered. winner: {winner}")
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
    return CONTINUE_GAME


# class HandlerOpponent(BaseHandler):
#     # https://docs.python-telegram-bot.org/en/v20.7/telegram.ext.basehandler.html
#     def check_update(self, update: object) -> bool | object | None:
#         return True


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
            CONTINUE_GAME: [
                CallbackQueryHandler(game, pattern="^" + f"{r}{c}" + "$")
                for r in range(3)
                for c in range(3)
            ],
            # add state with options: want to play again?
            # Aren't used for now, maybe will be with multiplayer
            END_STATE: [
            #     HandlerOpponent(bot_turn)
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
