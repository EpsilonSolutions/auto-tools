#include "sdlconfig.h"
#include "miracl.h"
#include <sstream>

#define MAX_LIST 100

/* helper methods to assist with serializing and base-64 encoding group elements */
static const string base64_chars =
             "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
             "abcdefghijklmnopqrstuvwxyz"
             "0123456789+/";

/* Note that the following was borrowed from Copyright (C) 2004-2008 Ren� Nyffenegger (*/

bool is_base64(unsigned char c) {
  return (isalnum(c) || (c == '+') || (c == '/'));
}

string _base64_encode(unsigned char const* bytes_to_encode, unsigned int in_len) {
  string ret;
  int i = 0;
  int j = 0;
  unsigned char char_array_3[3];
  unsigned char char_array_4[4];

  while (in_len--) {
    char_array_3[i++] = *(bytes_to_encode++);
    if (i == 3) {
      char_array_4[0] = (char_array_3[0] & 0xfc) >> 2;
      char_array_4[1] = ((char_array_3[0] & 0x03) << 4) + ((char_array_3[1] & 0xf0) >> 4);
      char_array_4[2] = ((char_array_3[1] & 0x0f) << 2) + ((char_array_3[2] & 0xc0) >> 6);
      char_array_4[3] = char_array_3[2] & 0x3f;

      for(i = 0; (i <4) ; i++)
        ret += base64_chars[char_array_4[i]];
      i = 0;
    }
  }

  if (i)
  {
    for(j = i; j < 3; j++)
      char_array_3[j] = '\0';

    char_array_4[0] = (char_array_3[0] & 0xfc) >> 2;
    char_array_4[1] = ((char_array_3[0] & 0x03) << 4) + ((char_array_3[1] & 0xf0) >> 4);
    char_array_4[2] = ((char_array_3[1] & 0x0f) << 2) + ((char_array_3[2] & 0xc0) >> 6);
    char_array_4[3] = char_array_3[2] & 0x3f;

    for (j = 0; (j < i + 1); j++)
      ret += base64_chars[char_array_4[j]];

    while((i++ < 3))
      ret += '=';

  }

  return ret;

}

string _base64_decode(string const& encoded_string) {
  int in_len = encoded_string.size();
  int i = 0;
  int j = 0;
  int in_ = 0;
  unsigned char char_array_4[4], char_array_3[3];
  std::string ret;

  while (in_len-- && ( encoded_string[in_] != '=') && is_base64(encoded_string[in_])) {
    char_array_4[i++] = encoded_string[in_]; in_++;
    if (i ==4) {
      for (i = 0; i <4; i++)
        char_array_4[i] = base64_chars.find(char_array_4[i]);

      char_array_3[0] = (char_array_4[0] << 2) + ((char_array_4[1] & 0x30) >> 4);
      char_array_3[1] = ((char_array_4[1] & 0xf) << 4) + ((char_array_4[2] & 0x3c) >> 2);
      char_array_3[2] = ((char_array_4[2] & 0x3) << 6) + char_array_4[3];

      for (i = 0; (i < 3); i++)
        ret += char_array_3[i];
      i = 0;
    }
  }

  if (i) {
    for (j = i; j <4; j++)
      char_array_4[j] = 0;

    for (j = 0; j <4; j++)
      char_array_4[j] = base64_chars.find(char_array_4[j]);

    char_array_3[0] = (char_array_4[0] << 2) + ((char_array_4[1] & 0x30) >> 4);
    char_array_3[1] = ((char_array_4[1] & 0xf) << 4) + ((char_array_4[2] & 0x3c) >> 2);
    char_array_3[2] = ((char_array_4[2] & 0x3) << 6) + char_array_4[3];

    for (j = 0; (j < i - 1); j++) ret += char_array_3[j];
  }

  return ret;
}

char *convert_buffer_to_hex(uint8_t * data, size_t len)
{
	size_t i;
	char tmp1[3];
	char *tmp = (char *) malloc(len * 3);
	memset(tmp, 0, len*3 - 1);

	for (i = 0; i < len; i++) {
		snprintf(tmp1, 3, "%02x ", data[i]);
		strcat(tmp, tmp1);
	}

	return tmp;
}

// Element implementation
Element::Element()
{
	type = None_t;
	isAllocated = false;
}

Element::Element(const char *s)
{
	type = Str_t;
	strPtr = string(s);
}

Element::Element(string s)
{
	type = Str_t;
	strPtr = s;
}

Element::Element(ZR & z)
{
	type = ZR_t;
	zr   = z;
	isAllocated = false;
}

Element::Element(CharmListZR & zList)
{
	type 	 = listZR_t;
	zrList   = zList;
	isAllocated = false;
}

Element::Element(CharmListG1 & gList)
{
	type 	 = listG1_t;
	g1List   = gList;
	isAllocated = false;
}

Element::Element(CharmListGT & gList)
{
	type 	 = listGT_t;
	gtList   = gList;
	isAllocated = false;
}

void Element::createNew(ZR &z)
{
	type = ZR_t;
	zr   = z; // new ZR(z);
	isAllocated = true;
}

Element::Element(G1 & g)
{
	type = G1_t;
	g1   = g;
	isAllocated = false;
}

void Element::createNew(G1 g)
{
	type = G1_t;
	g1   = g; // new G1(g);
}

Element::Element(G2 & g)
{
	type = G2_t;
	g2   = g;
	isAllocated = false;
}

void Element::createNew(G2 g)
{
	type = G2_t;
	g2   = g; // new G2(g);
	isAllocated = true;
}

Element::Element(GT & g)
{
	type = GT_t;
	gt   = g;
	isAllocated = false;
}

void Element::createNew(GT g)
{
	type = GT_t;
	gt   = g; // new GT(g);
	isAllocated = true;
}

Element::Element(const Element& e)
{
	type = e.type;
	if(type == Str_t)
		strPtr = e.strPtr;
	else if(type == ZR_t)
		zr = e.zr;
	else if(type == listZR_t)
		zrList = e.zrList;
	else if(type == G1_t)
		g1 = e.g1;
	else if(type == listG1_t)
		g1List = e.g1List;
	else if(type == G2_t)
		g2 = e.g2;
	else if(type == listG2_t)
		g2List = e.g2List;
	else if(type == GT_t)
		gt = e.gt;
	else if(type == listGT_t)
		gtList = e.gtList;

	isAllocated = false; // in case e.createNew() was called.
}

ZR Element::getZR()
{
	if(type == ZR_t) return zr;
	throw new string("invalid type.");
}

CharmListZR Element::getListZR()
{
	if(type == listZR_t) return zrList;
	throw new string("invalid type.");
}


ZR & Element::getRefZR()
{
	if(type == ZR_t) return zr;
	throw new string("invalid type.");
}

G1 Element::getG1()
{
	if(type == G1_t) return g1;
	throw new string("invalid type.");
}

CharmListG1 Element::getListG1()
{
	if(type == listG1_t) return g1List;
	throw new string("invalid type.");
}


#ifdef ASYMMETRIC
Element::Element(CharmListG2 & gList)
{
	type 	 = listG2_t;
	g2List   = gList;
	isAllocated = false;
}

G2 Element::getG2()
{
	if(type == G2_t) return g2;
	throw new string("invalid type.");
}

CharmListG2 Element::getListG2()
{
	if(type == listG2_t) return g2List;
	throw new string("invalid type.");
}

G2 & Element::getRefG2()
{
	if(type == G2_t) return g2;
	throw new string("invalid type.");
}
#endif

GT Element::getGT()
{
	if(type == GT_t) return gt;
	throw new string("invalid type.");
}

CharmListGT Element::getListGT()
{
	if(type == listGT_t) return gtList;
	throw new string("invalid type.");
}

string Element::str()
{
	stringstream ss;
	if(type == Str_t)
		ss << strPtr;
	else if(type == ZR_t)
		ss << zr;
	else if(type == listZR_t)
		ss << zrList;
	else if(type == G1_t)
		ss << g1.g;
	else if(type == listG1_t)
		ss << g1List;
	else if(type == G2_t)
		ss << g2.g;
	else if(type == listG2_t)
		ss << g2List;
	else if(type == GT_t)
		ss << gt.g;
	else if(type == listGT_t)
		ss << gtList;
	return ss.str();
}

