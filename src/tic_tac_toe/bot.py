"""
Bot for playing tic tac toe game with multiple CallbackQueryHandlers.
"""
import asyncio
from copy import deepcopy
import logging
from typing import Optional, Union
import random
from tic_tac_toe.exceptions import (
    CurrentGameError,
    InvalidMove,
    NotEnoughPlayersError,
    WaitRoomError,
)
from tic_tac_toe.game import (
    DEFAULT_STATE,
    find_optimal_move,
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

from tic_tac_toe.notifications import get_full_user_name, get_message, wide_message

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

(
    CHOICE_GAME_TYPE,
    CONTINUE_GAME_SINGLEPLAYER,
    CONTINUE_GAME_MULTIPLAYER,
    PLAY_AGAIN,
) = range(4)


multiplayer = Multiplayer()
games: list[Game] = []
games_fastkey: dict[ChatId, Game] = {}


def generate_keyboard(state: Grid) -> list[list[InlineKeyboardButton]]:
    """Generate tic tac toe keyboard 3x3 (telegram buttons)"""
    return [
        [InlineKeyboardButton(state[r][c], callback_data=f"{r}{c}") for c in range(3)]
        for r in range(3)
    ]


async def start_multichoice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if "bot_message" not in context.bot_data:
        context.bot_data["bot_message"] = {}
    keyboard = [
        [
            InlineKeyboardButton("Singleplayer", callback_data="1"),
            InlineKeyboardButton("Multiplayer", callback_data="2"),
        ]
    ]
    if update.message:  # if message (/start), then send a new message
        make_message = update.message.reply_text
    elif update.callback_query:  # if trigger originates from callback, edit message
        make_message = update.callback_query.message.edit_text
    else:
        raise ValueError("Something wrong with Updater")
    message = await make_message(
        text="Press what type of game you want to play",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    if multiplayer.is_this_player_in_waitlist(message.chat_id):
        player_last_game_info = multiplayer.get_player_from_queue(message.chat_id)
        multiplayer.remove_player_from_queue(message.chat_id)
        # bot_message_id = get_message(context, message.chat_id)
        await context.bot.edit_message_text(
            text="You left the queue for multiplayer",
            chat_id=message.chat_id,
            message_id=player_last_game_info["message_id"],
        )
    elif message.chat_id in multiplayer.games:
        game = multiplayer.get_game(message.chat_id)
        # and report to user that current game is dropped
        multiplayer.remove_game(message.chat_id)
        await context.bot.edit_message_text(
            text=f"Your old game with {game.opponent.user_name} has been abandoned.",
            chat_id=game.myself.chat_id,
            message_id=game.myself.message_id,
        )
        await context.bot.edit_message_text(
            chat_id=game.opponent.chat_id,
            message_id=game.opponent.message_id,
            text=f"Your game was abandoned by: {game.myself.user_name}",
        )

    context.user_data["bot_message"] = message  # keep message to edit it later on
    context.bot_data["bot_message"][message.chat_id] = message
    return CHOICE_GAME_TYPE


async def mark_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TODO: make use of it
    keyboard = [
        [
            InlineKeyboardButton(CROSS, callback_data="191"),
            InlineKeyboardButton(ZERO, callback_data="192"),
        ]
    ]
    query = update.callback_query
    await query.edit_message_text(
        "Which mark do you choose? Your choice might be changed under circumstances. So you'll be good anyway.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def wanna_play_again(
    update: Update, context: ContextTypes.DEFAULT_TYPE, chats_multiplayer=None
) -> int:
    keyboard = [
        [
            InlineKeyboardButton("Yeah! I'm feeling lucky!!", callback_data="91"),
            InlineKeyboardButton("Nah... I am a big grumpy...", callback_data="92"),
        ]
    ]
    text = "Do you want to play again?"
    if not chats_multiplayer:
        query = update.callback_query
        message = await query.message.reply_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        context.user_data["bot_message"] = message

        context.bot_data["bot_message"][message.chat_id] = message
        return PLAY_AGAIN
    else:
        for chat_id in chats_multiplayer:
            message = await context.bot.send_message(
                chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard)
            )
            context.bot_data["bot_message"][chat_id] = message


async def start_singleplayer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send message on `/start`."""

    query = update.callback_query
    user = query.from_user
    context.user_data["game"] = f"{user.username}-bot"
    logger.info(
        f"Player {user.first_name or ''} {user.last_name or ''} "
        f"(@{user.username}) has joined"
    )

    context.user_data["keyboard_state"] = get_default_state()
    keyboard = generate_keyboard(context.user_data["keyboard_state"])
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.user_data["GameConductor"] = GameConductor()
    context.user_data["handle1"] = context.user_data["GameConductor"].get_handler(CROSS)
    context.user_data["handle2"] = context.user_data["GameConductor"].get_handler(ZERO)

    await query.edit_message_text(
        text=wide_message("X (your) turn! Please, put X to the free place"),
        reply_markup=reply_markup,
    )

    logger.info(f"game {context.user_data['game']} has begun, keyboard rendered")
    return CONTINUE_GAME_SINGLEPLAYER


async def game_singleplayer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Main processing of the game"""
    query = update.callback_query
    assert query, "query is None, not good..."
    coords_keyboard = query.data
    assert coords_keyboard

    # grid = context.user_data["keyboard_state"]
    move = int(coords_keyboard[0]), int(coords_keyboard[1])
    logger.info(f"player chose move {move}")

    handle = context.user_data["handle1"]

    try:
        handle(move)
    except InvalidMove as f:
        await query.answer(text=f"Illegal move: {str(f)}", show_alert=True)
        logger.info(f"player tried to make illegal move")
        return CONTINUE_GAME_SINGLEPLAYER

    gc: GameConductor = context.user_data["GameConductor"]
    keyboard = generate_keyboard(gc.grid)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        reply_markup=reply_markup, text=wide_message("Opponent's turn")
    )
    logger.info(f"Player made move {move}, message rendered")

    if gc.is_game_over:
        return await end_singleplayer(update, context)
    return await bot_turn(update, context)


