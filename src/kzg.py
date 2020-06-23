#from ssbls12 import Fp, Poly, Group
#G = Group.G
#GT = Group.GT
import asyncio
from router import TestRouter

#def random_fp():
#    return Fp(random.randint(0, Fp.p-1))

class Blockchain:
    def __init__(self, send, recv):
        self.blocks = []
        self.send = send
        self.recv = recv
    async def run(self):
        while True:
            sender, msg = await self.recv()
            await self.process_msg(msg, sender)
            if msg[0] == "BREAK":
                break
    async def process_msg(self, msg, sender):
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

class KZGPlayer:
    def __init__(self, i, alpha_i, send, recv):
        self.i = i
        self.alpha_i = alpha_i
        self.send = send
        self.recv = recv
    async def run(self):
        while True:
            self.send(0, ["LEN"])
            sender, msg = await self.recv()
            #todo add sender check
            if msg == self.i:
                self.send(0, ["GET", self.i - 1])
                sender, crs = await self.recv()
                alphapow = 1
                print(len(crs))
                for j in range(len(crs)):
                    crs[j] *= alphapow
                    alphapow *= self.alpha_i
                self.send(0, ["SET", crs])
                break
            await asyncio.sleep(.5)
                
            

def get_routing(n):
    router = TestRouter(n)
    return [router.sends, router.recvs]


if __name__ == "__main__":
    n = 3
    sends, recvs = get_routing(n)
    bc = Blockchain(sends[0], recvs[0])
    loop = asyncio.get_event_loop()
    #asyncio.run(bc.run())
    alphas = [2,4,16]
    crs = [1,1,1]
    sends[1](0, ["SET",alphas])
    #sends[1](0, ["SET","block1"])
    #sends[1](0, ["PRINT"])
    #sends[1](0, ["BREAK"])
    bctask = loop.create_task(bc.run())
    players = [KZGPlayer(i, alphas[i], sends[i], recvs[i]) for i in range(1,n)]
    playertasks = [loop.create_task(players[i-1].run()) for i in range(1,n)]
    #asyncio.gather(task)
    #loop.run_until_complete(bc.run())
    #task.cancel()
    #await asyncio.gather(bctask + playertasks)
    #sleep(3)
    #sends[1](0, ["LEN"])
    loop.run_forever()