Element::~Element()
{
	if(type == ZR_t && isAllocated) {
//		delete zr;
	}
	if(type == G1_t && isAllocated) {
//		delete g1;
	}
	if(type == G2_t && isAllocated) {
//		delete g2;
	}
	if(type == GT_t && isAllocated) {
//		delete gt;
	}
}

//void Element::delGroupElement()
//{
//	if(type == ZR_t)
//	    delete zr;
//	else if(type == G1_t)
//	    delete g1;
//	else if(type == G2_t)
//	    delete g2;
//	else if(type == GT_t)
//	    delete gt;
//}

Element Element::operator=(const Element& e)
{
	if(this == &e)
		return *this;

	type = e.type;
	if(type == Str_t)
		strPtr = e.strPtr;
	else if(type == ZR_t)
		zr = e.zr;
	else if(type == listZR_t)
		zrList = e.zrList;
	else if(type == G1_t)
		g1 = e.g1;
	else if(type == listG1_t)
		g1List = e.g1List;
	else if(type == G2_t)
		g2 = e.g2;
	else if(type == listG2_t)
		g2List = e.g2List;
	else if(type == GT_t)
		gt = e.gt;
	else if(type == listGT_t)
		gtList = e.gtList;

	isAllocated = false; // in case e.createNew() was called.
	return *this;
}

CharmList Element::operator+ (const Element& e) const
{
	CharmList c;
	if (this->type == Str_t)
	      	c.append(this->strPtr);
	else if(this->type == ZR_t)
		c.append(this->zr);
	else if(this->type == G1_t)
		c.append(this->g1);
	else if(this->type == G2_t)
		c.append(this->g2);
	else if(this->type == GT_t)
		c.append(this->gt);

	if (e.type == Str_t)
     	c.append(e.strPtr);
	else if(e.type == ZR_t)
		c.append(e.zr);
	else if(e.type == G1_t)
		c.append(e.g1);
	else if(e.type == G2_t)
		c.append(e.g2);
	else if(e.type == GT_t)
		c.append(e.gt);

	return c;
}

CharmList Element::operator+(const CharmList& c) const
{
	CharmList c2 = c;
	CharmList result;
	Element e2 = *this;

	result.append(e2);
	result.append(c2);

	return result;
}

ostream& operator<<(ostream& s, const Element& e)
{
	Element e2 = e;
	int t = e2.type;
	if(t == Str_t)
		s << "str: ";
	else if(t == ZR_t)
		s << "ZR: ";
	else if(t == G1_t)
		s << "G1: ";
#ifdef ASYMMETRIC
	else if(t == G2_t)
		s << "G2: ";
#endif
	else if(t == GT_t)
		s << "GT: ";
	s << e2.str();

	return s;
}

string Element::serialize(Element & e)
{
	stringstream eSerialized;
	eSerialized << e.type << ":";
	if(e.type == Str_t)
		eSerialized << e.strPtr;
	else
		eSerialized << element_to_bytes(e);
	return eSerialized.str();
}

//TODO: add thorough error checking to deserialize functions
void Element::deserialize(Element & e, string & s)
{
	size_t found = s.find(':'); // delimeter

	if(found != string::npos) {
		int type = atoi(s.substr(0, found).c_str());
		if(type >= ZR_t && type < Str_t) {
			element_from_bytes(e, (int) type, (unsigned char *) s.substr(found+1, s.size()).c_str());
		}
		else if(type == Str_t) {
			e = Element(s.substr(found+1, s.size()).c_str());
		}
		return;
	}
	else {
		e = Element(s); // default to a string
		return;
	}

	throw new string("Invalid bytes.\n");
}

// end Element implementation

// start CharmList implementation

CharmList::CharmList(void)
{
	// increases as elements are appended
	cur_index = 0;
}

CharmList::~CharmList()
{
	for(int i = 0; i < (int) list.size(); i++)
		list.erase(i);
}

CharmList::CharmList(const CharmList& cList)
{
	//copy constructor
	cur_index = cList.cur_index;
	list = cList.list;
}

void CharmList::insert(int index, const char *s)
{
	Element elem(s);
	list[index] = elem;
	cur_index++;
}

void CharmList::append(const char *s)
{
	Element elem(s);
	list[cur_index] = elem;
	cur_index++;
}

void CharmList::insert(int index, string strs)
{
	Element elem(strs);
	list[index] = elem;
	cur_index++;
}


void CharmList::append(string strs)
{
	Element elem(strs);
	list[cur_index] = elem;
	cur_index++;
}

void CharmList::insert(int index, ZR & zr)
{
	Element elem(zr);
	list[index] = elem;
	cur_index++;
}



void CharmList::append(ZR & zr)
{
	Element elem(zr);
	list[cur_index] = elem;
	cur_index++;
}

void CharmList::insert(int index, const ZR & zr)
{
	ZR zr_1 = zr;
	Element elem(zr_1);
	list[index] = elem;
	cur_index++;
}

void CharmList::append(const ZR & zr)
{
	ZR zr_1 = zr;
	Element elem(zr_1);
	list[cur_index] = elem;
	cur_index++;
}

void CharmList::insert(int index, G1 & g1)
{
	Element elem(g1);
	list[index] = elem;
	cur_index++;
}

void CharmList::append(G1 & g1)
{
	Element elem(g1);
	list[cur_index] = elem;
	cur_index++;
}

void CharmList::insert(int index, const G1 & g1)
{
	G1 g1_1 = g1;
	Element elem(g1_1);
	list[index] = elem;
	cur_index++;
}

void CharmList::append(const G1 & g1)
{
	G1 g1_1 = g1;
	Element elem(g1_1);
	list[cur_index] = elem;
	cur_index++;
}


#ifdef ASYMMETRIC
void CharmList::insert(int index, G2 & g2)
{
	Element elem(g2);
	list[index] = elem;
	cur_index++;
}

void CharmList::append(G2 & g2)
{
	Element elem(g2);
	list[cur_index] = elem;
	cur_index++;
}

void CharmList::insert(int index, const G2 & g2)
{
	G2 g2_1 = g2;
	Element elem(g2_1);
	list[index] = elem;
	cur_index++;
}

void CharmList::append(const G2 & g2)
{
	G2 g2_1 = g2;
	Element elem(g2_1);
	list[cur_index] = elem;
	cur_index++;
}

#endif

void CharmList::insert(int index, GT & gt)
{
	Element elem(gt);
	list[index] = elem;
	cur_index++;
}

void CharmList::append(GT & gt)
{
	Element elem(gt);
	list[cur_index] = elem;
	cur_index++;
}

void CharmList::insert(int index, const GT & gt)
{
	GT gt_1 = gt;
	Element elem(gt_1);
	list[index] = elem;
	cur_index++;
}

void CharmList::append(const GT & gt)
{
	GT gt_1 = gt;
	Element elem(gt_1);
	list[cur_index] = elem;
	cur_index++;
}


void CharmList::insert(int index, Element & e)
{
	list[index] = e;
	cur_index++;
}

void CharmList::append(Element & e)
{
	list[cur_index] = e;
	cur_index++;
}

void CharmList::insert(int index, const Element & e)
{
	Element e1 = e;
	list[index] = e1;
	cur_index++;
}

void CharmList::append(const Element & e)
{
	Element e1 = e;
	list[cur_index] = e1;
	cur_index++;
}


void CharmList::append(const CharmList & c)
{
	CharmList c2 = c;
	for(int i = 0; i < (int) c2.length(); i++) {
		list[cur_index] = c2[i];
		cur_index++;
	}
}

void CharmList::insert(int index, CharmListZR c)
{
	CharmListZR c2 = c;
	Element elem(c2);
	list[index] = elem;
	cur_index++;
}

