"""Tic tac toe game engine with 3x3 grid and quite standard rules.

Definition and functions"""

import random
from copy import deepcopy
from functools import partial
from typing import Final, Literal, Protocol, TypeAlias

from tic_tac_toe.exceptions import GameRulesError, InvalidMove

FREE_SPACE: Final = "."
CROSS: Final = "X"
ZERO: Final = "O"


Move: TypeAlias = tuple[int, int]
Mark: TypeAlias = Literal[".", "X", "O"]  # cannot use variables (Pylance)
Grid: TypeAlias = list[list[Mark]]

# CONFUSED: don't know how to write type for it
# Final[List[FREE_SPACE]] doesn't work
DEFAULT_STATE = [[FREE_SPACE for _ in range(3)] for _ in range(3)]


def get_default_state() -> Grid:
    """Helper function to get default state of the game"""
    return deepcopy(DEFAULT_STATE)


def select_cell(grid: Grid, move: Move) -> Mark:
    r, c = move
    return grid[r][c]


def set_cell(grid: Grid, move: Move, mark: Mark) -> None:
    "Set a mark in play grid in place"
    r, c = move
    grid[r][c] = mark


def n_empty_cells(grid: Grid) -> int:
    """Count number of empty cells in play grid"""
    return sum(elem == FREE_SPACE for row in grid for elem in row)


def is_game_over(grid: Grid) -> bool:
    """Game is over if there is a winner of no empty cells"""
    return (n_empty_cells(grid) == 0) | (get_winner(grid) is not None)


def is_move_legal(grid: Grid, move: Move) -> bool:
    """Move is legal if there is an empty cell"""
    return select_cell(grid, move) == FREE_SPACE


def make_move(grid: Grid, move: Move, mark) -> None:
    """Put move into the grid.

    Raises:
        InvalidMove: if this cell is already taken"""
    cell = select_cell(grid, move)
    if cell == FREE_SPACE:
        set_cell(grid, move, mark)
    else:
        raise InvalidMove(f"this cell is not free, but {cell}")


def get_winner(grid: Grid) -> Mark | None:
    """Find a winner and return it. If None, return None"""
    winner = set()
    for mark in (CROSS, ZERO):
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
        raise GameRulesError("Two winners, this is nonsense")
    return list(winner)[0]


def random_available_move(grid: Grid) -> Move:
    "Get random move from available cells"
    if n_empty_cells(grid) == 0:
        raise ValueError("No empty cells")

    available_moves = [
        (row, col)
        for row in range(3)
        for col in range(3)
        if grid[row][col] == FREE_SPACE
    ]
    return random.choice(available_moves)


class HandleForPlayer(Protocol):
    mark: Mark

    def __call__(self, move: Move) -> None:
        ...

    def is_my_turn(self) -> bool:
        ...


class GameConductor:
    """Conductor
    Game Rules:
    X has the first move
    """

    def __init__(self):
        self.grid: Grid = get_default_state()
        self._available_marks: set[Mark] = {CROSS, ZERO}
        self.current_move: Mark = CROSS  # first move
        self.is_game_over: bool = False

    def get_handler(
        self,
        mark: Mark | None = None,
        what_is_left: bool = False,
    ) -> HandleForPlayer:
        """You just call returned function with coordinates"""
        if mark and mark not in (CROSS, ZERO):
            raise ValueError(f"This mark {mark} is unknown")

        # some logic is still unclear
        # TODO: think about it
        if what_is_left and len(self._available_marks) == 2:
            mark = CROSS
        elif not mark or what_is_left:
            mark = list(self._available_marks)[0]

        try:
            self._available_marks.remove(mark)
        except KeyError:
            raise KeyError("This mark is already taken for this game instance")

        handle = partial(self.full_handle, mark=mark)

        # full dynamism (Pylance is crazy)
        # but I really like this way
        # CONFUSED: is there a better way to create a handle for player?
        handle.is_my_turn = lambda: self.current_move == mark
        handle.mark = mark

        return handle

    @property
    def result(self) -> Mark | None:
        if not is_game_over(self.grid):
            raise GameRulesError("Game is not over")
        return get_winner(self.grid)

    def full_handle(self, move: Move, mark: Mark) -> None:
        """Might raise exception if the move is illegal"""
        if self.is_game_over:
            raise GameRulesError("Game has ended, no more moves!")
        if self.current_move != mark:
            raise InvalidMove(
                "Now it is the move of an opponent, keep calm and drink cool cola"
            )

        make_move(self.grid, move, mark)

        if is_game_over(self.grid):
            self.is_game_over = True
        self.current_move = get_opposite_mark(mark)  # now another player's turn

    def __str__(self) -> str:
        """Render grid in some readable string"""
        return "\n".join(["".join(row) for row in self.grid]).replace(".", "_")


def get_opposite_mark(mark: Mark) -> Mark:
    """Get opposite mark out of O and X"""
    if mark not in (CROSS, ZERO):
        raise ValueError(mark + " not in marks")
    return ZERO if mark == CROSS else CROSS


def iter_through_cells(grid: Grid):
    for r in range(2):
        for c in range(2):
            grid[r][c]


def minimax_move_score(grid: Grid, mark: Mark, max_score: int) -> int:
    if is_game_over(grid):
        winner = get_winner(grid)
        if not winner:  # draw
            return 0
        if winner == mark:  # win
            return 10
        return -10  # lose

    best_score = -200
    for r in range(3):
        for c in range(3):
            if grid[r][c] == FREE_SPACE:
                if best_score >= max_score:  # leave early if found better score
                    return best_score
                set_cell(grid, (r, c), mark)
                score = -minimax_move_score(
                    grid, mark=get_opposite_mark(mark), max_score=-best_score
                )
                set_cell(grid, (r, c), FREE_SPACE)
                if score > best_score:
                    best_score = score

    return best_score


def find_optimal_move(grid: Grid, mark: Mark) -> Move:
    best_score, move = -200, (100, 100)
    grid = deepcopy(grid)
    for r in range(3):
        for c in range(3):
            if grid[r][c] == FREE_SPACE:
                set_cell(grid, (r, c), mark)
                score = -minimax_move_score(grid, get_opposite_mark(mark), -best_score)
                set_cell(grid, (r, c), FREE_SPACE)
                if score > best_score:
                    best_score = score
                    move = (r, c)
    return move
