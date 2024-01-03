from collections import deque
from queue import Queue
from typing import Any, Literal, NamedTuple
from tic_tac_toe.exceptions import (
    CurrentGameError,
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
        # better to be Queue, but it is harder to work with
        self.players_queue: list[dict] = []
        self.games: dict[ChatId, Game] = {}

    @property
    def is_player_waiting(self):
        if len(self.players_queue) >= 2:
            raise ValueError("Too many players waiting game, tinder somebody please")
        return len(self.players_queue) != 0

    def register_player(self, **kwargs):
        # necessary keys to connect players
        if not all([key in kwargs for key in ("chat_id", "message_id")]):
            raise ValueError(
                "chat_id and message_id are necessary keys for registration"
            )
        if kwargs["chat_id"] in self.games:
            raise CurrentGameError

        if kwargs["chat_id"] in self.players_queue:  # how to make it simpler?
            raise WaitRoomError

        self.players_queue.append(kwargs)

    def register_pair(self) -> None:
        if len(self.players_queue) < 2:
            raise NotEnoughPlayersError("Not enough players")
        player1_dict = self.players_queue.pop(0)
        player2_dict = self.players_queue.pop(0)

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

    def is_this_player_in_waitlist(self, chat_id: ChatId) -> bool:
        for player in self.players_queue:
            if chat_id == player["chat_id"]:
                return True
        return False

    def remove_player_from_queue(self, chat_id: ChatId) -> bool:
        "Remove player from waitlist"
        for elem in self.players_queue:
            if elem["chat_id"] == chat_id:
                self.players_queue.remove(elem)
                return True
        return False

    def get_player_from_queue(self, chat_id: ChatId):
        for elem in self.players_queue:
            if elem["chat_id"] == chat_id:
                return elem
