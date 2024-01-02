from collections import deque
from queue import Queue
from typing import Any, Literal, NamedTuple
from exceptions import CurrentGameError, NotEnoughPlayersError, WaitRoomError

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


class ChatPlayerInfo(NamedTuple):
    chat_id: ChatId
    message_id: MessageId
    handle: Any  # maybe replace with Protocol (nice idea)
    mark: str
    user_name: str


class Game(NamedTuple):
    chat_dict: dict[ChatId, ChatPlayerInfo]
    game_conductor: GameConductor


class GamePersonalized(NamedTuple):
    myself: ChatPlayerInfo
    opponent: ChatPlayerInfo
    game_conductor: GameConductor


class Multiplayer:
    """Connects two players and other magic"""

    def __init__(self) -> None:
        self.players_queue: Queue[dict] = Queue()
        self.waitroom = []
        self.games: dict[ChatId, Game] = {}

    @property
    def is_player_waiting(self):
        if self.players_queue.qsize() >= 2:
            raise ValueError("Too many players waiting game, tinder somebody please")
        return self.players_queue.qsize() != 0

    def register_player(self, **kwargs):
        # necessary keys to connect players
        if not all([key in kwargs for key in ("chat_id", "message_id")]):
            raise ValueError(
                "chat_id and message_id are necessary keys for registration"
            )
        if kwargs["chat_id"] in self.games:
            raise CurrentGameError

        if kwargs["chat_id"] in self.waitroom:  # how to make it simpler?
            raise WaitRoomError
        self.waitroom.append(kwargs["chat_id"])

        self.players_queue.put(kwargs)

    def register_pair(self) -> None:
        if (self.players_queue.qsize()) < 2:
            raise NotEnoughPlayersError("Not enough players")
        player1_dict = self.players_queue.get_nowait()
        player2_dict = self.players_queue.get_nowait()
        [self.waitroom.pop(0) for _ in range(2)]

        gc = GameConductor()
        # TODO: change when need to use user mark preference
        handle1 = gc.get_handler(CROSS, what_is_left=True)
        handle2 = gc.get_handler(CROSS, what_is_left=True)
        game = Game(
            {
                player1_dict["chat_id"]: ChatPlayerInfo(handle=handle1, **player1_dict, mark=handle1.mark),  # type: ignore
                player2_dict["chat_id"]: ChatPlayerInfo(handle=handle2, **player2_dict, mark=handle2.mark),  # type: ignore
            },
            gc,
        )
        # two links for each player
        self.games[player1_dict["chat_id"]] = game
        self.games[player2_dict["chat_id"]] = game
        # return game  # do I even need to return?

    def get_game(self, chat_id: ChatId) -> GamePersonalized:
        "Get personalized game by chat_id"
        return self._make_personalized_game(self.games[chat_id], chat_id)

    def remove_game(self, chat_id) -> None:
        """Remove two links to the game to release memory. No need to call twice."""
        game_pers = self.get_game(chat_id)
        chat_id_opponent = game_pers.opponent.chat_id
        del self.games[chat_id]
        del self.games[chat_id_opponent]

    @staticmethod
    def _make_personalized_game(game: Game, chat_id) -> GamePersonalized:
        """Game but with attributes to distinguish myself and opponent"""
        other_chat_id = list(set(game.chat_dict.keys()) - {chat_id})[0]
        return GamePersonalized(
            game.chat_dict[chat_id], game.chat_dict[other_chat_id], game.game_conductor
        )