async def bot_turn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    gc = context.user_data["GameConductor"]
    grid = gc.grid
    # move = random_available_move(grid)
    handle = context.user_data["handle2"]
    move = find_optimal_move(grid, handle.mark)
    logger.info(f"bot chose move {move}")

    assert is_move_legal(grid, move), "Bot move is illegal"

    handle(move)
    logger.info(f"bot made move {move}")

    # thinking simulation
    # first moves are slow by computations
    if n_empty_cells(gc.grid) < 8:
        sec_sleep = random.randint(1, 5) / 10
        await asyncio.sleep(sec_sleep)

    keyboard = generate_keyboard(gc.grid)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        reply_markup=reply_markup, text=wide_message("Player's turn")
    )
    logger.info(f"bot made move {move}, message rendered")
    gc: GameConductor = context.user_data["GameConductor"]
    if gc.is_game_over:
        return await end_singleplayer(update, context)
    return CONTINUE_GAME_SINGLEPLAYER


async def start_multiplayer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send message on `/start`."""
    # likely unsafe with race conditions

    query = update.callback_query
    assert query.message, "How come no message?"
    user = query.from_user
    assert user, "User is unknown to this universe"
    user_name = get_full_user_name(user)

    logger.info(f"Player {user_name} has joined")
    chat_id = query.message.chat_id
    game = None

    keyboard_state = get_default_state()
    keyboard = generate_keyboard(keyboard_state)
    reply_markup = InlineKeyboardMarkup(keyboard)

    if multiplayer.is_player_waiting:  # == I will be his opponent
        text = "Configuring the game for you, Sir"
    else:
        text = "Waiting for anyone to join"

    # message = await update.message.reply_text(
    #     wide_message(text),
    # )

    message = context.user_data["bot_message"]
    message_id = context.user_data["bot_message"].message_id
    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=wide_message(text),
    )

    # we check in /start command that player doesn't play in multiplayer right now
    multiplayer.register_player(
        chat_id=chat_id, message_id=message_id, user_name=user_name
    )

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
        return CONTINUE_GAME_MULTIPLAYER

    logger.info(
        f"game {game.myself.user_name} vs {game.opponent.user_name} has begun, keyboard rendered"
    )

    return CONTINUE_GAME_MULTIPLAYER


async def game_multiplayer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Main processing of the game"""

    query = update.callback_query
    assert query, "query is None, not good..."
    coords_keyboard = query.data
    assert coords_keyboard, "No data from user"
    assert query.message, "Message is None. Why?"

    move = int(coords_keyboard[0]), int(coords_keyboard[1])
    logger.info(f"player chose move {move}")
    chat_id = query.message.chat_id

    game = multiplayer.get_game(chat_id)
    game_name = f"{game.myself.user_name} {game.opponent.user_name}"
    logger.info(f"{game_name}: entered game coroutine")

    gc = game.game_conductor
    handle = game.myself.handle

    if not handle.is_my_turn:
        logger.info(f"Player attempted to make a move not in his time")
        return CONTINUE_GAME_MULTIPLAYER

    try:
        handle(move)
    except InvalidMove as f:
        await query.answer(
            text=f"Illegal move: {str(f)}", show_alert=True
        )  # add actual text
        logger.info(f"{game_name}: player tried to make illegal move")
        return CONTINUE_GAME_MULTIPLAYER

    logger.info(f"Player made move {move}")

    keyboard = generate_keyboard(gc.grid)
    reply_markup = InlineKeyboardMarkup(keyboard)

    if gc.is_game_over:  # maybe edit somehow else, not looking nice
        await end_multiplayer(
            update, context, game.myself.chat_id, game.myself.message_id, gc
        )
        await end_multiplayer(
            update, context, game.opponent.chat_id, game.opponent.message_id, gc
        )
        multiplayer.remove_game(chat_id)
        n_games = len(multiplayer.games)  # should be zero during testing
        logger.info(f"Game is ended, and removed. How many games left: {n_games}")

        await wanna_play_again(
            update,
            context,
            chats_multiplayer=(game.myself.chat_id, game.opponent.chat_id),
        )
        return CONTINUE_GAME_MULTIPLAYER

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

    return CONTINUE_GAME_MULTIPLAYER


