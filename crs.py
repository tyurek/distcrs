from betterpairing import ZR, G1, G2, GT, pair
from hashlib import sha256
from pickle import dumps, loads
import random
#from betterpairing import *

#TODO:Integrate into pypairing
#def hash(bytestr):
#    assert type(bytestr) is bytes
#    hashout = sha256(bytestr).hexdigest()
#    seed = [int(hashout[i : i + 8], 16) for i in range(0, 64, 8)]
#    return ZR.rand(seed)
#ZR.hash = hash

def randstr():
    r = random.SystemRandom().randint(0, 2**256)
    return sha256(dumps(r)).hexdigest()
    
#Also works as SameRatio(g1pair, g2pair)
def SameRatio(V, g2pair):
    if type(V[0]) is list:
        return SameRatioVec(V, g2pair)
    g1identity = G1.identity()
    g2identity = G2.identity()
    p, q = V
    assert type(p) is G1 and type(q) is G1
    f, H = g2pair
    assert type(f) is G2 and type(H) is G2
    if p == g1identity or q == g1identity or f == g2identity or H == g2identity:
        return False
    return pair(p, H) == pair(q, f)

def SameRatioVec(V, g2pair):
    p = G1.identity()
    q = G1.identity()
    for pair in V:
        pi, qi = pair
        ci = ZR.rand()
        p *= pi**ci
        q *= qi**ci
    if p==q and p==G1.identity():
        return True
    return SameRatio([p,q], g2pair)

def SameRatioSec(V, g2pair):
    for i in range(len(V)-1):
        if SameRatio([V[i],V[i+1]], g2pair) is False:
            return False
    return True

#Prove that you know s, such that f**s = H. 
#where gpair = [f,H] and h is a random string
#Pair can be in either G1 or G2
def ProveSchnorr(gpair, s, h):
    f, H = gpair
    a = ZR.rand()
    R = f**a
    tohash = str(R) + h
    c = ZR.hash(bytes(tohash, encoding='utf8'))
    u = a + c*s
    return [R,u]

def VerifySchnorr(gpair, pi, h):
    R, u = pi
    f, H = gpair
    tohash = str(R) + h
    c = ZR.hash(bytes(tohash, encoding='utf8'))
    return f**u == R * H**c

#Assume f is a publicly known generator of G2
def RCPC_step(V, alpha):
    V_next = [Vi ** alpha for Vi in V]
    return V_next

def VerifyRCPC_step(V_old, V_new, g2pair):
    return SameRatioVec(zip(V_old, V_new), g2pair)

#V is {V, V_1, V_2, ... V_n}, g2pairs is length n
def VerifyRCPC(V, g2pairs):
    out = True
    for i in range(len(g2pairs)):
        out &= VerifyRCPC_step(V[i], V[i+1], g2pairs[i])
    return out

def Round1(g):
    g1, g2 = g
    [tau, rho_a, rho_b, alpha_a, alpha_b, alpha_c, beta, gamma] = [ZR.rand() for i in range(8)]
    e = [[g1 ** item, g2 ** item] for item in [tau, rho_a, rho_a * rho_b, rho_a * alpha_a, rho_a * rho_b * alpha_b, rho_a * rho_b * alpha_c, gamma, beta*gamma]]
    h = ZR.hash(dumps(e))
    return [h, e, secrets]

def CheckRound1(g, h, e):
    #part 1 (check consistency of hash commitment)
    if h != ZR.hash(dumps(e)):
        return False

    #part 2 (check that all group element commitments have the same exponent in G1 and G2)
    g1, g2 = g
    tau, rho_a, rho_a_rho_b, rho_a_alpha_a, rho_a_rho_b_alpha_b, rho_a_rho_b_alpha_c, gamma, beta_gamma = e
    out = True
    #check tau
    out &= SameRatio([g1, tau[0]], [g2, tau[1]])
    #check rho_a
    out &= SameRatio([g1, rho_a[0]], [g2, rho_a[1]])
    #check rho_b
    out &= SameRatio([g1, rho_b[0]], [g2, rho_b[1]])
    #check alpha_a
    out &= SameRatio([rho_a[0], rho_a_alpha_a[0]], [rho_a[1], rho_a_alpha_a[1]])
    #check alpha_b
    out &= SameRatio([rho_a_rho_b[0], rho_a_rho_b_alpha_b[0]], [rho_a_rho_b[1], rho_a_rho_b_alpha_b[1]])
    #check alpha_c
    out &= SameRatio([rho_a_rho_b[0], rho_a_rho_b_alpha_c[0]], [rho_a_rho_b[1], rho_a_rho_b_alpha_c[1]])
    #check beta
    out &= SameRatio([gamma[0], beta_gamma[0]], [gamma[1], beta_gamma[1]])
    #check gamma
    out &= SameRatio([g1, gamma[0]], [g2, gamma[1]])
    #check rho_a_alpha_a
    out &= SameRatio([g1, rho_a_alpha_a[0]], [g2, rho_a_alpha_a[1]])
    #check rho_b_alpha_b
    out &= SameRatio([rho_a[0], rho_a_rho_b_alpha_b[0]], [rho_a[1], rho_a_rho_b_alpha_b[1]])
    #check rho_a_rho_b
    out &= SameRatio([g1, rho_a_rho_b[0]], [g2, rho_a_rho_b[1]])
    #check rho_a_rho_b_alpha_c
    out &= SameRatio([g1, rho_a_rho_b_alpha_c[0]], [g2, rho_a_rho_b_alpha_c[1]])
    #check beta_gamma
    out &= SameRatio([g1, beta_gamma[0]], [g2, beta_gamma[1]])
    return out

