"""Script to validate that
- Rust Minimax is unbeatable
- On par with Python Minimax
- Faster than Python (order of magnitude - hundreds (WOW!))
"""
import functools
import time
from collections import defaultdict

import numpy as np
from tic_tac_toe import find_optimal_move_rs
from tic_tac_toe.game import (
    CROSS,
    ZERO,
    GameConductor,
    Mark,
    find_optimal_move,
    random_available_move,
)


# comprare rust with random bot
def test_2_strategies(strategy1, strategy2, n_games=10, first_mark: Mark = CROSS):
    results = []
    for _ in range(n_games):
        gc = GameConductor()
        handle1 = gc.get_handle(first_mark)
        handle2 = gc.get_handle(what_is_left=True)

        while not gc.is_game_over:
            if handle1.is_my_turn():
                move = strategy1(gc.game_board.grid, handle1.mark)
                handle1(move)
            elif handle2.is_my_turn():
                move = strategy2(gc.game_board.grid, handle2.mark)
                handle2(move)

            else:
                raise RuntimeError("Something's wrong with moves")

        winner = gc.game_board.get_winner()
        if winner == handle1.mark:
            winner_num = 1
        elif winner == handle2.mark:
            winner_num = 2
        else:
            winner_num = 0
        results.append(winner_num)
    return results


def get_prop_wins(results):
    return (np.array(results) == 1).mean()


rs_vs_bot1 = test_2_strategies(
    find_optimal_move_rs,
    random_available_move,
    n_games=50,
    first_mark=CROSS,
)
rs_vs_bot2 = test_2_strategies(
    find_optimal_move_rs,
    random_available_move,
    n_games=50,
    first_mark=ZERO,
)

assert len(list(filter(lambda x: x == 2, rs_vs_bot1))) == 0  # zero loses
assert len(list(filter(lambda x: x == 2, rs_vs_bot2))) == 0  # zero loses


print(f"Wins Rs with 1 move: {get_prop_wins(rs_vs_bot1):.2f}")
print(f"Wins Rs with 2 move: {get_prop_wins(rs_vs_bot2):.2f}")

rs_vs_py1 = test_2_strategies(
    find_optimal_move_rs,
    find_optimal_move,
    n_games=10,
    first_mark=CROSS,
)
rs_vs_py2 = test_2_strategies(
    find_optimal_move_rs,
    find_optimal_move,
    n_games=10,
    first_mark=ZERO,
)

assert len(list(filter(lambda x: x != 0, rs_vs_py1))) == 0  # only draws
assert len(list(filter(lambda x: x != 0, rs_vs_py2))) == 0  # only draws
print("Python vs Rust: all draws, good")


def measure_speed(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        t = time.process_time()

        result = func(*args, **kwargs)
        elapsed_time = time.process_time() - t
        return result, elapsed_time

    return wrapper


# compare speed between rust and python
def test_2_strategies_speed(strategy1, strategy2, n_games=10, first_mark: Mark = CROSS):
    strategy1_tm = measure_speed(strategy1)
    strategy2_tm = measure_speed(strategy2)
    speed = defaultdict(lambda: defaultdict(list))
    for _ in range(n_games):
        gc = GameConductor()
        handle1 = gc.get_handle(first_mark)
        handle2 = gc.get_handle(what_is_left=True)
        n_move = 1

        while not gc.is_game_over:
            if handle1.is_my_turn():
                move, tm = strategy1_tm(gc.game_board.grid, handle1.mark)
                handle1(move)
                speed[1][n_move].append(tm)
            elif handle2.is_my_turn():
                move, tm = strategy2_tm(gc.game_board.grid, handle2.mark)
                handle2(move)
                speed[2][n_move].append(tm)

            else:
                raise RuntimeError("Something's wrong with moves")
            n_move += 1
    speed_mean = defaultdict(lambda: defaultdict(float))
    for algo, val in speed.items():
        for n_move, tm_vals in val.items():
            speed_mean[algo][n_move] = np.array(tm_vals).mean()
    return speed_mean


speed_rs_vs_py1 = test_2_strategies_speed(
    find_optimal_move_rs, find_optimal_move, n_games=10, first_mark=CROSS
)
speed_rs_vs_py2 = test_2_strategies_speed(
    find_optimal_move_rs, find_optimal_move, n_games=10, first_mark=ZERO
)


def union_speeds(speed1, speed2, n):
    dict_speed = speed1[n] | speed2[n]
    return np.array(list(dict(sorted(dict_speed.items())).values()))


rs_speed = union_speeds(speed_rs_vs_py1, speed_rs_vs_py2, 1)
py_speed = union_speeds(speed_rs_vs_py1, speed_rs_vs_py2, 2)

diff_times = (py_speed / rs_speed).round(1)

assert np.all(rs_speed < py_speed)


def arr_to_ms(arr):
    return [round(elem * 1_000, 1) for elem in arr]


print(f"avg Py speeds from 1 to 9 move: {arr_to_ms(py_speed)}")
print(f"avg Rs speeds from 1 to 9 move: {arr_to_ms(rs_speed)}")
print(f"diff in speed (times): {diff_times}")

# При данных условиях реализация на Rust быстрее в 150 раз в самом начале,
# потом разница уменьшается до десяти примерно
