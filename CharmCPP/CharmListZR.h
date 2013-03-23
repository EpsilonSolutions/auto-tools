#ifndef CHARMLISTZR_H
#define CHARMLISTZR_H

#include "CryptoLib.h"
#include "CharmListStr.h"

struct zr_cmp_str
{
	bool operator()(const string a, const string b) {
		return strcmp(a.c_str(), b.c_str()) < 0;
	}
};

class CharmListZR
{
public:
	CharmListZR(void); // static list
	~CharmListZR();
    CharmListZR(const CharmListZR&); // copy constructor
    CharmListZR& operator=(const CharmListZR&);
	void insert(int, ZR);
	void insert(int, ZR, string);
	void insert(string, ZR);
	void append(ZR&);
	void set(int index, ZR);
	ZR& get(const int index);
	CharmListStr strkeys();
	int length(); // return length of lists
	string printAtIndex(int index);
	string printStrKeyIndex(int index);
	// retrieve a particular index
	ZR& operator[](const string index);
	ZR& operator[](const int index);
    friend ostream& operator<<(ostream&, const CharmListZR&);
private:
	int cur_index;
	map<int, ZR> list;
	map<string, int, zr_cmp_str> strList;
};

class CharmMetaListZR
{
public:
	CharmMetaListZR(void); // static list
	~CharmMetaListZR();
    CharmMetaListZR(const CharmMetaListZR&); // copy constructor
    CharmMetaListZR& operator=(const CharmMetaListZR&);

	// consider adding remove
	void insert(int, CharmListZR);
	void insert(string, CharmListZR);
	void append(CharmListZR&);

	int length(); // return length of lists
	string printAtIndex(int index);
	string printStrKeyIndex(int index);
	// retrieve a particular index
	CharmListZR& operator[](const int index);
	CharmListZR& operator[](const string index);

    friend ostream& operator<<(ostream&, const CharmMetaListZR&);
private:
	int cur_index;
	map<int, CharmListZR> list;
	map<string, int, zr_cmp_str> strList;
};

#endif
