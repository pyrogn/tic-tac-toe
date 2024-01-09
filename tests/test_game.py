"""Tests for game engine and different helpers."""
import pytest
from tic_tac_toe.exceptions import GameRulesError, InvalidMoveError
from tic_tac_toe.game import (
    CROSS,
    FREE_SPACE,
    ZERO,
    GameConductor,
    TTTBoard,
    get_opposite_mark,
    random_available_move,
)


# board examples
@pytest.fixture()
def board1():
    return TTTBoard(
        [
            [FREE_SPACE, CROSS, ZERO],
            [CROSS, FREE_SPACE, ZERO],
            [FREE_SPACE, CROSS, FREE_SPACE],
        ]
    )


@pytest.fixture()
def board2():
    return TTTBoard(
        [
            [FREE_SPACE, CROSS, ZERO],
            [CROSS, FREE_SPACE, ZERO],
            [FREE_SPACE, CROSS, ZERO],
        ]
    )


@pytest.fixture()
def board3_win1():
    return TTTBoard(
        [
            [CROSS, FREE_SPACE, FREE_SPACE],
            [FREE_SPACE, CROSS, FREE_SPACE],
            [FREE_SPACE, FREE_SPACE, CROSS],
        ]
    )


@pytest.fixture()
def board3_win2():
    return TTTBoard(
        [
            [FREE_SPACE, FREE_SPACE, ZERO],
            [FREE_SPACE, ZERO, FREE_SPACE],
            [ZERO, FREE_SPACE, FREE_SPACE],
        ]
    )


@pytest.fixture()
def board4():
    return TTTBoard(
        [
            [ZERO, CROSS, CROSS],
            [CROSS, ZERO, ZERO],
            [ZERO, CROSS, CROSS],
        ]
    )


def test_board_analysis(board1, board2, board4):
    assert board1.n_empty_cells() == 4  # magic values
    assert board2.n_empty_cells() == 3
    assert board4.n_empty_cells() == 0

    assert board1.select_cell((0, 2)) == ZERO
    assert board1.select_cell((1, 0)) == CROSS


def test_winners(board1, board2, board3_win1, board3_win2, board4):
    assert board1.get_winner() is None
    assert board1.is_game_over() is False

    assert board2.get_winner() == ZERO
    assert board2.is_game_over() is True

    assert board3_win1.get_winner() == CROSS
    assert board3_win1.is_game_over() is True

    assert board3_win2.get_winner() == ZERO
    assert board3_win2.is_game_over() is True

    assert board4.get_winner() is None
    assert board4.is_game_over() is True


def test_moves(board1, board2):
    board = TTTBoard()
    board.make_move((0, 1), CROSS)
    board.make_move((0, 2), ZERO)
    board.make_move((1, 0), CROSS)
    board.make_move((1, 2), ZERO)
    board.make_move((2, 1), CROSS)
    assert board == board1

    assert board.is_move_legal((2, 2)) is True

    board.make_move((2, 2), ZERO)
    assert board == board2

    assert board.is_move_legal((2, 2)) is False


def test_random_choice():
    board = TTTBoard()
    for _ in range(9):  # some rules bending, but random becomes determined
        move = random_available_move(board)
        board.set_cell(move, CROSS)

    assert board.n_empty_cells() == 0
    assert board.is_game_over() is True
    assert board.get_winner() == CROSS

    with pytest.raises(ValueError, match="No empty cells"):
        random_available_move(board)


def test_game_conductor1():
    """One game simulation"""
    gc = GameConductor()
    handle1 = gc.get_handle(CROSS)
    handle2 = gc.get_handle()  # get zero that is left

    handle1((0, 1))
    assert handle1.is_my_turn() is False
    assert handle2.is_my_turn() is True

    with pytest.raises(
        InvalidMoveError, match=r".*Now it is the move of an opponent.*"
    ):
        handle1((0, 1))
    assert gc.game_board.n_empty_cells() == 8
    assert gc.current_move == ZERO

    handle2((0, 0))
    assert gc.game_board.n_empty_cells() == 7
    assert gc.current_move == CROSS

    with pytest.raises(InvalidMoveError, match=r".*this cell is not free.*"):
        handle1((0, 0))
    assert gc.game_board.n_empty_cells() == 7
    assert gc.current_move == CROSS
    handle1((1, 1))
    handle2((0, 2))
    handle1((2, 1))  # first won
    assert gc.game_board.n_empty_cells() == 4
    assert gc.result == CROSS
    with pytest.raises(GameRulesError, match=r".*Game has ended, no more moves.*"):
        handle2((2, 2))

    rendered_board = "OXO\n_X_\n_X_"
    assert str(gc.game_board) == rendered_board  # мне хорошо, я так чувствую


def test_opposite_mark():
    """Test for basic ternary operator for marks"""
    assert get_opposite_mark(CROSS) == ZERO
    assert get_opposite_mark(ZERO) == CROSS
    with pytest.raises(ValueError):
        get_opposite_mark("some bogus mark")  # type: ignore


def test_get_mark():
    gc = GameConductor()
    handle1 = gc.get_handle(CROSS, what_is_left=True)
    handle2 = gc.get_handle(CROSS, what_is_left=True)
    assert handle1.is_my_turn() is True
    assert handle2.is_my_turn() is False
    assert handle1.mark == CROSS
    assert handle2.mark == ZERO

    handle1((0, 0))
    assert handle1.is_my_turn() is False
    assert handle2.is_my_turn() is True
    assert handle1.mark == CROSS
    assert handle2.mark == ZERO
