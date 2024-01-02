"""Exceptions for bot"""


class TicTacToeException(Exception):
    "General exception for the game"


class InvalidMove(TicTacToeException):
    "Invalid move"


class GameRulesException(TicTacToeException):
    "Something broken with rules"


class MultiplayerError(TicTacToeException):
    "Something wrong while playing in multiplayer mode"


class CurrentGameError(MultiplayerError):
    "If player already has the game"


class NotEnoughPlayersError(MultiplayerError):
    """Not enough players to start a multiplayer game"""


class WaitRoomError(MultiplayerError):
    "You are already in the queue"
