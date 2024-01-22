"""Tests for multiplayer helpers"""
import pytest
from tic_tac_toe.exceptions import NotEnoughPlayersError
from tic_tac_toe.multiplayer import Game, GamePersonalized, Multiplayer, PlayersQueue


def test_players_queue():
    """Test players queue"""
    queue = PlayersQueue()
    for elem in range(0, 100):  # queue elems
        queue.enqueue({"chat_id": elem, "message_id": elem * 1000})

    assert len(queue) == 100
    for elem in range(0, 100):  # dequeue all elems
        pop_elem = queue.dequeue()
        assert pop_elem["chat_id"] == elem
        assert pop_elem["message_id"] == elem * 1000

    queue.enqueue({"chat_id": -1, "message_id": -1})

    assert -1 in queue
    assert len(queue) == 1
    elem = queue.get(-1)
    assert elem["chat_id"] == -1 and elem["message_id"] == -1
    assert len(queue) == 1
    queue.remove(-1)
    assert len(queue) == 0


def test_startup_multiplayer():
    """Test match creation and pairing players from queue"""
    multiplayer = Multiplayer()
    assert len(multiplayer.players_queue) == 0
    multiplayer.register_player(chat_id=1, message_id=3, user_name="1")
    assert len(multiplayer.games) == 0
    assert len(multiplayer.players_queue) == 1
    with pytest.raises(NotEnoughPlayersError):
        multiplayer.register_pair()

    multiplayer.register_player(chat_id=2, message_id=4, user_name="2")
    assert len(multiplayer.players_queue) == 2
    assert len(multiplayer.games) == 0  # need to register pair

    multiplayer.register_pair()
    assert len(multiplayer.players_queue) == 0
    assert len(multiplayer.games) == 2  # two link to one game
    assert multiplayer.games[1] == multiplayer.games[2]  # same game
    assert isinstance(multiplayer.games[1], Game)  # for debug
    assert isinstance(multiplayer.get_game(1), GamePersonalized)  # will be used
    assert isinstance(multiplayer.get_game(2), GamePersonalized)

    # make sure that they do share same data, but in different attributes
    assert multiplayer.get_game(1).myself.chat_id == 1
    assert multiplayer.get_game(2).opponent.chat_id == 1
    assert multiplayer.get_game(1).opponent.chat_id == 2
    assert multiplayer.get_game(1).myself.message_id == 3
    assert multiplayer.get_game(1).opponent.message_id == 4
    assert multiplayer.get_game(1).myself.user_name == "1"

    multiplayer.remove_game(1)
    assert len(multiplayer.games) == 0
    assert len(multiplayer.players_queue) == 0
