from collections import deque
from queue import Queue
from typing import Any, Literal, NamedTuple
from tic_tac_toe.game import (
    DEFAULT_STATE,
    get_default_state,
    Cell,
    Grid,
    Move,
    FREE_SPACE,
    CROSS,
    ZERO,
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
import asyncio


MessageId = int
ChatId = int


class Player(NamedTuple):  # use when you enable mark preferences
    mark: str


class ChatPlayerInfo(NamedTuple):
    handle: Any  # maybe replace with Protocol (nice idea)
    message_id: MessageId


def get_player_info(chat_info_dict, chat_id):
    # handle = game_data.chat_dict[chat_id].handle
    # my_message_id = game_data.chat_dict[chat_id].message_id
    other_chat_id = int(list(set(chat_info_dict.keys()) - {chat_id})[0])
    # opponents_message_id = game_data.chat_dict[other_chat_id].message_id
    return (
        (*chat_info_dict[chat_id], chat_id),
        (*chat_info_dict[other_chat_id], other_chat_id),
    )


class Game(NamedTuple):
    """1 is X, 2 is O I guess (bad design)"""

    chat_dict: dict[ChatId, ChatPlayerInfo]
    game_conductor: GameConductor


# Add logging??? It should be necessary for debug
class Multiplayer:
    """Connects two players and gives handle with shared resources"""

    def __init__(self) -> None:
        self.players_queue = Queue()  # should be actual queue
        self.waiting_handle = None

    @property
    def is_player_waiting(self):
        if self.players_queue.qsize() > 2:
            raise ValueError("Too many players waiting game, tinder somebody please")
        return self.players_queue != 0

    def register_player(self, chat_id: ChatId, message_id: MessageId):
        self.players_queue.put((chat_id, message_id))

    def get_pair(self) -> Game:
        if (self.players_queue.qsize()) < 2:
            raise ValueError("Not enough players")
        player1 = self.players_queue.get_nowait()
        player2 = self.players_queue.get_nowait()
        gc = GameConductor()
        # change when need to use user mark preference
        handle1 = gc.get_handler(CROSS, what_is_left=True)
        handle2 = gc.get_handler(CROSS, what_is_left=True)
        return Game(
            {
                player1[0]: ChatPlayerInfo(handle1, player1[1]),
                player2[0]: ChatPlayerInfo(handle2, player2[1]),
            },
            gc,
        )
