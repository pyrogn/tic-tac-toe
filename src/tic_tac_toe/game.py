"""Tic Tac Toe game engine with 3x3 grid and quite standard rules.

Definition and functions. Simple bot engine (random and minimax)
"""

import random
from copy import deepcopy
from typing import Final, Literal, TypeAlias

from tic_tac_toe.exceptions import GameRulesError, InvalidMoveError

FREE_SPACE: Final = "."
CROSS: Final = "X"
ZERO: Final = "O"


Move: TypeAlias = tuple[int, int]
Mark: TypeAlias = Literal[".", "X", "O"]  # cannot use variables (Pylance)
Grid: TypeAlias = list[list[Mark]]

# CONFUSED: don't know how to write type for it
# Final[List[FREE_SPACE]] doesn't work
# Pylance: (constant) DEFAULT_STATE: list[list[str]]
DEFAULT_STATE = [[FREE_SPACE for _ in range(3)] for _ in range(3)]


class TTTBoard:
    """Game board for 3x3 Tic-Tac-Toe"""

    def __init__(self, grid: Grid | None = None) -> None:
        self.grid: Grid = grid or self.get_start_grid()

    @staticmethod
    def get_start_grid() -> Grid:
        """get default state of the game"""
        return deepcopy(DEFAULT_STATE)  # type: ignore

    def select_cell(self, move: Move) -> Mark:
        r, c = move
        return self.grid[r][c]

    def set_cell(self, move: Move, mark: Mark) -> None:
        "Set a mark in play grid in place"
        r, c = move
        self.grid[r][c] = mark

    def n_empty_cells(self) -> int:
        """Count number of empty cells in play grid"""
        return sum(elem == FREE_SPACE for row in self.grid for elem in row)

    def is_game_over(self) -> bool:
        """Game is over if there is a winner of no empty cells"""
        return (self.n_empty_cells() == 0) | (self.get_winner() is not None)

    def is_move_legal(self, move: Move) -> bool:
        """Move is legal if there is an empty cell"""
        return self.select_cell(move) == FREE_SPACE

    def make_move(self, move: Move, mark) -> None:
        """Put move into the grid.

        Raises:
            InvalidMove: if this cell is already taken
        """
        cell = self.select_cell(move)
        if cell == FREE_SPACE:
            self.set_cell(move, mark)
        else:
            raise InvalidMoveError(f"this cell is not free, but {cell}")

    def get_winner(self) -> Mark | None:
        """Find a winner and return it. If None, returns None"""
        winner = set()
        for mark in (CROSS, ZERO):
            for row in range(3):  # horizontal
                if all([i == mark for i in self.grid[row]]):
                    winner.add(mark)
            for column in range(3):  # vertical
                if all(
                    [
                        elem == mark
                        for row in range(3)
                        for elem in self.grid[row][column]
                    ]
                ):
                    winner.add(mark)
            if all([self.grid[i][i] == mark for i in range(3)]):  # left diagonal
                winner.add(mark)
            if all([self.grid[i][2 - i] == mark for i in range(3)]):  # right diagonal
                winner.add(mark)
        if len(winner) == 0:
            return None  # draw or game is not over
        if len(winner) > 1:
            raise GameRulesError("Two winners, this is nonsense")
        return list(winner)[0]

    def __str__(self) -> str:
        """Render grid in some readable string"""
        return "\n".join(["".join(row) for row in self.grid]).replace(".", "_")

    def __eq__(self, obj) -> bool:
        if isinstance(
            obj, list
        ):  # cannot get any further (Grid is generic and not allowed)
            return self.grid == obj
        if isinstance(obj, TTTBoard):
            return self.grid == obj.grid
        return NotImplemented


class HandleForPlayer:
    """Handle for player to play the game safely.

    Attributes:
        mark: mark of the player (X or O)
        _game: GameConductor instance. Shouldn't be accessed by player (imagine that)
    Methods:
        is_my_turn() -> (bool): is this player's turn
    Magic methods:
        __call__(move) -> None: call this handle to make a move in a board
    Example:
        handle((1, 2)) # put a move in the grid
        handle.mark # get a mark
        handle.is_my_turn() # understand if it is player's turn
    """

    mark: Mark
    _game: "GameConductor"

    def __init__(self, game: "GameConductor", mark: Mark) -> None:
        self._game = game
        self.mark: Mark = mark

    def __call__(self, move: Move) -> None:
        """Make a move."""
        self._game.full_handle(move, self.mark)

    def is_my_turn(self) -> bool:
        """Is it my turn."""
        # it is not property to be compatible with lambda func alternative
        return self._game.current_move == self.mark