def ProveRound2(g, secrets, e, h)
    g1, g2 = g
    nizks = []
    tau, rho_a, rho_b, alpha_a, alpha_b, alpha_c, beta, gamma = secrets
    gtau, grho_a, grho_a_rho_b, grho_a_alpha_a, grho_a_rho_b_alpha_b, grho_a_rho_b_alpha_c, ggamma, gbeta_gamma = e
    #prove  tau
    nizks.append(ProveSchnorr([g1, gtau[0]], tau, h))
    #prove rho_a
    nizks.append(ProveSchnorr([g1, grho_a[0]], rho_a, h))
    #prove rho_b
    nizks.append(ProveSchnorr([g1, grho_b[0]], rho_b, h))
    #prove alpha_a
    nizks.append(ProveSchnorr([grho_a[0], grho_a_alpha_a[0]], alpha_a, h))
    #prove alpha_b
    nizks.append(ProveSchnorr([grho_a_rho_b[0], grho_a_rho_b_alpha_b[0]], alpha_b, h))
    #prove alpha_c
    nizks.append(ProveSchnorr([grho_a_rho_b[0], grho_a_rho_b_alpha_c[0]], alpha_c, h))
    #prove beta
    nizks.append(ProveSchnorr([ggamma[0], gbeta_gamma[0]], beta, h))
    #prove gamma
    nizks.append(ProveSchnorr([g1, ggamma[0]], gamma, h))
    return nizks

def CheckRound2(g, proofs, e, h):
    out = True
    pi_tau, pi_rho_a, pi_rho_b, pi_alpha_a, pi_alpha_b, pi_alpha_c, pi_beta, pi_gamma = proofs
    gtau, grho_a, grho_a_rho_b, grho_a_alpha_a, grho_a_rho_b_alpha_b, grho_a_rho_b_alpha_c, ggamma, gbeta_gamma = e
    #verify tau nizk
    out &= VerifySchnorr([g1, gtau[0]], pi_tau, h)
    #verify rho_a
    out &= VerifySchnorr([g1, grho_a[0]], pi_rho_a, h)
    #verify rho_b
    out &= VerifySchnorr([g1, grho_b[0]], pi_rho_b, h)
    #verify alpha_a
    out &= VerifySchnorr([grho_a[0], grho_a_alpha_a[0]], pi_alpha_a, h)
    #verify alpha_b
    out &= VerifySchnorr([grho_a_rho_b[0], grho_a_rho_b_alpha_b[0]], pi_alpha_b, h)
    #verify alpha_c
    out &= VerifySchnorr([grho_a_rho_b[0], grho_a_rho_b_alpha_c[0]], pi_alpha_c, h)
    #verify beta
    out &= VerifySchnorr([ggamma[0], gbeta_gamma[0]], pi_beta, h)
    #verify gamma
    out &= VerifySchnorr([g1, ggamma[0]], pi_gamma, h)

#Round2a goes up to generating NIZKs in part 3
def Round2a(g, h_vec, e_vec, secrets):
    #parts 1 and 2: verify each party's round 1 inputs
    assert len(h_vec) == len(e_vec)
    n = len(h_vec)
    for i in range(n):
        if !CheckRound1(g, h_vec[i], e_vec[i]):
            #rej
            return False
    #part 3a:
    h_bytestr = bytes("", , encoding='utf8')
    for i in range(n)
        h_bytestr += dumps(h_vec[i])
    h = ZR.hash(h_bytestr)
    nizks = []
    pi = ProveSchnorr(gpair, s, h):
    
    
    

#ToDo: Move this to an actual test file
exp = ZR.rand()
g1a = G1.rand()
g1b = g1a ** exp
g2a = G2.rand()
g2b = g2a ** exp
print(SameRatio([g1a, g1b],[g2a, g2b]))
print(not SameRatio([g1a, g1b],[g2a, g2a**2]))
h = randstr()
pi = ProveSchnorr([g2a, g2b], exp, h)
print(VerifySchnorr([g2a, g2b], pi, h))
print(not VerifySchnorr([g2a, g2b], pi, randstr()))
print(not VerifySchnorr([g2a, G2.rand()], pi, h))

f = G2.rand()
alpha = ZR.rand()
V_0 = [G1.rand() for _ in range(10)]
V_1 = RCPC_step(V_0, alpha)
print(VerifyRCPC_step(V_0, V_1, [f, f**alpha]))

g = [G1.rand(), G2.rand()]