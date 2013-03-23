
#define AES_SECURITY 80
#define MAX_LEN 256

#ifdef ASYMMETRIC
#define MR_PAIRING_MNT	// AES-80 security
#include "pairing_3.h"
#define MNT160 AES_SECURITY
#endif

#ifdef SYMMETRIC
#define MR_PAIRING_SSP
#include "pairing_1.h"
#endif

#include <map>
#include <vector>
#include <string>
#include <fstream>
#include <math.h>

#define ZR Big
#define convert_str(point) point.g
#define stringify(s)  #s
#define setDict(k, v) \
     Element v##_tmp = Element(*v); \
     k.set(stringify(v), v##_tmp);
#define deleteDict(k, v) \
     delete k[v].delGroupElement();

//enum Type { ZR_t = 0, G1_t, G2_t, GT_t, Str_t, None_t };
enum ZR_type { ZR_t = 0, listZR_t = 1 };
enum G1_type { G1_t = 2, listG1_t = 3 };
enum G2_type { G2_t = 4, listG2_t = 5 };
enum GT_type { GT_t = 6, listGT_t = 7 };
enum Str_type { Str_t = 8, listStr_t = 9 };
enum None_type { None_t = 10 };

string _base64_encode(unsigned char const* bytes_to_encode, unsigned int in_len);
string _base64_decode(string const& encoded_string);
bool is_base64(unsigned char c);

class CharmListZR;
class CharmListG1;
class CharmListG2;
class CharmListGT;
class Element;

class CharmList
{
public:
	CharmList(void); // static list
	~CharmList();
    CharmList(const CharmList&); // copy constructor
	// consider adding remove
	void append(const char *);
	void append(string);
	void append(ZR&);
	void append(const ZR&);
	void append(G1&);
	void append(const G1&);
#ifdef ASYMMETRIC
	void append(G2&);
	void append(const G2&);
#endif
	void append(GT&);
	void append(const GT&);
	void append(Element&);
	void append(const Element&);
	void append(const CharmList&);

	void insert(int, const char *);
	void insert(int, string);
	void insert(int, ZR&);
	void insert(int, const ZR&);
	void insert(int, CharmListZR);
	void insert(int, G1&);
	void insert(int, const G1&);
	void insert(int, CharmListG1);
#ifdef ASYMMETRIC
	void insert(int, G2&);
	void insert(int, const G2&);
	void insert(int, CharmListG2);
#endif
	void insert(int, GT&);
	void insert(int, const GT&);
	void insert(int, CharmListGT);
	void insert(int, Element&);
	void insert(int, const Element&);
	//void append(const CharmList&);

	int length(); // return length of lists
	string printAtIndex(int index);

	// retrieve a particular index
	CharmList operator+(const Element&) const;
	CharmList operator+(const CharmList&) const;
	Element& operator[](const int index);
	CharmList& operator=(const CharmList&);
	//Element& operator=(const GT&);
    friend ostream& operator<<(ostream&, const CharmList&);
private:
	int cur_index;
	map<int, Element> list;
};

class CharmListZR
{
public:
	CharmListZR(void); // static list
	~CharmListZR();
    CharmListZR(const CharmListZR&); // copy constructor
    CharmListZR& operator=(const CharmListZR&);
	void insert(int, ZR);
	void append(ZR&);
	void set(int index, ZR);
	ZR& get(const int index);
	int length(); // return length of lists
	string printAtIndex(int index);

	// retrieve a particular index
	ZR& operator[](const int index);

    friend ostream& operator<<(ostream&, const CharmListZR&);
private:
	int cur_index;
	map<int, ZR> list;
};

class CharmListG1
{
public:
	CharmListG1(void); // static list
	~CharmListG1();
    CharmListG1(const CharmListG1&);
	void insert(int, G1);
	void append(G1&);
	void set(int index, G1);
//	G1& get(const int index);
	int length(); // return length of lists
	string printAtIndex(int index);

	// retrieve a particular index
	G1& operator[](const int index);
	CharmListG1& operator=(const CharmListG1&);
    friend ostream& operator<<(ostream&, const CharmListG1&);
private:
	int cur_index;
	map<int, G1> list;
};

class CharmListG2
{
public:
	CharmListG2(void); // static list
	~CharmListG2();
    CharmListG2(const CharmListG2&);
	void insert(int, G2);
	void append(G2&);
	int length(); // return length of lists
	string printAtIndex(int index);

	// retrieve a particular index
	G2& operator[](const int index);
	CharmListG2& operator=(const CharmListG2&);
    friend ostream& operator<<(ostream&, const CharmListG2&);
private:
	int cur_index;
	map<int, G2> list;
};

class CharmListGT
{
public:
	CharmListGT(void);
	~CharmListGT();
    CharmListGT(const CharmListGT&);
	void insert(int, GT&);
	void append(GT&);
	int length(); // return length of lists
	string printAtIndex(int index);

	// retrieve a particular index
	GT& operator[](const int index);
	CharmListGT& operator=(const CharmListGT&);
    friend ostream& operator<<(ostream&, const CharmListGT&);
private:
	int cur_index;
	map<int, GT> list;
};


class Element
{
public:
	// public values for now
	int type;
	ZR zr;
	G1 g1;
	G2 g2;
	GT gt;
	CharmListZR zrList;
	CharmListG1 g1List;
	CharmListG2 g2List;
	CharmListGT gtList;
	string strPtr;
	Element();
	~Element();
	Element(const char *);
	Element(string);
	Element(ZR&);
	Element(CharmListZR&);
	Element(G1&);
	Element(CharmListG1&);
#ifdef ASYMMETRIC
	Element(G2&);
	Element(CharmListG2&);
 	G2 getG2(); // returns value (or copy)
 	CharmListG2 getListG2(); // returns value (or copy)
 	G2& getRefG2(); // returns reference for G2 (for cleanup)
	void createNew(G2);
#endif
	Element(GT&);
	Element(CharmListGT&);
	Element(CharmList&);
 	Element(const Element& e);
 	ZR getZR(); // returns value (or copy)
 	ZR& getRefZR(); // returns reference for ZR (for cleanup)
 	CharmListZR getListZR(); // returns value (or copy)
 	G1 getG1(); // getter methods
 	CharmListG1 getListG1(); // returns value (or copy)
 	G1& getRefG1(); // getter methods
 	GT getGT();
 	CharmListGT getListGT(); // returns value (or copy)
 	GT& getRefGT();
	string str();
	void createNew(ZR&);
	void createNew(G1);
	void createNew(GT);
	//void delGroupElement();

	static string serialize(Element&);
	static void deserialize(Element&, string&);

	CharmList operator+(const Element&) const;       // operator+()
	CharmList operator+(const CharmList&) const;
 	Element operator=(const Element& e);
// 	Element operator=(const GT& g);

    	friend ostream& operator<<(ostream&, const Element&);
private:
    bool isAllocated; // if True, means Element class responsible
    // for releasing the memory.
    // False means Element field just holds a reference
};

string element_to_bytes(Element & e);
void element_from_bytes(Element&, int type, unsigned char *data);

class CharmListStr
{
public:
	CharmListStr(void); // static list
	~CharmListStr();
    CharmListStr(const CharmListStr&); // copy constructor
	void append(string&);
	int length(); // return length of lists
	string printAtIndex(int index);

	// retrieve a particular index
	string& operator[](const int index);
    CharmListStr& operator=(const CharmListStr&);
    friend ostream& operator<<(ostream&, const CharmListStr&);
private:
	int cur_index;
	map<int, string> list;
};

class CharmMetaListZR
{
public:
	CharmMetaListZR(void); // static list
	~CharmMetaListZR();
    CharmMetaListZR(const CharmMetaListZR&); // copy constructor
    CharmMetaListZR& operator=(const CharmMetaListZR&);
	// consider adding remove
	void append(CharmListZR&);

	int length(); // return length of lists
	string printAtIndex(int index);

	// retrieve a particular index
	CharmListZR& operator[](const int index);

    friend ostream& operator<<(ostream&, const CharmMetaListZR&);
private:
	int cur_index;
	map<int, CharmListZR> list;
};

class CharmMetaListG1
{
public:
	CharmMetaListG1(void); // static list
	~CharmMetaListG1();
    CharmMetaListG1(const CharmMetaListG1&); // copy constructor
    CharmMetaListG1& operator=(const CharmMetaListG1&);

	// consider adding remove
	void append(CharmListG1&);

	int length(); // return length of lists
	string printAtIndex(int index);

	// retrieve a particular index
	CharmListG1& operator[](const int index);

    friend ostream& operator<<(ostream&, const CharmMetaListG1&);
private:
	int cur_index;
	map<int, CharmListG1> list;
};

class CharmMetaListG2
{
public:
	CharmMetaListG2(void); // static list
	~CharmMetaListG2();
    CharmMetaListG2(const CharmMetaListG2&); // copy constructor
    CharmMetaListG2& operator=(const CharmMetaListG2&);

	// consider adding remove
	void append(CharmListG2&);

	int length(); // return length of lists
	string printAtIndex(int index);

	// retrieve a particular index
	CharmListG2& operator[](const int index);

    friend ostream& operator<<(ostream&, const CharmMetaListG2&);
private:
	int cur_index;
	map<int, CharmListG2> list;
};

class CharmMetaListGT
{
public:
	CharmMetaListGT(void); // static list
	~CharmMetaListGT();
    CharmMetaListGT(const CharmMetaListGT&); // copy constructor
    CharmMetaListGT& operator=(const CharmMetaListGT&);
	// consider adding remove
	void append(CharmListGT&);

	int length(); // return length of lists
	string printAtIndex(int index);

	// retrieve a particular index
	CharmListGT& operator[](const int index);

    friend ostream& operator<<(ostream&, const CharmMetaListGT&);
private:
	int cur_index;
	map<int, CharmListGT> list;
};


struct cmp_str
{
	bool operator()(const string a, const string b) {
		return strcmp(a.c_str(), b.c_str()) < 0;
	}
};

class CharmDict
{
public:
	CharmDict(void); // static list
	~CharmDict();
	// consider adding remove
	void set(string key, Element& value);
	int length(); // return length of lists
	CharmList keys(); // vector<string>
	string printAll();

	// retrieve a particular index
	Element& operator[](const string key);
    friend ostream& operator<<(ostream&, const CharmDict&);

private:
	map<string, Element, cmp_str> emap;
};

#define DeriveKey	group.aes_key

/* @description: wrapper around the MIRACL provided pairing-friendly class */
/* PairingGroup conforms to Charm-C++ API.
 */
class PairingGroup
{
public:
	PairingGroup(int);
	~PairingGroup();
	// generate random
	void init(ZR&, char*);
	void init(ZR&, int);
//	ZR* init(ZR_type);
//	ZR* init(ZR_type, int);
//	G1* init(G1_type);
//	G1* init(G1_type, int);
	void init(G1&, int);
//	GT* init(GT_type);
//	GT* init(GT_type, int);
	void init(GT&, int);

	ZR init(ZR_type);
	ZR init(ZR_type, int);
	G1 init(G1_type);
	G1 init(G1_type, int);
	GT init(GT_type);
	GT init(GT_type, int);

	ZR random(ZR_type);
	G1 random(G1_type);
	GT random(GT_type);
	bool ismember(CharmMetaListZR&);
	bool ismember(CharmMetaListG1&);
	bool ismember(CharmMetaListG2&);
	bool ismember(CharmMetaListGT&);
	bool ismember(CharmList&);
	bool ismember(CharmListStr&);
	bool ismember(CharmListZR&);
	bool ismember(CharmListG1&);
	bool ismember(CharmListG2&);
	bool ismember(CharmListGT&);
	bool ismember(ZR&);
	bool ismember(G1&);
	bool ismember(GT&);

#ifdef ASYMMETRIC
//	G2* init(G2_type);
//	G2* init(G2_type, int);
	G2 init(G2_type);
	G2 init(G2_type, int);
	void init(G2&, int);
	G2 random(G2_type);
	bool ismember(G2&);
	G2 mul(G2, G2);
	G2 div(G2, G2);
	G2 exp(G2, ZR);
	G2 exp(G2, int);
	GT pair(G1, G2);
#endif

	Big order(); // returns the order of the group

	// hash -- not done
	ZR hashListToZR(string);
	G1 hashListToG1(string);
	G2 hashListToG2(string);

	ZR hashListToZR(CharmList);
	G1 hashListToG1(CharmList);
	G2 hashListToG2(CharmList);

	GT pair(G1, G1);
	int mul(int, int);
	ZR mul(ZR, ZR);
	G1 mul(G1, G1);
	GT mul(GT, GT);
	int div(int, int);
	ZR div(int, ZR);
	ZR div(ZR, ZR);
	G1 div(G1, G1);
	GT div(GT, GT);

	ZR exp(ZR, int);
	ZR exp(ZR, ZR);
	G1 exp(G1, ZR);
	G1 exp(G1, int);
	GT exp(GT, ZR);
	GT exp(GT, int);

	ZR add(ZR, ZR);
	int add(int, int);

	int sub(int, int);
	ZR sub(ZR, ZR);
	ZR neg(ZR);
	ZR inv(ZR);
	string aes_key(GT & g);

private:
	PFC *pfcObject; // defined by above #defines SYMMETRIC or ASYMMETRIC (for now)
	GT *gt, *gt_id;
};

#define aes_block_size 16

class SymmetricEnc
{
public:
	SymmetricEnc(); // take Mode,
	~SymmetricEnc();
	// wrapper around AES code
	string encrypt(char *key, char *message, int len); // generate iv internally
	string decrypt(char *key, char *ciphertext, int len);
	static string pad(string s);

private:
	int keysize;
	int mode;
	char iv[aes_block_size];
	bool aes_initialized;
	aes a;
};

// to support codegen
ZR SmallExp(int bits);
void parsePartCT(const char *filename, CharmDict & d);
void parseKeys(const char *filename, ZR & sk, GT & pk);
string SymDec(string k, string c_encoded);
bool isNotEqual(string value1, string value2);
void stringToInt(PairingGroup & group, string strID, int z, int l, CharmListZR & zrlist);
CharmListZR stringToInt(PairingGroup & group, string strID, int z, int l);
string concat(CharmListStr & list);
ZR ceillog(int base, int value);

