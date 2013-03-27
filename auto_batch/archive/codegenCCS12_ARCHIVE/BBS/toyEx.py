from toolbox.pairinggroup import *
from toolbox.PKSig import PKSig
from charm.engine.util import *

debug=False
class ShortSig(PKSig):
    def __init__(self, groupObj):
        PKSig.__init__(self)
        global group, debug
        group = groupObj
        debug = False
        
    def keygen(self, n):
        g1, g2 = group.random(G1), group.random(G2)
        h = group.random(G1)
        xi1, xi2 = group.random(), group.random()

        u,v = h ** ~xi1, h ** ~xi2
        gamma = group.random(ZR)
        w = g2 ** gamma
        gpk = { 'g1':g1, 'g2':g2, 'h':h, 'u':u, 'v':v, 'w':w }
        gmsk = { 'xi1':xi1, 'xi2':xi2 }
                
        x = [group.random(ZR) for i in range(n)]
        A = [gpk['g1'] ** ~(gamma + x[i]) for i in range(n)]
        gsk = {}
        if debug: print("\nSecret keys...")
        for i in range(n):
            if debug: print("User %d: A = %s, x = %s" % (i, A[i], x[i]))
            gsk[i] = (A[i], x[i]) 
        return (gpk, gmsk, gsk)
    
    def sign(self, gpk, gsk, M):
        alpha, beta = group.random(), group.random()
        A, x = gsk[0], gsk[1]
        T1 = gpk['u'] ** alpha
        T2 = gpk['v'] ** beta
        T3 = A * (gpk['h'] ** (alpha + beta))
        
        gamma1 = x * alpha
        gamma2 = x * beta
        r = [group.random() for i in range(5)]
         
        R1 = gpk['u'] ** r[0]
        R2 = gpk['v'] ** r[1]
        R3 = (pair(T3, gpk['g2']) ** r[2]) * (pair(gpk['h'], gpk['w']) ** (-r[0] - r[1])) * (pair(gpk['h'], gpk['g2']) ** (-r[3] - r[4]))
        R4 = (T1 ** r[2]) * (gpk['u'] ** -r[3])
        R5 = (T2 ** r[2]) * (gpk['v'] ** -r[4])
        
        c = group.hash((M, T1, T2, T3, R1, R2, R3, R4, R5), ZR)
        s1, s2 = r[0] + c * alpha, r[1] + c * beta
        s3, s4 = r[2] + c * x, r[3] + c * gamma1
        s5 = r[4] + c * gamma2
        return { 'T1':T1, 'T2':T2, 'T3':T3, 'R3':R3,'c':c, 's_alpha':s1, 's_beta':s2, 's_x':s3, 's_gamma1':s4, 's_gamma2':s5 }
    
    def verify(self, gpk, M, sigma):        
        """alternative verification check for BGLS04 which allows it to be batched"""
        c, T1, T2, T3 = sigma['c'], sigma['T1'], sigma['T2'], sigma['T3']
        salpha, sbeta = sigma['s_alpha'], sigma['s_beta']
        sx, sgamma1, sgamma2 = sigma['s_x'], sigma['s_gamma1'], sigma['s_gamma2']
        R3 = sigma['R3']
        
        R1 = (gpk['u'] ** salpha) * (T1 ** -c)
        R2 = (gpk['v'] ** sbeta) * (T2 ** -c)
        R4 = (T1 ** sx) * (gpk['u'] ** -sgamma1)
        R5 = (T2 ** sx) * (gpk['v'] ** -sgamma2)
        if c == group.hash((M, T1, T2, T3, R1, R2, R3, R4, R5), ZR):
            if debug: print("c => '%s'" % c)
            if debug: print("Valid Group Signature for message: '%s'" % M)
            pass
        else:
            if debug: print("Not a valid signature for message!!!")
            return False
        
        #if ((pair(T3, gpk['g2']) ** sx) * (pair(gpk['h'],gpk['w']) ** (-salpha - sbeta)) * (pair(gpk['h'], gpk['g2']) ** (-sgamma1 - sgamma2)) * (pair(T3, gpk['w']) ** c) * (pair(gpk['g1'], gpk['g2']) ** -c) ) == R3: 

        if ((pair((T3 ** sx) * (gpk['h'] ** (-sgamma1 - sgamma2)) * (gpk['g1'] ** -c), gpk['g2'])) * (pair((gpk['h'] ** (-salpha - sbeta)) * (T3 ** c) , gpk['w']))) == R3:

            return True
        else:
            return False
    
    def open(self, gpk, gmsk, M, sigma):
        t1, t2, t3, xi1, xi2 = sigma['T1'], sigma['T2'], sigma['T3'], gmsk['xi1'], gmsk['xi2']
        
        A_prime = t3 / ((t1 ** xi1) * (t2 ** xi2))
        return A_prime
        
def main():

    groupObj = PairingGroup('/Users/matt/Documents/charm/param/d224.param')
    n = 3    # how manu users in the group
    user = 1 # which user's key to sign a message with
    
    sigTest = ShortSig(groupObj)
    
    (gpk, gmsk, gsk) = sigTest.keygen(n)

    message = 'Hello World this is a message!'
    if debug: print("\n\nSign the following M: '%s'" % (message))
    
    signature = sigTest.sign(gpk, gsk[user], message)
    
    result = sigTest.verify(gpk, message, signature)
    assert result, "Signature Failed"
    print(result)
    if debug: print('Successful Verification!')

    delta = groupObj.init(ZR, randomBits(80))

    '''
    dotA = (signature['T3'] ** (-signature['s_x'] * delta) * (gpk['h'] ** ((-signature['s_gamma1'] * -signature['s_gamma2']) * delta) * gpk['g1'] ** (signature['c'] * delta)))
    dotB = (gpk['h'] ** ((-signature['s_alpha'] * -signature['s_beta']) * delta) * signature['T3'] ** (-signature['c'] * delta))
    dotC = signature['R3'] ** delta

    if (pair(dotA,gpk['g2']) * pair(dotB,gpk['w'])) == dotC:
    '''

    dotA = ((signature['T3'] ** signature['s_x']) * (gpk['h'] ** ((-signature['s_gamma1'] * -signature['s_gamma2'])) * (gpk['g1'] ** -signature['c'])) ** delta
    dotB = (((gpk['h'] ** (-signature['s_alpha'] - signature['s_beta'])) * (signature['T3'] ** signature['c'])) ** delta)
    dotC = signature['R3'] ** delta

    if (pair(dotA,gpk['g2']) * pair(dotB,gpk['w'])) == dotC:


    '''
    dotA = ((T3 ** sx) * (gpk['h'] ** (-sgamma1 - sgamma2)) * (gpk['g1'] ** -c)) ** delta
    dotB = ((gpk['h'] ** (-salpha - sbeta)) * (T3 ** c)) ** delta
    dotC = R3 ** delta
    if (pair(dotA, gpk['g2']) * pair(dotB , gpk['w'])) == dotC: 
    '''

        print("correct")
    else:
        print("incorrect")


if __name__ == "__main__":
    debug = False
    main()
