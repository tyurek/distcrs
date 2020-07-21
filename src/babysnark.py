from player import Player
from ssbls12 import Fp, Poly, Group
from util import SameRatioSym, SameRatioSeqSym, ProveDL, VerifyDL, ExpEval, DLProof, random_fp
G = Group.G

class BabySNARKr1Player(Player):
    def inc_crs(crs, trapdoors_i, public=None):
        #note: creating a new crs copy here to avoid bugs
        g_gamma, kzg = crs
        alpha_i, gamma_i = trapdoors_i
        alphapow = 1
        newkzg = [None]*len(kzg)
        for j in range(len(kzg)):
            newkzg[j] = kzg[j] * alphapow
            alphapow *= alpha_i
        return [g_gamma * gamma_i, newkzg]
    def init_round(crs, public):
        pass
    def ver_integrity(crs):
        g_gamma, kzg = crs
        alpha_pair = [G, kzg[1]]
        gamma_pair = [G, g_gamma]
        out = SameRatioSeqSym(kzg, alpha_pair)
        out &= SameRatioSym([G, g_gamma], gamma_pair)
        return out

    #verify a chain of knoledge proofs
    #here a proof is really [[new g^alpha new g^gamma], DLProofs]
    def ver_knowledge(oldcrs, newcrs, proofs):
        if proofs[-1][0] != [newcrs[1][1], newcrs[0]]:
            return False
        lastbases = [oldcrs[1][1], oldcrs[0]]
        for proof in proofs:
            for i in range(2):
                if not VerifyDL([lastbases[i], proof[0][i]], proof[1][i]):
                    return False
            lastbases = proof[0]
        return True

    def prove_knowledge(oldcrs, newcrs, trapdoors_i):
        old_comms = [oldcrs[1][1], oldcrs[0]]
        new_comms = [newcrs[1][1], newcrs[0]]
        #alpha_i, gamma_i = trapdoors_i
        DLProofs = [ProveDL([old_comms[i], new_comms[i]], trapdoors_i[i]) for i in range(2)]
        #start a list of proofs (which are themselves lists) for easy appending later
        return [ [new_comms, DLProofs] ]
    
    def inc_knowledge_proof(proofs, trapdoors_i):
        old_comms = proofs[-1][0]
        old_g_alpha, old_g_gamma = old_comms
        alpha_i, gamma_i = trapdoors_i

        new_g_alpha = old_g_alpha * alpha_i
        new_g_gamma = old_g_gamma * gamma_i
        new_comms = [new_g_alpha, new_g_gamma]

        DLProofs = [ProveDL([old_comms[i], new_comms[i]], trapdoors_i[i]) for i in range(2)]
        proofs.append([new_comms, DLProofs])
        return proofs
    
    #This technically only needs the second element of each step along with the proofs
    #it only needs the full crs for the last step
    def verify_chain(blockchain, public):
        #part 1: ensure final scructure is correct
        _, lastcrs = blockchain[-1]
        if not BabySNARKr1Player.ver_integrity(lastcrs):
            return False
        #part 2: ensure each block was built off of the last
        for i in range(1, len(blockchain)):
            proof, crs = blockchain[i]
            _, crsold = blockchain[i-1]
            if not BabySNARKr1Player.ver_knowledge(crsold, crs, proof):
                return False
        return True


