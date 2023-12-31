from typing import Literal, NamedTuple
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


class Player(NamedTuple):
    mark: str


# Add logging??? It should be necessary for debug
class Multiplayer:
    """Connects two players and gives handle with shared resources"""

    def __init__(self) -> None:
        # self.players_queue = list()  # should be actual queue
        # self.games = list()  # it could be memory leak
        self.is_player_waiting = False
        self.waiting_handle = None

    def register_player(self) -> "HandleForPlayer":
        if not self.waiting_handle:
            handle1, handle2 = self.init_handles()
            self.waiting_handle = handle2
            return handle1
        handle2 = self.waiting_handle
        self.waiting_handle = None
        return handle2

    def init_handles(self):
        queue_p1 = list()
        queue_p2 = list()
        handle1 = HandleForPlayer(queue_p1, queue_p2)
        handle2 = HandleForPlayer(queue_p2, queue_p1)
        handle1.n = 0
        handle2.n = 1
        return handle1, handle2


class HandleForPlayer:
    """Pass information between two players

    Rules:
        In progress...
        Does not have knowledge about a game, only passing moves
    """

    # Add handle to make sure you don't pop value just pushed before

    def __init__(self, players_queue: list, opponents_queue: list):
        self.players_queue = players_queue
        self.opponents_queue = opponents_queue
        self.n: int

    def push_value(self, value):
        self.opponents_queue.append(value)
        assert len(self.opponents_queue) == 1

    async def pop_value(self):  # can it stop at ctrl+c?
        while True:  # can I make a Task?
            if not self.players_queue:
                await asyncio.sleep(0.1)
            else:
                return self.players_queue.pop()
