import random
from pickle import dumps
from hashlib import sha256
from ssbls12 import Fp, Poly, Group
G = Group.G

def print_exception_callback(future):
    if future.done():
        ex = future.exception()
        if ex is not None:
            raise ex

def random_fp():
    return Fp(random.randint(0, Fp.p-1))

def hash_to_fp(bytestr):
    assert type(bytestr) is bytes
    return Fp(int(sha256(bytestr).hexdigest(), 16)%Fp.p)

#Check if the two pairs differ by the same exponent
#Sym suffix denotes the symmetric version of X function
def SameRatioSym(pair1, pair2):
    g1, h1, g2, h2 = pair1 + pair2
    return Group.pair(g1, h2) == Group.pair(h1, g2)

def SameRatioSeqSymOld(sequence, pair):
    for i in range(len(sequence)-1):
        if not SameRatioSym([sequence[i], sequence[i+1]], pair):
            return False
    return True

#Use randomization to minimize pairings. A few times faster than SameRatioSeqSymOld
#(would be even faster to use a multiexponentiation)
def SameRatioSeqSym(sequence, pair):
    left = G * Fp(0)
    right = G * Fp(0)
    l = len(sequence)
    blinds = [random_fp() for i in range(l-1)]
    for i in range(l-1):
        left += sequence[i+1] * blinds[i]
        right += sequence[i] * blinds[i]
    return Group.pair(pair[0],left) == Group.pair(pair[1], right)

def ProveDL(pair, s):
    r = random_fp()
    g, h = pair
    R = g*r
    c = hash_to_fp(dumps(R))
    u = r + c*s
    return [R,u]

def VerifyDL(pair, pi):
    R, u = pi
    g, h = pair
    c = hash_to_fp(dumps(R))
    return g*u == R + h*c

def ExpEval(poly, kzg):
    out = G * 0
    i = 0
    for coeff in poly.coefficients:
        out += kzg[i] * coeff
        i += 1
    return out