class BabySNARKr2Player(Player):
    def inc_crs(crs, beta_i, public=None):
        if len(crs) == 2:
            polys = public["polys"]
            g_gamma, kzg = crs
            newg_gammabeta = g_gamma * beta_i
            newg_betapolys = []
            for poly in polys:
                newg_betapolys.append(ExpEval(poly, kzg) * beta_i)
        else:
            g_gamma, kzg, g_gammabeta, g_betapolys = crs
            newg_gammabeta = g_gammabeta * beta_i
            newg_betapolys = [ele * beta_i for ele in g_betapolys]
        return [g_gamma, kzg, newg_gammabeta, newg_betapolys]

    def init_round(crs, public):
        beta = random_fp()
        newcrs = BabySNARKr2Player.inc_crs(crs, beta, public)
        proof = [[newcrs[2], beta]]
        return [proof, newcrs]

    def ver_integrity(crs, public):
        def ver_r1(g_gamma, kzg):
            alpha_pair = [G, kzg[1]]
            gamma_pair = [G, g_gamma]
            out = SameRatioSeqSym(kzg, alpha_pair)
            out &= SameRatioSym([G, g_gamma], gamma_pair)
            return out
        
        def ver_r2(g_gamma, kzg, g_gammabeta, g_betapolys, polys):
            g_polys = [ExpEval(poly, kzg) for poly in polys]
            out = True
            for i in range(len(polys)):
                 out &= SameRatioSym([g_gamma, g_gammabeta],[g_polys[i], g_betapolys[i]])
            return out
        if len(crs) == 2:
            g_gamma, kzg = crs
            return ver_r1(g_gamma, kzg)
        else:
            g_gamma, kzg, g_gammabeta, g_betapolys = crs
            out = ver_r1(g_gamma, kzg)
            return out & ver_r2(g_gamma, kzg, g_gammabeta, g_betapolys, public["polys"])
        

    #verify a chain of knowledge proofs
    #here a proof could be [[new g^alpha new g^gamma], DLProofs]
    # or [new g^gammabeta, DLProof]
    def ver_knowledge(oldcrs, newcrs, proofs):
        #assert that last R1 block is from the beacon if necessary
        #todo, wrong condition
        if len(oldcrs) == 4 and len(newcrs) == 2:
            alpha, beta = proofs[-1][1]
            if type(alpha) is not Fp or type(beta) is not Fp:
                return False
        lastproof_comms = proofs[-1][0]
        #if chain is entirely R1 proofs
        if len(newcrs) == 2 or type(lastproof_comms) is list:
            if proofs[-1][0] != [newcrs[1][1], newcrs[0]]:
                return False
            lastbases = [oldcrs[1][1], oldcrs[0]]
            for proof in proofs:
                for i in range(2):
                    if not VerifyDL([lastbases[i], proof[0][i]], proof[1][i]):
                        return False
                lastbases = proof[0]
        #if chain is entirely R2 proofs
        else:
            if proofs[-1][0] != newcrs[2]:
                print("endpoint failure")
                return False
            if len(oldcrs) == 2:
                lastbase = oldcrs[0]
            else:
                lastbase = oldcrs[2]
            for proof in proofs:
                if not VerifyDL([lastbase, proof[0]], proof[1]):
                    print("verifyDL failure")
                    return False
                lastbase = proof[0]
        return True

    def prove_knowledge(oldcrs, newcrs, beta_i):
        if len(oldcrs) == 2:
            old_comm = oldcrs[0]
        else:
            old_comm = oldcrs[2]
        new_comm = newcrs[2]
        #alpha_i, gamma_i = trapdoors_i
        proof = ProveDL([old_comm, new_comm], beta_i)
        #start a list of proofs (which are themselves lists) for easy appending later
        return [ [new_comm, proof] ]
    
    def inc_knowledge_proof(proofs, beta_i):
        old_g_gammabeta = proofs[-1][0]
        new_g_gammabeta = old_g_gammabeta * beta_i

        proof = ProveDL([old_g_gammabeta, new_g_gammabeta], beta_i)
        proofs.append([new_g_gammabeta, proof])
        return proofs
    
    #This technically only needs the second element of each step along with the proofs
    #it only needs the full crs for the last step
    def verify_chain(blockchain, public):
        #part 1: ensure final scructure is correct
        _, lastcrs = blockchain[-1]
        if not BabySNARKr2Player.ver_integrity(lastcrs, public):
            print("bad integrity")
            return False
        #part 2: ensure each block was built off of the last
        for i in range(1, len(blockchain)):
            proof, crs = blockchain[i]
            _, crsold = blockchain[i-1]
            if not BabySNARKr2Player.ver_knowledge(crsold, crs, proof):
                print("knowledge failure at block " + str(i))
                return False
        return True

def init_babysnark(trapdoors, crslen):
    alpha, gamma = trapdoors
    assert crslen > 1
    kzg = [G]
    for i in range(crslen-1):
        kzg.append(kzg[-1] * alpha)
    crs = [G * gamma, kzg]
    return crs

def beacon_babysnark(block):
    _, crs = block
    if len(crs) == 2:
        trapdoors = [random_fp() for i in range(2)]
        newcrs = BabySNARKr1Player.inc_crs(crs, trapdoors)
        new_g_gamma, new_g_alpha = newcrs[0], newcrs[1][1]
        newproof = [[[new_g_alpha, new_g_gamma], trapdoors]]
    #if len(crs) is 4
    else:
        beta = random_fp()
        newcrs = BabySNARKr2Player.inc_crs(crs, beta)
        new_g_gammabeta = newcrs[2]
        newproof = [[new_g_gammabeta, beta]]
    newblock = [newproof, newcrs]
    return newblock
        