void CharmList::insert(int index, CharmListG1 c)
{
	CharmListG1 c2 = c;
	Element elem(c2);
	list[index] = elem;
	cur_index++;
}
#ifdef ASYMMETRIC
void CharmList::insert(int index, CharmListG2 c)
{
	CharmListG2 c2 = c;
	Element elem(c2);
	list[index] = elem;
	cur_index++;
}
#endif

void CharmList::insert(int index, CharmListGT c)
{
	CharmListGT c2 = c;
	Element elem(c2);
	list[index] = elem;
	cur_index++;
}

Element& CharmList::operator[](const int index)
{
	int len = (int) list.size();
	if(index >= 0 && index < len) {
		return list[index];
	}
	else {
		throw new string("Invalid access.\n");
	}
}

CharmList& CharmList::operator=(const CharmList& cList)
{
	if(this == &cList)
		return *this;

	// delete current list contents first
	int i;
	for(i = 0; i < (int) list.size(); i++)
		list.erase(i);
	cur_index = 0;

	cur_index = cList.cur_index;
	list = cList.list;
	return *this;
}

int CharmList::length()
{
	return (int) list.size();
}

CharmList CharmList::operator+(const Element& e) const
{
	CharmList result;
	Element e2 = e;
	result.append(*this);
	result.append(e2);
	return result;
}

CharmList CharmList::operator+(const CharmList& r) const
{
	CharmList result;
	result.append(*this);
	result.append(r);

	return result;
}

ostream& operator<<(ostream& s, const CharmList& cList)
{
	CharmList cList2 = cList;
	for(int i = 0; i < cList2.length(); i++) {
		s << "[" << i << "]:" << cList2.printAtIndex(i) << endl;
	}

	return s;
}

string CharmList::printAtIndex(int index)
{
	stringstream ss;
	int i;

	if(index >= 0 && index < (int) list.size()) {
		i = index;
		int t = list[i].type;
		if(t == Str_t) {
			ss << list[i].strPtr;
		}
		else if(t == ZR_t) {
			ss << list[i].zr;
		}
		else if(t == listZR_t) {
			ss << "ZR list\n" << list[i].zrList;
		}
		else if(t == G1_t) {
			ss << list[i].g1.g;
		}
		else if(t == listG1_t) {
			ss << "G1 list\n" << list[i].g1List;
		}
#ifdef ASYMMETRIC
		else if(t == G2_t) {
			ss << list[i].g2.g;
		}
		else if(t == listG2_t) {
			ss << "G2 list\n" << list[i].g2List;
		}
#endif
		else if(t == GT_t) {
			ss << list[i].gt.g;
		}
		else if(t == listGT_t) {
			ss << "GT list\n" << list[i].gtList;
		}
	}

	string s = ss.str();
	return s;
}

// end CharmList implementation

// start CharmListStr implementation

CharmListStr::CharmListStr(void)
{
	// increases as elements are appended
	cur_index = 0;
}

CharmListStr::~CharmListStr()
{
	for(int i = 0; i < (int) list.size(); i++)
		list.erase(i);
}

CharmListStr::CharmListStr(const CharmListStr& cList)
{
	//copy constructor
	cur_index = cList.cur_index;
	list = cList.list;
}

void CharmListStr::append(string & s)
{
	list[cur_index] = s;
	cur_index++;
}

string& CharmListStr::operator[](const int index)
{
	if(index == cur_index) { // means we are creating reference.
		string s;
		list[cur_index] = s; // create tmp value
		cur_index++;
		return list[index];
	}

	int len = (int) list.size();
	if(index >= 0 && index < len) {
		return list[index];
	}
	else {
		throw new string("Invalid access.\n");
	}
}

CharmListStr& CharmListStr::operator=(const CharmListStr& cList)
{
	if(this == &cList)
		return *this;

	// delete current list contents first
	int i;
	for(i = 0; i < (int) list.size(); i++)
		list.erase(i);
	cur_index = 0;

	cur_index = cList.cur_index;
	list = cList.list;
	return *this;
}

int CharmListStr::length()
{
	return (int) list.size();
}

string CharmListStr::printAtIndex(int index)
{
	stringstream ss;
	int i;

	if(index >= 0 && index < (int) list.size()) {
		i = index;
		ss << list[i];
	}

	string s = ss.str();
	return s;
}

ostream& operator<<(ostream& s, const CharmListStr& cList)
{
	CharmListStr cList2 = cList;
	for(int i = 0; i < cList2.length(); i++) {
		s << i << ": " << cList2.printAtIndex(i) << endl;
	}

	return s;
}

// end CharmListStr implementation


// start CharmListZR implementation

CharmListZR::CharmListZR(void)
{
	// increases as elements are appended
	cur_index = 0;
}

CharmListZR::~CharmListZR()
{
	for(int i = 0; i < (int) list.size(); i++)
		list.erase(i);
}

CharmListZR::CharmListZR(const CharmListZR& cList)
{
	//copy constructor
	cur_index = cList.cur_index;
	list = cList.list;
}

void CharmListZR::insert(int index, ZR zr)
{
	list[index] = zr;
	cur_index++;
}

void CharmListZR::append(ZR & zr)
{
	list[cur_index] = zr;
	cur_index++;
}

void CharmListZR::set(int index, ZR zr)
{
	ZR *zr2 = new ZR(zr);
	list[index] = *zr2;
}

ZR& CharmListZR::operator[](const int index)
{
	if(index == cur_index) { // means we are creating reference.
		list[cur_index] = NULL;
		cur_index++;
		return list[index];
	}
	else if(index < MAX_LIST) {
		return list[index];
	}

	int len = (int) list.size();
	if(index >= 0 && index < len) {
		return list[index];
	}
	else {
		throw new string("Invalid access.\n");
	}
}

ZR& CharmListZR::get(const int index)
{
	int len = (int) list.size();
	if(index >= 0 && index < len) {
		return list[index];
	}
	else {
		throw new string("Invalid access.\n");
	}
}

int CharmListZR::length()
{
	return (int) list.size();
}

string CharmListZR::printAtIndex(int index)
{
	stringstream ss;
	int i;

	if(index >= 0 && index < (int) list.size()) {
		i = index;
		ss << list[i];
	}

	string s = ss.str();
	return s;
}

ostream& operator<<(ostream& s, const CharmListZR& cList)
{
	CharmListZR cList2 = cList;

	for(int i = 0; i < cList2.length(); i++) {
		s << i << ": " << cList2.printAtIndex(i) << endl;
	}

	return s;
}

CharmListZR& CharmListZR::operator=(const CharmListZR& cList)
{
	if(this == &cList)
		return *this;

	// delete current list contents first
	int i;
	for(i = 0; i < (int) list.size(); i++)
		list.erase(i);
	cur_index = 0;

	cur_index = cList.cur_index;
	list = cList.list;
	return *this;
}

// end CharmListZR implementation

// start CharmMetaListZR implementation

CharmMetaListZR::CharmMetaListZR(void)
{
	// increases as elements are appended
	cur_index = 0;
}

CharmMetaListZR::~CharmMetaListZR()
{
	for(int i = 0; i < (int) list.size(); i++)
		list.erase(i);
}

CharmMetaListZR::CharmMetaListZR(const CharmMetaListZR& cList)
{
	//copy constructor
	cur_index = cList.cur_index;
	list = cList.list;
}

void CharmMetaListZR::append(CharmListZR & zr)
{
	list[cur_index] = zr;
	cur_index++;
}

CharmListZR& CharmMetaListZR::operator[](const int index)
{
	if(index == cur_index) { // means we are creating reference.
//		CharmListZR tmp;
//		list[cur_index] = tmp;
		cur_index++;
		return list[index];
	}

	int len = (int) list.size();
	if(index >= 0 && index < len) {
		return list[index];
	}
	else {
		throw new string("Invalid access.\n");
	}
}

int CharmMetaListZR::length()
{
	return (int) list.size();
}

string CharmMetaListZR::printAtIndex(int index)
{
	stringstream ss;
	int i;

	if(index >= 0 && index < (int) list.size()) {
		i = index;
		ss << list[i];
	}

	string s = ss.str();
	return s;
}

