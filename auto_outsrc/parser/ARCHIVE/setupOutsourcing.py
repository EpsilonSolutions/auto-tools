from userFuncs import *
from toolbox.pairinggroup import PairingGroup, ZR, G1, G2, GT, pair
from toolbox.secretutil import SecretUtil
from toolbox.symcrypto import AuthenticatedCryptoAbstraction
from toolbox.iterate import dotprod2
from charm.pairing import hash as SHA1

tau1b = {}
ga2 = {}
ga1 = {}
gb = {}
gba1 = {}
gba2 = {}
tau2 = {}
tau1 = {}
msk = {}
mpk = {}
v1 = {}
v2 = {}
egga = {}
alpha = {}
g = {}
h = {}
galpha_a1 = {}
u = {}
w = {}
v = {}
tau2b = {}
C = {}
D = {}
sk = {}
ct = {}
DBlinded = {}

def setup():
	global tau1b
	global ga2
	global ga1
	global gb
	global gba1
	global gba2
	global tau2
	global tau1
	global msk
	global mpk
	global v1
	global v2
	global egga
	global alpha
	global g
	global h
	global galpha_a1
	global u
	global w
	global v
	global tau2b

	input = None
	g = groupObj.random(G1)
	w = groupObj.random(G1)
	u = groupObj.random(G1)
	h = groupObj.random(G1)
	v = groupObj.random(G1)
	v1 = groupObj.random(G1)
	v2 = groupObj.random(G1)
	a1 = groupObj.random(ZR)
	a2 = groupObj.random(ZR)
	b = groupObj.random(ZR)
	alpha = groupObj.random(ZR)
	gb = (g ** b)
	ga1 = (g ** a1)
	ga2 = (g ** a2)
	gba1 = (gb ** a1)
	gba2 = (gb ** a2)
	tau1 = (v * (v1 ** a1))
	tau2 = (v * (v2 ** a2))
	tau1b = (tau1 ** b)
	tau2b = (tau2 ** b)
	egga = (pair(g, g) ** (alpha * (a1 * b)))
	galpha = (g ** alpha)
	galpha_a1 = (galpha ** a1)
	mpk = [g, gb, ga1, ga2, gba1, gba2, tau1, tau2, tau1b, tau2b, w, u, h, egga]
	msk = [galpha, galpha_a1, v, v1, v2, alpha]
	output = (mpk, msk)

def keygen(id):
	global D
	global sk
	global DBlinded

	input = [mpk, msk, id]
	idBlinded = id
	zz = groupObj.random(ZR)
	g, gb, ga1, ga2, gba1, gba2, tau1, tau2, tau1b, tau2b, w, u, h, egga = mpk
	galpha, galpha_a1, v, v1, v2, alpha = msk
	r1 = groupObj.random(ZR)
	r2 = groupObj.random(ZR)
	z1 = groupObj.random(ZR)
	z2 = groupObj.random(ZR)
	tag_k = groupObj.random(ZR)
	tag_kBlinded = (tag_k ** (1 / zz))
	r = (r1 + r2)
	id_hash = groupObj.hash(idBlinded, ZR)
	D[1] = (galpha_a1 * (v ** r))
	D[2] = ((g ** -alpha) * ((v1 ** r) * (g ** z1)))
	D[3] = (gb ** -z1)
	D[4] = ((v2 ** r) * (g ** z2))
	D[5] = (gb ** -z2)
	D[6] = (gb ** r2)
	D[7] = (g ** r1)
	for y in D:
		DBlinded[y] = (D[y] ** (1 / zz))
	K = ((((u ** id_hash) * (w ** tag_kBlinded)) * h) ** r1)
	KBlinded = (K ** (1 / zz))
	sk = [idBlinded, DBlinded, KBlinded, tag_kBlinded]
	skBlinded = [idBlinded, DBlinded, KBlinded, tag_kBlinded]
	output = (zz, skBlinded)
	return output

def encrypt(M, id):
	global C
	global ct

	input = [mpk, M, id]
	g, gb, ga1, ga2, gba1, gba2, tau1, tau2, tau1b, tau2b, w, u, h, egga = mpk
	s1 = groupObj.random(ZR)
	R = groupObj.random(GT)
	s2 = groupObj.hash([R, M], ZR)
	s2_sesskey = SHA1(R)
	C[0] = (R * (egga ** s2))
	t = groupObj.random(ZR)
	tag_c = groupObj.random(ZR)
	s = (s1 + s2)
	id_hash2 = groupObj.hash(id, ZR)
	C[1] = (gb ** s)
	C[2] = (gba1 ** s1)
	C[3] = (ga1 ** s1)
	C[4] = (gba2 ** s2)
	C[5] = (ga2 ** s2)
	C[6] = ((tau1 ** s1) * (tau2 ** s2))
	C[7] = (((tau1b ** s1) * (tau2b ** s2)) * (w ** -t))
	E1 = ((((u ** id_hash2) * (w ** tag_c)) * h) ** t)
	E2 = (g ** t)
	T1 = SymEnc(s2_sesskey, M)
	ct = [C, E1, E2, tag_c, T1]
	output = ct

def transform(sk):
	input = [ct, sk]
	id, D, K, tag_k = sk
	C, E1, E2, tag_c, T1 = ct
	tag = (1 / (tag_c - tag_k))
	A1 = (pair(C[1], D[1]) * (pair(C[2], D[2]) * (pair(C[3], D[3]) * (pair(C[4], D[4]) * pair(C[5], D[5])))))
	A2 = (pair(C[6], D[6]) * pair(C[7], D[7]))
	A3 = (A1 / A2)
	A4 = (pair((E1 ** tag), D[7]) * pair((E2 ** -tag), K))
	T2 = (A3 / A4)
	T0 = C[0]
	partCT = [T0, T1, T2]
	output = partCT
	return output

def decout(partCT, zz):
	input = [partCT, zz, egga]
	T0, T1, T2 = partCT
	R = (T0 / (T2 ** zz))
	s2_sesskey = SHA1(R)
	M = SymDec(s2_sesskey, T1)
	print("The message decrypts in decout to:  ", M)
	s2 = groupObj.hash([R, M], ZR)
	if ( ( (( (T0) == ((R * (egga ** s2))) )) and (( (T2) == ((R * (egga ** (s2 / zz)))) )) ) ):
		output = M
		print("RCCA check is successful")
	else:
		output = M
		print("RCCA check has failed.")
	return output

if __name__ == "__main__":
	global groupObj
	groupObj = PairingGroup('SS512')

	id = "user@blah.com"
	M = "balls on fire"

	setup()
	(zz, skBlinded) = keygen(id)
	encrypt(M, id)

	(partCT) = transform(skBlinded)
	(newM) = decout(partCT, zz)

	print("\n\n")
	print("From main():")
	print("Original message:  ", M)
	print("Decrypted message:  ", newM)
