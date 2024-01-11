#![allow(unused)]

use pyo3::prelude::*;

const TOTAL_ROWS: usize = 3;
const TOTAL_COLUMNS: usize = 3;
const MAX_FILL: usize = TOTAL_ROWS * TOTAL_COLUMNS;

#[derive(Clone, PartialEq, Copy)]
enum Mark {
    FreeSpace,
    Cross,
    Zero,
}

// there should be more idiomatic ways to that it
fn get_char_of_mark(mark: Mark) -> char {
    // get character from enum
    match mark {
        Mark::FreeSpace => '.',
        Mark::Cross => 'X',
        Mark::Zero => 'O',
    }
}

fn get_mark_of_char(mark: char) -> Mark {
    // reverse operation
    return match mark {
        '.' => Mark::FreeSpace,
        'X' => Mark::Cross,
        'O' => Mark::Zero,
        _ => panic!("Unrecognized character"),
    };
}

type Move = [usize; 2];
type Grid = Vec<Vec<Mark>>;

fn create_board() -> Grid {
    vec![vec![Mark::FreeSpace; TOTAL_COLUMNS]; TOTAL_ROWS]
}

fn is_valid_move(grid: &Grid, play_move: &Move) -> bool {
    let [r, c] = *play_move;
    match grid[r][c] {
        Mark::Cross | Mark::Zero => false, // already taken
        Mark::FreeSpace => true,           // free to go
    }
}

fn make_move(grid: &mut Grid, play_move: Move, mark: Mark) -> Result<(), String> {
    if !is_valid_move(&grid, &play_move) {
        return Err("Move is illegal".to_string());
    };
    let [r, c] = play_move;
    grid[r][c] = mark;
    Ok(())
}

fn set_cell(grid: &mut Grid, play_move: Move, mark: &Mark) -> () {
    let [r, c] = play_move;
    grid[r][c] = *mark;
}

fn check_winner(board: &Grid) -> Option<Mark> {
    for mark in [Mark::Cross, Mark::Zero] {
        for i in 0..TOTAL_ROWS {
            // check rows
            if board[i][0] == mark && board[i][1] == mark && board[i][2] == mark {
                return Some(mark);
            }
            // check columns
            if board[0][i] == mark && board[1][i] == mark && board[2][i] == mark {
                return Some(mark);
            }
        }
        // check diagonals
        if board[0][0] == mark && board[1][1] == mark && board[2][2] == mark {
            return Some(mark);
        }
        if board[0][2] == mark && board[1][1] == mark && board[2][0] == mark {
            return Some(mark);
        }
    }
    // no win condition found
    return None;
}

fn is_game_over(grid: &Grid) -> bool {
    if !check_winner(&grid).is_none() {
        return true;
    }
    for r in grid.iter() {
        for c in r {
            if *c == Mark::FreeSpace {
                return false;
            }
        }
    }
    return true;
}

fn get_opposite_mark(mark: &Mark) -> Mark {
    return match mark {
        Mark::Zero => Mark::Cross,
        Mark::Cross => Mark::Zero,
        Mark::FreeSpace => panic!("Free space is not The mark that has opposite value"),
    };
}

fn minimax_move_score(grid: &mut Grid, mark: Mark, max_score: i32) -> i32 {
    if is_game_over(grid) {
        let result = check_winner(&grid);
        match result {
            None => {
                // 0 if draw
                return 0;
            }
            _ => {
                // if previous player won, then return -10
                return -10;
            }
        }
    }
    let mut best_score: i32 = -200;
    for r in 0..TOTAL_ROWS {
        for c in 0..TOTAL_COLUMNS {
            if grid[r][c] == Mark::FreeSpace {
                if best_score >= max_score {
                    return best_score;
                }
                set_cell(grid, [r, c], &mark);
                let score = -minimax_move_score(grid, get_opposite_mark(&mark), -best_score);
                set_cell(grid, [r, c], &Mark::FreeSpace);
                if score > best_score {
                    best_score = score;
                }
            }
        }
    }
    return best_score;
}

fn grid_char_to_grid_mark(mut grid: Vec<Vec<char>>) -> Grid {
    let mut new_grid: Grid = create_board();
    for r in 0..TOTAL_ROWS {
        for c in 0..TOTAL_COLUMNS {
            new_grid[r][c] = get_mark_of_char(grid[r][c]);
        }
    }
    return new_grid;
}

#[pyfunction]
fn find_optimal_move_rs(mut grid: Vec<Vec<char>>, mark: char) -> Move {
    // there is specific function signature to match Python,
    // but we convert them to what's useful for us
    let mut proper_grid: Vec<Vec<Mark>> = grid_char_to_grid_mark(grid);
    let mark_enum: Mark = get_mark_of_char(mark);

    let mut best_score: i32 = -200;
    let mut play_move: Move = [100, 100];
    for r in 0..TOTAL_ROWS {
        for c in 0..TOTAL_COLUMNS {
            if proper_grid[r][c] == Mark::FreeSpace {
                set_cell(&mut proper_grid, [r, c], &mark_enum);
                let score: i32 = -minimax_move_score(
                    &mut proper_grid,
                    get_opposite_mark(&mark_enum),
                    -best_score,
                );
                set_cell(&mut proper_grid, [r, c], &Mark::FreeSpace);
                if score > best_score {
                    best_score = score;
                    play_move = [r, c];
                }
            }
        }
    }
    return play_move;
}

#[pymodule]
#[pyo3(name = "tic_tac_toe")]
fn tic_tac_toe(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(find_optimal_move_rs, m)?)?;
    Ok(())
}
