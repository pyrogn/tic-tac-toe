"""
Telegram bot for playing tic tac toe game.
There are implementations of singleplayer and multiplayer
"""
import asyncio
import logging
import os
import random
from typing import Collection
from warnings import filterwarnings

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)
from telegram.warnings import PTBUserWarning

from tic_tac_toe.bot_helpers import (
    GAME_RULES,
    get_full_user_name,
    parse_keyboard_move,
    render_message_at_game_end,
    wide_message,
)
from tic_tac_toe.exceptions import (
    InvalidMoveError,
    NotEnoughPlayersError,
)
from tic_tac_toe.game import (
    CROSS,
    ZERO,
    GameConductor,
    Grid,
    find_optimal_move,
    get_opposite_mark,
)
from tic_tac_toe.multiplayer import ChatId, MessageId, Multiplayer

# get token using BotFather
TOKEN = os.getenv("TIC_TAC_TOE_TOKEN_TG")  # I put it in zsh config
assert TOKEN, "Token not found in env vars (TIC_TAC_TOE_TOKEN_TG)"

(
    CHOICE_GAME_TYPE,
    CONTINUE_GAME_SINGLEPLAYER,
    CONTINUE_GAME_MULTIPLAYER,
    PLAY_AGAIN,
    MARK_CHOICE,
) = range(5)
START_AGAIN_CALLBACK, GOODBYE_CALLBACK = range(91, 93)

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

