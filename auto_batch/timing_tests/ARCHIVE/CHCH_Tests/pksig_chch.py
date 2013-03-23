""" TODO: Description of Scheme here.
"""
from charm.pairing import *
from toolbox.PKSig import PKSig

debug = False

class CHCH(PKSig):
    def __init__(self, groupObj):
        global group
        group = groupObj
        
    def setup(self):
        global H1,H2
        H1 = lambda x: group.H(x, G1)
        H2 = lambda x,y: group.H((x,y), ZR)
        g2, alpha = group.random(G2), group.random(ZR)
        msk = alpha
        P = g2 ** alpha 
        mpk = {'P':P, 'g2':g2}
        return (mpk, msk)

    def keygen(self, msk, ID):
        alpha = msk
        sk = H1(ID) ** alpha
        pk = H1(ID)
        return (pk, sk)
    
    def sign(self, pk, sk, M):
        print("sign...")
        s = group.random(ZR)
        S1 = pk ** s
        a = H2(M, S1)
        S2 = sk ** (s + a)
        return {'S1':S1, 'S2':S2}
    
    def verify(self, mpk, pk, M, sig):
        print("verify...")
        (S1, S2) = sig['S1'], sig['S2']
        a = H2(M, S1)
        if pair(S2, mpk['g2']) == pair(S1 * (pk ** a), mpk['P']): 
            return True
        return False

if __name__ == "__main__":
   
   #groupObj = pairing('../param/a.param')
   groupObj = pairing(80)
   chch = CHCH(groupObj)
   (mpk, msk) = chch.setup()

   _id = "janedoe@email.com"
   (pk, sk) = chch.keygen(msk, _id)  
   print("Keygen...")
   print("pk =>", pk)
   print("sk =>", sk)
 
   M = "this is a message!" 
   sig = chch.sign(pk, sk, M)
   print("Signature...")
   print("sig['S1'] =>", sig['S1'])
   print("sig['S2'] =>", sig['S2'])

   assert chch.verify(mpk, pk, M, sig), "invalid signature!"
   print("Verification successful!")
   
