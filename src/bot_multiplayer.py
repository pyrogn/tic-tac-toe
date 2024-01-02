#!/usr/bin/env python

"""
Bot for playing tic tac toe game with multiple CallbackQueryHandlers.
"""
import asyncio
from copy import deepcopy
import logging
from typing import Optional, Union
import random
from exceptions import (
    CurrentGameError,
    InvalidMove,
    NotEnoughPlayersError,
    WaitRoomError,
)
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
from tic_tac_toe.multiplayer import ChatId, Multiplayer, Game


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


multiplayer = Multiplayer()
games: list[Game] = []
games_fastkey: dict[ChatId, Game] = {}


def wide_message(msg):
    return f"{msg:_<50}"


def generate_keyboard(state: Grid) -> list[list[InlineKeyboardButton]]:
    """Generate tic tac toe keyboard 3x3 (telegram buttons)"""
    return [
        [InlineKeyboardButton(state[r][c], callback_data=f"{r}{c}") for c in range(3)]
        for r in range(3)
    ]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send message on `/start`."""
    # likely unsafe with race conditions

    # assert context.user_data
    assert update.message

    user = update.message.from_user
    user_name = user.first_name
    if user.last_name:
        user_name += " " + user.last_name
    user_name += " @" + user.username

    logger.info(f"Player {user_name} has joined")
    chat_id = update.message.chat_id
    game = None

    keyboard_state = get_default_state()
    keyboard = generate_keyboard(keyboard_state)
    reply_markup = InlineKeyboardMarkup(keyboard)

    if multiplayer.is_player_waiting:  # == I will be his opponent
        text = "Configuring the game for you, Sir"
    else:
        text = "Waiting for anyone to join"

    message = await update.message.reply_text(
        wide_message(text),
    )
    message_id = message.message_id

    try:  # maybe check with if statement to get rid of duplication?
        multiplayer.register_player(
            chat_id=chat_id, message_id=message_id, user_name=user_name
        )
    except CurrentGameError:
        game = multiplayer.get_game(chat_id)
        # and report to user that current game is dropped
        multiplayer.remove_game(chat_id)
        multiplayer.register_player(
            chat_id=chat_id, message_id=message_id, user_name=user_name
        )
        await context.bot.edit_message_text(
            text=f"Your old game with {game.opponent.user_name} has been abandoned. Creating a new game",
            chat_id=game.myself.chat_id,
            message_id=game.myself.message_id,
        )
        await context.bot.edit_message_text(
            chat_id=game.opponent.chat_id,
            message_id=game.opponent.message_id,
            text=f"Your game was abandoned by: {game.myself.user_name}",
        )

    except WaitRoomError:
        # alert that you are already in the queue
        await context.bot.edit_message_text(
            text="You are already in the queue, don't spam",
            chat_id=message.chat_id,
            message_id=message.message_id,
        )
        # await update.callback_query.answer(
        #     text="You are already in the queue", show_alert=True
        # )
        return CONTINUE_GAME

    try:
        multiplayer.register_pair()
        game = multiplayer.get_game(chat_id)
        logger.info(
            f"Game is registered between {game.opponent.user_name} and {game.myself.user_name}"
        )

        await context.bot.edit_message_text(
            text=wide_message(
                f"Your opponent {game.myself.user_name} has joined\nYour mark: {game.opponent.mark}. Make a move"
            ),
            chat_id=game.opponent.chat_id,
            message_id=game.opponent.message_id,
            reply_markup=reply_markup,
        )
        await context.bot.edit_message_text(
            text=wide_message(
                f"Your opponent {game.opponent.user_name}\bYour mark: {game.myself.mark}. Wait for a move"
            ),
            chat_id=game.myself.chat_id,
            message_id=game.myself.message_id,
            reply_markup=reply_markup,
        )

    except NotEnoughPlayersError:
        logger.info(f"Waiting for opponent")
        return CONTINUE_GAME

    logger.info(
        f"game {game.myself.user_name} vs {game.opponent.user_name} has begun, keyboard rendered"
    )

    return CONTINUE_GAME


# maybe to use context.bot_data
# https://github.com/python-telegram-bot/python-telegram-bot/issues/1804
async def game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Main processing of the game"""
    # PLACE YOUR CODE HERE

    # game_name = context.user_data.get("game", "Unknown game WTF?")

    query = update.callback_query
    assert query, "query is None, not good..."
    coords_keyboard = query.data
    assert coords_keyboard

    move = int(coords_keyboard[0]), int(coords_keyboard[1])
    logger.info(f"player chose move {move}")
    chat_id = query.message.chat_id

    game = multiplayer.get_game(chat_id)
    game_name = f"{game.myself.user_name} {game.opponent.user_name}"
    logger.info(f"{game_name}: entered game coroutine")

    # cries out for better design (very much)
    gc = game.game_conductor
    handle = game.myself.handle

    if not handle.is_my_turn:
        logger.info(f"Player attempted to make a move not in his time")
        return CONTINUE_GAME

    try:
        handle(move)
    except InvalidMove as f:
        await query.answer(
            text=f"Illegal move: {str(f)}", show_alert=True
        )  # add actual text
        logger.info(f"{game_name}: player tried to make illegal move")
        return CONTINUE_GAME

    logger.info(f"Player made move {move}")

    keyboard = generate_keyboard(gc.grid)
    reply_markup = InlineKeyboardMarkup(keyboard)

    if gc.is_game_over:  # maybe edit somehow else, not looking nice
        await end(update, context, game.myself.chat_id, game.myself.message_id, gc)
        await end(update, context, game.opponent.chat_id, game.opponent.message_id, gc)
        multiplayer.remove_game(chat_id)
        n_games = len(multiplayer.games)  # should be zero during testing
        logger.info(f"Game is ended, and removed. How many games left: {n_games}")

    await query.edit_message_text(
        reply_markup=reply_markup,
        text=wide_message(f"Waiting for opponent\nOpponent: {game.opponent.user_name}"),
    )

    await context.bot.edit_message_text(
        chat_id=game.opponent.chat_id,
        message_id=game.opponent.message_id,
        text=wide_message(
            f"Your turn ({game.opponent.mark})\nOpponent: {game.myself.user_name}"
        ),
        reply_markup=reply_markup,
    )
    logger.info(f"Player made move {move}, messages rendered")

    return CONTINUE_GAME


