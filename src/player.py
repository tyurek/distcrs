from abc import ABC, abstractmethod
class Player(ABC):
    def __init__(self, i, trapdoors_i, send, recv, bcfuncs, options, public=None):
        self.i = i
        self.trapdoors_i = trapdoors_i
        self.send = send
        self.recv = recv
        #todo, this might be cleaner if bcfuncs was a dict
        self.bc_len, self.bc_get_block, self.bc_post_block, self.bc_call_beacon = bcfuncs
        self.roles = options['roles']
        self.public = public

    @abstractmethod
    def inc_crs(crs, trapdoors):
        pass

    @abstractmethod
    def init_round(crs, public):
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
                self.send("self", [sender,msg])
                continue
            return msg[1:]
        
    async def run(self):
        #validator, contributor, roundstarter, roundender
        proofs, crs = await self.recv_inc()
        print("Node " + str(self.i) + " started, " + str(self.roles))
        newproofs, newcrs = proofs, crs
        if "validator" in self.roles:
            blockchain = await self.bc_get_block("ALL")
            #todo: replace with exception
            if proofs is None:
                print(self.__class__.verify_chain(blockchain, self.public))
            else:
                proposed_block = [proofs, crs]
                print(self.__class__.verify_chain(blockchain + [proposed_block], self.public))
        #simultaneous roundender and roundstarter roles is currently undefined behaviour
        if "roundstarter" in self.roles and "roundender" not in self.roles:
            #todo: add init_round func that returns trapdoors, crs
            startblock = self.__class__.init_round(crs, self.public)
            await self.bc_post_block(startblock)
        if "contributor" in self.roles:
            newcrs = self.__class__.inc_crs(crs, self.trapdoors_i, self.public)
            #todo: condense to one function
            if proofs is None:
                newproofs = self.__class__.prove_knowledge(crs, newcrs, self.trapdoors_i)
            else:
                newproofs = self.__class__.inc_knowledge_proof(proofs, self.trapdoors_i)
        #all proofs should be posted before the round ends
        if "roundender" in self.roles:
            if newproofs is not None:
                newblock = [newproofs, newcrs]
                await self.bc_post_block(newblock)
            await self.bc_call_beacon()
            newproofs = None
        #note: checkpoint role is redundant for players with the roundender role
        if "checkpoint" in self.roles:
            if newproofs is not None:
                newblock = [newproofs, newcrs]
                await self.bc_post_block(newblock)
            newproofs = None

        self.send(self.i+1, ["INC", newproofs, newcrs])
        print("Node " + str(self.i) + " finished")



            