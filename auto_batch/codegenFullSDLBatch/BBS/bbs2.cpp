#include "sdlconfig.h"
#include <iostream>
#include <sstream>
#include <string>
#include <list>
using namespace std;

int N = 100;

int secparam = 80;

PairingGroup group(AES_SECURITY);

bool precheck(G1 & g1, G2 & g2, G1 & h, G1 & u, G1 & v, G2 & w, string & M, G1 & T1, G1 & T2, G1 & T3, ZR & c, ZR & salpha, ZR & sbeta, ZR & sx, ZR & sgamma1, ZR & sgamma2, GT & R3)
{
    G1 R1ver = group.init(G1_t);
    G1 R2ver = group.init(G1_t);
    G1 R4ver = group.init(G1_t);
    G1 R5ver = group.init(G1_t);
    R1ver = group.mul(group.exp(u, salpha), group.exp(T1, group.neg(c)));
    R2ver = group.mul(group.exp(v, sbeta), group.exp(T2, group.neg(c)));
    R4ver = group.mul(group.exp(T1, sx), group.exp(u, group.neg(sgamma1)));
    R5ver = group.mul(group.exp(T2, sx), group.exp(v, group.neg(sgamma2)));
    if ( ( (c) != (group.hashListToZR((Element(M) + Element(T1) + Element(T2) + Element(T3) + Element(R1ver) + Element(R2ver) + Element(R3) + Element(R4ver) + Element(R5ver)))) ) )
    {
        return false;
    }
    else
    {
        return true;
    }
}

void keygen(int n, CharmList & gpk, CharmList & gmsk, CharmListG1 & A, CharmListZR & x)
{
    G1 g1 = group.init(G1_t);
    G2 g2 = group.init(G2_t);
    G1 h = group.init(G1_t);
    ZR xi1 = group.init(ZR_t);
    ZR xi2 = group.init(ZR_t);
    G1 u = group.init(G1_t);
    G1 v = group.init(G1_t);
    ZR gamma = group.init(ZR_t);
    G2 w = group.init(G2_t);
    g1 = group.random(G1_t);
    g2 = group.random(G2_t);
    h = group.random(G1_t);
    xi1 = group.random(ZR_t);
    xi2 = group.random(ZR_t);
    u = group.exp(h, group.div(1, xi1));
    v = group.exp(h, group.div(1, xi2));
    gamma = group.random(ZR_t);
    w = group.exp(g2, gamma);
    gpk.append(g1);
    gpk.append(g2);
    gpk.append(h);
    gpk.append(u);
    gpk.append(v);
    gpk.append(w);
    gmsk.append(xi1);
    gmsk.append(xi2);
    for (int y = 0; y < n; y++)
    {
        x[y] = group.random(ZR_t);
        A[y] = group.exp(g1, group.div(1, group.add(gamma, x[y])));
    }
    return;
}

