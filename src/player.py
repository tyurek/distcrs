from abc import ABC, abstractmethod
class Player(ABC):
    def __init__(self, i, trapdoors_i, send, recv, bcfuncs, options=None, public=None):
        self.i = i
        self.trapdoors_i = trapdoors_i
        self.send = send
        self.recv = recv
        self.bc_len, self.bc_get_block, self.bc_post_block = bcfuncs
        if options is None:
            options = {
                'mode': 'robust',
                'role': 'checkpoint',
                'pl_thresh': None
            }
        self.role = options['role']
        self.mode = options['mode']
        self.public = public

    @abstractmethod
    def inc_crs(crs, trapdoors):
        pass

    @abstractmethod
    def ver_integrity(crs, public):
        pass

    @abstractmethod
    def ver_knowledge(oldcrs, newcrs, proofs):
        pass

    @abstractmethod
    def prove_knowledge(old_comms, new_comms, trapdoors):
        pass

    @abstractmethod
    def inc_knowledge_proof(proofs, alpha):
        pass

    @abstractmethod
    def verify_chain(blockchain, public):
        pass

    async def recv_inc(self):
        while True:
            sender, msg = await self.recv()
            if type(msg) is not list or msg[0] != "INC":
                self.send(self.i, msg)
                continue
            return msg[1:]
        
    async def run(self):
        #Beware: a round starter will ignore any info from the previous round that hasn't been posted
        if self.role == "roundstarter":
            _, __ = await self.recv_inc()
            blockchain = await self.bc_get_block("ALL")
            print(self.__class__.verify_chain(blockchain, self.public))
            crs = blockchain[-1][1]
            newcrs = self.__class__.inc_crs(crs, self.trapdoors_i)
            newproof = self.__class__.prove_knowledge(crs, newcrs, self.trapdoors_i)
            newblock = [newproof, newcrs]
            await self.bc_post_block([pi,newcrs])
            self.send(self.i+1, ["INC", None, newcrs])

        elif self.mode == 'robust':
            while True:
                msg = await self.bc_len()
                if msg == self.i:
                    _, crs = await self.bc_get_block(self.i-1)
                    #todo: wouldn't mind a cleaner way of doing this
                    newcrs = self.__class__.inc_crs(crs, self.trapdoors_i)
                    blockchain = await self.bc_get_block("ALL")
                    print(self.__class__.verify_chain(blockchain, self.public))
                    pi = self.__class__.prove_knowledge(crs, newcrs, self.trapdoors_i)
                    await self.bc_post_block([pi,newcrs])
                    break
                await asyncio.sleep(.5)

        elif self.mode == 'optimistic':
            proofs, crs = await self.recv_inc()
            newcrs = self.__class__.inc_crs(crs, self.trapdoors_i, self.public)
            if proofs is None:
                newproof = self.__class__.prove_knowledge(crs, newcrs, self.trapdoors_i)
            else:
                newproof = self.__class__.inc_knowledge_proof(proofs, self.trapdoors_i)
            if self.role == 'checkpoint':
                blockchain = await self.bc_get_block("ALL")
                newblock = [newproof, newcrs]
                print(self.__class__.verify_chain(blockchain + [newblock], self.public))
                #print(self.__class__.verify_chain([blockchain, newblock], self.public))
                await self.bc_post_block(newblock)
                self.send(self.i+1, ["INC", None, newcrs])
            elif self.role == 'passthrough':
                self.send(self.i+1, ["INC", newproof, newcrs])

            