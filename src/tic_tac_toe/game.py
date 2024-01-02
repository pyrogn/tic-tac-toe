"""Tic tac toe 3x3 grid.
Definition and functions"""
from copy import deepcopy
from functools import partial
from typing import Any, Callable, Final, Literal, NamedTuple, TypeAlias
import random

from exceptions import GameRulesException, InvalidMove

FREE_SPACE: Final = "."
CROSS: Final = "X"
ZERO: Final = "O"


DEFAULT_STATE: Final = [[FREE_SPACE for _ in range(3)] for _ in range(3)]

Cell: TypeAlias = str
Grid: TypeAlias = list[list[Cell]]
Move: TypeAlias = tuple[int, int]
# Mark: TypeAlias = Literal[".", "X", "O"]  # cannot use variables (Pylance)


def get_default_state():
    """Helper function to get default state of the game"""
    return deepcopy(DEFAULT_STATE)


def select_cell(grid: Grid, move: Move) -> Cell:
    r, c = move
    return grid[r][c]


def set_cell(grid: Grid, move: Move, mark: str) -> None:
    "Set an element in place"
    # I like immutability, but it'll require extra data copy with only 1 change
    r, c = move
    grid[r][c] = mark


def n_empty_cells(grid: Grid) -> int:
    return sum(elem == FREE_SPACE for row in grid for elem in row)


def is_game_over(grid: Grid) -> bool:
    return (n_empty_cells(grid) == 0) | (get_winner(grid) is not None)


def is_move_legal(grid: Grid, move: Move) -> bool:
    return select_cell(grid, move) == FREE_SPACE


def make_move(grid: Grid, move: Move, mark) -> None:
    cell = select_cell(grid, move)
    if cell == FREE_SPACE:
        set_cell(grid, move, mark)
    else:
        raise InvalidMove(f"this cell is not free, but {cell}")


def get_winner(grid: Grid) -> str | None:
    """Find a winner and return it. If None, return None"""
    winner = set()
    for mark in (CROSS, ZERO):  # I can rewrite it maybe?
        for row in range(3):  # horizontal
            if all([i == mark for i in grid[row]]):
                winner.add(mark)
        for column in range(3):  # vertical
            if all([elem == mark for row in range(3) for elem in grid[row][column]]):
                winner.add(mark)
        if all([grid[i][i] == mark for i in range(3)]):  # left diagonal
            winner.add(mark)
        if all([grid[i][2 - i] == mark for i in range(3)]):  # right diagonal
            winner.add(mark)
    if len(winner) == 0:
        return None  # draw or game is not over
    if len(winner) > 1:
        raise ValueError("Two winners, this is nonsense")
    return list(winner)[0]


def random_available_move(grid: Grid) -> Move:
    if n_empty_cells(grid) == 0:
        raise ValueError("No empty cells")

    available_moves = [
        (row, col)
        for row in range(3)
        for col in range(3)
        if grid[row][col] == FREE_SPACE
    ]
    return random.choice(available_moves)


class GameConductor:
    """Conductor
    Game Rules:
    X has the first move
    """

    def __init__(self):
        self.grid = get_default_state()
        self._available_marks = {CROSS, ZERO}
        self.current_move = CROSS  # first move
        self.is_game_over = False

    def get_handler(self, mark: str | None = None, what_is_left: bool = False):
        """You just call returned function with coordinates"""
        if mark and mark not in (CROSS, ZERO):
            raise ValueError(f"This mark {mark} is unknown")

        # some logic is still unclear
        if what_is_left and len(self._available_marks) == 2:
            mark = CROSS
        elif not mark or what_is_left:
            mark = list(self._available_marks)[0]

        try:
            self._available_marks.remove(mark)
        except KeyError:
            raise KeyError("This mark is already taken for this game instance")

        handler = partial(self.move_handler, mark=mark)

        # full dynamism (most importantly, legal!)
        handler.is_my_turn = lambda: self.current_move == mark  # type: ignore
        handler.mark = mark  # type: ignore

        return handler

    @property
    def result(self):
        if not is_game_over(self.grid):
            raise GameRulesException("Game is not over")
        return get_winner(self.grid)

    def move_handler(self, move: Move, mark: str):
        """Might raise exception if the move is illegal"""
        if self.is_game_over:
            raise GameRulesException("Game has ended, no more moves!")
        if self.current_move != mark:
            raise InvalidMove(
                "Now it is the move of an opponent, keep calm and drink cool cola"
            )

        make_move(self.grid, move, mark)

        if is_game_over(self.grid):
            self.is_game_over = True
        self.current_move = get_opposite_mark(mark)  # now another player's turn


def get_opposite_mark(mark: str) -> str:
    if mark not in (CROSS, ZERO):
        raise ValueError(mark + " not in marks")
    return list({CROSS, ZERO} - {mark})[0]


def render_grid(grid: Grid) -> str:
    return "\n".join(["".join(row) for row in grid]).replace(".", "_")
