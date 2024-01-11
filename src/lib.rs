#![allow(unused)]

use pyo3::prelude::*;

const FREE_SPACE: char = '.';
const CROSS: char = 'X';
const ZERO: char = 'O';

const TOTAL_ROWS: usize = 3;
const TOTAL_COLUMNS: usize = 3;
const MAX_FILL: usize = TOTAL_ROWS * TOTAL_COLUMNS;

type Move = [usize; 2];
type Grid = Vec<Vec<char>>;
type Mark = char; // TODO: can I make it more constrained? like enum, struct or union?

fn create_board() -> Grid {
    vec![vec![FREE_SPACE; TOTAL_COLUMNS]; TOTAL_ROWS]
}

fn is_valid_move(grid: &Grid, play_move: &Move) -> Result<bool, String> {
    let [r, c] = play_move;
    match grid[*r][*c] {
        CROSS | ZERO => Ok(false),
        FREE_SPACE => Ok(true),
        _ => Err("Bad mark in the grid".to_string()),
    }
}

fn make_move(grid: &mut Grid, play_move: Move, mark: Mark) -> Result<(), String> {
    is_valid_move(&grid, &play_move)?;
    let [r, c] = play_move;
    grid[r][c] = mark;
    Ok(())
}

fn set_cell(grid: &mut Grid, play_move: Move, mark: Mark) -> () {
    let [r, c] = play_move;
    grid[r][c] = mark;
}

fn check_winner(board: &Grid) -> Option<Mark> {
    for mark in [CROSS, ZERO] {
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
            if *c == FREE_SPACE {
                return false;
            }
        }
    }
    return true;
}

fn get_opposite_mark(mark: Mark) -> Mark {
    return match mark {
        ZERO => CROSS,
        CROSS => ZERO,
        _ => panic!("EEEError some bogus mark, delete this after"),
    };
}

fn print_2d_vec(grid: Grid) -> () {
    grid.into_iter().for_each(|it| {
        println!("{:?}", it);
    })
}

fn minimax_move_score(grid: &mut Grid, mark: Mark, max_score: i32, depth: u8) -> i32 {
    // println!("{}", depth);
    // print_2d_vec(grid.to_vec());
    if is_game_over(grid) {
        let result = check_winner(&grid);
        // print!("{result:?}");
        let opposite_mark = get_opposite_mark(mark);
        match result {
            None => {
                // println!("draw");
                return 0;
            }
            Some(mark) => {
                // println!("win, {mark} {result:?}");
                return -10;
            }
            Some(opposite_mark) => {
                // println!("lose");
                return 10;
            }
            _ => {
                // println!("something else");
            }
        }
    }
    let mut best_score = -200;
    for r in 0..TOTAL_ROWS {
        for c in 0..TOTAL_COLUMNS {
            if grid[r][c] == FREE_SPACE {
                if best_score >= max_score {
                    return best_score;
                }
                set_cell(grid, [r, c], mark);
                let score =
                    -minimax_move_score(grid, get_opposite_mark(mark), -best_score, depth + 1);
                set_cell(grid, [r, c], FREE_SPACE);
                if score > best_score {
                    best_score = score;
                }
            }
        }
    }
    // println!("{} {}", mark, best_score);
    return best_score;
}

#[pyfunction]
fn find_optimal_move_rs(mut grid: Grid, mark: Mark) -> Move {
    let mut best_score = -200;
    let mut play_move: Move = [100, 100];
    for r in 0..TOTAL_ROWS {
        for c in 0..TOTAL_COLUMNS {
            if grid[r][c] == FREE_SPACE {
                set_cell(&mut grid, [r, c], mark);
                let score = -minimax_move_score(&mut grid, get_opposite_mark(mark), -best_score, 0);
                set_cell(&mut grid, [r, c], FREE_SPACE);
                if score > best_score {
                    // println!("{} {} {:?}", mark, score, [r, c]);
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
    // m.add_function(wrap_pyfunction!(ai_best_move, m)?)?;
    Ok(())
}

// fn main() {
//     let mut grid = create_board();
//     make_move(&mut grid, [0, 0], CROSS);
//     make_move(&mut grid, [2, 2], ZERO);
//     make_move(&mut grid, [0, 1], CROSS);
//     // make_move(&mut grid, [0, 1], CROSS);
//     // make_move(&mut grid, [2, 1], ZERO);
//     let play_move = find_optimal_move(grid, CROSS);
//     println!("{:?}", play_move);
//     // println!("{:?}", play_move);
// }
