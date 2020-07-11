from player import Player
from ssbls12 import Fp, Poly, Group
from util import SameRatioSym, SameRatioSeqSym, ProveDL, VerifyDL
G = Group.G

class BabySNARK1rPlayer(Player):
    @staticmethod
    def inc_crs(crs, trapdoors_i):
        #note: creating a new crs copy here to avoid bugs
        g_gamma, g_gammabeta, kzg, bkzg = crs
        alpha_i, beta_i, gamma_i = trapdoors_i
        alphapow = 1
        newkzg = [None]*len(kzg)
        newbkzg = [None]*len(kzg)
        for j in range(len(kzg)):
            newkzg[j] = kzg[j] * alphapow
            newbkzg[j] = bkzg[j] * (alphapow * beta_i)
            alphapow *= alpha_i
        return [g_gamma * gamma_i, g_gammabeta * (gamma_i * beta_i), newkzg, newbkzg]

    def ver_integrity(crs):
        g_gamma, g_gammabeta, kzg, bkzg = crs
        alpha_pair = [G, kzg[1]]
        beta_pair = [G, bkzg[0]]
        out = SameRatioSeqSym(kzg, alpha_pair)
        out &= SameRatioSym([g_gamma, g_gammabeta], beta_pair)
        out &= SameRatioSym([kzg[1], bkzg[1]], beta_pair)
        out &= SameRatioSeqSym(bkzg, alpha_pair)
        return out

    #verify a chain of knoledge proofs
    #here a proof is really [[new g^alpha, new g^beta, new g^gamma], DLProofs]
    def ver_knowledge(oldcrs, newcrs, proofs):
        if proofs[-1][0] != [newcrs[2][1], newcrs[3][0], newcrs[0]]:
            return False
        lastbases = [oldcrs[2][1], oldcrs[3][0], oldcrs[0]]
        for proof in proofs:
            for i in range(3):
                if not VerifyDL([lastbases[i], proof[0][i]], proof[1][i]):
                    return False
            lastbases = proof[0]
        return True

    def prove_knowledge(oldcrs, newcrs, trapdoors_i):
        old_comms = [oldcrs[2][1], oldcrs[3][0], oldcrs[0]]
        new_comms = [newcrs[2][1], newcrs[3][0], newcrs[0]]
        #alpha_i, beta_i, gamma_i = trapdoors_i
        DLProofs = [ProveDL([old_comms[i], new_comms[i]], trapdoors_i[i]) for i in range(3)]
        #start a list of proofs (which are themselves lists) for easy appending later
        return [ [new_comms, DLProofs] ]
    
    def inc_knowledge_proof(proofs, trapdoors_i):
        old_comms = proofs[-1][0]
        old_g_alpha, old_g_beta, old_g_gamma = old_comms
        alpha_i, beta_i, gamma_i = trapdoors_i

        new_g_alpha = old_g_alpha * alpha_i
        new_g_beta = old_g_beta * beta_i
        new_g_gamma = old_g_gamma * gamma_i
        new_comms = [new_g_alpha, new_g_beta, new_g_gamma]

        DLProofs = [ProveDL([old_comms[i], new_comms[i]], trapdoors_i[i]) for i in range(3)]
        proofs.append([new_comms, DLProofs])
        return proofs
    
    #This technically only needs the second element of each step along with the proofs
    #it only needs the full crs for the last step
    def verify_chain(blockchain, public):
        #part 1: ensure final scructure is correct
        _, lastcrs = blockchain[-1]
        if not BabySNARK1rPlayer.ver_integrity(lastcrs):
            return False
        #part 2: ensure each block was built off of the last
        for i in range(1, len(blockchain)):
            proof, crs = blockchain[i]
            _, crsold = blockchain[i-1]
            if not BabySNARK1rPlayer.ver_knowledge(crsold, crs, proof):
                return False
        return True

def init_babysnark1r(trapdoors, crslen):
    alpha, beta, gamma = trapdoors
    assert crslen > 1
    kzg = [G]
    bkzg = [G * beta]
    for i in range(crslen-1):
        kzg.append(kzg[-1] * alpha)
        bkzg.append(bkzg[-1] * alpha)
    crs = [G * gamma, G * (gamma*beta), kzg, bkzg]
    return crs