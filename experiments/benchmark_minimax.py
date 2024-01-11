from tic_tac_toe.game import TTTBoard, find_optimal_move, random_available_move

from rs_minimax import find_optimal_move as find_optimal_move_rs

FREE_SPACE = "."
CROSS = "X"
ZERO = "O"
grid = [[FREE_SPACE for _ in range(3)] for _ in range(3)]
grid[1][1] = ZERO

# comprare rust with random bot
results = []
for game in range(10):
    board = TTTBoard()

    while not board.is_game_over():
        move = random_available_move(board)
        board.set_cell(move, CROSS)
        if board.is_game_over():
            continue
        move_bot = find_optimal_move_rs(board.grid, ZERO)
        # print(board)
        # print(move_bot)
        board.set_cell(move_bot, ZERO)

    results.append(board.get_winner())
    # print(str(board))
    # print()

print(results)

# compare rust with python
results = []
for game in range(10):
    board = TTTBoard()

    while not board.is_game_over():
        move = find_optimal_move(board, CROSS)
        board.set_cell(move, CROSS)
        if board.is_game_over():
            continue
        move_bot = find_optimal_move_rs(board.grid, ZERO)
        # print(board)
        # print(move_bot)
        board.set_cell(move_bot, ZERO)

    results.append(board.get_winner())
    # print(str(board))
    # print()

print(results)  # should always be full None

# compare speed between rust and python
