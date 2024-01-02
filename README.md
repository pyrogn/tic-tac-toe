[![pdm-managed](https://img.shields.io/badge/pdm-managed-blueviolet)](https://pdm-project.org)

# tic-tac-toe

[Telegram-bot](https://t.me/tictactoe48573bot) (unlikely to be online)

## How to run

- `pip install .`
- `TIC_TAC_TOE_TOKEN_TG=token app`

## TODO

- [x] Write game logic (game.py)
- [x] Make tests for game (no tests for bot I think?)
- [x] Understand why grid is smaller before any move (add fix it)
- [x] Add bot logic
- [x] Understand `python-telegram-bot` architecture (`update`, `context`)
- [x] Add multiplayer
- [ ] Refactor project (single main script, readable code)
- [x] Make better exception hierarchy
- [ ] Add some description, annotations, docstrings
- [ ] Make more interesting text
- [ ] Linters

## Ideas

- Modify a game so you can rewrite or clear opponent's choice
- Make a bot with unbeatable minimax strategy
- Add inactivity checker (`context.job_queue.run_once`)