ostream& operator<<(ostream& s, const CharmMetaListZR& cList)
{
	CharmMetaListZR cList2 = cList;
	for(int i = 0; i < cList2.length(); i++) {
		s << "list " << i << "\n";
		s << cList2.printAtIndex(i) << endl;
	}

	return s;
}

CharmMetaListZR& CharmMetaListZR::operator=(const CharmMetaListZR& cList)
{
	if(this == &cList)
		return *this;

	// delete current list contents first
	int i;
	for(i = 0; i < (int) list.size(); i++)
		list.erase(i);
	cur_index = 0;

	cur_index = cList.cur_index;
	list = cList.list;
	return *this;
}


// end CharmMetaListZR implementation


// start CharmListG1 implementation

CharmListG1::CharmListG1(void)
{
	// increases as elements are appended
	cur_index = 0;
}

CharmListG1::~CharmListG1()
{
	for(int i = 0; i < (int) list.size(); i++)
		list.erase(i);
}

CharmListG1::CharmListG1(const CharmListG1& cList)
{
	//copy constructor
	cur_index = cList.cur_index;
	list = cList.list;
}

void CharmListG1::insert(int index, G1 g)
{
	list[index] = g;
	cur_index++;
}

void CharmListG1::append(G1 & g)
{
	list[cur_index] = g;
	cur_index++;
}

void CharmListG1::set(int index, G1 g1)
{
	G1 *g = new G1(g1);
	list[index] = *g;
}

//G1& CharmListG1::get(const int index)
//{
//	int len = (int) list.size();
//	if(index >= 0 && index < len) {
//		return list[index];
//	}
//	else {
//		throw new string("Invalid access.\n");
//	}
//}

G1& CharmListG1::operator[](const int index)
{
	if(index == cur_index) { // means we are creating reference.
//		G1 tmp;
//		list[cur_index] = tmp;
		cur_index++;
		return list[index];
	}
	else if(index < MAX_LIST) {
		return list[index];
	}

	int len = (int) list.size();
	if(index >= 0 && index < len) {
		return list[index];
	}
	else {
		throw new string("Invalid access.\n");
	}
}

//CharmListG1& CharmListG1::operator=(const CharmListG1 & newList)
//{
//    list = newList.list;
//    return *this;
//}

CharmListG1& CharmListG1::operator=(const CharmListG1& cList)
{
	if(this == &cList)
		return *this;

	// delete current list contents first
	int i;
	for(i = 0; i < (int) list.size(); i++)
		list.erase(i);
	cur_index = 0;

	cur_index = cList.cur_index;
	list = cList.list;
	return *this;
}


int CharmListG1::length()
{
	return (int) list.size();
}

string CharmListG1::printAtIndex(int index)
{
	stringstream ss;
	int i;

	if(index >= 0 && index < (int) list.size()) {
		i = index;
		ss << list[i].g;
	}

	string s = ss.str();
	return s;
}

ostream& operator<<(ostream& s, const CharmListG1& cList)
{
	CharmListG1 cList2 = cList;
	for(int i = 0; i < cList2.length(); i++) {
		s << i << ": " << cList2.printAtIndex(i) << endl;
	}

	return s;
}

// end CharmListG1 implementation

// start CharmMetaListG1 implementation

CharmMetaListG1::CharmMetaListG1(void)
{
	// increases as elements are appended
	cur_index = 0;
}

CharmMetaListG1::~CharmMetaListG1()
{
	for(int i = 0; i < (int) list.size(); i++)
		list.erase(i);
}

CharmMetaListG1::CharmMetaListG1(const CharmMetaListG1& cList)
{
	//copy constructor
	cur_index = cList.cur_index;
	list = cList.list;
}

void CharmMetaListG1::append(CharmListG1 & zr)
{
	list[cur_index] = zr;
	cur_index++;
}

CharmListG1& CharmMetaListG1::operator[](const int index)
{
	if(index == cur_index) { // means we are creating reference.
		CharmListG1 tmp;
		list[cur_index] = tmp;
		cur_index++;
		return list[index];
	}

	int len = (int) list.size();
	if(index >= 0 && index < len) {
		return list[index];
	}
	else {
		throw new string("Invalid access.\n");
	}
}

int CharmMetaListG1::length()
{
	return (int) list.size();
}

string CharmMetaListG1::printAtIndex(int index)
{
	stringstream ss;
	int i;

	if(index >= 0 && index < (int) list.size()) {
		i = index;
		ss << list[i];
	}

	string s = ss.str();
	return s;
}

ostream& operator<<(ostream& s, const CharmMetaListG1& cList)
{
	CharmMetaListG1 cList2 = cList;
	for(int i = 0; i < cList2.length(); i++) {
		s << "list " << i << "\n";
		s << cList2.printAtIndex(i) << endl;
	}

	return s;
}

CharmMetaListG1& CharmMetaListG1::operator=(const CharmMetaListG1& cList)
{
	if(this == &cList)
		return *this;

	// delete current list contents first
	int i;
	for(i = 0; i < (int) list.size(); i++)
		list.erase(i);
	cur_index = 0;

	cur_index = cList.cur_index;
	list = cList.list;
	return *this;
}

// end CharmMetaListG1 implementation


// start CharmListG2 implementation

CharmListG2::CharmListG2(void)
{
	// increases as elements are appended
	cur_index = 0;
}

CharmListG2::~CharmListG2()
{
	for(int i = 0; i < (int) list.size(); i++)
		list.erase(i);
}

CharmListG2::CharmListG2(const CharmListG2& cList)
{
	//copy constructor
	cur_index = cList.cur_index;
	list = cList.list;
}

void CharmListG2::insert(int index, G2 g)
{
	list[index] = g;
	cur_index++;
}

void CharmListG2::append(G2 & g)
{
	list[cur_index] = g;
	cur_index++;
}

G2& CharmListG2::operator[](const int index)
{
	if(index == cur_index) { // means we are creating reference.
//		G2 tmp;
//		list[cur_index] = tmp; // this type will disappear and just for creating reference only. caller expected to set result
		cur_index++;
		return list[index];
	}

	int len = (int) list.size();
	if(index >= 0 && index < len) {
		return list[index];
	}
	else {
		throw new string("Invalid access.\n");
	}
}

CharmListG2& CharmListG2::operator=(const CharmListG2& cList)
{
	if(this == &cList)
		return *this;

	// delete current list contents first
	int i;
	for(i = 0; i < (int) list.size(); i++)
		list.erase(i);
	cur_index = 0;

	cur_index = cList.cur_index;
	list = cList.list;
	return *this;
}

int CharmListG2::length()
{
	return (int) list.size();
}

string CharmListG2::printAtIndex(int index)
{
	stringstream ss;
	int i;

	if(index >= 0 && index < (int) list.size()) {
		i = index;
		ss << list[i].g;
	}

	string s = ss.str();
	return s;
}

ostream& operator<<(ostream& s, const CharmListG2& cList)
{
	CharmListG2 cList2 = cList;
	for(int i = 0; i < cList2.length(); i++) {
		s << i << ": " << cList2.printAtIndex(i) << endl;
	}

	return s;
}

// end CharmListG2 implementation

// start CharmMetaListG1 implementation

CharmMetaListG2::CharmMetaListG2(void)
{
	// increases as elements are appended
	cur_index = 0;
}

CharmMetaListG2::~CharmMetaListG2()
{
	for(int i = 0; i < (int) list.size(); i++)
		list.erase(i);
}

CharmMetaListG2::CharmMetaListG2(const CharmMetaListG2& cList)
{
	//copy constructor
	cur_index = cList.cur_index;
	list = cList.list;
}

void CharmMetaListG2::append(CharmListG2 & g2)
{
	list[cur_index] = g2;
	cur_index++;
}

CharmListG2& CharmMetaListG2::operator[](const int index)
{
	if(index == cur_index) { // means we are creating reference.
		cur_index++;
		return list[index];
	}

	int len = (int) list.size();
	if(index >= 0 && index < len) {
		return list[index];
	}
	else {
		throw new string("Invalid access.\n");
	}
}

int CharmMetaListG2::length()
{
	return (int) list.size();
}

