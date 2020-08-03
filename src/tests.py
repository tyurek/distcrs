from util import random_fp, print_exception_callback
from ssbls12 import Fp, Poly, Group
G = Group.G
GT = Group.GT
import asyncio
import pytest
from functools import partial
from router import get_routing
from blockchain import Blockchain, gen_blockchain_funcs
from SRS.babysnark1r import BabySNARK1rPlayer, init_babysnark1r
from SRS.babysnark import BabySNARKr1Player, BabySNARKr2Player, init_babysnark, beacon_babysnark
from SRS.kzg import KZGPlayer, init_kzg, beacon_kzg
from pytest import mark
from player import ValidationError


@mark.parametrize("crstype", ["KZG"])
def test_one_round(crstype):
    numplayers = 9
    crslen = 5
    
    n = numplayers+1
    sends, recvs = get_routing(n)
    bcfuncs = gen_blockchain_funcs(sends, recvs)
    loop = asyncio.get_event_loop()

    if crstype == "KZG":
        trapdoors = [random_fp() for i in range(n)]
        #assume a known alpha is used to initiate the CRS
        crs = init_kzg(trapdoors[0], crslen)
        TestPlayer = KZGPlayer
        bc = Blockchain(sends[0], recvs[0], beacon=beacon_kzg)
    
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
    mysleep = loop.create_task(asyncio.sleep(.5))
    loop.run_until_complete(mysleep)

    options = [{'roles' : ['contributor']} for i in range(numplayers)]
    players = [TestPlayer(i, trapdoors[i], sends[i], recvs[i], bcfuncs[i], options[i-1]) for i in range(1,n)]
    for i in range(3, numplayers, 3):
        players[i].roles += ["checkpoint"]
    players[numplayers // 2].roles += ["validator"]
    players[-1].roles += ["roundender"]
    #send starting message to first player
    sends[0](1, ["INC", None, crs])

    playertasks = [loop.create_task(player.run()) for player in players]
    for task in [bctask] + playertasks:
        task.add_done_callback(print_exception_callback)
    loop.run_until_complete(playertasks[-1])
    get_block = bcfuncs[1][1]
    mytask = loop.create_task(get_block("ALL"))
    blocks = loop.run_until_complete(mytask)
    assert TestPlayer.verify_chain(blocks, public = None)
    bctask.cancel()

@mark.parametrize("crstype", ["KZG"])
def test_pipeline(crstype):
    numplayers = 9
    crslen = 5
    
    n = numplayers+1
    sends, recvs = get_routing(n)
    bcfuncs = gen_blockchain_funcs(sends, recvs)
    loop = asyncio.get_event_loop()

    if crstype == "KZG":
        trapdoors = [random_fp() for i in range(n)]
        #assume a known alpha is used to initiate the CRS
        crs = init_kzg(trapdoors[0], crslen)
        TestPlayer = KZGPlayer
        bc = Blockchain(sends[0], recvs[0], beacon=beacon_kzg)
    
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
    mysleep = loop.create_task(asyncio.sleep(.5))
    loop.run_until_complete(mysleep)

    options = [{'roles': ['contributor'], 'pipelined': True, 'pl_pieces': 2} for i in range(numplayers)]
    players = [TestPlayer(i, trapdoors[i], sends[i], recvs[i], bcfuncs[i], options[i-1]) for i in range(1,n)]
    for i in range(3, numplayers, 3):
        players[i].roles += ["checkpoint"]
    players[numplayers // 2].roles += ["validator"]
    players[-1].roles += ["roundender"]
    #send starting message to first player
    sends[0](1, ["INC", None, crs])

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

    n = numr1players+numr2players+1
    numplayers = n-1
    sends, recvs = get_routing(n)
    bcfuncs = gen_blockchain_funcs(sends, recvs)
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
        bc = Blockchain(sends[0], recvs[0], beacon=beacon_babysnark)
    
    #A proof is unnecessary for the first block as trapdoors are public
    pi = None
    #set the original CRS
    sends[0](0, ["SET_NOWAIT",[pi, crs]])
    bctask = loop.create_task(bc.run())
    mysleep = loop.create_task(asyncio.sleep(.5))
    loop.run_until_complete(mysleep)

    options = [{'roles' : ['contributor']} for i in range(numplayers)]
    players = [None] * numplayers
    r1players = [TestPlayer1(i, trapdoors[i], sends[i], recvs[i], bcfuncs[i], options[i-1]) for i in range(1,numr1players+1)]
    r2players = [TestPlayer2(i, trapdoors[i], sends[i], recvs[i], bcfuncs[i], options[i-1], public) for i in range(numr1players+1,numplayers+1)]
    r1players[numr1players // 2].roles += ["validator"]
    r2players[numr2players // 2].roles += ["validator"]
    r2players[0].roles += ["roundstarter"]
    r1players[-1].roles += ["roundender"]
    r2players[-1].roles += ["roundender"]
    players = r1players + r2players
    for i in range(3, numplayers, 3):
        players[i].roles += ["checkpoint"]
    
    #send starting message to first player
    sends[0](1, ["INC", None, crs])
    playertasks = [loop.create_task(player.run()) for player in players]
    for task in [bctask] + playertasks:
        task.add_done_callback(print_exception_callback)
    loop.run_until_complete(playertasks[-1])
    get_block = bcfuncs[1][1]
    mytask = loop.create_task(get_block("ALL"))
    blocks = loop.run_until_complete(mytask)
    assert TestPlayer2.verify_chain(blocks, public)
    bctask.cancel()

def test_kzg_error():
    numplayers = 9
    crslen = 5
    
    n = numplayers+1
    sends, recvs = get_routing(n)
    bcfuncs = gen_blockchain_funcs(sends, recvs)
    loop = asyncio.get_event_loop()

    trapdoors = [random_fp() for i in range(n)]
    #assume a known alpha is used to initiate the CRS
    crs = init_kzg(trapdoors[0], crslen)
    TestPlayer = KZGPlayer
    bc = Blockchain(sends[0], recvs[0], beacon=beacon_kzg)
    
    #A proof is unnecessary for the first block as trapdoors are public
    pi = None
    #set the original CRS
    sends[0](0, ["SET_NOWAIT",[pi, crs]])
    bctask = loop.create_task(bc.run())
    mysleep = loop.create_task(asyncio.sleep(.5))
    loop.run_until_complete(mysleep)

    class MaliciousKZG(KZGPlayer):
        def inc_crs(crs, alpha_i, public=None):
            alphapow = 2
            newcrs = [None]*len(crs)
            for j in range(len(crs)):
                newcrs[j] = crs[j] * alphapow 
                alphapow *= alpha_i
            return newcrs

    options = [{'roles' : ['contributor']} for i in range(numplayers)]
    players = [TestPlayer(i, trapdoors[i], sends[i], recvs[i], bcfuncs[i], options[i-1]) for i in range(1,n)]
    players[1] = MaliciousKZG(2, trapdoors[2], sends[2], recvs[2], bcfuncs[2], options[1])
    for i in range(3, numplayers, 3):
        players[i].roles += ["checkpoint"]
    players[numplayers // 2].roles += ["validator"]
    players[-1].roles += ["roundender"]
    #send starting message to first player
    sends[0](1, ["INC", None, crs])

    playertasks = [loop.create_task(player.run()) for player in players]
    for task in [bctask] + playertasks:
        task.add_done_callback(print_exception_callback)
    #pass iff the validator node throws a validation error
    with pytest.raises(ValidationError):
        loop.run_until_complete(playertasks[numplayers // 2])
    _ = [t.cancel() for t in playertasks]
    bctask.cancel()

if __name__ == "__main__":
    #if you want to debug any tests, just run them here
    #test_one_round("KZG")
    #test_two_round("BabySNARK")
    test_pipeline("KZG")
    pass