async def end(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    chat_id,
    message_id,
    gc: GameConductor,
) -> int:
    """Returns `ConversationHandler.END`, which tells the
    ConversationHandler that the conversation is over.
    """
    # reset state to default so you can play again with /start
    # context.user_data["keyboard_state"] = get_default_state()

    # make it work, remove keyboard if someone is won
    game = multiplayer.get_game(chat_id)
    game_name = f"{game.myself.user_name} vs {game.opponent.user_name}"
    logger.info(f"{game_name} has ended")
    query = update.callback_query
    assert query, "Query is None. Message was deleted?"

    winner = gc.result or "Draw"
    emoji = "\N{Face with Finger Covering Closed Lips}"
    if winner != "Draw":
        if winner == game.myself.mark:
            winner_player = game.myself.user_name
            emoji = "\N{Smiling Face with Sunglasses}"
        else:
            winner_player = game.opponent.user_name
            emoji = "\N{Melting Face}"
        winner = f"{winner_player}({winner})"
    rendered_grid = render_grid(gc.grid)
    text = (
        rendered_grid
        + "\n"
        + emoji
        + f"\nWinner in this game: ({winner}).\nThanks for playing"
    )
    await query.answer()
    await context.bot.edit_message_text(
        text=text, chat_id=chat_id, message_id=message_id
    )
    logger.info(f"{game_name} has ended, message rendered. winner: {winner}")
    return ConversationHandler.END


async def first_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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


def main() -> None:
    # TODO: make block=False on handlers because we don't want wait for telegram response much
    """Run the bot"""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()

    # Setup conversation handler with the states CONTINUE_GAME and FINISH_GAME
    # Use the pattern parameter to pass CallbackQueries with specific
    # data pattern to the corresponding handlers.
    # ^ means "start of line/string"
    # $ means "end of line/string"
    # So ^ABC$ will only allow 'ABC'
    # conv_handler = ConversationHandler(
    #     entry_points=[
    #         CommandHandler("start", start),
    #         MessageHandler(filters.ALL, first_message),
    #     ],
    #     states={
    #         CONTINUE_GAME: [
    #             CallbackQueryHandler(game, pattern="^" + f"{r}{c}" + "$")
    #             for r in range(3)
    #             for c in range(3)
    #         ],
    #         # add state with options: want to play again?
    #         # Aren't used for now, maybe will be with multiplayer
    #         END_STATE: [
    #             #     HandlerOpponent(bot_turn)
    #             # CallbackQueryHandler(end, pattern="^" + f"{r}{c}" + "$")
    #             # for r in range(3)
    #             # for c in range(3)
    #         ],
    #     },
    #     fallbacks=[
    #         CommandHandler("start", start),
    #         MessageHandler(filters.ALL, inplay_message),
    #     ],
    #     per_message=False,
    # )

    application.add_handler(CommandHandler("start", start))
    [
        application.add_handler(
            CallbackQueryHandler(game, pattern="^" + f"{r}{c}" + "$")
        )
        for r in range(3)
        for c in range(3)
    ]
    # Add ConversationHandler to application that will be used for handling updates
    # application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
