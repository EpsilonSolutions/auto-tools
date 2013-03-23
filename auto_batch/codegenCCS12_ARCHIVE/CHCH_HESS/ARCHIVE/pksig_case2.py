""" 
Hess and ChCh - Identity-based Signatures

| From: "Hess - Efficient identity based signature schemes based on pairings."
| Published in: Selected Areas in Cryptography
| Available from: Vol. 2595. LNCS, pages 310-324
| Notes: 

* type:           signature (ID-based)
* setting:        bilinear groups (asymmetric)

:Authors:    J. Ayo Akinyele
:Date:       11/2011
"""
from toolbox.pairinggroup import PairingGroup,G1,G2,ZR,pair
from toolbox.PKSig import PKSig
from schemes.pksig_hess import Hess
from schemes.pksig_chch import CHCH

debug = False

def __init__(groupObj):
    global group
    group = groupObj
            
def verify(mpk, pk, M, sig, hess, chch):
    sig1, sig2 = sig['sig_hess'], sig['sig_chch']        
    isHessTrue = hess.verify(mpk, pk, M, sig1)
    isCHCHTrue = chch.verify(mpk, pk, M, sig2)
    if ( (isHessTrue and isCHCHTrue) == True):
        return True
    return False
        
def main():   
    groupObj = PairingGroup('/Users/matt/Documents/charm/param/d224.param')
    hess = Hess(groupObj)
    chch = CHCH(groupObj)
   
    (mpk, msk) = chch.setup()

    _id = "janedoe@email.com"
    (pk, sk) = chch.keygen(msk, _id)
    if debug:  
        print("Keygen...")
        print("pk =>", pk)
        print("sk =>", sk)
 
    M = "this is a message! twice!" 
    sig1 = hess.sign(mpk, sk, M)
    sig2 = chch.sign(pk, sk, M)
    sig = { 'sig_hess':sig1, 'sig_chch':sig2 }
    if debug:
        print("Signature...")
        print("sig1 =>", sig1)
        print("sig2 =>", sig2)
   
    assert verify(mpk, pk, M, sig, hess, chch), "invalid signature!"
    if debug: print("Verification successful!")

if __name__ == "__main__":
    debug = True
    main()
