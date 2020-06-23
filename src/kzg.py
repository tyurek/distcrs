#from ssbls12 import Fp, Poly, Group
#G = Group.G
#GT = Group.GT
import asyncio
from router import TestRouter


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
        if msg[0] == "PRINT":
            print(self.blocks)


def get_routing(n):
    router = TestRouter(n)
    return [router.sends, router.recvs]


if __name__ == "__main__":
    n = 3
    sends, recvs = get_routing(n)
    bc = Blockchain(sends[0], recvs[0])
    loop = asyncio.get_event_loop()
    #asyncio.run(bc.run())
    #task = loop.create_task(bc.run())
    sends[1](0, ["SET","block0"])
    sends[1](0, ["SET","block1"])
    sends[1](0, ["PRINT"])
    sends[1](0, ["BREAK"])
    #asyncio.gather(task)
    loop.run_until_complete(bc.run())
    #task.cancel()