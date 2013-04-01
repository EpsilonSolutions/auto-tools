import sys
from SDLang import *

class VarType:
    def __init__(self):
        self.type = None
        self.listNodesList = []
        self.lineNo = None
        self.isInAList = False
        self.listRefType = types.NO_TYPE
        self.srcLine = ""
        
    def getType(self):
        return self.type

    def getListNodesList(self):
        return self.listNodesList

    def getLineNo(self):
        return self.lineNo

    def setLineNo(self, lineNo):
        if ( (type(lineNo) is not int) or (lineNo < 1) ):
            sys.exit("setLineNo in VarType.py received as input a line number that is invalid.")

        self.lineNo = lineNo

    def setType(self, type):
        if ( (isValidType(type) == False) and (type != ops.LIST) ):
            sys.exit("setType in VarType.py received as input a line number that is invalid.")
        
        self.type = type
    
    def setRefType(self, _type):
        if str(_type) in types.getList():
            self.listRefType = _type
            return
        print("Specified an invalid type: ", _type)
        return
    
    def getRefType(self):
        return self.listRefType
    
    def setSrcLine(self, node):
        self.srcLine = str(node)
        return
    
    def getSrcLine(self):
        return self.srcLine