string CharmMetaListG2::printAtIndex(int index)
{
	stringstream ss;
	int i;

	if(index >= 0 && index < (int) list.size()) {
		i = index;
		ss << list[i];
	}

	string s = ss.str();
	return s;
}

ostream& operator<<(ostream& s, const CharmMetaListG2& cList)
{
	CharmMetaListG2 cList2 = cList;
	for(int i = 0; i < cList2.length(); i++) {
		s << "list " << i << "\n";
		s << cList2.printAtIndex(i) << endl;
	}

	return s;
}

CharmMetaListG2& CharmMetaListG2::operator=(const CharmMetaListG2& cList)
{
	if(this == &cList)
		return *this;

	// delete current list contents first
	int i;
	for(i = 0; i < (int) list.size(); i++)
		list.erase(i);
	cur_index = 0;

	cur_index = cList.cur_index;
	list = cList.list;
	return *this;
}


// end CharmMetaListG2 implementation

// start CharmListGT implementation

CharmListGT::CharmListGT(void)
{
	// increases as elements are appended
	cur_index = 0;
}

CharmListGT::~CharmListGT()
{
	for(int i = 0; i < (int) list.size(); i++)
		list.erase(i);
}

CharmListGT::CharmListGT(const CharmListGT& cList)
{
	//copy constructor
	cur_index = cList.cur_index;
	list = cList.list;
}

void CharmListGT::append(GT & g)
{
	list[cur_index] = g;
	cur_index++;
}

GT& CharmListGT::operator[](const int index)
{
	if(index == cur_index) { // means we are creating reference.
		GT tmp;
		list[cur_index] = tmp; // this type will disappear and just for creating reference only. caller expected to set result
		cur_index++;
		return list[index];
	}

	int len = (int) list.size();
	if(index >= 0 && index < len) {
		return list[index];
	}
	else {
		throw new string("Invalid access.\n");
	}
}

CharmListGT& CharmListGT::operator=(const CharmListGT& cList)
{
	if(this == &cList)
		return *this;

	// delete current list contents first
	int i;
	for(i = 0; i < (int) list.size(); i++)
		list.erase(i);
	cur_index = 0;

	cur_index = cList.cur_index;
	list = cList.list;
	return *this;
}

int CharmListGT::length()
{
	return (int) list.size();
}

string CharmListGT::printAtIndex(int index)
{
	stringstream ss;
	int i;

	if(index >= 0 && index < (int) list.size()) {
		i = index;
		ss << list[i].g;
	}

	string s = ss.str();
	return s;
}

ostream& operator<<(ostream& s, const CharmListGT& cList)
{
	CharmListGT cList2 = cList;
	for(int i = 0; i < cList2.length(); i++) {
		s << i << ": " << cList2.printAtIndex(i) << endl;
	}

	return s;
}

// end CharmListGT implementation

// start CharmMetaListGT implementation

CharmMetaListGT::CharmMetaListGT(void)
{
	// increases as elements are appended
	cur_index = 0;
}

CharmMetaListGT::~CharmMetaListGT()
{
	for(int i = 0; i < (int) list.size(); i++)
		list.erase(i);
}

CharmMetaListGT::CharmMetaListGT(const CharmMetaListGT& cList)
{
	//copy constructor
	cur_index = cList.cur_index;
	list = cList.list;
}

void CharmMetaListGT::append(CharmListGT & gt)
{
	list[cur_index] = gt;
	cur_index++;
}

CharmListGT& CharmMetaListGT::operator[](const int index)
{
	if(index == cur_index) { // means we are creating reference.
		cur_index++;
		return list[index];
	}

	int len = (int) list.size();
	if(index >= 0 && index < len) {
		return list[index];
	}
	else {
		throw new string("Invalid access.\n");
	}
}

int CharmMetaListGT::length()
{
	return (int) list.size();
}

string CharmMetaListGT::printAtIndex(int index)
{
	stringstream ss;
	int i;

	if(index >= 0 && index < (int) list.size()) {
		i = index;
		ss << list[i];
	}

	string s = ss.str();
	return s;
}

ostream& operator<<(ostream& s, const CharmMetaListGT& cList)
{
	CharmMetaListGT cList2 = cList;
	for(int i = 0; i < cList2.length(); i++) {
		s << "list " << i << "\n";
		s << cList2.printAtIndex(i) << endl;
	}

	return s;
}

CharmMetaListGT& CharmMetaListGT::operator=(const CharmMetaListGT& cList)
{
	if(this == &cList)
		return *this;

	// delete current list contents first
	int i;
	for(i = 0; i < (int) list.size(); i++)
		list.erase(i);
	cur_index = 0;

	cur_index = cList.cur_index;
	list = cList.list;
	return *this;
}


// end CharmMetaListGT implementation


// start CharmDict implementation

CharmDict::CharmDict()
{

}

CharmDict::~CharmDict()
{
	emap.clear();
}

int CharmDict::length()
{
	return (int) emap.size();
}

CharmList CharmDict::keys()
{
	CharmList s;
	map<string, Element>::iterator iter;
	for(iter = emap.begin(); iter != emap.end(); iter++) {
		// s.push_back(iter->first);
		const char *ptr = iter->first.c_str();
		s.append( ptr );
	}

	return s;
}

string CharmDict::printAll()
{
	stringstream ss;
	map<string, Element, cmp_str>::iterator iter;
	for(iter = emap.begin(); iter != emap.end(); iter++) {
		ss << "key = " << iter->first << ", value = " << iter->second << endl;
	}

	string s = ss.str();
	return s;
}

void CharmDict::set(string key, Element& value)
{
	emap.insert(pair<string, Element>(key, value));
}

Element& CharmDict::operator[](const string key)
{
	map<string, Element, cmp_str>::iterator iter;
	for(iter = emap.begin(); iter != emap.end(); iter++) {
		if (strcmp(key.c_str(), iter->first.c_str()) == 0) {
			return iter->second;
		}
	}

	// means it's a new index so set it
	throw new string("Invalid access.\n");
}

ostream& operator<<(ostream& s, const CharmDict& e)
{
	CharmDict e2 = e;
	s << e2.printAll();
	return s;
}

// defines the PairingGroup class

PairingGroup::PairingGroup(int sec_level)
{
	cout << "Initializing underlying curve." << endl;
	pfcObject = new PFC(sec_level);
	miracl *mip=get_mip();  // get handle on mip (Miracl Instance Pointer)
	mip->IOBASE = 10;

	time_t seed;
	time(&seed);
    irand((long)seed);

//    G1 *g1 = new G1();
    G1 g1;
    pfcObject->random(g1);
#ifdef ASYMMETRIC
//    G2 *g2 = new G2();
    G2 g2;
    pfcObject->random(g2);

    gt = new GT(pfcObject->pairing(g2, g1));
//    delete g2;
#else
    gt = new GT(pfcObject->pairing(*g1, *g1));
#endif
//    delete g1;

	gt_id = new GT(pfcObject->power(*gt, ZR(0)));
}

PairingGroup::~PairingGroup()
{
	delete pfcObject;
	delete gt;
	delete gt_id;
}

void PairingGroup::init(ZR & r, char *value)
{
	big x = mirvar(0);
	cinstr(x, value);
	r = ZR(x); //should copy this
	mr_free(x);
}

ZR PairingGroup::init(ZR_type t, int value)
{
	big x = mirvar(value);
	ZR zr(x); // = new ZR(x);
    mr_free(x);
	return zr;
}

void PairingGroup::init(ZR & r, int value)
{
	big x = mirvar(value);
	r = ZR(x); //should copy this
	mr_free(x);
	return;
}

ZR PairingGroup::init(ZR_type t)
{
	ZR zr; // = new ZR();
	return zr;
}

G1 PairingGroup::init(G1_type t)
{
	G1 g1;// = new G1();
	return g1;
}

void PairingGroup::init(G1 & t, int value)
{
	G1 g1;
	t = g1; // set to the identity element
	return;
}

G1 PairingGroup::init(G1_type t, int value)
{
	G1 g1; // = new G1();
	return g1;
}

