"""Custom exceptions for a bot and a game."""


class TicTacToeException(Exception):
    "General exception for the game"


class InvalidMoveError(TicTacToeException):
    "Invalid move"


class GameRulesError(TicTacToeException):
    "Something is broken with the game rules"


class MultiplayerError(TicTacToeException):
    "Something wrong while playing in multiplayer mode"


class CurrentGameError(MultiplayerError):
    "If player already has the game"


class NotEnoughPlayersError(MultiplayerError):
    """Not enough players to start a multiplayer game"""


class WaitRoomError(MultiplayerError):
    "You are already in the queue"