# Initialize multiplayer class
multiplayer = Multiplayer()


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send game rules on /rules handle. *Bold style*."""
    query = update.message
    await query.reply_text(text=GAME_RULES, parse_mode="MarkdownV2")


def generate_keyboard(state: Grid) -> list[list[InlineKeyboardButton]]:
    """Generate tic tac toe keyboard 3x3 (telegram buttons)"""
    return [
        [InlineKeyboardButton(state[r][c], callback_data=f"{r}{c}") for c in range(3)]
        for r in range(3)
    ]


async def start_multichoice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send message on `/start`.

    User can choose singleplayer or multiplayer game mode
    """

    keyboard = [
        [
            InlineKeyboardButton("Singleplayer", callback_data="1"),
            InlineKeyboardButton("Multiplayer", callback_data="2"),
        ]
    ]
    if update.message:  # if update is message (/start), then send a new message
        make_message = update.message.reply_text
    elif update.callback_query:  # if trigger originates from callback, edit message
        await update.callback_query.answer()
        make_message = update.callback_query.message.edit_text
    else:
        raise RuntimeError("Something wrong with Updater")

    message = await make_message(
        text=wide_message("Press what type of game you want to play"),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    # clean up old game in singleplayer
    # going to be False after the end of game
    if "active_singleplayer_game" in context.user_data:
        bot_message = context.user_data["bot_message"]
        await context.bot.edit_message_text(
            message_id=bot_message.message_id,
            chat_id=bot_message.chat_id,
            text="You abandoned your old game with bot 🤖",
        )
        del context.user_data["active_singleplayer_game"]

    # clean up old game in multiplayer
    # first check if player is in the queue
    if multiplayer.is_this_player_in_queue(message.chat_id):
        player_last_game_info = multiplayer.get_player_from_queue(message.chat_id)
        multiplayer.remove_player_from_queue(message.chat_id)
        await context.bot.edit_message_text(
            text="You left the queue for multiplayer",
            chat_id=message.chat_id,
            message_id=player_last_game_info["message_id"],
        )
    # and if this player has an active game
    elif message.chat_id in multiplayer.games:
        game = multiplayer.get_game(message.chat_id)
        # and report to user that current game is dropped
        multiplayer.remove_game(message.chat_id)
        await context.bot.edit_message_text(
            text=f"Your old game with {game.opponent.user_name} has been abandoned.",
            chat_id=game.myself.chat_id,
            message_id=game.myself.message_id,
        )
        # update message for opponent
        await context.bot.edit_message_text(
            chat_id=game.opponent.chat_id,
            message_id=game.opponent.message_id,
            text=(
                f"Your game was abandoned by: {game.myself.user_name}."
                "Type /start to start over"
            ),
        )

    # keep message to edit it later on in place
    context.user_data["bot_message"] = message  # for singleplayer

    if "user_name" not in context.user_data:
        context.user_data["user_name"] = get_full_user_name(update.message.from_user)
    return CHOICE_GAME_TYPE


async def start_singleplayer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start singleplayer game and ask user about mark choice using InlineKeyboard."""

    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton(CROSS, callback_data="1"),
            InlineKeyboardButton(ZERO, callback_data="2"),
            InlineKeyboardButton("🤪", callback_data="3"),  # random
        ]
    ]
    await query.edit_message_text(
        wide_message("Which mark do you choose?"),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    user = context.user_data["user_name"]
    context.user_data["game"] = f"{user}-bot"
    context.user_data["active_singleplayer_game"] = True
    # logger.info(f"Player {user} want to start singleplayer game")

    return MARK_CHOICE


async def mark_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process mark choice from user in singleplayer game and show InlineKeyboard"""
    query = update.callback_query
    await query.answer()

    mark_choice = query.data
    if mark_choice == "1":  # сомнительно, но окэй, better to use Enum maybe
        mark = CROSS
    elif mark_choice == "2":
        mark = ZERO
    elif mark_choice == "3":
        mark = random.choice([CROSS, ZERO])
    else:  # unexpected error
        raise ValueError(f"Mark isn't identified: {mark_choice}") from None

    gc = GameConductor()
    context.user_data["GameConductor"] = gc
    handle = gc.get_handle(mark)
    context.user_data["handle_player"] = handle
    context.user_data["handle_bot"] = gc.get_handle(what_is_left=True)

    keyboard = generate_keyboard(gc.game_board.grid)
    reply_markup = InlineKeyboardMarkup(keyboard)

    my_mark = handle.mark
    if context.user_data["handle_player"].is_my_turn():
        text = rf"*It is your turn*\. Your mark: {my_mark}\."
    else:
        text = "Waiting for a bot to make a move"
    await query.edit_message_text(
        text=wide_message(text, escape=True),
        parse_mode="MarkdownV2",
        reply_markup=reply_markup,
    )
    if not handle.is_my_turn():
        await bot_turn(update, context)

    logger_message = (
        f"singleplayer game {context.user_data['game']} has begun, keyboard rendered"
    )
    logger.info(logger_message)
    return CONTINUE_GAME_SINGLEPLAYER


async def game_singleplayer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Main processing of the game"""
    query = update.callback_query

    move = parse_keyboard_move(query.data)
    # CONFUSED: как работать с логами? Надо все писать или менять уровень для
    # обычных действий? или не писать рутинные действия?
    # logger.info(f"player chose move {move}")

    handle = context.user_data["handle_player"]

    try:
        handle(move)
    except InvalidMoveError as f:
        await query.answer(text=f"Illegal move: {str(f)}", show_alert=True)
        # logger.info("player tried to make illegal move")
        return CONTINUE_GAME_SINGLEPLAYER

    gc: GameConductor = context.user_data["GameConductor"]
    keyboard = generate_keyboard(gc.game_board.grid)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        reply_markup=reply_markup, text=wide_message("Opponent's turn")
    )
    # logger.info(f"Player made move {move}, message rendered")
    await query.answer()

    if gc.is_game_over:
        del context.user_data["active_singleplayer_game"]
        return await end_singleplayer(update, context)
    return await bot_turn(update, context)


async def bot_turn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Bot makes a move in a singleplayer game."""
    query = update.callback_query
    gc = context.user_data["GameConductor"]
    grid = gc.game_board
    handle = context.user_data["handle_bot"]
    # move = random_available_move(grid) # 10 IQ bot
    move = find_optimal_move(grid, handle.mark)  # 210 IQ bot
    # logger.info(f"bot chose move {move}")

    assert grid.is_move_legal(move), f"Bot move {move} is illegal"

    handle(move)
    # logger.info(f"bot made move {move}")

    # thinking simulation
    # first moves are slow by computations
    if gc.game_board.n_empty_cells() < 8:
        sec_sleep = random.randint(2, 5) / 10
        await asyncio.sleep(sec_sleep)

    keyboard = generate_keyboard(gc.game_board.grid)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        reply_markup=reply_markup,
        text=wide_message(r"*Your turn*", escape=True),
        parse_mode="MarkdownV2",
    )
    # logger.info(f"bot made move {move}, message rendered")
    gc: GameConductor = context.user_data["GameConductor"]
    if gc.is_game_over:
        del context.user_data["active_singleplayer_game"]
        return await end_singleplayer(update, context)
    return CONTINUE_GAME_SINGLEPLAYER