#ifdef ASYMMETRIC
G2 PairingGroup::init(G2_type t)
{
	G2 g2; // = new G2();
	return g2;
}

G2 PairingGroup::init(G2_type t, int value)
{
	G2 g2; // = new G2();
	return g2;
}

void PairingGroup::init(G2 & t, int value)
{
	G2 g2;
	t = g2;
	return;
}
#endif

GT PairingGroup::init(GT_type t)
{
	GT g(*gt_id); // = new GT(*gt_id);
	return g;
}

GT PairingGroup::init(GT_type t, int value)
{
	GT g(*gt_id); // = new GT(*gt_id);
	return g;
}

void PairingGroup::init(GT & t, int value)
{
	GT g(*gt_id);
	t = g;
	return;
}

ZR PairingGroup::random(ZR_type t)
{
	ZR zr; // = new ZR();
	pfcObject->random(zr);
	return zr;
}

G1 PairingGroup::random(G1_type t)
{
	G1  g1; // = new G1();
	pfcObject->random(g1);
	return g1;
}

GT PairingGroup::random(GT_type t)
{
	// choose random ZR
	ZR zr;
	GT gts; // = new GT();
	pfcObject->random(zr);

	gts = pfcObject->power(*gt, zr);
    return gts;
}

ZR PairingGroup::neg(ZR r)
{
     ZR zr = r;
     zr.negate();
     return zr;
}

ZR PairingGroup::inv(ZR r)
{
     ZR zr = inverse(r, pfcObject->order());
     return zr;
}

bool PairingGroup::ismember(CharmMetaListZR & g)
{
	return true;
}

bool PairingGroup::ismember(CharmMetaListG1 & g)
{
	return true;
}

bool PairingGroup::ismember(CharmMetaListG2 & g)
{
	return true;
}

bool PairingGroup::ismember(CharmMetaListGT & g)
{
	return true;
}

bool PairingGroup::ismember(CharmList & g)
{
	return true;
}

bool PairingGroup::ismember(CharmListZR & g)
{
	return true;
}

bool PairingGroup::ismember(CharmListG1 & g)
{
	return true;
}

bool PairingGroup::ismember(CharmListGT & g)
{
	return true;
}

bool PairingGroup::ismember(ZR & g)
{
	return true;
}

bool PairingGroup::ismember(G1 & g)
{
	return true;
}

#ifdef ASYMMETRIC

G2 PairingGroup::random(G2_type t)
{
	G2 g2; // = new G2();
	pfcObject->random(g2);
	return g2;
}

bool PairingGroup::ismember(G2 & g)
{
	return true; // add code to check
}

bool PairingGroup::ismember(CharmListG2 & g)
{
	return true;
}

G2 PairingGroup::mul(G2 g, G2 h)
{
	G2 l(g + h);
	return l;
}

G2 PairingGroup::div(G2 g, G2 h)
{
	G2 l(g + -h);
	return l;
}

G2 PairingGroup::exp(G2 g, ZR r)
{
	// g ^ r == g * r OR scalar multiplication
	G2 l = pfcObject->mult(g, r);
	return l;
}

G2 PairingGroup::exp(G2 g, int r)
{
	// g ^ r == g * r OR scalar multiplication
	G2 l = pfcObject->mult(g, ZR(r));
	return l;
}

GT PairingGroup::pair(G1 g, G2 h)
{
	GT gt = pfcObject->pairing(h, g);
	return gt;
}

#else
GT PairingGroup::pair(G1 g, G1 h)
{
	GT gt = pfcObject->pairing(g, h);
	return gt;
}
#endif

bool PairingGroup::ismember(GT & g)
{
	return true; // add code to check
}

ZR PairingGroup::order()
{
	return ZR(pfcObject->order());
}

int PairingGroup::add(int g, int h)
{
	return g + h;
}

ZR PairingGroup::add(ZR g, ZR h)
{
	ZR o = pfcObject->order();

	return (g + h) % o;
}

int PairingGroup::sub(int g, int h)
{
	return g - h;
}

ZR PairingGroup::sub(ZR g, ZR h)
{
	ZR o = pfcObject->order();

	return (g - h) % o;
}


int PairingGroup::mul(int g, int h)
{
	return g * h;
}


ZR PairingGroup::mul(ZR g, ZR h)
{
	ZR o = pfcObject->order();
	return modmult(g, h, o);
//	return (g * h) % o;
}

// mul for G1 & GT
G1 PairingGroup::mul(G1 g, G1 h)
{
	G1 l(g + h);
	return l;
}

GT PairingGroup::mul(GT g, GT h)
{
//	GT l(g * h);
	return g * h;
}

ZR PairingGroup::div(int g, ZR h)
{
	ZR o = pfcObject->order();
	return moddiv(ZR(g), h, o);
}


ZR PairingGroup::div(ZR g, ZR h)
{
	ZR o = pfcObject->order();
	return moddiv(g, h, o);
}

// div for G1 & GT
G1 PairingGroup::div(G1 g, G1 h)
{
	G1 l(g + -h);
	return l;
}

GT PairingGroup::div(GT g, GT h)
{
	GT l(g / h);
	return l;
}

int PairingGroup::div(int g, int h)
{
	return g / h;
}

ZR PairingGroup::exp(ZR x, int y)
{
	ZR z = pfcObject->order();
	if(y == -1) {
	     return inverse(x, z);
	}
	else if(y >= 0) {
		return pow(x, y, z);
	}
	else {
		throw new string("Raising to a negative that isn't -1 is not allowed.\n");
	}
}

ZR PairingGroup::exp(ZR x, ZR y)
{
	ZR z = pfcObject->order();
	ZR result = pow(x, y, z);
	//cout << "exp result: " << result << endl;
	return result;
}

// exp for G1 & GT
G1 PairingGroup::exp(G1 g, ZR r)
{
	// g ^ r == g * r OR scalar multiplication
	G1 l = pfcObject->mult(g, r);
 	return l;
}

G1 PairingGroup::exp(G1 g, int r)
{
	// g ^ r == g * r OR scalar multiplication
	G1 l = pfcObject->mult(g, ZR(r));
 	return l;
}

GT PairingGroup::exp(GT g, ZR r)
{
	// g ^ r == g * r OR scalar multiplication
	GT l = pfcObject->power(g, r);
	return l;
}

GT PairingGroup::exp(GT g, int r)
{
	// g ^ r == g * r OR scalar multiplication
	GT l = pfcObject->power(g, ZR(r));
	return l;
}

ZR PairingGroup::hashListToZR(string str)
{
	ZR r = pfcObject->hash_to_group((char *) str.c_str());
	return r;
}

G1 PairingGroup::hashListToG1(string str)
{
	G1 l; 
	pfcObject->hash_and_map(l, (char *) str.c_str());
	return l; 
}

#ifdef ASYMMETRIC
G2 PairingGroup::hashListToG2(string str)
{
	G2 l;
	pfcObject->hash_and_map(l, (char *) str.c_str());
	return l;
}
#endif

// serialize helper methods for going from Big to bytes and back
string bigToBytes(Big x)
{
	char c[MAX_LEN+1];
	memset(c, 0, MAX_LEN);
	int size = to_binary(x, MAX_LEN, c, FALSE);
	string bytes(c, size);
//	printf("bigToBytes before => ");
//	_printf_buffer_as_hex((uint8_t *) bytes.c_str(), size);
	stringstream ss;
	ss << size << ":" << bytes << "\0";
//	printf("bigToBytes after => ");
//	_printf_buffer_as_hex((uint8_t *) ss.str().c_str(), ss.str().size());
	return ss.str();
}

string bigToRawBytes(Big x)
{
	char c[MAX_LEN+1];
	memset(c, 0, MAX_LEN);
	int size = to_binary(x, MAX_LEN, c, FALSE);
	string bytes(c, size);
	stringstream ss;
	ss << bytes << "\0";
	return ss.str();
}

string PairingGroup::aes_key(GT & g)
{
	Big tmp = pfcObject->hash_to_aes_key(g);
	string tmp_str = bigToRawBytes(tmp);
	int output_len = strlen(tmp_str.c_str());
	return string(convert_buffer_to_hex((uint8_t *) tmp_str.c_str(), output_len));
}

