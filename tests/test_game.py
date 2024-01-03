import pytest
from tic_tac_toe.exceptions import GameRulesException, InvalidMove

from tic_tac_toe.game import (
    DEFAULT_STATE,
    get_default_state,
    Cell,
    Grid,
    Move,
    FREE_SPACE,
    CROSS,
    ZERO,
    get_opposite_mark,
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


@pytest.fixture()
def grid1():
    return [
        [FREE_SPACE, CROSS, ZERO],
        [CROSS, FREE_SPACE, ZERO],
        [FREE_SPACE, CROSS, FREE_SPACE],
    ]


@pytest.fixture()
def grid2():
    return [
        [FREE_SPACE, CROSS, ZERO],
        [CROSS, FREE_SPACE, ZERO],
        [FREE_SPACE, CROSS, ZERO],
    ]


@pytest.fixture()
def grid3_win1():
    return [
        [CROSS, FREE_SPACE, FREE_SPACE],
        [FREE_SPACE, CROSS, FREE_SPACE],
        [FREE_SPACE, FREE_SPACE, CROSS],
    ]


@pytest.fixture()
def grid3_win2():
    return [
        [FREE_SPACE, FREE_SPACE, ZERO],
        [FREE_SPACE, ZERO, FREE_SPACE],
        [ZERO, FREE_SPACE, FREE_SPACE],
    ]


@pytest.fixture()
def grid4():
    return [
        [ZERO, CROSS, CROSS],
        [CROSS, ZERO, ZERO],
        [ZERO, CROSS, CROSS],
    ]


def test_grid_analysis(grid1, grid2, grid4):
    assert n_empty_cells(grid1) == 4  # magic values
    assert n_empty_cells(grid2) == 3
    assert n_empty_cells(grid4) == 0

    assert select_cell(grid1, (0, 2)) == ZERO
    assert select_cell(grid1, (1, 0)) == CROSS


def test_winners(grid1, grid2, grid3_win1, grid3_win2, grid4):
    assert get_winner(grid1) is None
    assert is_game_over(grid1) is False

    assert get_winner(grid2) == ZERO
    assert is_game_over(grid2) is True

    assert get_winner(grid3_win1) == CROSS
    assert is_game_over(grid3_win1) is True

    assert get_winner(grid3_win2) == ZERO
    assert is_game_over(grid3_win2) is True

    assert get_winner(grid4) is None
    assert is_game_over(grid4) is True


def test_moves(grid1, grid2):
    grid = get_default_state()
    make_move(grid, (0, 1), CROSS)
    make_move(grid, (0, 2), ZERO)
    make_move(grid, (1, 0), CROSS)
    make_move(grid, (1, 2), ZERO)
    make_move(grid, (2, 1), CROSS)
    assert grid == grid1

    assert is_move_legal(grid, (2, 2))

    make_move(grid, (2, 2), ZERO)
    assert grid == grid2

    assert not is_move_legal(grid, (2, 2))


def test_random_choice():
    grid = get_default_state()
    for _ in range(9):  # some rule bending, but random resilient
        move = random_available_move(grid)
        set_cell(grid, move, CROSS)

    assert n_empty_cells(grid) == 0
    assert is_game_over(grid) is True
    assert get_winner(grid) == CROSS

    with pytest.raises(ValueError, match="No empty cells"):
        random_available_move(grid)


def test_game_conductor1():
    """One game simulation (others I don't want to write for now)"""
    gc = GameConductor()
    handle1 = gc.get_handler(CROSS)
    handle2 = gc.get_handler()  # get zero that is left

    handle1((0, 1))
    assert handle1.is_my_turn() == False  # type: ignore
    assert handle2.is_my_turn() == True  # type: ignore

    with pytest.raises(InvalidMove, match=r".*Now it is the move of an opponent.*"):
        handle1((0, 1))
    assert n_empty_cells(gc.grid) == 8
    assert gc.current_move == ZERO

    handle2((0, 0))
    assert n_empty_cells(gc.grid) == 7
    assert gc.current_move == CROSS

    with pytest.raises(InvalidMove, match=r".*this cell is not free.*"):
        handle1((0, 0))
    assert n_empty_cells(gc.grid) == 7
    assert gc.current_move == CROSS
    handle1((1, 1))
    handle2((0, 2))
    handle1((2, 1))  # first won
    assert n_empty_cells(gc.grid) == 4
    assert gc.result == CROSS
    with pytest.raises(GameRulesException, match=r".*Game has ended, no more moves.*"):
        handle2((2, 2))


# it is kind of broken, see function definition
def test_render_grid(grid1):
    rendered_grid = """_XO\nX_O\n_X_"""
    assert render_grid(grid1) == rendered_grid


def test_opposite_mark():
    assert get_opposite_mark(CROSS) == ZERO
    assert get_opposite_mark(ZERO) == CROSS
    with pytest.raises(ValueError):
        get_opposite_mark("some bogus mark")


def test_get_mark():
    gc = GameConductor()
    handle1 = gc.get_handler(CROSS, what_is_left=True)
    handle2 = gc.get_handler(CROSS, what_is_left=True)
    assert handle1.is_my_turn() == True  # type: ignore
    assert handle2.is_my_turn() == False  # type: ignore