async def end_singleplayer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns `ConversationHandler.END`, which tells the
    ConversationHandler that the conversation is over.
    """

    game_name = context.user_data["game"]
    # logger.info(f"{game_name} has ended")
    query = update.callback_query

    gc: GameConductor = context.user_data["GameConductor"]
    handle = context.user_data["handle_player"]
    winner = gc.game_board.get_winner()
    mark_username_dict = {handle.mark: "Myself", get_opposite_mark(handle.mark): "Bot"}
    text = render_message_at_game_end(gc.game_board, handle.mark, mark_username_dict)
    await query.answer()
    await query.edit_message_text(text=text)

    del context.user_data["bot_message"]  # since we don't touch this message any more

    if winner:
        winner = f"{mark_username_dict[winner]} ({winner})"
    else:
        winner = "Дружба"

    logger_message = (
        f"singleplayer game {game_name} has ended, message rendered. winner: {winner}"
    )
    logger.info(logger_message)

    await wanna_play_again(update, context)

    return PLAY_AGAIN


async def start_multiplayer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start multiplayer game by registering a player and if there were a player
    in the queue, register a pair of players and start a game.
    """

    query = update.callback_query
    await query.answer()
    user_name = context.user_data["user_name"]

    # logger.info(f"Player {user_name} has joined")
    chat_id = query.message.chat_id
    game = None

    if multiplayer.is_player_waiting:  # == I will be his opponent
        text = "Configuring the game for you, Sir"
    else:  # I am the first to join
        text = "Waiting for anyone to join"

    message_id = context.user_data["bot_message"].message_id
    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=wide_message(text),
    )

    # we check in /start command that player doesn't play in multiplayer right now
    # so every exception must be a developer's error
    multiplayer.register_player(
        chat_id=chat_id, message_id=message_id, user_name=user_name
    )

    try:
        multiplayer.register_pair()
        game = multiplayer.get_game(chat_id)
        game_name = f"{game.opponent.user_name} vs {game.myself.user_name}"
        logger_message = f"Multiplayer game {game_name} is registered"
        logger.info(logger_message)

        keyboard = generate_keyboard(game.game_conductor.game_board.grid)
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.edit_message_text(
            text=wide_message(
                rf"*Make a move*\. Your opponent {game.myself.user_name} has joined\. "
                rf"Your mark: {game.opponent.mark}\.",
                escape=True,
            ),
            chat_id=game.opponent.chat_id,
            message_id=game.opponent.message_id,
            reply_markup=reply_markup,
            parse_mode="MarkdownV2",
        )
        await context.bot.edit_message_text(
            text=wide_message(
                f"Wait for an opponent's move ({game.opponent.mark}). "
                f"Your opponent {game.opponent.user_name}. "
                f"Your mark: {game.myself.mark}."
            ),
            chat_id=game.myself.chat_id,
            message_id=game.myself.message_id,
            reply_markup=reply_markup,
        )
        # logger_message += "Keyboards are rendered for players"
        # logger.info(logger_message)

    except NotEnoughPlayersError:
        logger_message = f"{user_name} is waiting for opponent to join"
        logger.info(logger_message)
        return CONTINUE_GAME_MULTIPLAYER

    return CONTINUE_GAME_MULTIPLAYER