Big *bytesToBig(string str, int *counter)
{
	int pos = str.find_first_of(':');
	int len = atoi( str.substr(0, pos).c_str() );
	const char *elem = str.substr(pos+1, pos + len).c_str();
//		cout << "pos of elem => " << pos << endl;
//		cout << "elem => " << elem << endl;
//	printf("bytesToBig before => ");
//	_printf_buffer_as_hex((uint8_t *) elem, len);
	Big x = from_binary(len, (char *) elem);
//	cout << "Big => " << x << endl;
	Big *X  = new Big(x);
	*counter  = pos + len + 1;
	return X;
}

Big bytesToBigS(string str, int *counter)
{
	int pos = str.find_first_of(':');
	int len = atoi( str.substr(0, pos).c_str() );
	const char *elem = str.substr(pos+1, pos + len).c_str();

	Big x = from_binary(len, (char *) elem);
	*counter  = pos + len + 1;
	return x;
}


ZR PairingGroup::hashListToZR(CharmList list)
{
	int len = list.length();
	pfcObject->start_hash();
	for(int i = 0; i < len; i++) {
		Element e = list[i];
		if(e.type == Str_t) {
			ZR tmp = pfcObject->hash_to_group( (char *) e.strPtr.c_str());
			pfcObject->add_to_hash(tmp);
		}
		else if(e.type == ZR_t)
			pfcObject->add_to_hash(e.zr);
		else if(e.type == G1_t)
			pfcObject->add_to_hash(e.g1);
		else if(e.type == G2_t)
			pfcObject->add_to_hash(e.g2);
		else if(e.type == GT_t)
			pfcObject->add_to_hash(e.gt);
	}

	//ZR *result = new ZR(pfcObject->finish_hash_to_group());
	return pfcObject->finish_hash_to_group();
}

G1 PairingGroup::hashListToG1(CharmList list)
{
	int len = list.length();
	pfcObject->start_hash();
	for(int i = 0; i < len; i++) {
		Element e = list[i];
		if(e.type == Str_t) {
			ZR tmp = pfcObject->hash_to_group( (char *) e.strPtr.c_str());
			pfcObject->add_to_hash(tmp);
		}
		else if(e.type == ZR_t)
			pfcObject->add_to_hash(e.zr);
		else if(e.type == G1_t)
			pfcObject->add_to_hash(e.g1);
		else if(e.type == G2_t)
			pfcObject->add_to_hash(e.g2);
		else if(e.type == GT_t)
			pfcObject->add_to_hash(e.gt);
	}

	ZR tmp1 = pfcObject->finish_hash_to_group();
//	G1 *g1 = new G1();
	G1 g1;
	// convert result to bytes and hash to G1
	pfcObject->hash_and_map(g1, (char *) bigToBytes(tmp1).c_str());
	return g1;
}

#ifdef ASYMMETRIC
G2 PairingGroup::hashListToG2(CharmList list)
{
	int len = list.length();
	pfcObject->start_hash();
	for(int i = 0; i < len; i++) {
		Element e = list[i];
		if(e.type == Str_t) {
			ZR tmp = pfcObject->hash_to_group( (char *) e.strPtr.c_str());
			pfcObject->add_to_hash(tmp);
		}
		else if(e.type == ZR_t)
			pfcObject->add_to_hash(e.zr);
		else if(e.type == G1_t)
			pfcObject->add_to_hash(e.g1);
		else if(e.type == G2_t)
			pfcObject->add_to_hash(e.g2);
		else if(e.type == GT_t)
			pfcObject->add_to_hash(e.gt);
	}

	ZR tmp1 = pfcObject->finish_hash_to_group();
//	G2 *g2 = new G2();
	G2 g2;
	// convert result to bytes and hash to G2
	pfcObject->hash_and_map(g2, (char *) bigToBytes(tmp1).c_str());
	return g2;
}
#endif

string element_to_bytes(Element & e) {
	string t;
	int type = e.type;

	if(type == ZR_t) {
		Big s = e.zr;
		t.append(bigToBytes(s));
		string encoded = _base64_encode(reinterpret_cast<const unsigned char*>(t.c_str()), t.size());
		return encoded;
	}
	else if(type == G1_t) {
		G1 p = e.g1;
		Big x, y;
		p.g.get(x, y);
		string t;
		t.append(bigToBytes(x));
		t.append(bigToBytes(y));

		string encoded = _base64_encode(reinterpret_cast<const unsigned char*>(t.c_str()), t.size());
		return encoded;
	}
#ifdef ASYMMETRIC
	else if(type == G2_t) {
		G2 P = e.g2; // embeds an ECn3 element (for MNT curves)
		ZZn3 x, y;
			// ZZn a,b,c;
 		ZZn *a = new ZZn[6];
		P.g.get(x, y); // get ZZn3's
		x.get(a[0], a[1], a[2]); // get coordinates for each ZZn
		y.get(a[3], a[4], a[5]);

		string t;
		for(int i = 0; i < 6; i++) {

			t.append( bigToBytes( Big(a[i]) ) );
		}
			// base64 encode t and return
		string encoded = _base64_encode(reinterpret_cast<const unsigned char*>(t.c_str()), t.size());
 		delete [] a;
		return encoded;
	}
#endif
	else if(type == GT_t) {
		GT P = e.gt; // embeds an ZZn6 element (for MNT curves) is equivalent to
			// control this w/ a flag
#ifdef ASYMMETRIC
		ZZn2 x, y, z; // each zzn2 has a (x,y) coordinates of type Big
		Big *a = new Big[6];
		P.g.get(x, y, z); // get ZZn2's

		x.get(a[0], a[1]); // get coordinates for each ZZn2
		y.get(a[2], a[3]);
		z.get(a[4], a[5]);
	//	    cout << "Point => (" << x << ", " << y << ", " << z << ")" << endl;
		string t;
		for(int i = 0; i < 6; i++) {
		    t.append( bigToBytes(a[i]) );
		}
//		    cout << "Pre-encoding => ";
//		    _printf_buffer_as_hex((uint8_t *) t.c_str(), t.size());
			// base64 encode t and return
		string encoded = _base64_encode(reinterpret_cast<const unsigned char*>(t.c_str()), t.size());
		delete [] a;
		return encoded;
#else
		// it must be symmetric
#endif
	}

	throw new string("element_to_bytes: invalid type specified");
}

void element_from_bytes(Element& elem, int type, unsigned char *data)
{
	if(type == ZR_t) {
		if(is_base64((unsigned char) data[0])) {
			string b64_encoded((char *) data);
			string s = _base64_decode(b64_encoded);
			int cnt = 0;
			Big *b = new Big(bytesToBigS(s, &cnt));
//			cout << "Element_from_bytes : " << *b << endl;
			elem.createNew(*b);
			delete b;
			return;
		}
	}
	else if(type == G1_t) {
		if(is_base64((unsigned char) data[0])) {
		string b64_encoded((char *) data);
		string s = _base64_decode(b64_encoded);

		int cnt = 0;
		Big *x, *y;
		x = bytesToBig(s, &cnt);
		s = s.substr(cnt);
		y = bytesToBig(s, &cnt);
//		cout << "point => (" << x << ", " << y << ")" << endl;
		G1 *p = new G1();
		p->g.set(*x, *y);
		delete x;
		delete y;
		elem.createNew(*p);
		delete p;
		return;
		}
	}
#ifdef ASYMMETRIC
	else if(type == G2_t) {
		if(is_base64((unsigned char) data[0])) {
			string b64_encoded((char *) data);
			string s = _base64_decode(b64_encoded);
	//		cout << "original => " << s << endl;
			int cnt = 0;
			ZZn *a = new ZZn[6];
			for(int i = 0; i < 6; i++) {
				Big *b = bytesToBig(s, &cnt);
				a[i] = ZZn( *b ); // retrieve all six coordinates
				s = s.substr(cnt);
				delete b;
			}
			ZZn3 x (a[0], a[1], a[2]);
			ZZn3 y (a[3], a[4], a[5]);

			G2 *point = new G2();
			point->g.set(x, y);
			delete [] a;
			// cout << "Recovered pt => " << point->g << endl;
			// Element elem(*point);
			elem.createNew(*point);
			delete point;
			return;
		}
	}
#endif
	else if(type == GT_t) {
		if(is_base64((unsigned char) data[0])) {
			string b64_encoded((char *) data);
			string s = _base64_decode(b64_encoded);
	//		cout << "original => " << s << endl;
			int cnt = 0;
#ifdef ASYMMETRIC
			Big *a = new Big[6];
			for(int i = 0; i < 6; i++) {
//				// cout << "buffer => ";
//			    // printf_buffer_as_hex((uint8_t *) s.c_str(), s.size());
				Big *b = bytesToBig(s, &cnt);
				a[i] =  Big(*b); // retrieve all six coordinates
				s = s.substr(cnt);
				delete b;
//				// cout << "i => " << a[i] << endl;
			}
			ZZn2 x, y, z;
			x.set(a[0], a[1]);
			y.set(a[2], a[3]);
			z.set(a[4], a[5]);

			GT *point = new GT();
			point->g.set(x, y, z);
			elem.createNew(*point);
//			Element elem (*point);
			delete [] a;
//			delete point;
			return;
#else
		// must be symmetric
#endif
		}
	}

	throw new string("Invalid type specified.\n");
}

