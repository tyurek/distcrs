from ssbls12 import Fp, Poly, Group
G = Group.G
GT = Group.GT
import asyncio
from player import Player
from util import SameRatioSym, SameRatioSeqSym, ProveDL, VerifyDL, random_fp

                
class KZGPlayer(Player):
    def __init__(self, i, trapdoors_i, send, recv, bcfuncs, options, public=None):
        super().__init__(i, trapdoors_i, send, recv, bcfuncs, options, public)
        self.Frag = KZGFrag

    def inc_crs(crs, alpha_i, public=None):
        #note: creating a new crs copy here to avoid bugs
        alphapow = 1
        newcrs = [None]*len(crs)
        for j in range(len(crs)):
            newcrs[j] = crs[j] * alphapow
            alphapow *= alpha_i
        return newcrs

    def init_round(crs, public):
        alpha = random_fp()

    def ver_integrity(crs, public=None):
        pair = [crs[0], crs[1]]
        return SameRatioSeqSym(crs, pair)

    #verify a chain of knoledge proofs
    #here a proof is really [new g^alpha, DLProof]
    def ver_knowledge(oldcrs, newcrs, proofs):
        if proofs[-1][0] != newcrs[1]:
            print("INVALID KNOWLEDGE 1")
            return False
        lastbase = oldcrs[1]
        for proof in proofs:
            if not VerifyDL([lastbase, proof[0]], proof[1]):
                print("INVALID KNOWLEDGE 2")
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
    def verify_chain(blockchain, public=None):
        #part 1: ensure final scructure is correct
        _, lastcrs = blockchain[-1]
        if not KZGPlayer.ver_integrity(lastcrs):
            print("INTEGRITY FAILURE")
            return False
        #part 2: ensure each block was built off of the last
        for i in range(1, len(blockchain)):
            proof, crs = blockchain[i]
            _, crsold = blockchain[i-1]
            if not KZGPlayer.ver_knowledge(crsold, crs, proof):
                print("knowledge failure in block " + str(i))
                return False
        return True

def init_kzg(alpha, crslen):
    assert crslen > 1
    crs = [G]
    for i in range(crslen-1):
        crs.append(crs[-1] * alpha)
    return crs

def beacon_kzg(block):
    _, crs = block
    alpha = random_fp()
    newcrs = KZGPlayer.inc_crs(crs, alpha)
    proof = [[newcrs[1], alpha]]
    newblock = [proof, newcrs]
    return newblock

class KZGFrag():
    def __init__(self, piecenum, numpieces, value, range):
        #which piece is this
        self.piecenum = piecenum
        #how many total pieces are there
        self.numpieces = numpieces
        #actual part of the crs
        self.value = value
        #[i,j] what range of entries is represented in this fragment
        self.range = range

    def inc(self, alpha_i):
        alphapow = alpha_i ** self.range[0]
        newvalue = [None]*len(self.value)
        for j in range(len(newvalue)):
            newvalue[j] = self.value[j] * alphapow
            alphapow *= alpha_i
        return KZGFrag(self.piecenum, self.numpieces, newvalue, self.range)
    
    @staticmethod
    def join(fraglist):
        sortedfrags = sorted(fraglist, key=lambda frag: frag.piecenum)
        crs = []
        for frag in sortedfrags:
            crs += frag.value
        return crs

    @staticmethod
    def split(crs, numpieces):
        assert numpieces <= len(crs)
        fragsize = len(crs) // numpieces
        #this part is needed to make knowledge proofs less clunky. Also really, you shouldn't send these one element at a time...
        assert fragsize >= 2
        frags = [KZGFrag(i, numpieces, crs[fragsize * i: (fragsize * i) + fragsize], [fragsize * i, (fragsize * i) + fragsize]) for i in range(numpieces-1)]
        #last fragment has all the leftover pieces
        i = numpieces - 1
        frags.append(KZGFrag(i, numpieces, crs[fragsize * i:], [fragsize * i, len(crs)]))
        return frags
        