async def game_multiplayer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Main processing of the multiplayer game"""

    query = update.callback_query

    move = parse_keyboard_move(query.data)
    # logger.info(f"player chose move {move}")
    chat_id = query.message.chat_id

    game = multiplayer.get_game(chat_id)
    # game_name = f"{game.myself.user_name} {game.opponent.user_name}"

    gc = game.game_conductor
    handle = game.myself.handle

    try:
        handle(move)
    except InvalidMoveError as f:
        await query.answer(text=f"Illegal move: {str(f)}", show_alert=True)
        # logger.info(f"{game_name}: player tried to make illegal move")
        return CONTINUE_GAME_MULTIPLAYER
    await query.answer()

    # logger.info(f"Player made move {move}")

    keyboard = generate_keyboard(gc.game_board.grid)
    reply_markup = InlineKeyboardMarkup(keyboard)

    if gc.is_game_over:
        # make last edit to message with game result for two players
        await end_multiplayer(context, game.myself.chat_id, game.myself.message_id)
        await end_multiplayer(context, game.opponent.chat_id, game.opponent.message_id)
        multiplayer.remove_game(chat_id)

        # logger_message = game_name + ": Game is ended, and removed"
        # logger.info(logger_message)

        # send a new message for two players
        await wanna_play_again(
            update,
            context,
            chats_multiplayer=(game.myself.chat_id, game.opponent.chat_id),
        )
        return CONTINUE_GAME_MULTIPLAYER

    await query.edit_message_text(
        text=wide_message(f"Waiting for opponent. Opponent: {game.opponent.user_name}"),
        reply_markup=reply_markup,
    )

    await context.bot.edit_message_text(
        chat_id=game.opponent.chat_id,
        message_id=game.opponent.message_id,
        text=wide_message(
            rf"*Your turn \({game.opponent.mark}\)*\. "
            rf"Opponent: {game.myself.user_name}",
            escape=True,
        ),
        parse_mode="MarkdownV2",
        reply_markup=reply_markup,
    )
    # logger.info(f"Player made move {move}, messages rendered")

    return CONTINUE_GAME_MULTIPLAYER


async def end_multiplayer(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: ChatId,
    message_id: MessageId,
) -> None:
    """Edit last message of 2 chats with grid as string and result of game."""
    game = multiplayer.get_game(chat_id)
    gc = game.game_conductor
    game_name = f"{game.myself.user_name} vs {game.opponent.user_name}"

    mark_username_dict = {
        game.myself.mark: game.myself.user_name,
        game.opponent.mark: game.opponent.user_name,
    }
    text = render_message_at_game_end(
        gc.game_board, game.myself.mark, mark_username_dict
    )
    await context.bot.edit_message_text(
        text=text, chat_id=chat_id, message_id=message_id
    )

    winner = gc.game_board.get_winner() or "Дружба"
    logger_message = (
        f"multiplayer game {game_name} has ended, message rendered. winner: {winner}"
    )
    logger.info(logger_message)


async def wanna_play_again(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    chats_multiplayer: Collection[ChatId] | None = None,
) -> int | None:
    """Present to user InlineKeyboard with choice to start a new game.

    Arguments:
        chats_multiplayers: if None, then make a reply in current conversation
            if not None, then send messages to these chat ids
    """
    keyboard = [
        [
            InlineKeyboardButton(
                "Yeah! I'm feeling lucky!!", callback_data=str(START_AGAIN_CALLBACK)
            ),
            InlineKeyboardButton(
                "Nah... I am a big grumpy...", callback_data=str(GOODBYE_CALLBACK)
            ),
        ]
    ]
    text = "Do you want to play again?"
    if not chats_multiplayer:  # singleplayer
        query = update.callback_query
        message = await query.message.reply_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        context.user_data["bot_message"] = message

        return PLAY_AGAIN

    # multiplayer
    for chat_id in chats_multiplayer:
        message = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def goodbye_sir(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Print farewell and end conversation with user until new /start command."""
    query = update.callback_query
    await query.answer()

    message = query.message
    await context.bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=message.message_id,
        text="It was nice playing with you. Type /start if you want to play again",
    )
    del context.user_data["bot_message"]  # release memory (or it is done automatically)
    return ConversationHandler.END


def main() -> None:
    """Run the bot"""
    application = Application.builder().token(TOKEN).build()

    # block is False so we don't get blocked while sending a message
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start_multichoice, block=False),
            CommandHandler("rules", rules, block=False),
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
            MARK_CHOICE: [
                CallbackQueryHandler(
                    mark_choice, pattern="^" + str(i) + "$", block=False
                )
                for i in (1, 2, 3)
            ],
            CONTINUE_GAME_SINGLEPLAYER: [
                CallbackQueryHandler(
                    game_singleplayer, pattern="^" + f"{r}{c}" + "$", block=False
                )
                for r in range(3)
                for c in range(3)
            ],
            CONTINUE_GAME_MULTIPLAYER: [
                *[
                    CallbackQueryHandler(
                        game_multiplayer, pattern="^" + f"{r}{c}" + "$", block=False
                    )
                    for r in range(3)
                    for c in range(3)
                ],
                CallbackQueryHandler(  # options in case of game over
                    start_multichoice,
                    pattern="^" + str(START_AGAIN_CALLBACK) + "$",
                    block=False,
                ),
                CallbackQueryHandler(
                    goodbye_sir, pattern="^" + str(GOODBYE_CALLBACK) + "$", block=False
                ),
            ],
            PLAY_AGAIN: [
                CallbackQueryHandler(
                    start_multichoice,
                    pattern="^" + str(START_AGAIN_CALLBACK) + "$",
                    block=False,
                ),
                CallbackQueryHandler(
                    goodbye_sir, pattern="^" + str(GOODBYE_CALLBACK) + "$", block=False
                ),
            ],
        },
        fallbacks=[
            # you might start over at any moment, dropping a current game
            CommandHandler("start", start_multichoice, block=False),
            CommandHandler("rules", rules, block=False),
            # But no option of emergency stop! - you shall play all day and night
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