SymmetricEnc::SymmetricEnc()
{
	keysize = aes_block_size; // 16 * 8 = 128-bit key
	mode = MR_CBC;
	aes_initialized = false;
}

SymmetricEnc::~SymmetricEnc()
{
	aes_end(&a);
}

string SymmetricEnc::encrypt(char *key, char *message, int len)
{
	csprng RNG;
	unsigned long ran;
	time((time_t *) &ran);
	string raw = "seeding RNGs"; // read from /dev/random
	strong_init(&RNG, (int) raw.size(), (char *) raw.c_str(), ran);

	int i;
	// select random IV here
    for (i=0;i<16;i++) iv[i]=i;
//	for (i=0;i<16;i++) iv[i]=strong_rng(&RNG);
    if (!aes_init(&a, mode, keysize, key, iv))
	{
    	aes_initialized = false;
		printf("Failed to Initialize\n");
		return string("");
	}

	// set flag that aes-initialized
    aes_initialized = true;
    char message_buf[len + 1];
	memset(message_buf, 0, len);
	memcpy(message_buf, message, len);
    aes_encrypt(&a, message_buf);
//    for (i=0;i<aes_block_size;i++) printf("%02x",(unsigned char) message_buf[i]);
//    aes_end(&a);

	strong_kill(&RNG);
    string t = string(message_buf, len);
	return _base64_encode(reinterpret_cast<const unsigned char*>(t.c_str()), t.size());
}

string SymmetricEnc::decrypt(char *key, char *ciphertext, int len)
{

	// assumes we're dealing with 16-block aligned buffers
	int i;
	if(aes_initialized) {
		aes_reset(&a, mode, iv);
	}
	else {
		for (i=0;i<16;i++) iv[i]=i; // TODO: retrieve IV from ciphertext
	    if (!aes_init(&a, mode, keysize, key, iv))
		{
	    	aes_initialized = true;
			printf("Failed to Initialize\n");
			return string("");
		}
	}

	char *ciphertext2;
	int len2;
	if(is_base64((unsigned char) ciphertext[0])) {
		string b64_encoded((char *) ciphertext, len);
		string t = _base64_decode(b64_encoded);
		ciphertext2 = (char *) t.c_str();
		len2 = (int) t.size();
	}
	else {
		ciphertext2 = ciphertext;
		len2 = len;
	}

//	for(i=0;i<len2;i++) printf("%02x",(unsigned char) ciphertext2[i]);
	char message_buf[len2 + 1];
	memset(message_buf, 0, len2);
	memcpy(message_buf, ciphertext2, len2);

	aes_decrypt(&a, message_buf);
//	for (i=0;i<aes_block_size;i++) printf("%02x",(unsigned char) ciphertext_buf[i]);

	return string(message_buf, len2);
}

string SymmetricEnc::pad(string s)
{
	// check length and append bytes up until 15-bytes
	int i, padding_needed = aes_block_size - (((int) s.size()) % aes_block_size);

	string s2 = s;
	for(i = 0; i < padding_needed; i++)
		s2 += " ";
	return s2;
}

void parsePartCT(const char *filename, CharmDict & d)
{
	ifstream stream(filename);

	string input;
	while(!stream.eof()) {
		stream >> input;
		int input_len = (int) input.size();
		int pos = input.find('=');
		if(pos != -1) {
			string key = input.substr(0, pos);
			string value = input.substr(pos+1, input_len);
			// deserialize value
			Element::deserialize(d[key], value);
		}
		input.clear();
	}
	cout << d << endl;
}

void parseKeys(const char *filename, ZR & sk, GT & pk)
{
	Element skElem, pkElem;
	ifstream stream(filename);

	string input;
	while(!stream.eof()) {
		stream >> input;
		int input_len = (int) input.size();
		int pos = input.find('=');
		if(pos != -1) {
			char *key = (char *) input.substr(0, pos).c_str();
			string value = input.substr(pos+1, input_len);

			if(strcmp(key, "sk") == 0) {
				Element::deserialize(skElem, value);
				sk = skElem.getZR();
			}
			else if(strcmp(key, "pk") == 0) {
				Element::deserialize(pkElem, value);
				pk = pkElem.getGT();
			}
		}
		input.clear();
	}
}

// ciphertext expected to be base64 encoded
string SymDec(string k, string c_encoded)
{
	SymmetricEnc Symm;
	char *key = (char *) k.c_str();
	char *ciphertext = (char *) c_encoded.c_str();
	int c_len = (int) c_encoded.size();
	return Symm.decrypt(key, ciphertext, c_len);
}

/* test inequality for two strings */
bool isEqual(string value1, string value2)
{
    string s1 = value1;
    string s2 = value2;
    if (strcmp(s1.c_str(), s2.c_str()) == 0)
	return true;
    else
	return false;
}

/* test inequality for two strings */
bool isNotEqual(string value1, string value2)
{
    string s1 = value1;
    string s2 = value2;
    if (strcmp(s1.c_str(), s2.c_str()) != 0)
	return true;
    else
	return false;
}

/* converts a string to a z-list of integers of size l-bits. 
   Result is stored in zrlist.
*/  
void stringToInt(PairingGroup & group, string strID, int z, int l, CharmListZR & zrlist)
{
    /* 1. hash string. */
    ZR intval;
    Big mask( pow(Big(2), l) - 1 ); 
    ZR id = group.hashListToZR(strID); 

    /* 2. cut up result into zz pieces of ll size */
    for(int i = 0; i < z; i++) {
        intval = land(id, mask); 
        zrlist.append(intval);
        id = id >> l; // shift to the right by ll bits
    }

    return;
}

CharmListZR stringToInt(PairingGroup & group, string strID, int z, int l)
{
    /* 1. hash string. */
    CharmListZR zrlist; // = new CharmListZR;
    ZR intval;
    Big mask( pow(Big(2), l) - 1 ); 
    ZR id = group.hashListToZR(strID); 

    /* 2. cut up result into zz pieces of ll size */
    for(int i = 0; i < z; i++) {
        intval = land(id, mask); 
        zrlist.append(intval);
        id = id >> l; // shift to the right by ll bits
    }

    return zrlist;
}

ZR SmallExp(int bits) {
	big t = mirvar(0);
	bigbits(bits, t);
    ZR zr(t);
    mr_free(t);
	return zr;
}

string concat(CharmListStr & list)
{
    int l = 0;
    string L = "";
    l = list.length();
    for (int y = 0; y < l; y++)
    {
        L = (L + list[y]);
    }
    return L;
}

ZR ceillog(int base, int value)
{
   // logb(x) ==> log(x) / log(b)
   big x = mirvar((int) ceil(log10(value) / log10(base))); 
   ZR zr(x);
   mr_free(x);
   return zr;
}

