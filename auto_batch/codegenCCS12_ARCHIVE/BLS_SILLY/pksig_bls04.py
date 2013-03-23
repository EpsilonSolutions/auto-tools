from toolbox.pairinggroup import *
from charm.engine.util import *
import sys, random, string

debug = False
class IBSig():
    def __init__(self, groupObj):
        global group, debug
        group = groupObj
        debug = False
        
    def dump(self, obj):
        ser_a = serializeDict(obj, group)
        return str(pickleObject(ser_a))
            
    def keygen(self, secparam=None):
        g, x = group.random(G2), group.random()
        g_x = g ** x
        pk = { 'g^x':g_x, 'g':g, 'identity':str(g_x), 'secparam':secparam }
        sk = { 'x':x }
        return (pk, sk)
        
    def sign(self, x, message):
        M = message
        if debug: print("Message => '%s'" % M)
        sig1 = group.hash(M, G1) ** x
        sig2 = group.random()
        sig = {}
        sig['sig1'] = sig1
        sig['sig2'] = sig2
        return sig
        
    def verify(self, pk, sigDict, message):
        M = message
        h = group.hash(M, G1)
        sig = sigDict['sig1']
        t = sigDict['sig2']

        if pair(sig, (pk['g'] ** t)) == (pair(h, pk['g^x']) ** t):
            return True  
        return False 

def main():
    #if ( (len(sys.argv) != 7) or (sys.argv[1] == "-help") or (sys.argv[1] == "--help") ):
        #sys.exit("Usage:  python " + sys.argv[0] + " [# of valid messages] [# of invalid messages] [size of each message] [prefix name of each message] [name of valid output dictionary] [name of invalid output dictionary]")

    groupObj = PairingGroup('/Users/matt/Documents/charm/param/d224.param')
    
    #m = { 'a':"hello world!!!" , 'b':"test message" }
    m = "rest"
    bls = IBSig(groupObj)
    
    (pk, sk) = bls.keygen(0)
    
    sig = bls.sign(sk['x'], m)
    
    if debug: print("Message: '%s'" % m)
    if debug: print("Signature: '%s'" % sig)     
    assert bls.verify(pk, sig, m), "Failure!!!"
    result = bls.verify(pk, sig, m)
    print(result)
    if debug: print('SUCCESS!!!')

    '''
    numValidMessages = int(sys.argv[1])
    numInvalidMessages = int(sys.argv[2])
    messageSize = int(sys.argv[3])
    prefixName = sys.argv[4]
    validOutputDictName = sys.argv[5]
    invalidOutputDictName = sys.argv[6]

    f_mpk = open('mpk.charmPickle', 'wb')
    pick_mpk = pickleObject(serializeDict(pk, groupObj))
    f_mpk.write(pick_mpk)
    f_mpk.close()

    validOutputDict = {}
    validOutputDict[0] = {}
    validOutputDict[0]['pk'] = 'mpk.charmPickle'

    invalidOutputDict = {}
    invalidOutputDict[0] = {}
    invalidOutputDict[0]['pk'] = 'mpk.charmPickle'

    for index in range(0, numValidMessages):
        if (index != 0):
            validOutputDict[index] = {}
            validOutputDict[index]['pk'] = 'mpk.charmPickle'

        message = ""
        for randomChar in range(0, messageSize):
            message += random.choice(string.printable)

        sig = bls.sign(sk['x'], message)
        assert bls.verify(pk, sig, message)

        f_message = open(prefixName + str(index) + '_ValidMessage.pythonPickle', 'wb')
        validOutputDict[index]['message'] = prefixName + str(index) + '_ValidMessage.pythonPickle'

        f_sig = open(prefixName + str(index) + '_ValidSignature.charmPickle', 'wb')
        validOutputDict[index]['sigDict'] = prefixName + str(index) + '_ValidSignature.charmPickle'

        pickle.dump(message, f_message)
        f_message.close()

        pick_sig = pickleObject(serializeDict(sig, groupObj))

        f_sig.write(pick_sig)
        f_sig.close()

        del message
        del sig
        del f_message
        del f_sig
        del pick_sig

    dict_pickle = pickleObject(serializeDict(validOutputDict, groupObj))
    f = open(validOutputDictName, 'wb')
    f.write(dict_pickle)
    f.close()
    del dict_pickle
    del f

    for index in range(0, numInvalidMessages):
        if (index != 0):
            invalidOutputDict[index] = {}
            invalidOutputDict[index]['pk'] = 'mpk.charmPickle'

        message = ""
        for randomChar in range(0, messageSize):
            message += random.choice(string.printable)

        sig = bls.sign(sk['x'], message)
        assert bls.verify(pk, sig, message)

        f_message = open(prefixName + str(index) + '_InvalidMessage.pythonPickle', 'wb')
        invalidOutputDict[index]['message'] = prefixName + str(index) + '_InvalidMessage.pythonPickle'
        randomIndex = random.randint(0, (messageSize - 1))
        oldValue = message[randomIndex]
        newValue = random.choice(string.printable)
        while (newValue == oldValue):
            newValue = random.choice(string.printable)

        if (messageSize == 1):
            message = newValue
        elif (randomIndex != (messageSize -1) ):
            message = message[0:randomIndex] + newValue + message[(randomIndex + 1):messageSize]
        else:
            message = message[0:randomIndex] + newValue

        f_sig = open(prefixName + str(index) + '_InvalidSignature.charmPickle', 'wb')
        invalidOutputDict[index]['sigDict'] = prefixName + str(index) + '_InvalidSignature.charmPickle'

        pickle.dump(message, f_message)
        f_message.close()

        pick_sig = pickleObject(serializeDict(sig, groupObj))

        f_sig.write(pick_sig)
        f_sig.close()

        del message
        del sig
        del f_message
        del f_sig
        del pick_sig

    dict_pickle = pickleObject(serializeDict(invalidOutputDict, groupObj))
    f = open(invalidOutputDictName, 'wb')
    f.write(dict_pickle)
    f.close()
    del dict_pickle
    del f
    '''

if __name__ == "__main__":
    debug = False
    main()
    