void sign(CharmList & gpk, G1 & A_ind, ZR & x_ind, string & M, CharmList & sig)
{
    G1 g1;
    G2 g2;
    G1 h;
    G1 u;
    G1 v;
    G2 w;
    ZR alpha = group.init(ZR_t);
    ZR beta = group.init(ZR_t);
    G1 T1 = group.init(G1_t);
    G1 T2 = group.init(G1_t);
    G1 T3 = group.init(G1_t);
    ZR gamma1 = group.init(ZR_t);
    ZR gamma2 = group.init(ZR_t);
    CharmListZR r;
    G1 R1 = group.init(G1_t);
    G1 R2 = group.init(G1_t);
    GT R3 = group.init(GT_t);
    G1 R4 = group.init(G1_t);
    G1 R5 = group.init(G1_t);
    ZR c = group.init(ZR_t);
    ZR salpha = group.init(ZR_t);
    ZR sbeta = group.init(ZR_t);
    ZR sx = group.init(ZR_t);
    ZR sgamma1 = group.init(ZR_t);
    ZR sgamma2 = group.init(ZR_t);
    
    g1 = gpk[0].getG1();
    g2 = gpk[1].getG2();
    h = gpk[2].getG1();
    u = gpk[3].getG1();
    v = gpk[4].getG1();
    w = gpk[5].getG2();
    alpha = group.random(ZR_t);
    beta = group.random(ZR_t);
    T1 = group.exp(u, alpha);
    T2 = group.exp(v, beta);
    T3 = group.mul(A_ind, group.exp(h, group.add(alpha, beta)));
    gamma1 = group.mul(x_ind, alpha);
    gamma2 = group.mul(x_ind, beta);
    r[0] = group.random(ZR_t);
    r[1] = group.random(ZR_t);
    r[2] = group.random(ZR_t);
    r[3] = group.random(ZR_t);
    r[4] = group.random(ZR_t);
    r[5] = group.random(ZR_t);
    R1 = group.exp(u, r[0]);
    R2 = group.exp(v, r[1]);
    R3 = group.mul(group.exp(group.pair(T3, g2), r[2]), group.mul(group.exp(group.pair(h, w), group.sub(group.neg(r[0]), r[1])), group.exp(group.pair(h, g2), group.sub(group.neg(r[3]), r[4]))));
    R4 = group.mul(group.exp(T1, r[2]), group.exp(u, group.neg(r[3])));
    R5 = group.mul(group.exp(T2, r[2]), group.exp(v, group.neg(r[4])));
    c = group.hashListToZR((Element(M) + Element(T1) + Element(T2) + Element(T3) + Element(R1) + Element(R2) + Element(R3) + Element(R4) + Element(R5)));
    salpha = group.add(r[0], group.mul(c, alpha));
    sbeta = group.add(r[1], group.mul(c, beta));
    sx = group.add(r[2], group.mul(c, x_ind));
    sgamma1 = group.add(r[3], group.mul(c, gamma1));
    sgamma2 = group.add(r[4], group.mul(c, gamma2));
    sig.append(T1);
    sig.append(T2);
    sig.append(T3);
    sig.append(c);
    sig.append(salpha);
    sig.append(sbeta);
    sig.append(sx);
    sig.append(sgamma1);
    sig.append(sgamma2);
    sig.append(R3);
    return;
}

bool verify(G1 & g1, G2 & g2, G1 & h, G1 & u, G1 & v, G2 & w, string & M, G1 & T1, G1 & T2, G1 & T3, ZR & c, ZR & salpha, ZR & sbeta, ZR & sx, ZR & sgamma1, ZR & sgamma2, GT & R3)
{
    if ( ( (precheck(g1, g2, h, u, v, w, M, T1, T2, T3, c, salpha, sbeta, sx, sgamma1, sgamma2, R3)) == (false) ) )
    {
        return false;
    }
    if ( ( (group.mul(group.exp(group.pair(T3, g2), sx), group.mul(group.exp(group.pair(h, w), group.sub(group.neg(salpha), sbeta)), group.mul(group.exp(group.pair(h, g2), group.sub(group.neg(sgamma1), sgamma2)), group.mul(group.exp(group.pair(T3, w), c), group.exp(group.pair(g1, g2), group.neg(c))))))) == (R3) ) )
    {
        return true;
    }
    else
    {
        return false;
    }
}

