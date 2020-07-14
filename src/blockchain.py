import asyncio
from functools import partial

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