class GameConductor:
    """Game engine for tic tac toe"""

    def __init__(self):
        self.game_board: TTTBoard = TTTBoard()
        self._available_marks: set[Mark] = {CROSS, ZERO}
        self.current_move: Mark = CROSS  # first move (my game rule)
        self.is_game_over: bool = False

    def get_handle(
        self,
        mark: Mark | None = None,
        what_is_left: bool = False,
    ) -> HandleForPlayer:
        """Get handle for playing in this instance of a game.

        Attributes:
            mark: choose your preferred mark
            what_is_left: you don't have preference in marks, get anything
        """
        if mark and mark not in (CROSS, ZERO):
            raise ValueError(f"This mark {mark} is unknown")

        # if you can take anything and there are two free mark, choose CROSS
        # if you have no preference, take what is left
        # else get exception to the face for being too assertive
        if what_is_left and len(self._available_marks) == 2:
            mark = CROSS
        elif not mark or what_is_left:
            mark = list(self._available_marks)[0]

        try:
            self._available_marks.remove(mark)
        except KeyError:
            raise GameRulesError("This mark is already taken for this game instance")

        # full dynamism (Pylance is crazy)
        # but I like this way
        # CONFUSED: is there a better way to create a such handle for player?

        # handle = partial(self.full_handle, mark=mark)
        # handle.is_my_turn = lambda: self.current_move == mark
        # handle.mark = mark

        # attempt with explicit class
        handle = HandleForPlayer(self, mark)

        return handle

    @property
    def result(self) -> Mark | None:
        if not (self.game_board.is_game_over()):
            raise GameRulesError("Game is not over")
        return self.game_board.get_winner()

    def full_handle(self, move: Move, mark: Mark) -> None:
        """Might raise exception if the move is illegal"""
        if self.is_game_over:
            raise GameRulesError("Game has ended, no more moves!")
        if self.current_move != mark:
            raise InvalidMoveError("Now it is the move of an opponent, keep calm")

        self.game_board.make_move(move, mark)

        if self.game_board.is_game_over():
            self.is_game_over = True
        self.current_move = get_opposite_mark(mark)  # now another player's turn


def get_opposite_mark(mark: Mark) -> Mark:
    """Get opposite mark out of O and X. Useful when player made a move."""
    if mark not in (CROSS, ZERO):
        raise ValueError(mark + " not in marks")
    return ZERO if mark == CROSS else CROSS


def random_available_move(game_board: TTTBoard) -> Move:
    "Get random move from available cells"
    if game_board.n_empty_cells() == 0:
        raise ValueError("No empty cells")

    available_moves = [
        (row, col)
        for row in range(3)
        for col in range(3)
        if game_board.grid[row][col] == FREE_SPACE
    ]
    return random.choice(available_moves)


def _minimax_move_score(game_board: TTTBoard, mark: Mark, max_score: int) -> int:
    """Get minimax game score for the grid and mark move."""
    if game_board.is_game_over():  # end condition
        winner = game_board.get_winner()
        if not winner:  # draw
            return 0
        if winner == mark:  # win
            return 10
        return -10  # lose

    best_score = -200
    for r in range(3):
        for c in range(3):
            if game_board.grid[r][c] == FREE_SPACE:
                if best_score >= max_score:  # leave early if found better score
                    return best_score
                game_board.set_cell((r, c), mark)
                score = -_minimax_move_score(
                    game_board, mark=get_opposite_mark(mark), max_score=-best_score
                )
                game_board.set_cell((r, c), FREE_SPACE)
                if score > best_score:
                    best_score = score

    return best_score


def find_optimal_move(game_board: TTTBoard, mark: Mark) -> Move:
    """Get optimal move based on minimax strategy"""
    # if move hasn't changed, we are in trouble, but it shouln't happen
    best_score, move = -200, (100, 100)
    game_board = deepcopy(game_board)
    for r in range(3):
        for c in range(3):
            if game_board.grid[r][c] == FREE_SPACE:
                game_board.set_cell((r, c), mark)
                score = -_minimax_move_score(
                    game_board, get_opposite_mark(mark), -best_score
                )
                game_board.set_cell((r, c), FREE_SPACE)
                if score > best_score:
                    best_score = score
                    move = (r, c)
    return move
