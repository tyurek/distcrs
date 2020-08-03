from abc import ABC, abstractmethod

class ValidationError(Exception):
    pass

class Player(ABC):
    def __init__(self, i, trapdoors_i, send, recv, bcfuncs, options, public=None):
        self.i = i
        self.trapdoors_i = trapdoors_i
        self.send = send
        self.recv = recv
        #todo, this might be cleaner if bcfuncs was a dict
        self.bc_len, self.bc_get_block, self.bc_post_block, self.bc_call_beacon = bcfuncs
        self.roles = options['roles']
        #if 'pipelined' not in options:
        #    self.pipelined = False
        #else:
        #    self.pipelined = options['pipelined']
        self.pipelined = False if 'pipelined' not in options else options['pipelined']
        self.pl_pieces = None if 'pl_pieces' not in options else options['pl_pieces']
        self.public = public
        self.Frag = None
        self.oldfrags = []
        self.newfrags = []
        self.proofs = None

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
        print("Node " + str(self.i) + " started, " + str(self.roles))
        while True:
            if not self.pipelined:
                proofs, crs = await self.recv_inc()
                newproofs, newcrs = proofs, crs
            else:
                #todo: this could be layered more niceley with non-pipelined logic
                payload = await self.recv_inc()
                if len(payload) == 2:
                    proofs, frag = payload
                    self.proofs = proofs
                    #if we received an unfragmented CRS, fragment it and iterate on the fragments.
                    #quick and dirty way to do this is sending yourself all the fragments
                    if type(frag) is not self.Frag:
                        crs = frag
                        frags = self.Frag.split(crs, self.pl_pieces)
                        for frag in frags:
                            self.send(self.i, ["INC", frag])
                        continue
                else:
                    frag = payload[0]
                self.oldfrags.append(frag)
                fragnum = frag.piecenum
                if "contributor" in self.roles:
                    newfrag = frag.inc(self.trapdoors_i)
                    self.newfrags.append(newfrag)
                    if frag.piecenum == 0:
                        if self.proofs is None:
                            newproofs = self.__class__.prove_knowledge(frag.value, newfrag.value, self.trapdoors_i)
                        else:
                            newproofs = self.__class__.inc_knowledge_proof(self.proofs, self.trapdoors_i)
                        if "checkpoint" not in self.roles:
                            self.send(self.i+1, ["INC", newproofs, newfrag])
                        else:
                            self.send(self.i+1, ["INC", None, newfrag])
                        self.proofs = newproofs
                    else:
                        self.send(self.i+1, ["INC", newfrag])
                numfrags = frag.numpieces
                if len(self.oldfrags) < numfrags:
                    continue
                newproofs = self.proofs
                crs = self.Frag.join(self.oldfrags)
                newcrs = self.Frag.join(self.newfrags)
            
            #newproofs, newcrs = proofs, crs
            if "validator" in self.roles:
                blockchain = await self.bc_get_block("ALL")
                if proofs is None:
                    proposed_block = []
                else:
                    proposed_block = [[proofs, crs]]
                if not self.__class__.verify_chain(blockchain + proposed_block, self.public):
                    raise ValidationError
            #simultaneous roundender and roundstarter roles is currently undefined behaviour
            if "roundstarter" in self.roles and "roundender" not in self.roles:
                beaconblock = await self.bc_get_block(-1)
                _, crs = beaconblock
                startblock = self.__class__.init_round(crs, self.public)
                await self.bc_post_block(startblock)
                _, crs = startblock
                proofs = None
            if "contributor" in self.roles and not self.pipelined:
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
                newcrs = None
            #note: checkpoint role is redundant for players with the roundender role
            if "checkpoint" in self.roles:
                if newproofs is not None:
                    newblock = [newproofs, newcrs]
                    #print("publishing " + str(len(newproofs)) + " proofs!")
                    await self.bc_post_block(newblock)
                newproofs = None
            #pipeline logic will need to be improved in order to be generalizable. Kind of a hack right now
            if not self.pipelined:
                self.send(self.i+1, ["INC", newproofs, newcrs])
            print("Node " + str(self.i) + " finished")
            break

            