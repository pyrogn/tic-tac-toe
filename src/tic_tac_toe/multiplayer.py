"""Module with helpers for multiplayer game of Tic Tac Toe"""
from typing import NamedTuple, TypeAlias

from tic_tac_toe.exceptions import (
    CurrentGameError,
    NotEnoughPlayersError,
    WaitRoomError,
)
from tic_tac_toe.game import (
    CROSS,
    GameConductor,
    HandleForPlayer,
    Mark,
)

MessageId: TypeAlias = int
ChatId: TypeAlias = int


class ChatPlayerInfo(NamedTuple):
    """Struct with basic info about user in the game."""

    chat_id: ChatId
    message_id: MessageId
    handle: HandleForPlayer
    mark: Mark
    user_name: str


class Game(NamedTuple):
    """Full info about the game."""

    chat_dict: dict[ChatId, ChatPlayerInfo]
    game_conductor: GameConductor


class GamePersonalized(NamedTuple):
    """Full info about the game with convenience attributes."""

    myself: ChatPlayerInfo
    opponent: ChatPlayerInfo
    game_conductor: GameConductor


class Multiplayer:
    """Connects two players, manages queue and games.

    Attributes:
        players_queue: queue for players waiting for multiplayer game
        games: dict that links chat_id to a Game. For 1 game there are two links
            from two players for convenience.
    Methods:
        register_player: put player in the queue
        register_pair: start a game with two earliest players
        get_game: get personalized game by chat_id
        remove_game: remove game from current_games by chat_id
        is_this_player_in_queue
        remove_player_from_queue
        get_player_from_queue
    """

    def __init__(self) -> None:
        # better and more efficient to be Queue, but it is harder to work with
        # anyway queue won't store more than 2 players
        self.players_queue: list[dict] = []
        self.games: dict[ChatId, Game] = {}

    @property
    def is_player_waiting(self):
        """Check if somebody is already in the queue, waiting for a game"""
        if len(self.players_queue) >= 2:
            raise ValueError("Too many players wait for game, tinder somebody please")
        return len(self.players_queue) != 0

    def register_player(self, **kwargs):
        """Register player and put his info in the queue"""
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
        """Try to make a pair from players in the queue and start a game.

        If not enough players (0 or 1), raises NotEnoughPlayersError
        """
        if len(self.players_queue) < 2:
            raise NotEnoughPlayersError("Not enough players")
        player1_dict = self.players_queue.pop(0)
        player2_dict = self.players_queue.pop(0)

        gc = GameConductor()
        # First joined player will get CROSS always
        handle1 = gc.get_handle(CROSS, what_is_left=True)
        handle2 = gc.get_handle(CROSS, what_is_left=True)
        game = Game(
            {
                player1_dict["chat_id"]: ChatPlayerInfo(
                    handle=handle1, mark=handle1.mark, **player1_dict
                ),
                player2_dict["chat_id"]: ChatPlayerInfo(
                    handle=handle2, mark=handle2.mark, **player2_dict
                ),
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
    def _make_personalized_game(game: Game, chat_id: ChatId) -> GamePersonalized:
        """Convert Game into GamePersonalized"""
        other_chat_id = list(set(game.chat_dict.keys()) - {chat_id})[0]
        return GamePersonalized(
            game.chat_dict[chat_id], game.chat_dict[other_chat_id], game.game_conductor
        )

    # I don't know what to do with it, looks like a candidate for
    # a new class PlayerQueue with these methods
    def is_this_player_in_queue(self, chat_id: ChatId) -> bool:
        "Check if the player is already in the queue"
        for player in self.players_queue:
            if chat_id == player["chat_id"]:
                return True
        return False

    def remove_player_from_queue(self, chat_id: ChatId) -> bool:
        "Remove player from the queue"
        for player in self.players_queue:
            if player["chat_id"] == chat_id:
                self.players_queue.remove(player)
                return True
        return False

    def get_player_from_queue(self, chat_id: ChatId) -> dict | None:
        """Get player info from the queue"""
        for player in self.players_queue:
            if player["chat_id"] == chat_id:
                return player
