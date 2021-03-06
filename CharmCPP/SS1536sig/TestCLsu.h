#ifndef CL04_H
#define CL04_H

#include "Charm.h"
#include <iostream>
#include <sstream>
#include <string>
#include <list>
using namespace std;


class Cl04
{
public:
	PairingGroup group;
	Cl04() { group.setCurve(SS1536); };
	~Cl04() {};
	
	void setup(G1 & g);
	void keygen(G1 & g, CharmList & pk, CharmList & sk, CharmList & chpk);
	void sign(CharmList & chpk, CharmList & sk, string & M, CharmList & sig);
	bool verify(CharmList & chpk, CharmList & pk, G1 & g, string & M, CharmList & sig);
	ZR chamH(CharmList & chpk, ZR & t0, ZR & t1);
};


#endif
