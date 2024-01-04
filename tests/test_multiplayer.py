"""Tests for multiplayer helpers"""
import pytest
from tic_tac_toe.exceptions import NotEnoughPlayersError
from tic_tac_toe.multiplayer import GamePersonalized, Multiplayer


def test_startup_multiplayer():
    """Test match creation and pairing players from queue"""
    multiplayer = Multiplayer()
    multiplayer.register_player(chat_id=1, message_id=3, user_name="1")
    assert len(multiplayer.games) == 0
    with pytest.raises(NotEnoughPlayersError):
        multiplayer.register_pair()

    multiplayer.register_player(chat_id=2, message_id=4, user_name="2")
    assert len(multiplayer.games) == 0  # need to register pair

    multiplayer.register_pair()
    assert len(multiplayer.games) == 2  # two link to one game
    assert multiplayer.games[1] == multiplayer.games[2]
    assert isinstance(multiplayer.get_game(1), GamePersonalized)
    assert isinstance(multiplayer.get_game(2), GamePersonalized)

    assert multiplayer.get_game(1).myself.chat_id == 1
    assert multiplayer.get_game(2).opponent.chat_id == 1
    assert multiplayer.get_game(1).opponent.chat_id == 2
    assert multiplayer.get_game(1).myself.message_id == 3
    assert multiplayer.get_game(1).opponent.message_id == 4
    assert multiplayer.get_game(1).myself.user_name == "1"

    multiplayer.remove_game(1)
    assert len(multiplayer.games) == 0
