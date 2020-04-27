from pypairing import PyFr as ZR, PyG1 as G1, PyG2 as G2, PyFq12 as GT, pair
from hashlib import sha256
from pickle import dumps, loads
import random
#from betterpairing import *

#TODO:Integrate into pypairing
def hash_to_ZR(bytestr):
    assert type(bytestr) is bytes
    hashout = sha256(bytestr).hexdigest()
    seed = [int(hashout[i : i + 8], 16) for i in range(0, 64, 8)]
    return ZR.rand(seed)

def randstr():
    r = random.SystemRandom().randint(0, 2**256)
    return sha256(dumps(r)).hexdigest()
    
    
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
#where g2pair = [f,H] and h is a random string
def ProveSchnorr(g2pair, s, h):
    f, H = g2pair
    a = ZR.rand()
    R = f**a
    tohash = str(R) + h
    c = hash_to_ZR(bytes(tohash, encoding='utf8'))
    u = a + c*s
    return [R,u]

def VerifySchnorr(g2pair, pi, h):
    R, u = pi
    f, H = g2pair
    tohash = str(R) + h
    c = hash_to_ZR(bytes(tohash, encoding='utf8'))
    return f**u == R * H**c

#Assume f is a publicly known generator of G2
def RCPC_step(V, alpha):
    V_next = [Vi ** alpha for Vi in V]
    return V_next

def VerifyRCPC_step(V_old, V_new, g2pair):
    return SameRatioVec(zip(V_old, V_new), g2pair)

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