from util import random_fp, print_exception_callback
from ssbls12 import Fp, Poly, Group
G = Group.G
GT = Group.GT
import asyncio
from functools import partial
from router import TestRouter, get_routing
from blockchain import Blockchain, gen_blockchain_funcs
from babysnark1r import BabySNARK1rPlayer, init_babysnark1r
from babysnark import BabySNARKr1Player, BabySNARKr2Player, init_babysnark
from kzg import KZGPlayer, init_kzg
from pytest import mark

@mark.parametrize("crstype", ["KZG", "BabySNARK1r"])
def test_one_round(crstype):
    numplayers = 9
    crslen = 5
    test = 'robust'
    test = 'optimistic'
    
    n = numplayers+1
    sends, recvs = get_routing(n)
    bcfuncs = gen_blockchain_funcs(sends, recvs)
    bc = Blockchain(sends[0], recvs[0])
    loop = asyncio.get_event_loop()

    if crstype == "KZG":
        trapdoors = [random_fp() for i in range(n)]
        #assume a known alpha is used to initiate the CRS
        crs = init_kzg(trapdoors[0], crslen)
        TestPlayer = KZGPlayer
    
    if crstype == "BabySNARK1r":
        #generate a random alpha, beta, gamma for each party
        trapdoors = [[random_fp() for j in range(3)] for i in range(n)]
        crs = init_babysnark1r(trapdoors[0], crslen)
        TestPlayer = BabySNARK1rPlayer
    
    #A proof is unnecessary for the first block as trapdoors are public
    pi = None
    #set the original CRS
    sends[0](0, ["SET_NOWAIT",[pi, crs]])
    bctask = loop.create_task(bc.run())

    if test == 'optimistic':
        checkpoint_options = {
            'mode': 'optimistic',
            'role': 'checkpoint',
            'pl_thresh': None
        }
        passthrough_options = {
            'mode': 'optimistic',
            'role': 'passthrough',
            'pl_thresh': None
        }
        players = [None] * numplayers
        for i in range(1,n):
            #make every third player a "checkpoint" (player that posts progress to the blockchain)
            if i%3 == 0:
                players[i-1] = TestPlayer(i, trapdoors[i], sends[i], recvs[i], bcfuncs[i], checkpoint_options)
            else:
                players[i-1] = TestPlayer(i, trapdoors[i], sends[i], recvs[i], bcfuncs[i], passthrough_options)
        #send starting message to first player
        sends[0](1, ["INC", None, crs])

    if test == 'robust':
        players = [TestPlayer(i, trapdoors[i], sends[i], recvs[i], bcfuncs[i]) for i in range(1,n)]

    playertasks = [loop.create_task(player.run()) for player in players]
    for task in [bctask] + playertasks:
        task.add_done_callback(print_exception_callback)
    loop.run_until_complete(playertasks[-1])
    get_block = bcfuncs[1][1]
    mytask = loop.create_task(get_block("ALL"))
    blocks = loop.run_until_complete(mytask)
    assert TestPlayer.verify_chain(blocks, public = None)
    bctask.cancel()

@mark.parametrize("crstype", ["BabySNARK"])
def test_two_round(crstype):
    numr1players = 6
    numr2players = 6
    numpolys = 3
    crslen = 5
    test = 'robust'
    test = 'optimistic'
    
    n = numr1players+numr2players+1
    sends, recvs = get_routing(n)
    bcfuncs = gen_blockchain_funcs(sends, recvs)
    bc = Blockchain(sends[0], recvs[0])
    loop = asyncio.get_event_loop()
    public = {}

    if crstype == "BabySNARK":
        #generate a random alpha, gamma for each party
        trapdoors1 = [[random_fp() for j in range(2)] for i in range(numr1players+1)]
        #generate a random beta for round 2 players
        trapdoors2 = [random_fp() for i in range(numr2players)]
        trapdoors = trapdoors1 + trapdoors2
        polys = [Poly([random_fp() for j in range(crslen)]) for i in range(numpolys)]
        public['polys'] = polys
        crs = init_babysnark(trapdoors[0], crslen)
        TestPlayer1 = BabySNARKr1Player
        TestPlayer2 = BabySNARKr2Player
    
    #A proof is unnecessary for the first block as trapdoors are public
    pi = None
    #set the original CRS
    sends[0](0, ["SET_NOWAIT",[pi, crs]])
    bctask = loop.create_task(bc.run())


    roundstarter_options = {
        'mode': "N/A",
        'role': 'roundstarter',
        'pl_thresh': None
    }
    if test == 'optimistic':
        checkpoint_options = {
            'mode': 'optimistic',
            'role': 'checkpoint',
            'pl_thresh': None
        }
        passthrough_options = {
            'mode': 'optimistic',
            'role': 'passthrough',
            'pl_thresh': None
        }
        players = [None] * (numr1players + numr2players)
        for i in range(1,numr1players+1):
            #make every third player a "checkpoint" (player that posts progress to the blockchain)
            if i%3 == 0:
                players[i-1] = TestPlayer1(i, trapdoors[i], sends[i], recvs[i], bcfuncs[i], checkpoint_options)
            else:
                players[i-1] = TestPlayer1(i, trapdoors[i], sends[i], recvs[i], bcfuncs[i], passthrough_options)
        i = numr1players
        players[numr1players+1] = TestPlayer2(i, trapdoors[i], sends[i], recvs[i], bcfuncs[i], roundstarter_options, public)
        for i in range(numr1players+1, numr1players+numr2players+1):
            if i%3 == 0:
                players[i-1] = TestPlayer2(i, trapdoors[i], sends[i], recvs[i], bcfuncs[i], checkpoint_options, public)
            else:
                players[i-1] = TestPlayer2(i, trapdoors[i], sends[i], recvs[i], bcfuncs[i], passthrough_options, public)
        #send starting message to first player
        sends[0](1, ["INC", None, crs])

    if test == 'robust':
        #todo: fix this
        robust_options = {
            'mode': 'robust',
            'role': 'N/A',
            'pl_thresh': None
        }
        players = [None] * (numr1players + numr2players)
        for i in range(1,numr1players+1):
            players[i-1] = TestPlayer1(i, trapdoors[i], sends[i], recvs[i], bcfuncs[i], robust_options)
        i = numr1players
        players[numr1players+1] = TestPlayer2(i, trapdoors[i], sends[i], recvs[i], bcfuncs[i], roundstarter_options, public)
        for i in range(numr1players+1, numr1players+numr2players+1):
            players[i-1] = TestPlayer2(i, trapdoors[i], sends[i], recvs[i], bcfuncs[i], robust_options, public)

    playertasks = [loop.create_task(player.run()) for player in players]
    for task in [bctask] + playertasks:
        task.add_done_callback(print_exception_callback)
    loop.run_until_complete(playertasks[-1])
    get_block = bcfuncs[1][1]
    mytask = loop.create_task(get_block("ALL"))
    blocks = loop.run_until_complete(mytask)
    assert TestPlayer2.verify_chain(blocks, public)
    bctask.cancel()

if __name__ == "__main__":
    #if you want to debug any tests, just run them here
    test_one_round("KZG")
    #test_two_round("BabySNARK")
    pass