from ssbls12 import Fp, Poly, Group
G = Group.G
GT = Group.GT
import asyncio
from functools import partial
from router import TestRouter

from babysnark1r import BabySNARK1rPlayer, init_babysnark1r
from babysnark import BabySNARKr1Player, BabySNARKr2Player, init_babysnark
from player import Player
from util import SameRatioSym, SameRatioSeqSym, ProveDL, VerifyDL
from util import random_fp, print_exception_callback

class Blockchain:
    def __init__(self, send, recv):
        self.blocks = []
        self.send = send
        self.recv = recv
    async def run(self):
        while True:
            sender, msg = await self.recv()
            self.process_msg(msg, sender)
            if msg[0] == "BREAK":
                break
    def process_msg(self, msg, sender):
        if msg[0] == "GET":
            blocknum = msg[1]
            if blocknum == "ALL":
                self.send(sender, self.blocks)
            else:
                self.send(sender, self.blocks[blocknum])
        if msg[0] == "SET":
            self.blocks.append(msg[1])
            self.send(sender, 'ACK')
            #print(self.blocks)
            print("block " + str(len(self.blocks)-1) + " posted")
        if msg[0] == "SET_NOWAIT":
            self.blocks.append(msg[1])
            #print(self.blocks)
            print("block " + str(len(self.blocks)-1) + " posted")
        if msg[0] == "LEN":
            self.send(sender, len(self.blocks))
            #print(len(self.blocks))
        if msg[0] == "PRINT":
            print(self.blocks)               
            

def get_routing(n):
    router = TestRouter(n)
    return [router.sends, router.recvs]

def gen_blockchain_funcs(sends, recvs):
    n = len(sends)
    async def get_len(id, send, recv):
        send(0, ["LEN"])
        while True:
            sender, msg = await recv()
            #if the message isn't from the blockchain, receive it again later
            #TODO: This changes who the sender is, which could be a problem (maybe add a re-receive function?)
            if sender != 0:
                send(id, msg)
                continue
            break
        return msg
    #def check_for_work(id) (maybe it can go in player?)
    async def get_block(id, send, recv, blockindex):
        send(0, ["GET", blockindex])
        while True:
            sender, msg = await recv()
            if sender != 0:
                send(id, msg)
                continue
            break
        return msg
    async def post_block(id, send, recv, msg):
        send(0, ["SET", msg])
        #wait for acknowledgement from the chain
        while True:
            sender, msg = await recv()
            if sender != 0 or msg != 'ACK':
                send(id, msg)
                continue
            break
    get_lens = [partial(get_len, i, sends[i], recvs[i]) for i in range(n)]
    get_blocks = [partial(get_block, i, sends[i], recvs[i]) for i in range(n)]
    post_blocks = [partial(post_block, i, sends[i], recvs[i]) for i in range(n)]
    outs = [[get_lens[i], get_blocks[i], post_blocks[i]] for i in range(n)] 
    return outs

                
class KZGPlayer(Player):
    @staticmethod
    def inc_crs(crs, alpha_i):
        #note: creating a new crs copy here to avoid bugs
        alphapow = 1
        newcrs = [None]*len(crs)
        for j in range(len(crs)):
            newcrs[j] = crs[j] * alphapow
            alphapow *= alpha_i
        return newcrs

    def ver_integrity(crs, public):
        pair = [crs[0], crs[1]]
        return SameRatioSeqSym(crs, pair)

    #verify a chain of knoledge proofs
    #here a proof is really [new g^alpha, DLProof]
    def ver_knowledge(oldcrs, newcrs, proofs):
        if proofs[-1][0] != newcrs[1]:
            return False
        lastbase = oldcrs[1]
        for proof in proofs:
            if not VerifyDL([lastbase, proof[0]], proof[1]):
                return False
            lastbase = proof[0]
        return True

    def prove_knowledge(oldcrs, newcrs, alpha):
        old_g_alpha, new_g_alpha = [oldcrs[1], newcrs[1]]
        #start a list of proofs (which are themselves lists) for easy appending later
        return [ [new_g_alpha, ProveDL([old_g_alpha, new_g_alpha], alpha)] ]
    
    def inc_knowledge_proof(proofs, alpha):
        old_g_alpha = proofs[-1][0]
        new_g_alpha = old_g_alpha * alpha
        proofs.append([new_g_alpha, ProveDL([old_g_alpha, new_g_alpha], alpha)])
        return proofs
    
    #This technically only needs the second element of each step along with the proofs
    #it only needs the full crs for the last step
    def verify_chain(blockchain, public):
        #part 1: ensure final scructure is correct
        _, lastcrs = blockchain[-1]
        if not KZGPlayer.ver_integrity(lastcrs):
            return False
        #part 2: ensure each block was built off of the last
        for i in range(1, len(blockchain)):
            proof, crs = blockchain[i]
            _, crsold = blockchain[i-1]
            if not KZGPlayer.ver_knowledge(crsold, crs, proof):
                return False
        return True

def init_kzg(alpha, crslen):
    assert crslen > 1
    crs = [G]
    for i in range(crslen-1):
        crs.append(crs[-1] * alpha)
    return crs


def test_one_round():
    numplayers = 9
    crslen = 5
    test = 'robust'
    test = 'optimistic'
    crstype = "KZG"
    crstype = "BabySNARK1r"
    crstype = "BabySNARK"
    
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

    if crstype == "BabySNARK":
        #generate a random alpha, gamma for each party
        trapdoors = [[random_fp() for j in range(2)] for i in range(n)]
        crs = init_babysnark(trapdoors[0], crslen)
        TestPlayer = BabySNARKr1Player
    
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
    #loop.run_forever()
    loop.run_until_complete(playertasks[-1])

def test_two_round():
    numr1players = 6
    numr2players = 6
    numpolys = 3
    crslen = 5
    test = 'robust'
    test = 'optimistic'
    crstype = "BabySNARK"
    
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
        roundstarter_options = {
            'mode': 'optimistic',
            'role': 'roundstarter',
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
        players[numr1players+1] = TestPlayer1(i, trapdoors[i], sends[i], recvs[i], bcfuncs[i], roundstarter_options, public)
        for i in range(numr1players+1, numr1players+numr2players+1):
            if i%3 == 0:
                players[i-1] = TestPlayer2(i, trapdoors[i], sends[i], recvs[i], bcfuncs[i], checkpoint_options, public)
            else:
                players[i-1] = TestPlayer2(i, trapdoors[i], sends[i], recvs[i], bcfuncs[i], passthrough_options, public)
        #send starting message to first player
        sends[0](1, ["INC", None, crs])

    if test == 'robust':
        #todo: this
        players = [TestPlayer(i, trapdoors[i], sends[i], recvs[i], bcfuncs[i]) for i in range(1,n)]

    playertasks = [loop.create_task(player.run()) for player in players]
    for task in [bctask] + playertasks:
        task.add_done_callback(print_exception_callback)
    #loop.run_forever()
    loop.run_until_complete(playertasks[-1])

if __name__ == "__main__":
    test_two_round()