bool membership(CharmListGT & R3list, CharmListG1 & T1list, CharmListG1 & T2list, CharmListG1 & T3list, CharmListZR & clist, G1 & g1, G2 & g2, G1 & h, CharmListZR & salphalist, CharmListZR & sbetalist, CharmListZR & sgamma1list, CharmListZR & sgamma2list, CharmListZR & sxlist, G1 & u, G1 & v, G2 & w)
{
    if ( ( (group.ismember(R3list)) == (false) ) )
    {
        return false;
    }
    if ( ( (group.ismember(T1list)) == (false) ) )
    {
        return false;
    }
    if ( ( (group.ismember(T2list)) == (false) ) )
    {
        return false;
    }
    if ( ( (group.ismember(T3list)) == (false) ) )
    {
        return false;
    }
    if ( ( (group.ismember(clist)) == (false) ) )
    {
        return false;
    }
    if ( ( (group.ismember(g1)) == (false) ) )
    {
        return false;
    }
    if ( ( (group.ismember(g2)) == (false) ) )
    {
        return false;
    }
    if ( ( (group.ismember(h)) == (false) ) )
    {
        return false;
    }
    if ( ( (group.ismember(salphalist)) == (false) ) )
    {
        return false;
    }
    if ( ( (group.ismember(sbetalist)) == (false) ) )
    {
        return false;
    }
    if ( ( (group.ismember(sgamma1list)) == (false) ) )
    {
        return false;
    }
    if ( ( (group.ismember(sgamma2list)) == (false) ) )
    {
        return false;
    }
    if ( ( (group.ismember(sxlist)) == (false) ) )
    {
        return false;
    }
    if ( ( (group.ismember(u)) == (false) ) )
    {
        return false;
    }
    if ( ( (group.ismember(v)) == (false) ) )
    {
        return false;
    }
    if ( ( (group.ismember(w)) == (false) ) )
    {
        return false;
    }
    return true;
}

void dividenconquer(CharmListZR & delta, int startSigNum, int endSigNum, list<int> & incorrectIndices, CharmListG1 & dotACache, CharmListG1 & dotBCache, CharmListGT & dotCCache, G2 & g2, G2 & w)
{
    G1 dotALoopVal = group.init(G1_t, 1);
    G1 dotBLoopVal = group.init(G1_t, 1);
    GT dotCLoopVal = group.init(GT_t, 1);
    int midwayFloat = 0;
    int midway = 0;
    int midSigNum = 0;
    group.init(dotALoopVal, 1);
    group.init(dotBLoopVal, 1);
    group.init(dotCLoopVal, 1);
    for (int z = startSigNum; z < endSigNum; z++)
    {
        dotALoopVal = group.mul(dotALoopVal, dotACache[z]);
        dotBLoopVal = group.mul(dotBLoopVal, dotBCache[z]);
        dotCLoopVal = group.mul(dotCLoopVal, dotCCache[z]);
    }
    if ( ( (group.mul(group.pair(dotALoopVal, g2), group.pair(dotBLoopVal, w))) == (dotCLoopVal) ) )
    {
        return;
    }
    else
    {
        midwayFloat = group.div(group.sub(endSigNum, startSigNum), 2);
        midway = int(midwayFloat);
    }
    if ( ( (midway) == (0) ) )
    {
        incorrectIndices.push_back(startSigNum);
    }
    else
    {
        midSigNum = group.add(startSigNum, midway);
        dividenconquer(delta, startSigNum, midway, incorrectIndices, dotACache, dotBCache, dotCCache, g2, w);
        dividenconquer(delta, midSigNum, endSigNum, incorrectIndices, dotACache, dotBCache, dotCCache, g2, w);
    }
    return;
}

bool batchverify(CharmListStr & Mlist, CharmListGT & R3list, CharmListG1 & T1list, CharmListG1 & T2list, CharmListG1 & T3list, CharmListZR & clist, G1 & g1, G2 & g2, G1 & h, CharmListZR & salphalist, CharmListZR & sbetalist, CharmListZR & sgamma1list, CharmListZR & sgamma2list, CharmListZR & sxlist, G1 & u, G1 & v, G2 & w, list<int> & incorrectIndices)
{
    CharmListZR delta;
    CharmListG1 dotACache;
    CharmListG1 dotBCache;
    CharmListGT dotCCache;
    for (int z = 0; z < N; z++)
    {
        delta[z] = SmallExp(secparam);
    }
    if ( ( (membership(R3list, T1list, T2list, T3list, clist, g1, g2, h, salphalist, sbetalist, sgamma1list, sgamma2list, sxlist, u, v, w)) == (false) ) )
    {
        return false;
    }
    for (int z = 0; z < N; z++)
    {
        if ( ( (precheck(g1, g2, h, u, v, w, Mlist[z], T1list[z], T2list[z], T3list[z], clist[z], salphalist[z], sbetalist[z], sxlist[z], sgamma1list[z], sgamma2list[z], R3list[z])) == (false) ) )
        {
            return false;
        }
    }
    for (int z = 0; z < N; z++)
    {
        dotACache[z] = group.mul(group.exp(T3list[z], group.mul(sxlist[z], delta[z])), group.mul(group.exp(h, group.mul(group.add(group.neg(sgamma1list[z]), group.neg(sgamma2list[z])), delta[z])), group.exp(g1, group.mul(group.neg(clist[z]), delta[z]))));
        dotBCache[z] = group.mul(group.exp(h, group.mul(group.add(group.neg(salphalist[z]), group.neg(sbetalist[z])), delta[z])), group.exp(T3list[z], group.mul(clist[z], delta[z])));
        dotCCache[z] = group.exp(R3list[z], delta[z]);
    }
    dividenconquer(delta, 0, N, incorrectIndices, dotACache, dotBCache, dotCCache, g2, w);
    return true;
}

