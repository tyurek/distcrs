from ssbls12 import Fp, Poly, Group
G = Group.G
GT = Group.GT
import asyncio
from player import Player
from util import SameRatioSym, SameRatioSeqSym, ProveDL, VerifyDL

                
class KZGPlayer(Player):
    @staticmethod
    def inc_crs(crs, alpha_i, public=None):
        #note: creating a new crs copy here to avoid bugs
        alphapow = 1
        newcrs = [None]*len(crs)
        for j in range(len(crs)):
            newcrs[j] = crs[j] * alphapow
            alphapow *= alpha_i
        return newcrs

    def ver_integrity(crs, public=None):
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
    def verify_chain(blockchain, public=None):
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

