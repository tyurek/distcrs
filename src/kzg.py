from ssbls12 import Fp, Poly, Group
G = Group.G
GT = Group.GT
import asyncio
import random
from functools import partial
from router import TestRouter
from pickle import dumps
from hashlib import sha256

def random_fp():
    return Fp(random.randint(0, Fp.p-1))

def hash_to_fp(bytestr):
    assert type(bytestr) is bytes
    return Fp(int(sha256(bytestr).hexdigest(), 16)%Fp.p)

#Check if the two pairs differ by the same exponent
#Sym suffix denotes the symmetric version of X function
def SameRatioSym(pair1, pair2):
    g1, h1, g2, h2 = pair1 + pair2
    return Group.pair(g1, h2) == Group.pair(h1, g2)

def SameRatioSeqSym(sequence, pair):
    for i in range(len(sequence)-1):
        if not SameRatioSym([sequence[i], sequence[i+1]], pair):
            return False
    return True

def ProveDL(pair, s):
    r = random_fp()
    g, h = pair
    R = g*r
    c = hash_to_fp(dumps(R))
    u = r + c*s
    return [R,u]

def VerifyDL(pair, pi):
    R, u = pi
    g, h = pair
    c = hash_to_fp(dumps(R))
    print(type(u))
    print(type(c))
    return g*u == R + h*c

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
            self.send(sender, self.blocks[blocknum])
        if msg[0] == "SET":
            self.blocks.append(msg[1])
            print(self.blocks)
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
            #if the message isn't from the blockchain, receive it again later
            if sender != 0:
                send(id, msg)
                continue
            break
        return msg
    def post_block(send, msg):
        send(0, ["SET", msg])
    get_lens = [partial(get_len, i, sends[i], recvs[i]) for i in range(n)]
    get_blocks = [partial(get_block, i, sends[i], recvs[i]) for i in range(n)]
    post_blocks = [partial(post_block, sends[i]) for i in range(n)]
    outs = [[get_lens[i], get_blocks[i], post_blocks[i]] for i in range(n)] 
    return outs

class KZGPlayer:
    def __init__(self, i, alpha_i, send, recv, bcfuncs):
        self.i = i
        self.alpha_i = alpha_i
        self.send = send
        self.recv = recv
        self.bc_len, self.bc_get_block, self.bc_post_block = bcfuncs
    async def run(self):
        while True:
            msg = await self.bc_len()
            #self.send(0, ["LEN"])
            #sender, msg = await self.recv()
            #todo add sender check
            if msg == self.i:
                #self.send(0, ["GET", self.i - 1])
                #sender, crs = await self.recv()
                crs = await self.bc_get_block(self.i-1)
                newcrs = inc_kzg(self.alpha_i)
                print(ver_integ_kzg(newcrs))
                self.bc_post_block(newcrs)
                #self.send(0, ["SET", newcrs])
                break
            await asyncio.sleep(.5)

def init_kzg(alpha, crslen):
    assert crslen > 1
    crs = [G]
    for i in range(crslen-1):
        crs.append(crs[-1] * alpha)
    return crs

def inc_kzg(alpha_i):
    #note: creating a new crs copy here to avoid bugs
    alphapow = 1
    newcrs = [None]*len(crs)
    for j in range(len(crs)):
        newcrs[j] = crs[j] * alphapow
        alphapow *= alpha_i
    return newcrs

def ver_integ_kzg(crs):
    pair = [crs[0], crs[1]]
    return SameRatioSeqSym(crs, pair)

if __name__ == "__main__":
    n = 3
    crslen = 2
    sends, recvs = get_routing(n)
    bcfuncs = gen_blockchain_funcs(sends, recvs)
    bc = Blockchain(sends[0], recvs[0])
    loop = asyncio.get_event_loop()
    #asyncio.run(bc.run())
    alphas = [random_fp() for i in range(3)]
    #assume a known alpha is used to initiate the CRS
    crs = init_kzg(alphas[0], crslen)
    sends[1](0, ["SET",crs])
    #sends[1](0, ["SET","block1"])
    #sends[1](0, ["PRINT"])
    #sends[1](0, ["BREAK"])
    bctask = loop.create_task(bc.run())
    players = [KZGPlayer(i, alphas[i], sends[i], recvs[i], bcfuncs[i]) for i in range(1,n)]
    playertasks = [loop.create_task(player.run()) for player in players]
    loop.run_forever()