int main()
{
    CharmList gpk, gmsk;
    CharmListG1 A, T1list, T2list, T3list;
    CharmListZR x, clist, salphalist, sbetalist, sxlist, sgamma1list, sgamma2list;
    CharmListGT R3list;

    keygen(2, gpk, gmsk, A, x);
    G1 A_ind = A[0];
    ZR x_ind = x[0];
    CharmList sig0, sig1;
    string m0 = "message0";
    string m1 = "message1";

    sign(gpk, A_ind, x_ind, m0, sig0);
    sign(gpk, A_ind, x_ind, m1, sig1);

    G1 g1 = gpk[0].getG1();
    G2 g2 = gpk[1].getG2();
    G1 h = gpk[2].getG1();
    G1 u = gpk[3].getG1();
    G1 v = gpk[4].getG1();
    G2 w = gpk[5].getG2();

    T1list[0] = sig0[0].getG1();
    T2list[0] = sig0[1].getG1();
    T3list[0] = sig0[2].getG1();
    clist[0] =  sig0[3].getZR();
    salphalist[0] = sig0[4].getZR();
    sbetalist[0] = sig0[5].getZR();
    sxlist[0] = sig0[6].getZR();
    sgamma1list[0] = sig0[7].getZR();
    sgamma2list[0] = sig0[8].getZR();
    R3list[0] = sig0[9].getGT();

    T1list[1] = sig1[0].getG1();
    T2list[1] = sig1[1].getG1();
    T3list[1] = sig1[2].getG1();
    clist[1] =  sig1[3].getZR();
    salphalist[1] = sig1[4].getZR();
    sbetalist[1] = sig1[5].getZR();
    sxlist[1] = sig1[6].getZR();
    sgamma1list[1] = sig1[7].getZR();
    sgamma2list[1] = sig1[8].getZR();
    R3list[1] = sig1[9].getGT();
    bool status0 = verify(g1, g2, h, u, v, w, m0, T1list[0], T2list[0], T3list[0], clist[0], salphalist[0], sbetalist[0], sxlist[0], sgamma1list[0], sgamma2list[0], R3list[0]);

    if (status0 == true)
        cout << "True" << endl;
    else
        cout << "False" << endl;

    bool status1 = verify(g1, g2, h, u, v, w, m1, T1list[1], T2list[1], T3list[1], clist[1], salphalist[1], sbetalist[1], sxlist[1], sgamma1list[1], sgamma2list[1], R3list[1]);
    if (status1 == true)
        cout << "True" << endl;
    else
        cout << "False" << endl;


    CharmListStr Mlist;
    list<int> incorrectIndices;
    Mlist[0] = m0;
    Mlist[1] = m1;
    batchverify(Mlist, R3list, T1list, T2list, T3list, clist, g1, g2, h, salphalist, sbetalist, sgamma1list, sgamma2list, sxlist, u, v, w, incorrectIndices);

    cout << "Incorrect indices: ";
    for (list<int>::iterator it = incorrectIndices.begin(); it != incorrectIndices.end(); it++)
             cout << *it << " ";
    cout << endl;

    return 0;
}
