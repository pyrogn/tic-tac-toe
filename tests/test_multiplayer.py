import pytest
import asyncio

# TODO: write tests when you will have understanding with your API

# from tic_tac_toe.multiplayer import HandleForPlayer, Multiplayer


# @pytest.fixture(scope="module")
# def multiplayer():
#     return Multiplayer()


# @pytest.mark.asyncio
# async def test_async_communication():
#     p1_queue = []
#     p2_queue = []
#     handle1 = HandleForPlayer(p1_queue, p2_queue)
#     handle2 = HandleForPlayer(p2_queue, p1_queue)
#     handle1.push_value(12)
#     assert p2_queue == [12]
#     assert p1_queue == []
#     assert await handle2.pop_value() == 12
#     assert p2_queue == []

#     handle2.push_value(34)
#     assert p1_queue == [34]
#     assert p2_queue == []
#     assert await handle1.pop_value() == 34
#     assert p1_queue == []


# # maybe add test on multiplayer attributes
# @pytest.mark.asyncio
# async def test_run_2_players():
#     multiplayer = Multiplayer()

#     async def test_player1():
#         handle = multiplayer.register_player()
#         handle.push_value(1)
#         val2 = await handle.pop_value()
#         assert val2 == 2

#     async def test_player2():
#         handle = multiplayer.register_player()
#         val1 = await handle.pop_value()
#         assert val1 == 1
#         handle.push_value(2)

#     async def test_player3():  # joined later
#         await asyncio.sleep(0.1)
#         handle = multiplayer.register_player()
#         handle.push_value(3)
#         val1 = await handle.pop_value()
#         assert val1 == 4

#     async def test_player4():
#         await asyncio.sleep(0.2)
#         handle = multiplayer.register_player()
#         val1 = await handle.pop_value()
#         assert val1 == 3
#         handle.push_value(4)

#     def make_tasks(coros: list):
#         return [asyncio.create_task(coro) for coro in coros]

#     tasks_done = make_tasks(
#         [
#             test_player1(),
#             test_player2(),
#             test_player3(),
#             test_player4(),
#         ]
#     )
#     await asyncio.wait(tasks_done)


# @pytest.mark.asyncio
# async def test_run_waiting():
#     """Will wait forever"""
#     multiplayer = Multiplayer()

#     async def test_player5():
#         handle = multiplayer.register_player()
#         handle.push_value(3)
#         val1 = await handle.pop_value()
#         assert val1 == 4

#     with pytest.raises(TimeoutError):
#         await asyncio.wait_for(asyncio.create_task(test_player5()), timeout=0.2)