async def end_singleplayer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns `ConversationHandler.END`, which tells the
    ConversationHandler that the conversation is over.
    """
    # reset state to default so you can play again with /start
    # context.user_data["keyboard_state"] = get_default_state()

    # make it work, remove keyboard if someone is won
    game_name = context.user_data["game"]
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

    await wanna_play_again(update, context)
    return PLAY_AGAIN


async def goodbuy_sir(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    message = context.bot_data["bot_message"][query.message.chat_id]
    # message = get_message(context, chat_id=query.message.chat_id)
    await context.bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=message.message_id,
        text="It was nice playing with you",
    )
    return ConversationHandler.END


async def end_multiplayer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    chat_id,
    message_id,
    gc: GameConductor,
) -> None:
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
    # return ConversationHandler.END


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
            CommandHandler("start", start_multichoice, block=False),
        ],
        states={
            CHOICE_GAME_TYPE: [
                CallbackQueryHandler(
                    start_singleplayer, pattern="^" + str(1) + "$", block=False
                ),
                CallbackQueryHandler(
                    start_multiplayer, pattern="^" + str(2) + "$", block=False
                ),
            ],
            CONTINUE_GAME_MULTIPLAYER: [
                *[
                    CallbackQueryHandler(
                        game_multiplayer, pattern="^" + f"{r}{c}" + "$", block=False
                    )
                    for r in range(3)
                    for c in range(3)
                ],
                CallbackQueryHandler(
                    start_multichoice, pattern="^" + str(91) + "$", block=False
                ),
                CallbackQueryHandler(
                    goodbuy_sir, pattern="^" + str(92) + "$", block=False
                ),
            ],
            CONTINUE_GAME_SINGLEPLAYER: [
                CallbackQueryHandler(
                    game_singleplayer, pattern="^" + f"{r}{c}" + "$", block=False
                )
                for r in range(3)
                for c in range(3)
            ],
            PLAY_AGAIN: [
                CallbackQueryHandler(
                    start_multichoice, pattern="^" + str(91) + "$", block=False
                ),
                CallbackQueryHandler(
                    goodbuy_sir, pattern="^" + str(92) + "$", block=False
                ),
            ],
        },
        fallbacks=[
            # you might start over at any moment
            CommandHandler("start", start_multichoice, block=False),
        ],
        per_message=False,
        block=False,
    )

    # Add ConversationHandler to application that will be used for handling updates
    application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
