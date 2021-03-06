import src.sdlpath, sys, os, copy, string, re, importlib
import sdlparser.SDLParser as sdl
from sdlparser.SDLang import *
from src.outsrctechniques import SubstituteVar, SubstitutePairings, SplitPairings, HasPairings, CountOfPairings, MaintainOrder, PairInstanceFinderImproved, TestForMultipleEq, GetAttributeVars, GetEquqlityNodes, CountExpOp, CountMulOp, DelAnyVarInList
from src.solver import *
import operator

assignInfo = None
SHORT_ASSUMPTION = "assumption" # for minimizing the assumption
SHORT_SECKEYS = "secret-keys" # for
SHORT_PUBKEYS = "public-keys"
SHORT_CIPHERTEXT = "ciphertext" # in case, an encryption scheme
SHORT_SIGNATURE  = "signature" # in case, a sig algorithm
SHORT_FORALL = "both"
SHORT_DEFAULT = "all"
SHORT_OPTIONS = [SHORT_ASSUMPTION, SHORT_SECKEYS, SHORT_PUBKEYS, SHORT_CIPHERTEXT, SHORT_SIGNATURE, SHORT_FORALL]
minOp = "operation"
PKENC = "PKENC" # encryption
PKSIG = "PKSIG" # signatures
functionOrder = "functionOrder"
curveID = "curve"

G1Prefix = "G1"
G2Prefix = "G2"
bothPrefix = "both"
Gtypes = [G1Prefix, G2Prefix]
length = 5 # length of temporary file
oldListTypeRefs = {}
newListTypeRefs = {}
loc = "src"


DOTPROD = 'dotProd'
class GetPairingVariables:
    def __init__(self, list1, list2):
        assert type(list1) == type(list2) and type(list1) == list, "GetPairingVariables: invalid input type"
        self.listLHS = list1
        self.listRHS = list2
        self.pairing_map = {}
        self.pairing_count = 1
        self.dep_graph = {}
        self.name = None
        self.depListData = None
        self.funcName = None
        self.pair_ids = set()

    def setDepListData(self, data):
        self.depListData = data

    def setFuncName(self, varName):
        self.funcName = varName

    def processDepListData(self, varName):
        if self.depListData and self.funcName:
            the_data = self.depListData.get(self.funcName)
            if the_data:
                dep_list = the_data.get(varName)
                if varName in dep_list:
                    real_dep = list(set(dep_list).difference([varName, G1Prefix]))
                    if len(real_dep) == 1:
                        return real_dep[0]
                    else:
                        raise Exception("Didn't anticipate this case: ", real_dep)
        # if anything goes wrong above, then for now just return input
        # (not many cases like this though)
        return varName

    def getDepGraph(self):
        return self.dep_graph

    def getPairingIds(self):
        return self.pair_ids

    def setFunctionName(self, name):
        self.name = name
        #self.pairing_count += 1
        if name not in self.dep_graph:
            self.dep_graph[name] = []

    def retrieveNode(self, node):
        if Type(node) == ops.EXP:
            return node.left
        #elif Type(node) == ops.MUL:
        #    pass
        raise Exception('failed to retrieve nodes in GetPairingVariables')
        return
        
    def visit(self, node, data):
        pass
    
    def visit_pair(self, node, data):
        if str(node.left.getRefAttribute()) == str(node.right.getRefAttribute()):
            return # skip
        the_lhs_var = the_rhs_var = None
        if Type(node.left) == ops.ATTR and Type(node.right) == ops.ATTR:
            the_lhs_var = str(node.left.getRefAttribute())
            the_rhs_var = str(node.right.getRefAttribute())
        elif Type(node.left) == ops.ATTR and Type(node.right) != ops.ATTR:
            the_lhs_var = str(node.left.getRefAttribute())
            the_rhs_var = str(self.retrieveNode(node.right))
        elif Type(node.left) != ops.ATTR and Type(node.right) == ops.ATTR:
            the_lhs_var = str(self.retrieveNode(node.left))
            the_rhs_var = str(node.right.getRefAttribute())
        elif Type(node.left) != ops.ATTR and Type(node.right) != ops.ATTR:
            the_lhs_var = str(self.retrieveNode(node.left))
            the_rhs_var = str(self.retrieveNode(node.right))
        else:
            pass

        if the_lhs_var and the_rhs_var:
            if DOTPROD in the_lhs_var:
                the_lhs_var = self.processDepListData(the_lhs_var)
            if DOTPROD in the_rhs_var:
                the_rhs_var = self.processDepListData(the_rhs_var)
            self.listLHS.append(the_lhs_var)
            self.listRHS.append(the_rhs_var)
        else:
            print("Couldn't define the lhs or rhs!")
        # store for latter use
        lhs_var = self.listLHS[-1]
        rhs_var = self.listRHS[-1]
        self.pairing_map[ lhs_var ] = rhs_var
        if self.name:
            lhs_oid = "\"P" + str(self.pairing_count)
            rhs_oid = "\"P" + str(self.pairing_count)
            # assume self.name has been defined via setFuncName
            the_lhs_oid = lhs_oid + "[0]\""
            the_rhs_oid = rhs_oid + "[1]\""
            self.dep_graph[self.name].append( (lhs_var, the_lhs_oid) )
            self.dep_graph[self.name].append( (rhs_var, the_rhs_oid) )
            self.pair_ids = self.pair_ids.union([the_lhs_oid, the_rhs_oid])
            self.pairing_count += 1 # increment since we're done with this pairing
        else:
            pass
            #print("Function Name was not set. Therefore, cannot set pairing IDs. ERROR!")

def getOtherPairingVar(var_map, target_var):
    for i,j in var_map.items():
        # if the var is the key
        if i == target_var:
            return j
        # if the var is the value
        if j == target_var:
            return i

def removeList(theList, aList):
    return list(set(theList).difference(aList))

class transformXOR:
    def __init__(self, fixedValues):
        self.groundTruth = fixedValues
        self.varMap = {}
        self.varsList = [] # records variable instances?
        self.xorList = [] # records tuple
        self.alphabet = list(string.ascii_lowercase)
        self.count = 0

    def __getNextVar(self):
        suffixCount = int(self.count / len(self.alphabet))
        if suffixCount > 0: suffix = str(suffixCount)
        else: suffix = '0'
        
        count = self.count % len(self.alphabet)
        a = self.alphabet[ count ] + suffix
        self.count += 1
        return a
    
    def visit(self, node, data):
        return
    
    def visit_xor(self, node, data):
        var1 = str(node.left)
        var2 = str(node.right)
        if var1 not in self.varMap.keys():
            alpha_x = self.__getNextVar()
        else:
            alpha_x = self.varMap[ var1 ]
            
        if var2 not in self.varMap.keys():
            alpha_y = self.__getNextVar()
        else:
            alpha_y = self.varMap[ var2 ]
        
        self.varMap[ var1 ] = alpha_x
        self.varMap[ var2 ] = alpha_y
        
        self.xorList.append( (alpha_x, alpha_y) )
        return
        
    def getVarMap(self):
        return self.varMap
    
    def getVariables(self):
        keys = list(set(self.varMap.values()))
        keys.sort()
        return keys
    
    def getClauses(self):
        return self.xorList        


"""
1. generic function that takes three lists of group assignments..
    { 'G1' : varList, 'G2' : varList, 'both': varList }
2. goes through a given 'block' and goes each statement:
    - exponentiation, multiplication and pairing
    - rewrite each statement where a generator appears (or derivative of one) using three lists:
        if leftAssignVar in 'both': create 2 statements
        if leftAssignVar in 'G1': create 1 statement in G1
        if leftAssignVar in 'G2': create 1 statement in G2
"""
def transformFunction(entireSDL, funcName, blockStmts, info, noChangeList, startLines={}):
    parser = sdl.SDLParser()
    funcNode = BinaryNode("func:" + str(funcName))
    begin = BinaryNode(ops.BEGIN, funcNode, None) # "BEGIN :: func:" + funcName
    end = BinaryNode(ops.END, funcNode, None) # "END :: func:" + funcName
    newLines = [begin] # + list(startLines)
    stack = []
    lines = list(blockStmts.keys())
    lines.sort()

    for index, i in enumerate(lines):
        assert type(blockStmts[i]) == sdl.VarInfo, "transformFunction: blockStmts must be VarInfo Objects."
        if blockStmts[i].getIsForLoopBegin():
            if blockStmts[i].getIsForType(): newLines.append(parser.parse("BEGIN :: for\n")) # "\n" + START_TOKEN + " " + BLOCK_SEP + ' for')
            elif blockStmts[i].getIsForAllType(): newLines.append(parser.parse("BEGIN :: forall\n"))  # "\n" + START_TOKEN + " " + BLOCK_SEP + ' forall')
            newLines.append(blockStmts[i].getAssignNode())
        elif blockStmts[i].getIsForLoopEnd():
            newLines.append(blockStmts[i].getAssignNode())
        
        elif blockStmts[i].getIsIfElseBegin():
            newLines.append(parser.parse("BEGIN :: if\n")) # "\n" + START_TOKEN + " " + BLOCK_SEP + ' if')
            assign = blockStmts[i].getAssignNode()
            if info['verbose']: print(i, ":", assign, end="")           
            handleVarInfo(newLines, assign, blockStmts[i], info, noChangeList)
        
        elif blockStmts[i].getIsIfElseEnd():
            newLines.append(blockStmts[i].getAssignNode()) 
        
        elif blockStmts[i].getIsElseBegin():
            newLines.append(blockStmts[i].getAssignNode())
        
        else:
            assign = blockStmts[i].getAssignNode()
            if info['verbose']: print(i, ":", assign, end="")
            handleVarInfo(newLines, assign, blockStmts[i], info, noChangeList, startLines)

        if info['verbose']: print("")
    newLines.append(end)
    return newLines

"""
1. generic function that takes three lists of group assignments..
    { 'G1' : varList, 'G2' : varList, 'both': varList }
2. goes through a given 'block' and goes each statement:
    - exponentiation, multiplication and pairing
    - rewrite each statement where a generator appears (or derivative of one) using three lists:
        if leftAssignVar in 'both': create 2 statements
        if leftAssignVar in 'G1': create 1 statement in G1
        if leftAssignVar in 'G2': create 1 statement in G2
"""
def transformFunctionAssump(entireSDL, funcName, blockStmts, info, noChangeList, deps, varmap, startLines={}):
    parser = sdl.SDLParser()
    funcNode = BinaryNode("func:" + str(funcName))
    begin = BinaryNode(ops.BEGIN, funcNode, None) # "BEGIN :: func:" + funcName
    end = BinaryNode(ops.END, funcNode, None) # "END :: func:" + funcName
    newLines = [begin] # + list(startLines)
    stack = []
    lines = list(blockStmts.keys())
    lines.sort()

    for index, i in enumerate(lines):
        assert type(blockStmts[i]) == sdl.VarInfo, "transformFunction: blockStmts must be VarInfo Objects."
        if blockStmts[i].getIsForLoopBegin():
            if blockStmts[i].getIsForType(): newLines.append(parser.parse("BEGIN :: for\n")) # "\n" + START_TOKEN + " " + BLOCK_SEP + ' for')
            elif blockStmts[i].getIsForAllType(): newLines.append(parser.parse("BEGIN :: forall\n"))  # "\n" + START_TOKEN + " " + BLOCK_SEP + ' forall')
            newLines.append(blockStmts[i].getAssignNode())
        elif blockStmts[i].getIsForLoopEnd():
            newLines.append(blockStmts[i].getAssignNode())
        
        elif blockStmts[i].getIsIfElseBegin():
            newLines.append(parser.parse("BEGIN :: if\n")) # "\n" + START_TOKEN + " " + BLOCK_SEP + ' if')
            assign = blockStmts[i].getAssignNode()
            if info['verbose']: print(i, ":", assign, end="")           
            handleVarInfoAssump(newLines, assign, blockStmts[i], info, noChangeList, deps, varmap, startLines)
        
        elif blockStmts[i].getIsIfElseEnd():
            newLines.append(blockStmts[i].getAssignNode()) 
        
        elif blockStmts[i].getIsElseBegin():
            newLines.append(blockStmts[i].getAssignNode())
        
        else:
            assign = blockStmts[i].getAssignNode()
            if info['verbose']: print(i, ":", assign, end="")
            handleVarInfoAssump(newLines, assign, blockStmts[i], info, noChangeList, deps, varmap, startLines)

        if info['verbose']: print("")
    newLines.append(end)
    return newLines

"""theType either types.G1 or types.G2"""
def updateForIfConditional(node, assignVar, varInfo, info, theType, noChangeList):
    new_node2 = BinaryNode.copy(node)
        
    if assignVar not in noChangeList: new_assignVar = assignVar + G1Prefix
    else: new_assignVar = str(assignVar)

    sdl.ASTVisitor( SubstituteVar(assignVar, new_assignVar) ).preorder( new_node2 )
    info['generatorMapG1'][assignVar] = new_assignVar
    
    # in case of init() calls...
    sdl.ASTVisitor( SubstituteVar('', str(theType), initChange=True) ).preorder( new_node2 )
    return new_node2

def handleVarInfo(newLines, assign, blockStmt, info, noChangeList, startLines={}):
    if Type(assign) == ops.EQ:
        assignVar = blockStmt.getAssignVar()
        # store for later
        newLine = None
        varTypeObj = info['varTypes'].get(assignVar)
        # case A: randomness and occurs in startLines
        if blockStmt.getHasRandomness() and startLines.get(assignVar) != None:
            newLines.extend( startLines[assignVar] )
            return True
            #if not assignVarIsGenerator(assignVar, info):
        # case B: randomness and varTypeObj != None
        if blockStmt.getHasRandomness() and varTypeObj != None:
            if varTypeObj.getType() in [types.ZR, types.GT]:
                if info['verbose']: print(" :-> not a generator, so add to newLines.", end=" ")
                #newLine = str(assign) # unmodified
                newLines.append(assign) # unmodified
                return True
            else:
                if info['verbose']: print(assignVar, " :-> what type ?= ", info['varTypes'].get(assignVar).getType(), end=" ")
                if info['varTypes'].get(assignVar).getType() == types.G1:
                    pass # figure out what to do here
        if assignVar == outputKeyword:
            vardeps = blockStmt.getVarDepsNoExponents()
            if len(set(blockStmt.getVarDepsNoExponents()).intersection(info['generators'])) > 0:
                if Type(assign.right) == ops.LIST:
                    newLine = updateForLists(blockStmt, assignVar, info)                    
                    newLines.append( newLine )
                    return True
                elif Type(assign.right) == ops.ATTR:
                    assign.right = BinaryNode(ops.LIST)
                    assign.right.listNodes = list(vardeps)
                    newLine = updateForLists(blockStmt, assignVar, info)
                    newLines.append( newLine )
                    return True
                
        if assignVarOccursInBoth(assignVar, info):
            if info['verbose']: print(" :-> split computation in G1 & G2:", blockStmt.getVarDepsNoExponents(), end=" ")
            newLine = updateAllForBoth(assign, assignVar, blockStmt, info, True, noChangeList)
        elif assignVarOccursInG1(assignVar, info):
            if info['verbose']: print(" :-> just in G1:", blockStmt.getVarDepsNoExponents(), end=" ")
            noChangeList.append(str(assignVar))
            newLine = updateAllForG1(assign, assignVar, blockStmt, info, False, noChangeList)
        elif assignVarOccursInG2(assignVar, info):
            if info['verbose']: print(" :-> just in G2:", blockStmt.getVarDepsNoExponents(), end=" ")
            noChangeList.append(str(assignVar))
            newLine = updateAllForG2(assign, assignVar, blockStmt, info, False, noChangeList)
        elif blockStmt.getHasPairings(): # in GT so don't need to touch assignVar
            if info['verbose']: print(" :-> update pairing.", end=" ")
            noChangeList.append(str(assignVar))
            newLine = updateForPairing(blockStmt, info, noChangeList)
        elif blockStmt.getIsList() or blockStmt.getIsExpandNode():
            if info['verbose']: print(" :-> updating list...", end=" ")
            newLine = updateForLists(blockStmt, assignVar, info)
        elif len(set(blockStmt.getVarDepsNoExponents()).intersection(info['generators'])) > 0:
            if info['verbose']: print(" :-> update assign iff lhs not a pairing input AND not changed by traceback.", end=" ")
            if assignVar not in info['pairing'][G1Prefix] and assignVar not in info['pairing'][G2Prefix]:
                noChangeList.append(str(assignVar))
                info['G1'] = info['G1'].union( assignVar )
                newLine = updateAllForG1(assign, assignVar, blockStmt, info, False, noChangeList)
                if info['verbose']: print(":-> var deps = ", blockStmt.getVarDepsNoExponents())
        else:
            info['myAsymSDL'].recordUsedVar(blockStmt.getVarDepsNoExponents())                
            newLine = assign
        # add to newLines
        if type(newLine) == list:
            newLines.extend(newLine)
        elif newLine != None:
            #if newLine not in newLines:
            newLines.append(newLine)
        return True
    elif Type(assign) == ops.IF:
#        print("JAA type: ", Type(assign), blockStmt.getVarDepsNoExponents())
        # TODO: there might be some missing cases in updateForIfConditional. Revise as appropriate.
        assignVars = blockStmt.getVarDepsNoExponents()
        assign2 = assign
        if not HasPairings(assign):
            for assignVar in assignVars:
                if assignVarOccursInG1(assignVar, info):
                    if info['verbose']: print(" :-> just in G1:", assignVar, end="")
                    assign2 = updateForIfConditional(assign2, assignVar, blockStmt, info, types.G1, noChangeList)
                elif assignVarOccursInG2(assignVar, info):
                    if info['verbose']: print(" :-> just in G2:", assignVar, end="")
                    assign2 = updateForIfConditional(assign2, assignVar, blockStmt, info, types.G2, noChangeList)
            #print("TODO: Not a good sign. how do we handle this case for ", assignVar, "in", assign)
        else: # pairing case
            assign2 = updateForPairing(blockStmt, info, noChangeList)
            
        if str(assign2) == str(assign):
            newLines.append(assign)
        else:
            newLines.append(assign2)
    else:
        print("Unrecognized type: ", Type(assign))
    return False

def handleVarInfoAssump(newLines, assign, blockStmt, info, noChangeList, deps, varmap, startLines={}):
    if Type(assign) == ops.EQ:
        assignVartmp = blockStmt.getAssignVar()
        if(assignVartmp in varmap.keys()):
            assignVar = varmap[assignVartmp]
        else:
            assignVar = assignVartmp
        # store for later
        newLine = None
        varTypeObj = info['varTypes'].get(assignVar)
        # case A: randomness and occurs in startLines
        if blockStmt.getHasRandomness() and startLines.get(assignVar) != None:
            newLines.extend( startLines[assignVar] )
            return True
            #if not assignVarIsGenerator(assignVar, info):
        # case B: randomness and varTypeObj != None
        if blockStmt.getHasRandomness() and varTypeObj != None:
            if varTypeObj.getType() in [types.ZR, types.GT]:
                if info['verbose']: print(" :-> not a generator, so add to newLines.", end=" ")
                #newLine = str(assign) # unmodified
                newLines.append(assign) # unmodified
                return True
            else:
                if info['verbose']: print(assignVar, " :-> what type ?= ", info['varTypes'].get(assignVar).getType(), end=" ")
                if info['varTypes'].get(assignVar).getType() == types.G1:
                    pass # figure out what to do here
        if assignVar == outputKeyword:
            vardeps = blockStmt.getVarDepsNoExponents()
            if len(set(blockStmt.getVarDepsNoExponents()).intersection(info['generators'])) > 0:
                if Type(assign.right) == ops.LIST:
                    newLine = updateForLists(blockStmt, assignVar, info)                    
                    newLines.append( newLine )
                    return True
                elif Type(assign.right) == ops.ATTR:
                    assign.right = BinaryNode(ops.LIST)
                    assign.right.listNodes = list(vardeps)
                    newLine = updateForLists(blockStmt, assignVar, info)
                    newLines.append( newLine )
                    return True

        numG1 = 0
        numG2 = 0
        numBoth = 0
        if(assignVar in deps.keys()):
            depList = []
            for (key,val) in deps.items():
                if(assignVar in val):
                    depList.append(key)

            depListGroups = {}
            numG1 = 0
            numG2 = 0
            numBoth = 0
            for i in depList:
                if((i in varmap) and (varmap[i] in info['G1'])):
                    depListGroups[i] = types.G1
                    numG1+=1
                elif((i in varmap) and (varmap[i] in info['G2'])):
                    depListGroups[i] = types.G2
                    numG2+=1
                elif((i in varmap) and (varmap[i] in info['both'])):
                    depListGroups[i] = "both"
                    numBoth+=1
                elif(i in info['G1']):
                    depListGroups[i] = types.G1
                    numG1+=1
                elif(i in info['G2']):
                    depListGroups[i] = types.G2
                    numG2+=1
                elif(i in info['both']):
                    depListGroups[i] = "both"
                    numBoth+=1
                
        if assignVarOccursInBoth(assignVar, info) or ( not(numBoth == 0) or (not(numG1 == 0) and not(numG2 == 0)) ):
            if info['verbose']: print(" :-> split computation in G1 & G2:", blockStmt.getVarDepsNoExponents(), end=" ")
            info['both'] = set(list(info['both']) + list(assignVartmp)) #assignVartmp??
            newLine = updateAllForBoth(assign, assignVartmp, blockStmt, info, True, noChangeList)
        elif assignVarOccursInG1(assignVar, info) or (not(numG1 == 0) and (numG2 == 0) and (numBoth == 0)):
            if info['verbose']: print(" :-> just in G1:", blockStmt.getVarDepsNoExponents(), end=" ")
            info['G1'] = set(list(info['G1']) + list(assignVartmp)) #assignVartmp??
            noChangeList.append(str(assignVartmp))
            newLine = updateAllForG1(assign, assignVartmp, blockStmt, info, False, noChangeList)
        elif assignVarOccursInG2(assignVar, info) or (not(numG2 == 0) and (numG1 == 0) and (numBoth == 0)):
            if info['verbose']: print(" :-> just in G2:", blockStmt.getVarDepsNoExponents(), end=" ")
            info['G2'] = set(list(info['G2']) + list(assignVartmp)) #assignVartmp??
            noChangeList.append(str(assignVartmp))
            newLine = updateAllForG2(assign, assignVartmp, blockStmt, info, False, noChangeList)
        elif blockStmt.getHasPairings(): # in GT so don't need to touch assignVar
            if info['verbose']: print(" :-> update pairing.", end=" ")
            noChangeList.append(str(assignVartmp))
            newLine = updateForPairing(blockStmt, info, noChangeList)
        elif blockStmt.getIsList() or blockStmt.getIsExpandNode():
            if info['verbose']: print(" :-> updating list...", end=" ")
            newLine = updateForLists(blockStmt, assignVartmp, info)
        elif len(set(blockStmt.getVarDepsNoExponents()).intersection(info['generators'])) > 0:
            #TODO: modify here with new code for assumption variables??
            if info['verbose']: print(" :-> update assign iff lhs not a pairing input AND not changed by traceback.", end=" ")

            depList = []
            for (key,val) in deps.items():
                if(assignVar in val):
                    depList.append(key)

            depListGroups = {}
            numG1 = 0
            numG2 = 0
            numBoth = 0
            for i in depList:
                if((i in varmap) and (varmap[i] in info['G1'])):
                    depListGroups[i] = types.G1
                    numG1+=1
                elif((i in varmap) and (varmap[i] in info['G2'])):
                    depListGroups[i] = types.G2
                    numG2+=1
                elif((i in varmap) and (varmap[i] in info['both'])):
                    depListGroups[i] = "both"
                    numBoth+=1
                elif(i in info['G1']):
                    depListGroups[i] = types.G1
                    numG1+=1
                elif(i in info['G2']):
                    depListGroups[i] = types.G2
                    numG2+=1
                elif(i in info['both']):
                    depListGroups[i] = "both"
                    numBoth+=1

            if not(numG1 == 0) and not(numG2 == 0):
                if info['verbose']: print(" :-> split computation in G1 & G2:", blockStmt.getVarDepsNoExponents(), end=" ")
                info['both'] = set(list(info['both']) + list(assignVartmp)) #assignVartmp??
                newLine = updateAllForBoth(assign, assignVartmp, blockStmt, info, True, noChangeList)
            elif not(numBoth == 0):
                if info['verbose']: print(" :-> split computation in G1 & G2:", blockStmt.getVarDepsNoExponents(), end=" ")
                info['both'] = set(list(info['both']) + list(assignVartmp)) #assignVartmp??
                newLine = updateAllForBoth(assign, assignVartmp, blockStmt, info, True, noChangeList)
            elif (not(numG1 == 0) and (numG2 == 0)) or (not(numBoth == 0) and (numG1 == 0) and (numG2 == 0)):
                if info['verbose']: print(" :-> just in G1:", blockStmt.getVarDepsNoExponents(), end=" ")
                info['G1'] = set(list(info['G1']) + list(assignVartmp)) #assignVartmp??
                noChangeList.append(str(assignVartmp))
                newLine = updateAllForG1(assign, assignVartmp, blockStmt, info, False, noChangeList)
            elif (numG1 == 0) and not(numG2 == 0):
                if info['verbose']: print(" :-> just in G2:", blockStmt.getVarDepsNoExponents(), end=" ")
                info['G2'] = set(list(info['G2']) + list(assignVartmp)) #assignVartmp??
                noChangeList.append(str(assignVartmp))
                newLine = updateAllForG2(assign, assignVartmp, blockStmt, info, False, noChangeList)
            elif assignVar not in info['pairing'][G1Prefix] and assignVar not in info['pairing'][G2Prefix]:
                noChangeList.append(str(assignVartmp))
                info['G1'] = info['G1'].union( assignVartmp )
                newLine = updateAllForG1(assign, assignVartmp, blockStmt, info, False, noChangeList)
                if info['verbose']: print(":-> var deps = ", blockStmt.getVarDepsNoExponents())
        else:
            info['myAsymSDL'].recordUsedVar(blockStmt.getVarDepsNoExponents())                
            newLine = assign
        # add to newLines
        if type(newLine) == list:
            newLines.extend(newLine)
        elif newLine != None:
            #if newLine not in newLines:
            newLines.append(newLine)
        return True
    elif Type(assign) == ops.IF:
#        print("JAA type: ", Type(assign), blockStmt.getVarDepsNoExponents())
        # TODO: there might be some missing cases in updateForIfConditional. Revise as appropriate.
        assignVars = blockStmt.getVarDepsNoExponents()
        assign2 = assign
        if not HasPairings(assign):
            for assignVar in assignVars:
                if assignVarOccursInG1(assignVar, info):
                    if info['verbose']: print(" :-> just in G1:", assignVar, end="")
                    assign2 = updateForIfConditional(assign2, assignVar, blockStmt, info, types.G1, noChangeList)
                elif assignVarOccursInG2(assignVar, info):
                    if info['verbose']: print(" :-> just in G2:", assignVar, end="")
                    assign2 = updateForIfConditional(assign2, assignVar, blockStmt, info, types.G2, noChangeList)
            #print("TODO: Not a good sign. how do we handle this case for ", assignVar, "in", assign)
        else: # pairing case
            assign2 = updateForPairing(blockStmt, info, noChangeList)
            
        if str(assign2) == str(assign):
            newLines.append(assign)
        else:
            newLines.append(assign2)
    else:
        print("Unrecognized type: ", Type(assign))
    return False

def instantiateZ3Solver(info, conf, shortOpt, timeOpt, variables, clauses,
                        hardConstraints, constraints, bothConstraints,
                        countOpt, minOptions, dropFirst, pkMapMin, pkListMin,
                        assumpMapMin, assumpList, xorVarMap):

    verbose = info.get('verbose')
    options = {variableKeyword:variables, clauseKeyword:clauses, constraintKeyword:constraints}
    options[verboseKeyword] = verbose
         
    # uncomment for SAT version of AutoGroup
    #(result1, satisfiable) = solveUsingSAT(options)    
    #print("Satisfiable: ", satisfiable)
    #print("Result: ", result1)
    options[curveKeyword] = False # TODO: check option from user (not ready for prime-time)
    
#    options[searchKeyword] = True 
    options[countKeyword] = countOpt # set iff min ops like exp or mul are selected
    options[minKeyword] = minOptions # (minOps, specificOp)
    options[hardConstKeyword] = hardConstraints
    options[bothKeyword] = bothConstraints
    options[dropFirstKeyword] = dropFirst
    options[pkMapKeyword]  = pkMapMin
    options[pkListKeyword] = pkListMin
    options[assumpKeyword] = assumpMapMin
    options[assumpListKeyword] = assumpList
    options[schemeTypeKeyword] = conf.schemeType
    options[pairingVarMapKeyword] = xorVarMap
    options[mergedGraphKeyword] = info.get(mergedGraphKeyword)
    (result, satisfiable) = solveUsingSMT(info, options, shortOpt, timeOpt)
    return (satisfiable, result)

def getAssignmentForName(var, varTypes, estimate=False):
    global assignInfo
    dataTypes = {}
    (funcName, varInfo) = getVarNameEntryFromAssignInfo(assignInfo, var)
    if funcName != None:
        funcStmts = sdl.getVarInfoFuncStmts( funcName )
        Stmts = funcStmts[0]
        StmtTypes = funcStmts[1]
    resultVars = []
    if varInfo.getIsList():
        assignNode = varInfo.getAssignNode()
        varList = assignNode.getRight().listNodes
        resultVars = []
        for i in varList:
            varType = varTypes.get(i)
            theType = varType.getType()
            if theType == types.G1:
                # JAA: commented out for benchmarking                
                #if not estimate: print(i, ":", theType)
                resultVars.append(i)

            if theType in [types.ZR, types.G1, types.G2, types.GT]: dataTypes[ i ] = str(theType)
            
            if theType in [types.list, types.listG1]:
                #print("Find all refs: ", i) # JAA: commented out for benchmarking
                for j,k in Stmts.items():
                    if Type(k.getAssignNode()) == ops.EQ:
                        kvar = k.getAssignVar()
                        if i in kvar and StmtTypes.get(kvar).getType() == types.G1:
                            if kvar not in resultVars: resultVars.append(str(kvar))
                            if kvar not in dataTypes: dataTypes[ i ] = str(StmtTypes.get(kvar).getType())

    # JAA: commented out for benchmarking                            
    #if not estimate: print("varList: ", resultVars)
    if estimate: return dataTypes 
    return resultVars

def getOpCost(op_key, xorVarMap, varNames):
    global assignInfo
    varCounts = {}
    if op_key == expOp:
        for i in varNames:
            (funcName, varInfo) = getVarNameEntryFromAssignInfo(assignInfo, i)
            ceo = CountExpOp()
            sdl.ASTVisitor(ceo).preorder(varInfo.getAssignNode())
            v = xorVarMap.get(i)
            varCounts[ v ] = ceo.getCount()
        # JAA: commented out for benchmarking    
        #print("Final varCount for expOp: ", varCounts)

    return varCounts
    
def getConstraintList(info, constraintList, configVarName, xorVarMap, varTypes, generators, returnList=False):
    VarNames = getAssignmentForName(configVarName, varTypes)
    VarNames = list(set(VarNames).difference(generators))
    VarNames.sort()
    if info['verbose']: print("pruned varList: ", VarNames)
    if info != None:
        info['notInAPairing'] = list(set(VarNames).difference(xorVarMap.keys()))
        info['notInAPairing'].sort()
        if info[minOp] != None:
            # extract counts for whatever operation
            info[minKeyword] = getOpCost(info[minOp], xorVarMap, VarNames)
    # JAA: commented out for benchmarking
    #if len(info['notInAPairing']) > 0: print("Not in a pairing: ", info['notInAPairing'])
    VarNameList = []
    for i in VarNames:
        if xorVarMap.get(i) != None: VarNameList.append( xorVarMap.get(i) )
    if len(constraintList) > 0:
        for i in constraintList: # in case there are hash values
            if xorVarMap.get(i) != None and xorVarMap.get(i) not in VarNameList: 
                VarNameList.append( xorVarMap.get(i) )
    if returnList:
        return VarNameList # list
    return str(VarNameList) # string
 

def searchForSolution(info, shortOpt, hardConstraintList, txor, varTypes, conf, generators):
    resultDict = None
    satisfiable = False
    adjustConstraints = False
    mofnConstraints = None # only used if necessary
    fileSuffix = ""
    bothConstraints = {isSet:False }
    constraints = []
    # determine if user specified granular options such as 
    info[minOp] = None
    minOps = sizeOp # default operation
    info[minKeyword] = {}
    dropFirst = info.get('dropFirst')
    pkMapData  = info.get('pk_map')
    pkMapMin = None
    pkListMin = info.get('pk_list')
    assumpMapMin = None
    assumpData = info.get('assump_map')
    assumpList = info.get('assump_list')
    # check if user set the min operation field in config file?
    # this indicates interest in measuring 
    if hasattr(conf, minOp):
        info[minOp] = conf.operation
        minOps = info[minOp]           
    
    while not satisfiable:
        #print("\n<===== Generate Constraints =====>")    
        xorVarMap = txor.getVarMap()
        if shortOpt == SHORT_SECKEYS:
            # create constraints around keys
            fileSuffix = 'sk'
            assert type(conf.keygenSecVar) == str, "keygenSecVar in config file expected as a string"
            if not adjustConstraints:
                constraints = getConstraintList(info, hardConstraintList, conf.keygenSecVar, xorVarMap, varTypes, generators)
            else:
                flexConstraints = getConstraintList(info, [], conf.keygenSecVar, xorVarMap, varTypes, generators, returnList=True)
                newConstraintList = [xorVarMap.get(i) for i in hardConstraintList]
                flexConstraints = list(set(flexConstraints).difference(newConstraintList))
                if info['verbose']: 
                    print("DEBUG: n-of-n constraints: ", newConstraintList)
                    print("DEBUG: m-of-n constraints: ", flexConstraints)
                constraints = newConstraintList
                mofnConstraints = flexConstraints                        
        elif shortOpt == SHORT_ASSUMPTION:
            fileSuffix = 'assm'
            assert type(conf.assumption) in [str, list], "assumption in config file expected as a string or list"
            constraints = []
            assumpMapMin = {}
            for i,j in assumpData.items():
                assumpMapMin[xorVarMap.get(i)] = j
            #print("Assumption map: ", assumpMapMin)
            #print("Assumption list: ", assumpList)
        elif shortOpt == SHORT_PUBKEYS and conf.forAutoGroupPlus:
            # create constraints around keys
            assert pkMapData != None, "pkMapData was not set"
            fileSuffix = 'pk'
            assert type(conf.keygenPubVar) == str, "keygenPubVar in config file expected as a string"
            constraints = []
            pkMapMin = {}
            for i,j in pkMapData.items():
                pkMapMin[xorVarMap.get(i)] = j
            #print("Updated pk map  : ", pkMapMin)
            #print("Original pk list: ", pkListMin)
            # here is where we need to encode some stuff in the pairing
        # to remain backwards compatible with AutoGroup
        elif shortOpt == SHORT_PUBKEYS and conf.schemeType == PKSIG and not conf.forAutoGroupPlus:
            # create constraints around keys
            fileSuffix = 'pk'
            assert type(conf.keygenPubVar) == str, "keygenPubVar in config file expected as a string"
            if not adjustConstraints:
                constraints = getConstraintList(info, hardConstraintList, conf.keygenPubVar, xorVarMap, varTypes, generators)
            else:
                flexConstraints = getConstraintList(info, [], conf.keygenPubVar, xorVarMap, varTypes, generators, returnList=True)
                newConstraintList = [xorVarMap.get(i) for i in hardConstraintList]
                flexConstraints = list(set(flexConstraints).difference(newConstraintList))
                if info['verbose']:
                    print("DEBUG: n-of-n constraints: ", newConstraintList)
                    print("DEBUG: m-of-n constraints: ", flexConstraints)
                constraints = newConstraintList
                mofnConstraints = flexConstraints
        elif shortOpt == SHORT_CIPHERTEXT:
            fileSuffix = 'ct'
            assert type(conf.ciphertextVar) == str, "ciphertextVar in config file expected as a string"
            if not adjustConstraints:
                constraints = getConstraintList(info, hardConstraintList, conf.ciphertextVar, xorVarMap, varTypes, generators)
            else:
                flexConstraints = getConstraintList(info, [], conf.ciphertextVar, xorVarMap, varTypes, generators, returnList=True)
                newConstraintList = [xorVarMap.get(i) for i in hardConstraintList]
                flexConstraints = list(set(flexConstraints).difference(newConstraintList))
                if info['verbose']:
                    print("DEBUG: n-of-n constraints: ", newConstraintList)
                    print("DEBUG: m-of-n constraints: ", flexConstraints)
                constraints = newConstraintList
                mofnConstraints = flexConstraints
        elif shortOpt == SHORT_SIGNATURE:
            fileSuffix = 'sig'
            assert type(conf.signatureVar) == str, "signatureVar in config file expected as a string"
            if not adjustConstraints:
                constraints = getConstraintList(info, hardConstraintList, conf.signatureVar, xorVarMap, varTypes, generators)
            else:
                flexConstraints = getConstraintList(info, [], conf.signatureVar, xorVarMap, varTypes, generators, returnList=True)
                newConstraintList = [xorVarMap.get(i) for i in hardConstraintList]
                flexConstraints = list(set(flexConstraints).difference(newConstraintList))
                if info['verbose']:
                    print("DEBUG: n-of-n constraints: ", newConstraintList)
                    print("DEBUG: m-of-n constraints: ", flexConstraints)
                constraints = newConstraintList
                mofnConstraints = flexConstraints
        elif shortOpt == SHORT_FORALL and conf.schemeType == PKENC:
            fileSuffix = 'both' #default
            _hardConstraintList = [xorVarMap.get(i) for i in hardConstraintList]
            if info['verbose']: print("default constraints: ", _hardConstraintList)
            constraints_ky = getConstraintList(info, [], conf.keygenSecVar, xorVarMap, varTypes, generators, returnList=True)
            constraints_ky = list(set(constraints_ky).difference(_hardConstraintList))
            if info['verbose']: print("Constraints for ky: ", constraints_ky)
            constraints_ct = getConstraintList(info, [], conf.ciphertextVar, xorVarMap, varTypes, generators, returnList=True)
            constraints_ct = list(set(constraints_ct).difference(_hardConstraintList))
            if info['verbose']: print("Constraints for ct: ", constraints_ct)
            constraints = list(_hardConstraintList) + [conf.keygenSecVar, conf.ciphertextVar]
            bothConstraints[ isSet ] = True
            bothConstraints[ conf.keygenSecVar ] = constraints_ky
            bothConstraints[ conf.ciphertextVar ] = constraints_ct
            if dropFirst != None:
                if dropFirst == SHORT_SECKEYS:      dropFirst = conf.ciphertextVar 
                elif dropFirst == SHORT_CIPHERTEXT: dropFirst = conf.keygenSecVar
        elif shortOpt == SHORT_FORALL and conf.schemeType == PKSIG:
            fileSuffix = 'both' #default
            _hardConstraintList = [xorVarMap.get(i) for i in hardConstraintList]
            if info['verbose']: print("default constraints: ", _hardConstraintList)
            constraints_ky = getConstraintList(info, [], conf.keygenPubVar, xorVarMap, varTypes, generators, returnList=True)
            constraints_ky = list(set(constraints_ky).difference(_hardConstraintList))
            if info['verbose']: print("Constraints for ky: ", constraints_ky)
            constraints_sig = getConstraintList(info, [], conf.signatureVar, xorVarMap, varTypes, generators, returnList=True)
            constraints_sig = list(set(constraints_sig).difference(_hardConstraintList))
            if info['verbose']: print("Constraints for sig: ", constraints_sig)
            constraints = list(_hardConstraintList) + [conf.keygenPubVar, conf.signatureVar]
            bothConstraints[ isSet ] = True            
            bothConstraints[ conf.keygenPubVar ] = constraints_ky
            bothConstraints[ conf.signatureVar ] = constraints_sig
            if dropFirst != None:
                if dropFirst == SHORT_PUBKEYS:      dropFirst = conf.signatureVar # dropping the other 
                elif dropFirst == SHORT_SIGNATURE:  dropFirst = conf.keygenPubVar
        else:
            # JAA: commented out for benchmarking
            #print("'short' option not specified.\n")
            shortOpt = ""
        
        # time options
        timeOpt = ""
        if info[minOp] != None:
            fileSuffix += info[minOp]                
            if conf.schemeType == PKENC:
                configVarName = conf.keygenSecVar
                VarNames1 = getAssignmentForName(configVarName, varTypes)
                VarNames1 = list(set(VarNames1).difference(generators))
                VarNames1.sort()
                configVarName = conf.ciphertextVar
                VarNames2 = getAssignmentForName(configVarName, varTypes)
                VarNames2 = list(set(VarNames2).difference(generators))
                VarNames2.sort()
                
                VarNames = VarNames1 + VarNames2
                info[minKeyword] = getOpCost(info[minOp], xorVarMap, VarNames)
                timeOpt = info[minOp]
            elif conf.schemeType == PKSIG:
                configVarName = conf.keygenPubVar
                VarNames1 = getAssignmentForName(configVarName, varTypes)
                VarNames1 = list(set(VarNames1).difference(generators))
                VarNames1.sort()
                configVarName = conf.signatureVar
                VarNames2 = getAssignmentForName(configVarName, varTypes)
                VarNames2 = list(set(VarNames2).difference(generators))
                VarNames2.sort()
                
                VarNames = VarNames1 + VarNames2
                info[minKeyword] = getOpCost(info[minOp], xorVarMap, VarNames)
                timeOpt = info[minOp]
                
        #else:
        #    print("Unexpected configuration. Run python runAutoGroup.py --help-config")
        #    sys.exit(-1)
                
        #print("<===== Generate Constraints =====>\n")
        
        #print("<===== Generate SAT solver input =====>")
        
        # TODO: process constraints and add to output
        print("<===== Instantiate Z3 solver =====>")
        hardConstraints = [xorVarMap.get(i) for i in hardConstraintList]
        minOptions = info[curveID] # user should provide this information
        countOpt = info[minKeyword] # the cost of group operations
        (satisfiable, resultDict) = instantiateZ3Solver(info, conf, shortOpt, timeOpt, txor.getVariables(), txor.getClauses(),
                                                        hardConstraints, constraints, bothConstraints, countOpt, minOptions, dropFirst,
                                                        pkMapMin, pkListMin, assumpMapMin, assumpList, xorVarMap)
        if satisfiable == False:
            adjustConstraints = True
        print("<===== Instantiate Z3 solver =====>")

    return fileSuffix, resultDict

def convertType(v, i):
    if i == types.Int:
        return "Int"
    elif i == types.listInt:
        return "list{Int}"
    elif i == types.Str:
        return "Str"
    elif i == types.listStr:
        return "list{Str}"
    elif i == types.GT:
        return "GT"
    elif i == types.listGT:
        return "list{GT}"
    elif i == types.pol:
        return "pol"
    elif i == types.list:
        return "list"
    elif i == types.ZR:
        return "ZR"
    elif i == types.listZR:
        return "list{ZR}"
    elif i == types.metalistInt:
        pass
    print("DEBUG: convertType error: ", v, " = ", i)
    return False

def newTypeFrom(t, suffix):
    if suffix == G1Prefix:
        if t == types.G1:
            return "G1"
        elif t == types.listG1:
            return "list{G1}"
    elif suffix == G2Prefix:
        if t == types.G1:
            return "G2"
        elif t == types.listG1:
            return "list{G2}"
    return str(t) # not sure here
    
def transformTypes(typesH, info):
    typesHeadBegin = "BEGIN :: " + sdl.TYPES_HEADER
    typesHeadEnd = "END :: " + sdl.TYPES_HEADER
    newLines = [typesHeadBegin]
    typeLines = {}
    # extract line numbers
    for i, j in typesH.items():
        typeLines[ j.getLineNo() ] = (i, j)
    
    # sort based on line number, then process each type
    typeKeysList = list(typeLines.keys())
    typeKeysList.sort() # sort the line numbers
    for k in typeKeysList:
        (i, j) = typeLines[k]
        t = j.getType()
        if t in [types.G1, types.listG1]: #, types.Int, types.listInt, types.Str, types.listStr, types.GT]:
            if assignVarOccursInBoth(i, info):
                newLines.append( i + G1Prefix + " := " + newTypeFrom(t, G1Prefix) )
                newLines.append( i + G2Prefix + " := " + newTypeFrom(t, G2Prefix) )
            elif assignVarOccursInG1(i, info):
                newLines.append( i + " := " + newTypeFrom(t, G1Prefix) )
            elif assignVarOccursInG2(i, info):
                newLines.append( i + " := " + newTypeFrom(t, G2Prefix) )
            elif i in info['generators']:
                if i in info['generatorMapG1']:
                    newLines.append(info['generatorMapG1'][i] + " := " + newTypeFrom(t, G1Prefix) )
                if i in info['generatorMapG2']:
                    newLines.append(info['generatorMapG2'][i] + " := " + newTypeFrom(t, G2Prefix) )
        else:
            resType = convertType(i, t)
            if resType != False:
                newLines.append( i + " := " + resType )
            else:
                # keep the original SDL type line
                newLines.append( j.getSrcLine() )
    
    newLines.append(typesHeadEnd)
    return newLines

def searchForChildren(key, depValue, data_map, info, seen_before):
    lhs_orig_vars, lhs_var_map = info['G1_lhs']
    rhs_orig_vars, rhs_var_map = info['G1_rhs']

    depList = []
    for i in lhs_orig_vars:
        if key in lhs_var_map[i]:
            data_map[i] = data_map[i].union([depValue])
            depList.append(i)

    for i in rhs_orig_vars:
        if key in rhs_var_map[i]:
            data_map[i] = data_map[i].union([depValue])
            depList.append(i)

    # recursively visit children of depList
    depList = list(set(depList))
    for i in depList:
        if i not in seen_before:
            seen_before.append(i)
            seen_before = list(set(seen_before))
            searchForChildren(i, depValue, data_map, info, seen_before)

    return

def look_for_map(node, group_info, target_type):
    (a, b) = node
    a_pr = a # by default
    if a in group_info['generatorMapG1'] and target_type == types.G1:
        a_pr = group_info['generatorMapG1'][a]
    elif a in group_info['generatorMapG2'] and target_type == types.G2:
        a_pr = group_info['generatorMapG2'][a]
    else:
        pass # keep the same in the defualt case
    return (a_pr, b)


def buildSplitGraphForScheme(sdl_filename, sdl_name, config, sdlVerbose, pair_graph, group_info):
    sdl.parseFile(sdl_filename, sdlVerbose, ignoreCloudSourcing=True)
    varTypes = dict(sdl.getVarTypes().get(TYPES_HEADER))

    # TODO: extend to signatures
    if config.schemeType == PKENC:
        (stmtS, typesS, depListS, depListNoExpS, infListS, infListNoExpS) = sdl.getVarInfoFuncStmts( config.setupFuncName )
        (stmtK, typesK, depListK, depListNoExpK, infListK, infListNoExpK) = sdl.getVarInfoFuncStmts( config.keygenFuncName )
        (stmtE, typesE, depListE, depListNoExpE, infListE, infListNoExpE) = sdl.getVarInfoFuncStmts( config.encryptFuncName )
        (stmtD, typesD, depListD, depListNoExpD, infListD, infListNoExpD) = sdl.getVarInfoFuncStmts( config.decryptFuncName )
        varTypes.update(typesS)
        varTypes.update(typesK)
        varTypes.update(typesE)
        varTypes.update(typesD)
        # add smart update only if there is an existing edge in the graph (e.g., a -> b, either a or b in the set of nodes)
        dg_setup1 = generateGraphForward(config.setupFuncName, (stmtS, typesS, infListNoExpS), types.G1)
        dg_keygen1 = generateGraph(config.keygenFuncName, (typesK, depListNoExpK), types.G1, varTypes)
        dg_encrypt1 = generateGraph(config.encryptFuncName, (typesE, depListNoExpE), types.G1, varTypes)
        dg_decrypt1 = generateGraph(config.decryptFuncName, (typesD, depListNoExpD), types.G1, varTypes)
        dg_scheme1 = DotGraph(sdl_name)
        if sdlVerbose:
            print("<=== Setup Graph ===>")
            print(dg_setup1)
            print("<=== Setup Graph ===>")

            print("<=== Keygen Graph ===>")
            print(dg_keygen1)
            print("<=== Keygen Graph ===>")

            print("<=== Encrypt Graph ===>")
            print(dg_encrypt1)
            print("<=== Encrypt Graph ===>")

            print("<=== Decrypt Graph ===>")
            print(dg_decrypt1)
            print("<=== Decrypt Graph ===>")

        # merge the different graphs into one big one
        dg_scheme1 += dg_setup1 + dg_keygen1 + dg_encrypt1 + dg_decrypt1
        dg_scheme1.smart_update(pair_graph)
        if sdlVerbose:
            print("<=== Scheme Graph ===>")
            print(dg_scheme1)
            print("<=== Scheme Graph ===>")

        dg_setup2 = generateGraphForward(config.setupFuncName, (stmtS, typesS, infListNoExpS), types.G2)
        dg_keygen2 = generateGraph(config.keygenFuncName, (typesK, depListNoExpK), types.G2, varTypes)
        dg_encrypt2 = generateGraph(config.encryptFuncName, (typesE, depListNoExpE), types.G2, varTypes)
        dg_decrypt2 = generateGraph(config.decryptFuncName, (typesD, depListNoExpD), types.G2, varTypes)
        dg_scheme2 = DotGraph(sdl_name)
        if sdlVerbose:
            print("<=== Setup Graph ===>")
            print(dg_setup2)
            print("<=== Setup Graph ===>")

            print("<=== Keygen Graph ===>")
            print(dg_keygen2)
            print("<=== Keygen Graph ===>")

            print("<=== Encrypt Graph ===>")
            print(dg_encrypt2)
            print("<=== Encrypt Graph ===>")

            print("<=== Decrypt Graph ===>")
            print(dg_decrypt2)
            print("<=== Decrypt Graph ===>")

        # merge the different graphs into one big one
        dg_scheme2 += dg_setup2 + dg_keygen2 + dg_encrypt2 + dg_decrypt2
        dg_scheme2.smart_update(pair_graph)
        if sdlVerbose:
            print("<=== G2 side of Scheme Graph ===>")
            print(dg_scheme2)
            print("<=== G2 side of Scheme Graph ===>")
    elif config.schemeType == PKSIG:
        (stmtS, typesS, depListS, depListNoExpS, infListS, infListNoExpS) = sdl.getVarInfoFuncStmts( config.setupFuncName )
        (stmtK, typesK, depListK, depListNoExpK, infListK, infListNoExpK) = sdl.getVarInfoFuncStmts( config.keygenFuncName )
        (stmtSi, typesSi, depListSi, depListNoExpSi, infListSi, infListNoExpSi) = sdl.getVarInfoFuncStmts( config.signFuncName )
        (stmtV, typesV, depListV, depListNoExpV, infListV, infListNoExpV) = sdl.getVarInfoFuncStmts( config.verifyFuncName )
        varTypes.update(typesS)
        varTypes.update(typesK)
        varTypes.update(typesSi)
        varTypes.update(typesV)
        # create the graph0 and graph1 lists from the pairing portion of graph
        nodes = []
        for k,v in pair_graph.items():
            nodes += v
        graph0 = []
        graph1 = []
        for i in range(0, len(nodes), 2):
            (lhs, a) = nodes[i]
            # check against original pairing variables in input SDL file
            if lhs in group_info['pairing']['G1']:
                graph0.append(look_for_map(nodes[i], group_info, types.G1))
                graph1.append(look_for_map(nodes[i+1], group_info, types.G2))
            else:
                graph0.append(look_for_map(nodes[i+1], group_info, types.G1))
                graph1.append(look_for_map(nodes[i], group_info, types.G2))

        if sdlVerbose:
            print("Graph 0: ", graph0)
            print("Graph 1: ", graph1)
        assert len(graph0) == len(graph1), "Something wrong with SDL output"

        if hasattr(config, 'setupFuncName'):
            dg_setup1 = generateGraph(config.setupFuncName, (typesS, depListNoExpS), types.G1)
            has_setup = True
        else:
            has_setup = False

        new_depListNoExpK = simplifyDepMap(stmtK, typesK, infListNoExpK, depListNoExpK)
        dg_keygen1 = generateGraph(config.keygenFuncName, (typesK, new_depListNoExpK), types.G1, varTypes)

        new_depListNoExpSi = simplifyDepMap(stmtSi, typesSi, infListNoExpSi, depListNoExpSi)
        dg_sign1 = generateGraph(config.signFuncName, (typesSi, new_depListNoExpSi), types.G1, varTypes)
        dg_verify1 = generateGraph(config.verifyFuncName, (typesV, depListNoExpV), types.G1, varTypes)
        dg_scheme1 = DotGraph(sdl_name)

        # if sdlVerbose:
        #     if has_setup:
        #         print("<=== Setup Graph ===>")
        #         print(dg_setup1)
        #         print("<=== Setup Graph ===>")
        #
        #     print("<=== Keygen Graph ===>")
        #     print(dg_keygen1)
        #     print("<=== Keygen Graph ===>")
        #
        #     print("<=== Sign Graph ===>")
        #     print(dg_sign1)
        #     print("<=== Sign Graph ===>")
        #
        #     print("<=== Verify Graph ===>")
        #     print(dg_verify1)
        #     print("<=== Verify Graph ===>")

        # merge the different graphs into one big one
        dg_scheme1 += dg_setup1 + dg_keygen1 + dg_sign1 + dg_verify1
        dg_scheme1.add_pair_edges(graph0)
        if sdlVerbose:
             print("<=== G1 side of Scheme Graph ===>")
             print(dg_scheme1)
             print("<=== G1 side of Scheme Graph ===>")

        ######### focus on G2 ################
        if hasattr(config, 'setupFuncName'):
            dg_setup2 = generateGraph(config.setupFuncName, (typesS, depListNoExpS), types.G2)
            has_setup = True
        else:
            has_setup = False

        new_depListNoExpK = simplifyDepMap(stmtK, typesK, infListNoExpK, depListNoExpK)
        dg_keygen2 = generateGraph(config.keygenFuncName, (typesK, new_depListNoExpK), types.G2, varTypes)

        new_depListNoExpSi = simplifyDepMap(stmtSi, typesSi, infListNoExpSi, depListNoExpSi)
        dg_sign2 = generateGraph(config.signFuncName, (typesSi, new_depListNoExpSi), types.G2, varTypes)
        dg_verify2 = generateGraph(config.verifyFuncName, (typesV, depListNoExpV), types.G2, varTypes)
        dg_scheme2 = DotGraph(sdl_name)
        # if sdlVerbose:
        #     if has_setup:
        #         print("<=== Setup Graph ===>")
        #         print(dg_setup2)
        #         print("<=== Setup Graph ===>")
        #
        #     print("<=== Keygen Graph ===>")
        #     print(dg_keygen2)
        #     print("<=== Keygen Graph ===>")
        #
        #     print("<=== Sign Graph ===>")
        #     print(dg_sign2)
        #     print("<=== Sign Graph ===>")
        #
        #     print("<=== Verify Graph ===>")
        #     print(dg_verify2)
        #     print("<=== Verify Graph ===>")

        # merge the different graphs into one big one
        dg_scheme2 += dg_setup2 + dg_keygen2 + dg_sign2 + dg_verify2
        dg_scheme2.add_pair_edges(graph1)
        if sdlVerbose:
             print("<=== G2 side of Scheme Graph ===>")
             print(dg_scheme2)
             print("<=== G2 side of Scheme Graph ===>")
    return

def buildSplitGraphForAssumption(sdl_filename, sdl_name, config, sdlVerbose):
    sdl.parseFile(sdl_filename, sdlVerbose, ignoreCloudSourcing=True)
    varTypes = dict(sdl.getVarTypes().get(TYPES_HEADER))

    (stmtS, typesS, depListS, depListNoExpS, infListS, infListNoExpS) = sdl.getVarInfoFuncStmts( config.assumpSetupFuncName )
    (stmtA, typesA, depListA, depListNoExpA, infListA, infListNoExpA) = sdl.getVarInfoFuncStmts( config.assumpFuncName )
    varTypes.update(typesS)
    varTypes.update(typesA)

    dg_assumption1 = DotGraph(sdl_name)
    dg_assump_setup1 = generateGraph(config.assumpSetupFuncName, (typesS, depListNoExpS), types.G1, varTypes)
    dg_assump_itself1 = generateGraph(config.assumpFuncName, (typesA, depListNoExpA), types.G1, varTypes)

    dg_assumption1 += dg_assump_setup1 + dg_assump_itself1
    print("<=== Assumption Instance Graph ===>")
    print(dg_assumption1)
    print("<=== Assumption Instance Graph ===>")

    dg_assumption2 = DotGraph(sdl_name)
    dg_assump_setup2 = generateGraph(config.assumpSetupFuncName, (typesS, depListNoExpS), types.G2, varTypes)
    dg_assump_itself2 = generateGraph(config.assumpFuncName, (typesA, depListNoExpA), types.G2, varTypes)

    dg_assumption2 += dg_assump_setup2 + dg_assump_itself2
    print("<=== Assumption Instance Graph ===>")
    print(dg_assumption2)
    print("<=== Assumption Instance Graph ===>")

    sys.exit(0)

"""
runAutoGroup is the main entry point into the AutoGroup tool. It takes as input the
sdl filename, a config file and the options which include security parameter,
a drop first requirement in case multiple solutions achieve the user's requirements,
and a destination path for the generated Asymmetric-based scheme and accompanying code.
"""
def runAutoGroupOld(sdlFile, config, options, sdlVerbose=False):
    sdl.parseFile(sdlFile, sdlVerbose, ignoreCloudSourcing=True)
    global assignInfo
    # this contains a Variable Object for each statement in the SDL file
    assignInfo = sdl.getAssignInfo()
    # this consists of the type of the input scheme (e.g., symmetric)
    setting = sdl.assignInfo[sdl.NONE_FUNC_NAME][ALGEBRAIC_SETTING].getAssignNode().getRight().getAttribute()
    # name of the scheme
    sdl_name = sdl.assignInfo[sdl.NONE_FUNC_NAME][BV_NAME].getAssignNode().getRight().getAttribute()
    # the block of types in the SDL
    typesBlock = sdl.getFuncStmts( TYPES_HEADER )
    info = {'verbose':sdlVerbose, isAutoGroupKeyword: True}

    # we want to ignore user defined functions from our analysis
    # (unless certain variables that we care about are manipulated there)
    userCodeBlocks = list(set(list(assignInfo.keys())).difference(config.functionOrder + [TYPES_HEADER, NONE_FUNC_NAME]))
    options['userFuncList'] += userCodeBlocks
    print("name is", sdl_name)
    print("setting is", setting)
    
    lines = list(typesBlock[0].keys())
    lines.sort()
    typesBlockLines = [ i.rstrip() for i in sdl.getLinesOfCodeFromLineNos(lines) ]
    begin = ["BEGIN :: " + TYPES_HEADER]
    end = ["END :: " + TYPES_HEADER]

    # start constructing the preamble for the Asymmetric SDL output
    newLines0 = [ BV_NAME + " := " + sdl_name, SETTING + " := " + sdl.ASYMMETRIC_SETTING ] 
    newLines1 = begin + typesBlockLines + end
    # this fact is already verified by the parser
    # but if scheme claims symmetric
    # and really an asymmetric scheme then parser will
    # complain.
    assert setting == sdl.SYMMETRIC_SETTING, "No need to convert to asymmetric setting."    
    # determine user preference in terms of keygen or encrypt
    short = SHORT_DEFAULT # default option
    if hasattr(config, 'short'):
        if config.short in SHORT_OPTIONS:
            short = config.short
    print("reducing size of '%s'" % short) 

    varTypes = dict(sdl.getVarTypes().get(TYPES_HEADER))
    typesH = dict(varTypes)
    if not hasattr(config, 'schemeType'):
        sys.exit("'schemeType' option missing in specified config file.")
    pairingSearch = []
    # extract the statements, types, dependency list, influence list and exponents of influence list
    # for each algorithm in the SDL scheme
    if config.schemeType == PKENC:
        (stmtS, typesS, depListS, depListNoExpS, infListS, infListNoExpS) = sdl.getVarInfoFuncStmts( config.setupFuncName )
        (stmtK, typesK, depListK, depListNoExpK, infListK, infListNoExpK) = sdl.getVarInfoFuncStmts( config.keygenFuncName )
        (stmtE, typesE, depListE, depListNoExpE, infListE, infListNoExpE) = sdl.getVarInfoFuncStmts( config.encryptFuncName )    
        (stmtD, typesD, depListD, depListNoExpD, infListD, infListNoExpD) = sdl.getVarInfoFuncStmts( config.decryptFuncName )
        varTypes.update(typesS)
        varTypes.update(typesK)
        varTypes.update(typesE)
        varTypes.update(typesD)
        # TODO: expand search to encrypt and potentially setup
        pairingSearch += [stmtS, stmtE, stmtD] # aka start with decrypt.
    # extract statements, etc ... for each algorithm in the SDL scheme.
    elif config.schemeType == PKSIG:
        if hasattr(config, 'setupFuncName'): 
            (stmtS, typesS, depListS, depListNoExpS, infListS, infListNoExpS) = sdl.getVarInfoFuncStmts( config.setupFuncName )
            varTypes.update(typesS)
            pairingSearch += [stmtS]
        (stmtK, typesK, depListK, depListNoExpK, infListK, infListNoExpK) = sdl.getVarInfoFuncStmts( config.keygenFuncName )
        (stmtSi, typesSi, depListSi, depListNoExpSi, infListSi, infListNoExpSi) = sdl.getVarInfoFuncStmts( config.signFuncName )    
        (stmtV, typesV, depListV, depListNoExpV, infListV, infListNoExpV) = sdl.getVarInfoFuncStmts( config.verifyFuncName )
        varTypes.update(typesK)
        varTypes.update(typesSi)
        varTypes.update(typesV)
        pairingSearch += [stmtV] # aka start with verify
        #pairingSearch += [stmtSi, stmtV] # aka start with verify
    else:
        sys.exit("'schemeType' options are 'PKENC' or 'PKSIG'")

    info[curveID] = options['secparam']
    info[dropFirstKeyword] = options[dropFirstKeyword]
    gen = Generators(info)
    # JAA: commented out for benchmarking    
    #print("List of generators for scheme")
    # retrieve the generators selected by the scheme
    # typically found in the setup routine in most cases.
    if hasattr(config, "extraSetupFuncName"):
        (stmtSe, typesSe, depListSe, depListNoExpSe, infListSe, infListNoExpSe) = sdl.getVarInfoFuncStmts( config.extraSetupFuncName )
        gen.extractGens(stmtSe, typesSe)
        #extractGeneratorList(stmtSe, typesSe, generators)
        varTypes.update(typesSe)
    # extract the generators from the setup and keygen routine for later use
    if hasattr(config, 'setupFuncName'):
        gen.extractGens(stmtS, typesS)
    if hasattr(config, 'keygenFuncName'):
        gen.extractGens(stmtK, typesK)
    else:
        sys.exit("Assumption failed: setup not defined for this function. Where to extract generators?")
    generators = gen.getGens()
    # JAA: commented out for benchmarking    
    #print("Generators extracted: ", generators)


    ##### check generators for hashes #####
    hashgens = []

    if hasattr(config, "extraSetupFuncName"):
        for i in stmtSe.keys():
            if(not len(stmtSe[i].getHashArgsInAssignNode()) == 0):

                t = stmtSe[i].getAssignVar()

                if typesSe.get(t) == None:
                    typ = stmtSe[i].getAssignNode().right.left.attr
                else:
                    typ = typesSe[t].getType()

                if typ == types.G1:
                    hashgens.append(t)

                    print("\nWARNING!!!!  Hash in extra Setup.  If AutoGroup+ fails later on, this could be the cause!")
                    print("line ", i, " : ", t, "\n")


    if hasattr(config, 'setupFuncName'):
        for i in stmtS.keys():
            if(not len(stmtS[i].getHashArgsInAssignNode()) == 0):

                t = stmtS[i].getAssignVar()

                if typesS.get(t) == None:
                    typ = stmtS[i].getAssignNode().right.left.attr
                else:
                    typ = typesS[t].getType()

                if typ == types.G1:
                    hashgens.append(t)

                    print("\nWARNING!!!!  Hash in Setup.  If AutoGroup+ fails later on, this could be the cause!")
                    print("line ", i, " : ", t, "\n")


    if hasattr(config, 'keygenFuncName'):
        for i in stmtK.keys():
            if(not len(stmtK[i].getHashArgsInAssignNode()) == 0):

                t = stmtK[i].getAssignVar()

                if typesK.get(t) == None:
                    typ = stmtK[i].getAssignNode().right.left.attr
                else:
                    typ = typesK[t].getType()

                if typ == types.G1:
                    t = stmtK[i].getAssignVar()
                    hashgens.append(t)

                    print("\nWARNING!!!!  Hash in KeyGen.  If AutoGroup+ fails later on, this could be the cause!")
                    print("line ", i, " : ", t, "\n")

    #######################################


    # need a Visitor class to build these variables  
    # TODO: expand to other parts of algorithm including setup, keygen, encrypt
    # Visits each pairing computation in the SDL and
    # extracts the inputs. This is the beginning of the
    # analysis of these variables as the SDL is converted into
    # an asymmetric scheme.
    hashVarList = []
    pair_vars_G1_lhs = [] 
    pair_vars_G1_rhs = []    
    gpv = GetPairingVariables(pair_vars_G1_lhs, pair_vars_G1_rhs)
    for eachStmt in pairingSearch: # loop through each pairing statement
        lines = eachStmt.keys() # for each line, do the following
        for i in lines:
            if type(eachStmt[i]) == sdl.VarInfo: # make sure we have the Var Object
                # assert that the statement contains a pairing computation
                if HasPairings(eachStmt[i].getAssignNode()):
                    path_applied = []
                    # split pairings if necessary so that we don't influence
                    # the solve in anyway. We can later recombine these during
                    # post processing of the SDL
                    eachStmt[i].assignNode = SplitPairings(eachStmt[i].getAssignNode(), path_applied)
                    # JAA: commented out for benchmarking                    
                    #if len(path_applied) > 0: print("Split Pairings: ", eachStmt[i].getAssignNode())
                    if info['verbose']: print("Each: ", eachStmt[i].getAssignNode())
                    sdl.ASTVisitor( gpv ).preorder( eachStmt[i].getAssignNode() )
                elif eachStmt[i].getHashArgsInAssignNode(): 
                    # in case there's a hashed value...build up list and check later to see if it appears
                    # in pairing variable list
                    hashVarList.append(str(eachStmt[i].getAssignVar()))
                else:
                    continue # not interested

    # constraint list narrows the solutions that
    # we care about
    constraintList = []
    # for example, include any hashed values that show up in a pairing by default
    for i in hashVarList:
        if i in pair_vars_G1_lhs or i in pair_vars_G1_rhs:
            constraintList.append(i)
    # JAA: commented out for benchmarking            
    # for each pairing variable, we construct a dependency graph all the way back to
    # the generators used. The input of assignTraceback consists of the list of SDL statements,
    # generators from setup, type info, and the pairing variables.
    # We do this analysis for both sides
    info[ 'G1_lhs' ] = (pair_vars_G1_lhs, assignTraceback(assignInfo, generators, varTypes, pair_vars_G1_lhs, constraintList))
    info[ 'G1_rhs' ] = (pair_vars_G1_rhs, assignTraceback(assignInfo, generators, varTypes, pair_vars_G1_rhs, constraintList))

    # JAA: commented out for benchmarking
    #print("<===== Determine Asymmetric Generators =====>")
    # construct the asymmetric generators for the new SDL
    (generatorMapG1, generatorMapG2) = gen.setupNewGens() #TODO: do we need to setup any generators from the assumption/reduction??
    # generate the relevant SDL lines
    generatorLines = gen.getGenLines()
    # JAA: commented out for benchmarking    
    #print("Generators in G1: ", generatorMapG1)
    #print("Generators in G2: ", generatorMapG2)
    #print("Generator Lines: ", generatorLines)
    #print("<===== Determine Asymmetric Generators =====>\n")
    
    #print("<===== Generate XOR clauses =====>")  
    # let the user's preference for fixing the keys or ciphertext guide this portion of the algorithm.
    # info[ 'G1' ] : represents (varKeyList, depVarMap).
    # sanity check that we have an equivalent number of inputs to pairings
    assert len(pair_vars_G1_lhs) == len(pair_vars_G1_rhs), "Uneven number of pairings. Please inspect your SDL file."
    # now we can construct the logical formula input to the SMT solver
    #TODO: add any pairings from assumption/reduction
    varsLen = len(pair_vars_G1_lhs)
    xorList = []
    for i in range(varsLen):
        xor = BinaryNode(ops.XOR)
        xor.left = BinaryNode(pair_vars_G1_lhs[i])
        xor.right = BinaryNode(pair_vars_G1_rhs[i])
        xorList.append(xor)
    
    ANDs = [ BinaryNode(ops.AND) for i in range(len(xorList)-1) ]
    for i in range(len(ANDs)):
        ANDs[i].left = BinaryNode.copy(xorList[i])
        if i < len(ANDs)-1: ANDs[i].right = ANDs[i+1]
        else: ANDs[i].right = BinaryNode.copy(xorList[i+1])
    # JAA: commented out for benchmarking        
    #print("XOR clause: ", ANDs[0])
    txor = transformXOR(None) # accepts dictionary of fixed values
    sdl.ASTVisitor(txor).preorder(ANDs[0])
    #print("<===== Generate XOR clauses =====>")

    #constraints = "[]"
    # given the above formula and the constraint list and options we can
    # run the solver to produce an initial set of solutions
    fileSuffix, resultDict = searchForSolution(info, short, constraintList, txor, varTypes, config, generators)
    # map of Z3 to SDL pairing variables (so we can map the solution to SDL)
    xorVarMap = txor.getVarMap()
#    if short != SHORT_FORALL:
#        res, resMap = NaiveEvaluation(resultDict, short)
#        print("Group Mapping: ", res)
#        # determine whether to make True = G1 and False = G2. 
#        # It depends on which counts more since they're interchangeable...
#        groupInfo = DeriveGeneralSolution(res, resMap, xorVarMap, info)
#    else:

    # narrow the specific solution that user asked for
    groupInfo = DeriveSpecificSolution(resultDict, xorVarMap, info)
    newAssignments = groupInfo['newSol']
    symDataTypePK  = {}
    asymDataTypePK = {}
    # we include some code to estimate size of SK/PK and CTs/Sigs
    # if the 'computeSize' option is set (e.g., --estimate option)
    #TODO: update??
    if config.schemeType == PKENC and options['computeSize']:   
        symDataTypeSK = getAssignmentForName(config.keygenSecVar, varTypes, True)
        symDataTypeCT = getAssignmentForName(config.ciphertextVar, varTypes, True)
        asymDataTypeSK = {}
        asymDataTypeCT = {}
        newSol = groupInfo['newSol']
        for i in symDataTypeSK:
            if i in newSol.keys():
               asymDataTypeSK[i] = newSol[i]
            else:
               asymDataTypeSK[i] = symDataTypeSK[i]
               
        for i in symDataTypeCT:
            if i in newSol.keys():
               asymDataTypeCT[i] = newSol[i]
            else:
               asymDataTypeCT[i] = symDataTypeCT[i]
        print("<====================>")
        print("SK => ", list(symDataTypeSK.keys()))
        print("estimated  sym:  ", estimateSize(symDataTypeSK, symmetric_curves['SS1536']))        
        print("estimated asym: ", estimateSize(asymDataTypeSK, asymmetric_curves['BN256']))
        print("CT => ", list(symDataTypeCT.keys()))               
        print("estimated  sym: ", estimateSize(symDataTypeCT, symmetric_curves['SS1536']))            
        print("estimated asym: ", estimateSize(asymDataTypeCT, asymmetric_curves['BN256']))
        print("<====================>")
    elif config.schemeType == PKSIG and options['computeSize']:
        symDataTypePK = getAssignmentForName(config.keygenPubVar, varTypes, True)
        symDataTypeSIG = getAssignmentForName(config.signatureVar, varTypes, True)
        #asymDataTypePK = {}
        asymDataTypeSIG = {}
        newSol = groupInfo['newSol']
        for i in symDataTypePK:
            if i in newSol.keys():
               asymDataTypePK[i] = newSol[i]
            else:
               asymDataTypePK[i] = symDataTypePK[i] # keep old type
               
        for i in symDataTypeSIG:
            if i in newSol.keys():
               asymDataTypeSIG[i] = newSol[i]
            else:
               asymDataTypeSIG[i] = symDataTypeSIG[i]
        print("<====================>")
#        print("PK => ", list(symDataTypePK.keys()))
#        print("estimated  sym:  ", estimateSize(symDataTypePK, symmetric_curves['SS1536']))        
#        print("estimated asym: ", estimateSize(asymDataTypePK, asymmetric_curves['BN256']))
        print("SIG => ", list(symDataTypeSIG.keys()))               
        print("estimated  sym: ", estimateSize(symDataTypeSIG, symmetric_curves['SS1536']))            
        print("estimated asym: ", estimateSize(asymDataTypeSIG, asymmetric_curves['BN256']))
        print("<====================>")

    # we still care about group elements that are not used in pairings
    # the rule is that we always assign these elements to G1 (so as long as
    # so as long as it doesn't affect any pairing computations)
    if info.get('notInAPairing') != None and len(info['notInAPairing']) > 0:
        #groupInfo['G1'] = groupInfo['G1'].union( info['notInAPairing'] )
        for i in info['notInAPairing']:
            if not(i in groupInfo['G2']) and not(i in groupInfo['both']):
                groupInfo['G1'] = set((list(groupInfo['G1']) + [i]))
        #print("Update: new G1 deps=>", groupInfo['G1'])    

    # put all the info together so that we can generate the new Asym SDL
    groupInfo['generators'] = generators 
    groupInfo['generatorMapG1'] = generatorMapG1
    groupInfo['generatorMapG2'] = generatorMapG2
    groupInfo['baseGeneratorG1'] = info['baseGeneratorG1'] # usually 'g'
    groupInfo['baseGeneratorG2'] = info['baseGeneratorG2']
    groupInfo['newTypes'] = {}
    groupInfo['varTypes'] = {}
    groupInfo['varTypes'].update(varTypes)
    groupInfo['usedVars'] = set()
    groupInfo['verbose'] = info['verbose']
    transFunc = {}
    transFuncGen = {}

    # determine the structure of the input SDL and stick as close as
    # possible to that in the output SDL
    if hasattr(config, "extraSetupFuncName"):
        transFuncGen[ config.extraSetupFuncName ] = stmtSe
    if hasattr(config, 'setupFuncName'):    
        transFuncGen[ config.setupFuncName ] = stmtS
    elif hasattr(config, 'keygenFuncName'):
        transFuncGen[ config.keygenFuncName ] = stmtK

    if config.schemeType == PKENC:
        transFunc[ config.keygenFuncName ]  = stmtK
        transFunc[ config.encryptFuncName ] = stmtE
        transFunc[ config.decryptFuncName ] = stmtD
    elif config.schemeType == PKSIG:
        if hasattr(config, 'setupFuncName') or hasattr(config, "extraSetupFuncName"):
            transFunc[ config.keygenFuncName ] = stmtK
        transFunc[ config.signFuncName ] = stmtSi
        transFunc[ config.verifyFuncName ] = stmtV
    
    if options['computeSize']:
        options['symPK']  = symDataTypePK
        options['asymPK'] = asymDataTypePK

    # with the functions and SDL statements defined, can simply run AsymSDL to construct the new SDL
    newSDL = AsymSDL(options, assignInfo, groupInfo, typesH, generatorLines, transFunc, transFuncGen)
    newLinesT, newLinesSe, newLinesS, newLinesK, newLines2, newLines3, userFuncLines = newSDL.constructSDL(config)

    # debug output of the SDL file
    print_sdl(info['verbose'], newLinesS, newLinesK, newLines2, newLines3)
    # output the new SDL file with right suffix (which indicates options that were set)
    outputFile = sdl_name + "_asym_" + fileSuffix + sdlSuffix
    writeConfig(options['path'] + outputFile, newLines0, newLinesT, newLinesSe, newLinesS, newLinesK, newLines2, newLines3, userFuncLines)

    return outputFile

dotProdPrefix = 'dotProd'
def stripExtraVars( someList ):
    newList = []
    if someList:
        for i in someList:
            if i != 'G1' and dotProdPrefix not in i:
                newList.append(i)
            else:
                pass
                #print("got one: ", i)
        return newList

def addAllEdgesIfSourceGroup(graph, a, depMap, typeMap, target_type, addlTypes):
    the = typeMap.get(a)
    the_list = depMap.get(a)
    if the_list:
        if len(the_list) == 0 and the.type == target_type:
            #print("Missing case: ", a) # probably a root?
            graph.addDirectedEdge(a, a)
    elif addlTypes:
        the = addlTypes.get(a)
        if the and the.type == target_type:
            graph.addDirectedEdge(a, a)   # print("Found a G1 type for: ", a)
        return
    else:
        #print("No record for: ", a)
        return

    filtered = stripExtraVars(depMap.get(a))
    for b in filtered:
        the2 = typeMap.get(str(b))
        if not the2 and addlTypes: # not in
            the2 = addlTypes.get(str(b))
        else:
            #assert addlTypes != None, "Can't check add'l types dictionary for: " + b
            if addlTypes != None:
                the2 = addlTypes.get(str(b))
            else:
                pass #print("Need add'l types to verify an edge is possible for: ", b)

        if the2 == None:
            #print("Could not locate type info: " + str(b))
            continue
        if the2.type == target_type:
            # b -> a (we want it backwards)
            graph.addDirectedEdge(b, a)
    return

def simplifyDepMap(stmtS, typesS, infListNoExpS, depListNoExpS):
    new_dep_map = dict(depListNoExpS)

    eachStmt = stmtS
    lines = eachStmt.keys() # for each line, do the following
    for i in lines:
        if type(eachStmt[i]) == sdl.VarInfo: # make sure we have the Var Object
            assignVarName = eachStmt[i].getAssignVar()
            the_stmt = eachStmt[i].getAssignNode()
            dep_list = eachStmt[i].getVarDepsNoExponents()
            if new_dep_map.get(assignVarName):
                new_dep_map[assignVarName] = list(set(new_dep_map[assignVarName]).intersection(dep_list))
                new_dep_map[assignVarName].sort()
    return new_dep_map

def generateGraphForward(alg_name, alg_structure, target_type=types.G1, exclude=[]):
    dg = DotGraph(alg_name)
    assert len(alg_structure) == 3, "expecting (stmtS, typesS, infListNoExpS)"
    (stmtS, typesS, infListNoExpS) = alg_structure

    eachStmt = stmtS
    lines = eachStmt.keys() # for each line, do the following
    for i in lines:
        if type(eachStmt[i]) == sdl.VarInfo: # make sure we have the Var Object
            # assert that the statement contains a pairing computation
            source = eachStmt[i].getAssignVar()
            if source in exclude: # don't process any further
                continue
            if eachStmt[i].getHasPairings():
                #print("Variable in GT: ", source, "=>", eachStmt[i].getAssignNode())
                continue
            if eachStmt[i].getHasRandomness():
                the_type = typesS.get(str(source))
                if the_type:
                    pass #print("Random: ", the_type.type)
                elif not the_type and LIST_INDEX_SYMBOL in str(source):
                    new_source = source.split(LIST_INDEX_SYMBOL)[0]
                    the_type = typesS.get(str(new_source))
                    pass #print("Random type: ", the_type.type)
                assert the_type != None, "generateGraphForward => invalid type: " + str(source)
                if the_type.type == target_type:
                    dg.addDirectedEdge(source, source)
                else:
                    continue # can ignore since we don't care about that link
            elif eachStmt[i].isList:
                continue
            elif HasPairings(eachStmt[i].getAssignNode()):
                continue
            else:
                #print("Do some inf parsing here...")
                depList = eachStmt[i].getVarDepsNoExponents()
                for t in depList:
                    the_type = typesS.get(str(t))
                    # if part of target type, then include as a direct edge
                    if the_type and the_type.type == target_type:
                        dg.addDirectedEdge(t, source)
    return dg

def is_related(found_type, target_type):
    if target_type == types.G1 and found_type in [types.G1, types.listG1, types.metalistG1]:
        return True
    elif target_type == types.G2 and found_type in [types.G2, types.listG2, types.metalistG2]:
        return True
    # only concerned with these two cases
    return False


def generateGraph(alg_name, alg_structure, target_type=types.G1, addlTypes=None): # stmts=None, infListNoExp=None):
    dg = DotGraph(alg_name)
    (typesS, depListNoExpS) = alg_structure
    output = typesS.get('output')
    if len(output.listNodesList) == 0:
        # in case of indirection in output := someVar and someVar := list{x,y,z}
        someVar = output.srcLine.replace(" ", "").split(":=")[1]
        output = typesS.get(someVar)

    if output:
        elems = output.listNodesList
        if len(elems) > 0: # not an empty list
            # start trace from the list of output elements
            for i in elems:
                # get the type of each one then traceback
                i_type = typesS.get(str(i))
                if not i_type:
                    if addlTypes:
                        i_type = addlTypes.get(str(i))
                    else:
                        pass #print("What to do in this case?")
                if not i_type and LIST_INDEX_SYMBOL in str(i):
                    i_star = i.split(LIST_INDEX_SYMBOL)[0]
                    i_type = typesS.get(i_star) or addlTypes.get(i_star)
                #assert i_type != None, "generateGraph => invalid type: " + str(i)
                if not i_type:
                    #print("Could not find var type for: " + str(i))
                    continue
                if i_type.type == target_type: # assuming symmetric
                    # check its dependencies
                    if i in depListNoExpS:
                        addAllEdgesIfSourceGroup(dg, i, depListNoExpS, typesS, target_type, addlTypes)

                if i_type.type == types.list: # just a data structure so can ignore
                    for j in depListNoExpS[i]:
                        # build edges with 'j' as the target
                        j_type = typesS.get(str(j))
                        if j_type and j_type.type != target_type:
                            #print("SKIPPING: ", j, " ... type => ", j_type.type)
                            continue
                        addAllEdgesIfSourceGroup(dg, j, depListNoExpS, typesS, target_type, addlTypes)

        else:
            #print("We have two layers of indirection.. :-> ", someVar)
            the_type = typesS.get(someVar)
            found_type = None
            if not the_type and addlTypes:
                the_type = addlTypes.get(someVar)
                if the_type:
                    #print(someVar, "=>", the_type.type)
                    found_type = the_type.type
            else:
                #print(someVar, "=>", the_type.type)
                found_type = the_type.type

            if found_type and is_related(found_type, target_type):
                some_var_list = depListNoExpS.get(someVar)
                assert some_var_list != None, "invalid definition for: " + someVar
                for i in some_var_list:
                    addAllEdgesIfSourceGroup(dg, i, depListNoExpS, typesS, target_type, addlTypes)

            #if someVar in depListNoExpS:
    #print("Dot graph: ", str(dg))

    return dg

def lookForMoreDeps(i, the_map, dep_map, the_target_list):
    if not the_map.get(i) or not dep_map.get(i):
        return False
    the_map[i] = the_map[i].union( set(dep_map[i]).intersection(the_target_list) )
    for k in dep_map[i]:
        if k in dep_map:
            the_map[i] = the_map[i].union( set(the_map[k]).intersection(the_target_list) )

    return True


"""
runAutoGroup is the main entry point into the AutoGroup tool. It takes as input the
sdl filename, a config file and the options which include security parameter,
a drop first requirement in case multiple solutions achieve the user's requirements,
and a destination path for the generated Asymmetric-based scheme and accompanying code.
"""
def runAutoGroup(sdlFile, config, options, sdlVerbose=False, assumptionData=None, reductionData=None):
    sdl.parseFile(sdlFile, sdlVerbose, ignoreCloudSourcing=True)
    global assignInfo
    # this contains a Variable Object for each statement in the SDL file
    assignInfo = sdl.getAssignInfo()
    # this consists of the type of the input scheme (e.g., symmetric)
    setting = sdl.assignInfo[sdl.NONE_FUNC_NAME][ALGEBRAIC_SETTING].getAssignNode().getRight().getAttribute()
    # name of the scheme
    sdl_name = sdl.assignInfo[sdl.NONE_FUNC_NAME][BV_NAME].getAssignNode().getRight().getAttribute()
    # the block of types in the SDL
    typesBlock = sdl.getFuncStmts( TYPES_HEADER )
    info = {'verbose':sdlVerbose, 'single_reduction': config.single_reduction, isAutoGroupKeyword: False}

    # we want to ignore user defined functions from our analysis
    # (unless certain variables that we care about are manipulated there)
    userCodeBlocks = list(set(list(assignInfo.keys())).difference(config.functionOrder + [TYPES_HEADER, NONE_FUNC_NAME]))
    options['userFuncList'] += userCodeBlocks
    print("name is", sdl_name)
    print("setting is", setting)
    
    lines = list(typesBlock[0].keys())
    lines.sort()
    typesBlockLines = [ i.rstrip() for i in sdl.getLinesOfCodeFromLineNos(lines) ]
    begin = ["BEGIN :: " + TYPES_HEADER]
    end = ["END :: " + TYPES_HEADER]

    # start constructing the preamble for the Asymmetric SDL output
    newLines0 = [ BV_NAME + " := " + sdl_name, SETTING + " := " + sdl.ASYMMETRIC_SETTING ] 
    newLines1 = begin + typesBlockLines + end
    # this fact is already verified by the parser
    # but if scheme claims symmetric
    # and really an asymmetric scheme then parser will
    # complain.
    assert setting == sdl.SYMMETRIC_SETTING, "No need to convert to asymmetric setting."    
    # determine user preference in terms of keygen or encrypt
    short = SHORT_DEFAULT # default option
    if hasattr(config, 'short'):
        if config.short in SHORT_OPTIONS:
            short = config.short
    print("reducing size of '%s'" % short) 

    varTypes = dict(sdl.getVarTypes().get(TYPES_HEADER))
    typesH = dict(varTypes)
    if not hasattr(config, 'schemeType'):
        sys.exit("'schemeType' option missing in specified config file.")
    pairingSearch = []
    # extract the statements, types, dependency list, influence list and exponents of influence list
    # for each algorithm in the SDL scheme
    if config.schemeType == PKENC:
        (stmtS, typesS, depListS, depListNoExpS, infListS, infListNoExpS) = sdl.getVarInfoFuncStmts( config.setupFuncName )
        (stmtK, typesK, depListK, depListNoExpK, infListK, infListNoExpK) = sdl.getVarInfoFuncStmts( config.keygenFuncName )
        (stmtE, typesE, depListE, depListNoExpE, infListE, infListNoExpE) = sdl.getVarInfoFuncStmts( config.encryptFuncName )    
        (stmtD, typesD, depListD, depListNoExpD, infListD, infListNoExpD) = sdl.getVarInfoFuncStmts( config.decryptFuncName )
        varTypes.update(typesS)
        varTypes.update(typesK)
        varTypes.update(typesE)
        varTypes.update(typesD)
        # TODO: expand search to encrypt and potentially setup
        pairingSearch += [stmtS, stmtE, stmtD] # aka start with decrypt.
        func_name_for_pairings = None
    # extract statements, etc ... for each algorithm in the SDL scheme.
    elif config.schemeType == PKSIG:
        if hasattr(config, 'setupFuncName'): 
            (stmtS, typesS, depListS, depListNoExpS, infListS, infListNoExpS) = sdl.getVarInfoFuncStmts( config.setupFuncName )
            varTypes.update(typesS)
            pairingSearch += [stmtS]
        (stmtK, typesK, depListK, depListNoExpK, infListK, infListNoExpK) = sdl.getVarInfoFuncStmts( config.keygenFuncName )
        (stmtSi, typesSi, depListSi, depListNoExpSi, infListSi, infListNoExpSi) = sdl.getVarInfoFuncStmts( config.signFuncName )    
        (stmtV, typesV, depListV, depListNoExpV, infListV, infListNoExpV) = sdl.getVarInfoFuncStmts( config.verifyFuncName )
        varTypes.update(typesK)
        varTypes.update(typesSi)
        varTypes.update(typesV)
        pairingSearch += [stmtV] # aka start with verify
        func_name_for_pairings = config.verifyFuncName
    else:
        sys.exit("'schemeType' options are 'PKENC' or 'PKSIG'")
            
    info[curveID] = options['secparam']
    info[dropFirstKeyword] = options[dropFirstKeyword]
    gen = Generators(info)
    # JAA: commented out for benchmarking    
    #print("List of generators for scheme")
    # retrieve the generators selected by the scheme
    # typically found in the setup routine in most cases.
    if hasattr(config, "extraSetupFuncName"):
        (stmtSe, typesSe, depListSe, depListNoExpSe, infListSe, infListNoExpSe) = sdl.getVarInfoFuncStmts( config.extraSetupFuncName )
        gen.extractGens(stmtSe, typesSe)
        #extractGeneratorList(stmtSe, typesSe, generators)
        varTypes.update(typesSe)
    # extract the generators from the setup and keygen routine for later use
    if hasattr(config, 'setupFuncName'):
        gen.extractGens(stmtS, typesS)
    if hasattr(config, 'keygenFuncName'):
        gen.extractGens(stmtK, typesK)
    else:
        sys.exit("Assumption failed: setup not defined for this function. Where to extract generators?")
    generators = gen.getGens()
    # JAA: commented out for benchmarking    
    #print("Generators extracted: ", generators)


    ##### check generators for hashes #####
    hashgens = []

    if hasattr(config, "extraSetupFuncName"):
        for i in stmtSe.keys():
            if(not len(stmtSe[i].getHashArgsInAssignNode()) == 0):

                t = stmtSe[i].getAssignVar()

                if typesSe.get(t) == None:
                    typ = stmtSe[i].getAssignNode().right.left.attr
                else:
                    typ = typesSe[t].getType()

                if typ == types.G1:
                    hashgens.append(t)

                    print("\nWARNING!!!!  Hash in extra Setup.  If AutoGroup+ fails later on, this could be the cause!")
                    print("line ", i, " : ", t, "\n")


    if hasattr(config, 'setupFuncName'):
        for i in stmtS.keys():
            if(not len(stmtS[i].getHashArgsInAssignNode()) == 0):

                t = stmtS[i].getAssignVar()

                if typesS.get(t) == None:
                    typ = stmtS[i].getAssignNode().right.left.attr
                else:
                    typ = typesS[t].getType()

                if typ == types.G1:
                    hashgens.append(t)

                    print("\nWARNING!!!!  Hash in Setup.  If AutoGroup+ fails later on, this could be the cause!")
                    print("line ", i, " : ", t, "\n")


    if hasattr(config, 'keygenFuncName'):
        for i in stmtK.keys():
            if(not len(stmtK[i].getHashArgsInAssignNode()) == 0):

                t = stmtK[i].getAssignVar()

                if typesK.get(t) == None:
                    typ = stmtK[i].getAssignNode().right.left.attr
                else:
                    typ = typesK[t].getType()

                if typ == types.G1:
                    t = stmtK[i].getAssignVar()
                    hashgens.append(t)

                    print("\nWARNING!!!!  Hash in KeyGen.  If AutoGroup+ fails later on, this could be the cause!")
                    print("line ", i, " : ", t, "\n")

    #######################################


    # need a Visitor class to build these variables  
    # TODO: expand to other parts of algorithm including setup, keygen, encrypt
    # Visits each pairing computation in the SDL and
    # extracts the inputs. This is the beginning of the
    # analysis of these variables as the SDL is converted into
    # an asymmetric scheme.
    hashVarList = []
    pair_vars_G1_lhs = []
    pair_vars_G1_rhs = []
    pair_list = []
    for (assumpname, assumprecord) in assumptionData.items():
        the_lhs = assumprecord.get('G1_lhs')[0]
        the_rhs = assumprecord.get('G1_rhs')[0]
        for i,j in zip(the_lhs, the_rhs):
            if (i == j): # skip e(g,g)
                continue
            if (i, j) not in pair_list and (j, i) not in pair_list:
                # add (i,j) combo to pair_list
                pair_list.append( (i, j) )

    # THIS DOESN'T SEEM TO BE NECESSARY
    # for (reducname, reducrecord) in reductionData.items():
    #     the_lhs = reducrecord.get('G1_lhs')[0]
    #     the_rhs = reducrecord.get('G1_rhs')[0]
    #     for i,j in zip(the_lhs, the_rhs):
    #         if (i == j): # skip e(g, g)
    #             continue
    #         if (i, j) not in pair_list and (j, i) not in pair_list:
    #             # add (i,j) combo to pair_list
    #             pair_list.append( (i, j) )

    gpv = GetPairingVariables(pair_vars_G1_lhs, pair_vars_G1_rhs)
    for eachStmt in pairingSearch: # loop through each pairing statement
        lines = eachStmt.keys() # for each line, do the following
        for i in lines:
            if type(eachStmt[i]) == sdl.VarInfo: # make sure we have the Var Object
                # assert that the statement contains a pairing computation
                if HasPairings(eachStmt[i].getAssignNode()):
                    path_applied = []
                    # split pairings if necessary so that we don't influence
                    # the solve in anyway. We can later recombine these during
                    # post processing of the SDL
                    eachStmt[i].assignNode = SplitPairings(eachStmt[i].getAssignNode(), path_applied)
                    # JAA: commented out for benchmarking
                    #if len(path_applied) > 0: print("Split Pairings: ", eachStmt[i].getAssignNode())
                    if info['verbose']: print("Each: ", eachStmt[i].getAssignNode())
                    # record where we found the pairing (help with constructing dep graph)
                    if func_name_for_pairings:
                        func_name = func_name_for_pairings
                    else:
                        func_name = eachStmt[i].funcName
                    gpv.setFunctionName(func_name)
                    sdl.ASTVisitor( gpv ).preorder(eachStmt[i].getAssignNode())
                elif eachStmt[i].getHashArgsInAssignNode(): 
                    # in case there's a hashed value...build up list and check later to see if it appears
                    # in pairing variable list
                    hashVarList.append(str(eachStmt[i].getAssignVar()))
                else:
                    continue # not interested

    # record list of hashes for later
    info['hashVarList'] = hashVarList
    the_lhs = pair_vars_G1_lhs
    the_rhs = pair_vars_G1_rhs
    for i,j in zip(the_lhs, the_rhs):
        if (i == j): # skip e(g, g)
            continue
        if (i, j) not in pair_list and (j, i) not in pair_list:
            # add (i,j) combo to pair_list
            pair_list.append( (i, j) )

    # reset
    pair_vars_G1_lhs = []
    pair_vars_G1_rhs = []
    for the_pairs in pair_list:
        (i, j) = the_pairs
        pair_vars_G1_lhs.append(i)
        pair_vars_G1_rhs.append(j)

    # expand graphing to PKSIGs
    if options.get('graphit') and config.schemeType == PKENC:
        pair_graph = gpv.getDepGraph()
        print("Pairing info: ", pair_graph)
        dg_setup = generateGraph(config.setupFuncName, (typesS, depListNoExpS))
        dg_setup.update(pair_graph)
        dg_keygen = generateGraph(config.keygenFuncName, (typesK, depListNoExpK), types.G1, varTypes)
        dg_keygen.update(pair_graph)
        dg_encrypt = generateGraph(config.encryptFuncName, (typesE, depListNoExpE), types.G1, varTypes)
        dg_encrypt.update(pair_graph)
        dg_decrypt = generateGraph(config.decryptFuncName, (typesD, depListNoExpD), types.G1, varTypes)
        dg_decrypt.update(pair_graph)
        dg_scheme = DotGraph(sdl_name)
        if info.get('verbose'):
            print("<=== Setup Graph ===>")
            print(dg_setup)
            print("<=== Setup Graph ===>")

            print("<=== Keygen Graph ===>")
            print(dg_keygen)
            print("<=== Keygen Graph ===>")

            print("<=== Encrypt Graph ===>")
            print(dg_encrypt)
            print("<=== Encrypt Graph ===>")

            print("<=== Decrypt Graph ===>")
            print(dg_decrypt)
            print("<=== Decrypt Graph ===>")

        # merge the different graphs into one big one
        dg_scheme += dg_setup + dg_keygen + dg_encrypt + dg_decrypt
        if info.get('verbose'):
            print("<=== Scheme Graph ===>")
            print(dg_scheme)
            print("<=== Scheme Graph ===>")
        merged_graph = DotGraph("merged")
        print("")
        merged_graph += dg_scheme

        if config.single_reduction:
            for (assumpname, assumprecord) in assumptionData.items():
                dg_assumption = assumprecord['assumptionGraph']
                # print("<=== Assumption Graph ===>")
                # print(dg_assumption)
                # print("<=== Assumption Graph ===>")
                # merge
                merged_graph += dg_assumption

            for (reducname, reducrecord) in reductionData.items():
                dg_reduction = reducrecord['reductionGraph']
                # print("<=== Reduction Graph ===>")
                # print(dg_reduction)
                # print("<=== Reduction Graph ===>")
                # merge
                merged_graph += dg_reduction

            merged_graph.setPairingIds(gpv.getPairingIds())
            info[mergedGraphKeyword] = merged_graph
            # print("<=== Merged Graph ===>")
            # print(merged_graph)
            # print("<=== Merged Graph ===>")

        else:
            # multiple reduction/assumption case
            if not hasattr(config, "assumption_reduction_map"):
                sys.exit("configAutoGroup: need to set 'assumption_reduction_map' in config.")
            else:
                assumption_reduction_data_map = sorted(config.assumption_reduction_map.items())

            merged_graph.setPairingIds(gpv.getPairingIds())

            the_merged_graphs = { }
            info['merged_graph_map'] = {}

            for index in range(len(assumption_reduction_data_map)):
                (reducname, assumpname) = assumption_reduction_data_map[index]
                new_merged_graph = DotGraph("merged_" + assumpname + "_" + str(index))
                new_merged_graph += merged_graph
                dg_assumption = assumptionData.get(assumpname)['assumptionGraph']
                dg_reduction  = reductionData.get(reducname)['reductionGraph']

                new_merged_graph += dg_assumption + dg_reduction
                if info.get('verbose'):
                    print("<=== Merged Graph %s ===>" % index)
                    print(new_merged_graph)
                    print("<=== Merged Graph %s ===>" % index)
                the_merged_graphs[ index ] = new_merged_graph
                info['merged_graph_map'][index] = (reducname, assumpname)

            merged_graph = the_merged_graphs
            info[mergedGraphKeyword] = merged_graph

    elif options.get('graphit') and config.schemeType == PKSIG:
        pair_graph = gpv.getDepGraph()
        #print("Pairing info: ", pair_graph)
        if hasattr(config, 'setupFuncName'):
            dg_setup = generateGraph(config.setupFuncName, (typesS, depListNoExpS))
            dg_setup.update(pair_graph)
            has_setup = True
        else:
            has_setup = False

        new_depListNoExpK = simplifyDepMap(stmtK, typesK, infListNoExpK, depListNoExpK)
        dg_keygen = generateGraph(config.keygenFuncName, (typesK, new_depListNoExpK), types.G1, varTypes)
        dg_keygen.update(pair_graph)

        new_depListNoExpSi = simplifyDepMap(stmtSi, typesSi, infListNoExpSi, depListNoExpSi)
        dg_sign = generateGraph(config.signFuncName, (typesSi, new_depListNoExpSi), types.G1, varTypes)
        dg_sign.update(pair_graph)
        dg_verify = generateGraph(config.verifyFuncName, (typesV, depListNoExpV), types.G1, varTypes)
        dg_verify.update(pair_graph)
        dg_scheme = DotGraph(sdl_name)
        #if info.get('verbose'):
        if has_setup:
            if info.get('verbose'):
                print("<=== Setup Graph ===>")
                print(dg_setup)
                print("<=== Setup Graph ===>")
            dg_scheme += dg_setup

        if info.get('verbose'):
            print("<=== Keygen Graph ===>")
            print(dg_keygen)
            print("<=== Keygen Graph ===>")

            print("<=== Sign Graph ===>")
            print(dg_sign)
            print("<=== Sign Graph ===>")

            print("<=== Verify Graph ===>")
            print(dg_verify)
            print("<=== Verify Graph ===>")

        # merge the different graphs into one big one
        dg_scheme += dg_keygen + dg_sign + dg_verify
        if info.get('verbose'):
            print("<=== Scheme Graph ===>")
            print(dg_scheme)
            print("<=== Scheme Graph ===>")
        merged_graph = DotGraph("merged")
        print("")
        merged_graph += dg_scheme

        if config.single_reduction:
            for (assumpname, assumprecord) in assumptionData.items():
                dg_assumption = assumprecord['assumptionGraph']
                if info.get('verbose'):
                    print("<=== Assumption Graph ===>")
                    print(dg_assumption)
                    print("<=== Assumption Graph ===>")
                # merge
                merged_graph += dg_assumption

            for (reducname, reducrecord) in reductionData.items():
                dg_reduction = reducrecord['reductionGraph']
                if info.get('verbose'):
                    print("<=== Reduction Graph ===>")
                    print(dg_reduction)
                    print("<=== Reduction Graph ===>")
                # merge
                merged_graph += dg_reduction

            if info.get('verbose'):
                print("<=== Merged Graph ===>")
                print(merged_graph)
                print("<=== Merged Graph ===>")

            merged_graph.setPairingIds(gpv.getPairingIds())
            info[mergedGraphKeyword] = merged_graph
        else:
            # multiple reduction/assumption case
            if not hasattr(config, "assumption_reduction_map"):
                sys.exit("configAutoGroup: need to set 'assumption_reduction_map' in config.")
            else:
                assumption_reduction_data_map = sorted(config.assumption_reduction_map.items())

            merged_graph.setPairingIds(gpv.getPairingIds())

            the_merged_graphs = { }
            info['merged_graph_map'] = {}

            for index in range(len(assumption_reduction_data_map)):
                (reducname, assumpname) = assumption_reduction_data_map[index]
                print("Processing '%s' and '%s'" % (reducname, assumpname))
                new_merged_graph = DotGraph("merged_" + assumpname + "_" + str(index))
                new_merged_graph += merged_graph
                dg_assumption = assumptionData.get(assumpname)['assumptionGraph']
                dg_reduction  = reductionData.get(reducname)['reductionGraph']

                new_merged_graph += dg_assumption + dg_reduction
                if info.get('verbose'):
                    print("<=== Merged Graph %s ===>" % index)
                    print(new_merged_graph)
                    print("<=== Merged Graph %s ===>" % index)
                the_merged_graphs[ index ] = new_merged_graph
                info['merged_graph_map'][index] = (reducname, assumpname)

            info[mergedGraphKeyword] = the_merged_graphs

    # constraint list narrows the solutions that
    # we care about
    constraintList = []
    
    # for example, include any hashed values that show up in a pairing by default
    for i in hashVarList:
        if i in pair_vars_G1_lhs or i in pair_vars_G1_rhs:
            constraintList.append(i)
    # JAA: commented out for benchmarking
    if info.get('verbose'):
        print("pair vars LHS:", pair_vars_G1_lhs)
        print("pair vars RHS:", pair_vars_G1_rhs)
        print("list of gens :", generators)
        print("constraintList: ", constraintList)
    # for each pairing variable, we construct a dependency graph all the way back to
    # the generators used. The input of assignTraceback consists of the list of SDL statements,
    # generators from setup, type info, and the pairing variables.
    # We do this analysis for both sides
    info[ 'G1_lhs' ] = (pair_vars_G1_lhs, assignTraceback(assignInfo, generators, varTypes, pair_vars_G1_lhs, constraintList))
    info[ 'G1_rhs' ] = (pair_vars_G1_rhs, assignTraceback(assignInfo, generators, varTypes, pair_vars_G1_rhs, constraintList))

    assumpDepstmp = {}
    for (assumpname, assumprecord) in assumptionData.items():
        #assumpDeps = dict(list(assumpDeps.items()) + list(assumprecord['newDeps'].items()))
        assumpDepstmp = dict(list(assumpDepstmp.items()) + list(assumprecord['newDeps'].items()) + [(k, list(assumpDepstmp[k]) + list(assumprecord['newDeps'][k])) for k in set(assumprecord['newDeps']) & set(assumpDepstmp)])

    assumpDeps = {}
    for (key,val) in assumpDepstmp.items():
        assumpDeps[key] = set(val)

    reducDepstmp = {}
    for (reducname, reducrecord) in reductionData.items():
        reducDepstmp = dict(list(reducDepstmp.items()) + list(reducrecord['newDeps'].items()) + [(k, list(reducDepstmp[k]) + list(reducrecord['newDeps'][k])) for k in set(reducrecord['newDeps']) & set(reducDepstmp)])
        #reducDeps = dict(list(reducDeps.items()) + list(reducrecord['newDeps'].items()))

    reducDeps = {}
    for (key,val) in reducDepstmp.items():
        reducDeps[key] = set(val)

    #additionalDeps = dict(list(assumptionData['newDeps'].items()) + list(reductionData['newDeps'].items()))
    additionalNewDeps = dict(list(assumpDeps.items()) + list(reducDeps.items()))

    # JAA: use this map in split test code
    info['merged_deps'] = additionalNewDeps

    #TODO: Do we need to include this?  We did include it in the single assumption/reduction case.
    #TODO: check where this merge should be located...
    for (key,val) in info['G1_lhs'][1].items():
        if key in additionalNewDeps:
            info['G1_lhs'][1][key] = set(list(info['G1_lhs'][1][key]) + list(additionalNewDeps[key]))

    for (key,val) in info['G1_rhs'][1].items():
        if key in additionalNewDeps:
            info['G1_rhs'][1][key] = set(list(info['G1_rhs'][1][key]) + list(additionalNewDeps[key]))

    #TODO: need to update this for the multi-case
    # if we want to minimize the assumption
    if short == SHORT_ASSUMPTION:
        assumpDepList = []
        assump_map = {}

        for (assumpname, assumprecord) in assumptionData.items():
            # need to build a map of pairing variables to assumptions
            assumpKey = assumprecord.get('prunedMap') # is this the right data structure?
            for i,j in assumpKey.items():
                assumpDepList += list(j)
            assumpDepList = list(set(assumpDepList))
            assumpDepList += list(assumpKey.keys())
            assumpDepList.sort()
            lhs_orig_vars, lhs_var_map = info['G1_lhs']
            rhs_orig_vars, rhs_var_map = info['G1_rhs']
            for i in lhs_orig_vars + rhs_orig_vars:
                assump_map[i] = set()
            # first do a backwards analysis from pairing variables and up
            for i in assumpDepList: # lhs_orig_vars:
                for j in lhs_orig_vars:
                    for k in lhs_var_map[j]:
                        if k in additionalNewDeps and i in additionalNewDeps[k]:
                            #print("Found: ", i, "=>", j, ":", additionalNewDeps[k])
                            assump_map[j] = assump_map[j].union([i])

                for j in rhs_orig_vars:
                    for k in rhs_var_map[j]:
                        if k in additionalNewDeps and i in additionalNewDeps[k]:
                            #print("Found: ", i, "=>", j, ":", additionalNewDeps[k])
                            assump_map[j] = assump_map[j].union([i])

        # do a top down tracing to
        for i in assumpDepList:
            searchForChildren(i, i, assump_map, info, seen_before=[])
        # might want to check for any deps in additional deps?
        #print("Assumption Map: ", assump_map)
        info['assump_map'] = assump_map
        info['assump_list'] = assumpDepList


    ### REFACTORED Public-Key minimization for Encryption
    if short == SHORT_PUBKEYS and config.schemeType in [PKENC, PKSIG]:
        # special case for PK encryption and signatures
        pk_var_obj = varTypes[config.keygenPubVar]
        if Type(pk_var_obj) == types.list:
            pk_list = pk_var_obj.getListNodesList()
        else:
            pk_list = None

        lhs_orig_vars, lhs_var_map = info['G1_lhs']
        rhs_orig_vars, rhs_var_map = info['G1_rhs']

        # build up the map for the PK list
        pk_map = {}
        if info['verbose']:
            print("pk list: ", pk_list)
            print("<=========================>")
        for i in lhs_orig_vars:
            if i not in pk_list:
                pk_map[i] = set(lhs_var_map[i]).intersection(pk_list)
                if i in additionalNewDeps:
                    pk_map[i] = pk_map[i].union( set(additionalNewDeps[i]).intersection(pk_list) )
                    for k in additionalNewDeps[i]:
                        if k in additionalNewDeps:
                            pk_map[i] = pk_map[i].union( set(additionalNewDeps[k]).intersection(pk_list) )
                else:
                    lookForMoreDeps(i, pk_map, lhs_var_map, pk_list)
            else:
                pk_map[i] = set({i})
        for i in rhs_orig_vars:
            if i not in pk_list:
                pk_map[i] = set(rhs_var_map[i]).intersection(pk_list)
                if i in additionalNewDeps:
                    pk_map[i] = pk_map[i].union( set(additionalNewDeps[i]).intersection(pk_list) )
                    for k in additionalNewDeps[i]:
                        if k in additionalNewDeps:
                            pk_map[i] = pk_map[i].union( set(additionalNewDeps[k]).intersection(pk_list) )
                else:
                    lookForMoreDeps(i, pk_map, rhs_var_map, pk_list)
            else:
                pk_map[i] = set({i})


        if info['verbose']:
            print("Final PK map: ", pk_map)
        info['pk_map']  = pk_map
        info['pk_list'] = pk_list

#####################

    # JAA: commented out for benchmarking
    #print("info => G1 lhs : ", info['G1_lhs'])
    #print("info => G1 rhs : ", info['G1_rhs'])   
    #print("<===== Determine Asymmetric Generators =====>")
    # construct the asymmetric generators for the new SDL
    (generatorMapG1, generatorMapG2) = gen.setupNewGens() #TODO: do we need to setup any generators from the assumption/reduction??
    # generate the relevant SDL lines
    generatorLines = gen.getGenLines()
    # JAA: commented out for benchmarking    
    #print("Generators in G1: ", generatorMapG1)
    #print("Generators in G2: ", generatorMapG2)
    #print("Generator Lines: ", generatorLines)
    #print("<===== Determine Asymmetric Generators =====>\n")
    
    #print("<===== Generate XOR clauses =====>")
    # let the user's preference for fixing the keys or ciphertext guide this portion of the algorithm.
    # info[ 'G1' ] : represents (varKeyList, depVarMap).
    # sanity check that we have an equivalent number of inputs to pairings
    assert len(pair_vars_G1_lhs) == len(pair_vars_G1_rhs), "Uneven number of pairings. Please inspect your SDL file."
    # now we can construct the logical formula input to the SMT solver
    #TODO: add any pairings from assumption/reduction
    varsLen = len(pair_vars_G1_lhs)
    xorList = []
    for i in range(varsLen):
        xor = BinaryNode(ops.XOR)
        xor.left = BinaryNode(pair_vars_G1_lhs[i])
        xor.right = BinaryNode(pair_vars_G1_rhs[i])
        xorList.append(xor)
    
    ANDs = [ BinaryNode(ops.AND) for i in range(len(xorList)-1) ]
    for i in range(len(ANDs)):
        ANDs[i].left = BinaryNode.copy(xorList[i])
        if i < len(ANDs)-1: ANDs[i].right = ANDs[i+1]
        else: ANDs[i].right = BinaryNode.copy(xorList[i+1])
    # JAA: commented out for benchmarking        
    #print("XOR clause: ", ANDs[0])
    txor = transformXOR(None) # accepts dictionary of fixed values
    sdl.ASTVisitor(txor).preorder(ANDs[0])
    #print("<===== Generate XOR clauses =====>")

#TODO: Do we need this?  Or is it the same as above?
    for (key,val) in info['G1_lhs'][1].items():
        if key in additionalNewDeps:
            info['G1_lhs'][1][key] = set(list(info['G1_lhs'][1][key]) + list(additionalNewDeps[key]))

    for (key,val) in info['G1_rhs'][1].items():
        if key in additionalNewDeps:
            info['G1_rhs'][1][key] = set(list(info['G1_rhs'][1][key]) + list(additionalNewDeps[key]))

    #merge in generators from assumption
    for (assumpname, assumprec) in assumptionData.items():
        assumpGens = assumprec['gen'].getGens()
        generators = generators + assumpGens
    generators = set(generators)

    #constraints = "[]"
    # given the above formula and the constraint list and options we can
    # run the solver to produce an initial set of solutions
    info['reductionData'] = reductionData
    info['assumptionData'] = assumptionData
    fileSuffix, resultDict = searchForSolution(info, short, constraintList, txor, varTypes, config, generators)
    # map of Z3 to SDL pairing variables (so we can map the solution to SDL)
    xorVarMap = txor.getVarMap()

#    if short != SHORT_FORALL:
#        res, resMap = NaiveEvaluation(resultDict, short)
#        print("Group Mapping: ", res)
#        # determine whether to make True = G1 and False = G2. 
#        # It depends on which counts more since they're interchangeable...
#        groupInfo = DeriveGeneralSolution(res, resMap, xorVarMap, info)
#    else:

    # narrow the specific solution that user asked for
    groupInfo = DeriveSpecificSolution(resultDict, xorVarMap, info)
    newAssignments = groupInfo['newSol']
    symDataTypePK  = {}
    asymDataTypePK = {}
    # we include some code to estimate size of SK/PK and CTs/Sigs
    # if the 'computeSize' option is set (e.g., --estimate option)
    #TODO: update??
    if config.schemeType == PKENC and options['computeSize']:   
        symDataTypeSK = getAssignmentForName(config.keygenSecVar, varTypes, True)
        symDataTypeCT = getAssignmentForName(config.ciphertextVar, varTypes, True)
        asymDataTypeSK = {}
        asymDataTypeCT = {}
        newSol = groupInfo['newSol']
        for i in symDataTypeSK:
            if i in newSol.keys():
               asymDataTypeSK[i] = newSol[i]
            else:
               asymDataTypeSK[i] = symDataTypeSK[i]
               
        for i in symDataTypeCT:
            if i in newSol.keys():
               asymDataTypeCT[i] = newSol[i]
            else:
               asymDataTypeCT[i] = symDataTypeCT[i]
        print("<====================>")
        print("SK => ", list(symDataTypeSK.keys()))
        print("estimated  sym:  ", estimateSize(symDataTypeSK, symmetric_curves['SS1536']))        
        print("estimated asym: ", estimateSize(asymDataTypeSK, asymmetric_curves['BN256']))
        print("CT => ", list(symDataTypeCT.keys()))               
        print("estimated  sym: ", estimateSize(symDataTypeCT, symmetric_curves['SS1536']))            
        print("estimated asym: ", estimateSize(asymDataTypeCT, asymmetric_curves['BN256']))
        print("<====================>")
    elif config.schemeType == PKSIG and options['computeSize']:
        symDataTypePK = getAssignmentForName(config.keygenPubVar, varTypes, True)
        symDataTypeSIG = getAssignmentForName(config.signatureVar, varTypes, True)
        #asymDataTypePK = {}
        asymDataTypeSIG = {}
        newSol = groupInfo['newSol']
        for i in symDataTypePK:
            if i in newSol.keys():
               asymDataTypePK[i] = newSol[i]
            else:
               asymDataTypePK[i] = symDataTypePK[i] # keep old type
               
        for i in symDataTypeSIG:
            if i in newSol.keys():
               asymDataTypeSIG[i] = newSol[i]
            else:
               asymDataTypeSIG[i] = symDataTypeSIG[i]
        print("<====================>")
#        print("PK => ", list(symDataTypePK.keys()))
#        print("estimated  sym:  ", estimateSize(symDataTypePK, symmetric_curves['SS1536']))        
#        print("estimated asym: ", estimateSize(asymDataTypePK, asymmetric_curves['BN256']))
        print("SIG => ", list(symDataTypeSIG.keys()))               
        print("estimated  sym: ", estimateSize(symDataTypeSIG, symmetric_curves['SS1536']))            
        print("estimated asym: ", estimateSize(asymDataTypeSIG, asymmetric_curves['BN256']))
        print("<====================>")

    # we still care about group elements that are not used in pairings
    # the rule is that we always assign these elements to G1 (so as long as
    # so as long as it doesn't affect any pairing computations)
    #if info.get('notInAPairing') != None and len(info['notInAPairing']) > 0:
    #    groupInfo['G1'] = groupInfo['G1'].union( info['notInAPairing'] )
    #    print("Update: new G1 deps=>", groupInfo['G1'])
    if info.get('notInAPairing') != None and len(info['notInAPairing']) > 0:
        #groupInfo['G1'] = groupInfo['G1'].union( info['notInAPairing'] )
        for i in info['notInAPairing']:
            if not(i in groupInfo['G2']) and not(i in groupInfo['both']):
                groupInfo['G1'] = set((list(groupInfo['G1']) + [i]))
        #print("Update: new G1 deps=>", groupInfo['G1'])   

    # put all the info together so that we can generate the new Asym SDL
    groupInfo['generators'] = generators 
    groupInfo['generatorMapG1'] = generatorMapG1
    groupInfo['generatorMapG2'] = generatorMapG2
    groupInfo['baseGeneratorG1'] = info['baseGeneratorG1'] # usually 'g'
    groupInfo['baseGeneratorG2'] = info['baseGeneratorG2']
    groupInfo['newTypes'] = {}
    groupInfo['varTypes'] = {}
    groupInfo['varTypes'].update(varTypes)
    groupInfo['usedVars'] = set()
    groupInfo['verbose'] = info['verbose']
    transFunc = {}
    transFuncGen = {}

    # determine the structure of the input SDL and stick as close as
    # possible to that in the output SDL
    if hasattr(config, "extraSetupFuncName"):
        transFuncGen[ config.extraSetupFuncName ] = stmtSe
    if hasattr(config, 'setupFuncName'):    
        transFuncGen[ config.setupFuncName ] = stmtS
    elif hasattr(config, 'keygenFuncName'):
        transFuncGen[ config.keygenFuncName ] = stmtK

    if config.schemeType == PKENC:
        transFunc[ config.keygenFuncName ]  = stmtK
        transFunc[ config.encryptFuncName ] = stmtE
        transFunc[ config.decryptFuncName ] = stmtD
    elif config.schemeType == PKSIG:
        if hasattr(config, 'setupFuncName') or hasattr(config, "extraSetupFuncName"):
            transFunc[ config.keygenFuncName ] = stmtK
        transFunc[ config.signFuncName ] = stmtSi
        transFunc[ config.verifyFuncName ] = stmtV
    
    if options['computeSize']:
        options['symPK']  = symDataTypePK
        options['asymPK'] = asymDataTypePK

    # with the functions and SDL statements defined, can simply run AsymSDL to construct the new SDL
    newSDL = AsymSDL(options, assignInfo, groupInfo, typesH, generatorLines, transFunc, transFuncGen)
    newLinesT, newLinesSe, newLinesS, newLinesK, newLines2, newLines3, userFuncLines = newSDL.constructSDL(config)

    # debug output of the SDL file
    print_sdl(info['verbose'], newLinesS, newLinesK, newLines2, newLines3)
    # output the new SDL file with right suffix (which indicates options that were set)
    outputFile = sdl_name + "_asym_" + fileSuffix + sdlSuffix
    writeConfig(options['path'] + outputFile, newLines0, newLinesT, newLinesSe, newLinesS, newLinesK, newLines2, newLines3, userFuncLines)

    # TODO: make this a command line option (build split graph for scheme output file)
    ## new_pair_graph = dict(pair_graph)
    # need to update variable names wherever necessary
    ## buildSplitGraphForScheme(options['path'] + outputFile, sdl_name, config, sdlVerbose, new_pair_graph, groupInfo)

###########################
    if(len(reductionData) == 1):
        outputFile_assump_array = []
        counter = 0

        #merge reductionData['deps']??
        reducDeps0 = {}
        reducDeps1 = {}
        for (reducname, reducrecord) in reductionData.items():
            tmp0 = reducrecord['deps'][0]
            tmp1 = reducrecord['deps'][1]

            reducDeps0 = dict(list(reducDeps0.items()) + list(tmp0.items()))
            reducDeps1 = dict(list(reducDeps1.items()) + list(tmp1.items()))
        reducDeps = (reducDeps0, reducDeps1)

        for (assumpname, assumprecord) in assumptionData.items():
            funcOrder = [assumprecord['config'].assumpSetupFuncName, assumprecord['config'].assumpFuncName]
            setattr(assumprecord['config'], functionOrder, funcOrder)

            sdl.parseFile(assumprecord['assumptionFile'], assumprecord['info']['verbose'], ignoreCloudSourcing=True)
            (generatorMapG1, generatorMapG2) = assumprecord['gen'].setupNewGens() #TODO: do we need to setup any generators from the assumption/reduction??
            # generate the relevant SDL lines
            generatorLines = assumprecord['gen'].getGenLines()

            # we still care about group elements that are not used in pairings
            # the rule is that we always assign these elements to G1 (so as long as
            # so as long as it doesn't affect any pairing computations)
            #if assumprecord['info'].get('notInAPairing') != None and len(assumprecord['info']['notInAPairing']) > 0:
            #    groupInfo['G1'] = groupInfo['G1'].union( assumprecord['info']['notInAPairing'] )
            #    print("Update: new G1 deps=>", groupInfo['G1'])
            if assumprecord['info'].get('notInAPairing') != None and len(assumprecord['info']['notInAPairing']) > 0:
                #groupInfo['G1'] = groupInfo['G1'].union( info['notInAPairing'] )
                for i in assumprecord['notInAPairing']:
                    if not(i in groupInfo['G2']) and not(i in groupInfo['both']):
                        #print(i)
                        groupInfo['G1'] = set((list(groupInfo['G1']) + [i]))
                #print("Update: new G1 deps=>", groupInfo['G1']) 

            # put all the info together so that we can generate the new Asym SDL
            groupInfo['generators'] = generators 
            groupInfo['generatorMapG1'] = generatorMapG1
            groupInfo['generatorMapG2'] = generatorMapG2
            groupInfo['baseGeneratorG1'] = assumprecord['info']['baseGeneratorG1'] # usually 'g'
            groupInfo['baseGeneratorG2'] = assumprecord['info']['baseGeneratorG2']
            groupInfo['newTypes'] = {}
            groupInfo['varTypes'] = {}
            groupInfo['varTypes'].update(assumprecord['varTypes'])
            groupInfo['usedVars'] = set()
            groupInfo['verbose'] = info['verbose']
            transFunc = {}
            transFuncGen = {}

            # determine the structure of the input SDL and stick as close as
            # possible to that in the output SDL
            if hasattr(assumprecord['config'], 'assumpSetupFuncName'):    
                transFuncGen[ assumprecord['config'].assumpSetupFuncName ] = assumprecord['stmtS']
            if hasattr(assumprecord['config'], 'assumpFuncName'):
                transFunc[ assumprecord['config'].assumpFuncName ] = assumprecord['stmtA']

            if options['computeSize']:
                options['symPK']  = symDataTypePK
                options['asymPK'] = asymDataTypePK

            # with the functions and SDL statements defined, can simply run AsymSDL to construct the new SDL
            newSDL_assump = AsymAssumpSDL(assumprecord['options'], assumprecord['assignInfo'], groupInfo, assumprecord['typesH'], generatorLines, transFunc, transFuncGen, reducDeps, assumprecord['varmap'])#TODO: change this!!! we can't guarantee the order of the dictionary....though isn't it a list??
            newLinesT, newLinesSe, newLinesS, newLinesA, userFuncLines = newSDL_assump.constructSDL(assumprecord['config'])

            # debug output of the SDL file
            print_sdl(assumprecord['info']['verbose'], newLinesS, newLinesA)
            # output the new SDL file with right suffix (which indicates options that were set)
            outputFile_assump = "assumption_" + assumprecord['sdl_name'] + "_asym_" + fileSuffix + sdlSuffix
            outputFile_assump_array.append(outputFile_assump)
            writeConfig(options['path'] + outputFile_assump, assumprecord['newLines0'], newLinesT, newLinesSe, newLinesS, newLinesA, userFuncLines)

            #TODO: figure out why this line is giving errors for sig schemes
            #buildSplitGraphForAssumption(options['path'] + outputFile_assump, assumprecord['sdl_name'], assumprecord['config'], sdlVerbose)

            counter += 1
    else: #multiple reduction/assumption code
        for (reducname, reducrecord) in reductionData.items():
            outputFile_assump_array = []
            counter = 0

            reducDeps = (reducrecord['deps'][0], reducrecord['deps'][1])

            if hasattr(config, "assumption_reduction_map"):
                assumpname = config.assumption_reduction_map[reducname]
            else:
                sys.exit("configAutoGroup: need to set 'assumption_reduction_map' in config.")

            assumprecord = assumptionData[assumpname]
           
            funcOrder = [assumprecord['config'].assumpSetupFuncName, assumprecord['config'].assumpFuncName]
            setattr(assumprecord['config'], functionOrder, funcOrder)

            sdl.parseFile(assumprecord['assumptionFile'], assumprecord['info']['verbose'], ignoreCloudSourcing=True)
            (generatorMapG1, generatorMapG2) = assumprecord['gen'].setupNewGens() #TODO: do we need to setup any generators from the assumption/reduction??
            # generate the relevant SDL lines
            generatorLines = assumprecord['gen'].getGenLines()

            # we still care about group elements that are not used in pairings
            # the rule is that we always assign these elements to G1 (so as long as
            # so as long as it doesn't affect any pairing computations)
            #print(groupInfo)
            #if assumprecord['info'].get('notInAPairing') != None and len(assumprecord['info']['notInAPairing']) > 0:
            #    groupInfo['G1'] = groupInfo['G1'].union( assumprecord['info']['notInAPairing'] )
            #    print("Update: new G1 deps=>", groupInfo['G1'])
            if assumprecord['info'].get('notInAPairing') != None and len(assumprecord['info']['notInAPairing']) > 0:
                #groupInfo['G1'] = groupInfo['G1'].union( info['notInAPairing'] )
                for i in assumprecord['notInAPairing']:
                    if not(i in groupInfo['G2']) and not(i in groupInfo['both']):
                        #print(i)
                        groupInfo['G1'] = set((list(groupInfo['G1']) + [i]))
                #print("Update: new G1 deps=>", groupInfo['G1']) 

            # put all the info together so that we can generate the new Asym SDL
            groupInfo['generators'] = generators 
            groupInfo['generatorMapG1'] = generatorMapG1
            groupInfo['generatorMapG2'] = generatorMapG2
            groupInfo['baseGeneratorG1'] = assumprecord['info']['baseGeneratorG1'] # usually 'g'
            groupInfo['baseGeneratorG2'] = assumprecord['info']['baseGeneratorG2']
            groupInfo['newTypes'] = {}
            groupInfo['varTypes'] = {}
            groupInfo['varTypes'].update(assumprecord['varTypes'])
            groupInfo['usedVars'] = set()
            groupInfo['verbose'] = info['verbose']
            transFunc = {}
            transFuncGen = {}

            # determine the structure of the input SDL and stick as close as
            # possible to that in the output SDL
            if hasattr(assumprecord['config'], 'assumpSetupFuncName'):    
                transFuncGen[ assumprecord['config'].assumpSetupFuncName ] = assumprecord['stmtS']
            if hasattr(assumprecord['config'], 'assumpFuncName'):
                transFunc[ assumprecord['config'].assumpFuncName ] = assumprecord['stmtA']

            if options['computeSize']:
                options['symPK']  = symDataTypePK
                options['asymPK'] = asymDataTypePK

            # with the functions and SDL statements defined, can simply run AsymSDL to construct the new SDL
            newSDL_assump = AsymAssumpSDL(assumprecord['options'], assumprecord['assignInfo'], groupInfo, assumprecord['typesH'], generatorLines, transFunc, transFuncGen, reducDeps, assumprecord['varmap'])#TODO: change this!!! we can't guarantee the order of the dictionary....though isn't it a list??
            newLinesT, newLinesSe, newLinesS, newLinesA, userFuncLines = newSDL_assump.constructSDL(assumprecord['config'])

            # debug output of the SDL file
            print_sdl(assumprecord['info']['verbose'], newLinesS, newLinesA)
            # output the new SDL file with right suffix (which indicates options that were set)
            outputFile_assump = "assumption_" + assumprecord['sdl_name'] + "_" + reducname + "_asym_" + fileSuffix + sdlSuffix
            outputFile_assump_array.append(outputFile_assump)
            writeConfig(options['path'] + outputFile_assump, assumprecord['newLines0'], newLinesT, newLinesSe, newLinesS, newLinesA, userFuncLines)

            #TODO: figure out why this line is giving errors for sig schemes
            #buildSplitGraphForAssumption(options['path'] + outputFile_assump, assumprecord['sdl_name'], assumprecord['config'], sdlVerbose)

    return (outputFile, outputFile_assump_array)

        
"""
Aymmetric SDL class takes as input the assignment info from the SDL, new group info, type assignments,
the new generators for the scheme and other functional details.
AsymSDL mechanically converts the symmetric scheme to asymmetric based on all the inferred information.
"""
class AsymSDL:
    def __init__(self, options, assignInfo, groupInfo, typesH, generatorLines, transFunc, transFuncGen):
        self.assignInfo     = assignInfo
        self.groupInfo      = copy.deepcopy(groupInfo)
        self.groupInfo['myAsymSDL'] = self # this is for recording used vars in each function
        self.generatorMap   = list(self.groupInfo['generatorMapG1'].values()) + list(self.groupInfo['generatorMapG2'].values()) 
        self.typesH         = copy.deepcopy(typesH)
        self.generatorLines = copy.deepcopy(generatorLines)
        self.transFunc      = transFunc
        self.transFuncGen   = transFuncGen
        self.userFuncList   = options['userFuncList']
        if options['computeSize']:
            self.__computeSize = True
            if options.get('asymPK') != None: self.__aPKdict = options['asymPK']            
            else: self.__aPKdict = None
            if options.get('symPK') != None: self.__sPKdict = options['symPK']
            else: self.__sPKdict = None
        else:
            self.__computeSize = False
            self.__aPKdict = None
            self.__sPKdict = None            
        self.verbose        = groupInfo['verbose']
        self.__currentFunc    = None
        self.__funcUsedVar    = {}

    def __getFuncLines(self, funcName):
        usedVars = set()
        if funcName != LATEX_HEADER:
            funcConfig = sdl.getVarInfoFuncStmts( funcName )
            Stmts = funcConfig[0]
            funcName = "func:" + funcName
        else:
            Latex = self.assignInfo[LATEX_HEADER]
            Stmts = {}
            for i,j in Latex.items():
                Stmts[ int(j.getLineNo()) ] = j

        begin = "BEGIN :: " + funcName
        end   = "END :: " + funcName            
        
        lines = list(Stmts.keys())
        lines.sort()
        newLines = [begin]
        for index, i in enumerate(lines):
            assert type(Stmts[i]) == sdl.VarInfo, "transformFunction: blockStmts must be VarInfo Objects."
            if LATEX_HEADER in funcName:
                newLines.append( Stmts[i].getLineStrKey() + " := " + Stmts[i].getLineStrValue() )
                continue
            if Stmts[i].getIsExpandNode() or Stmts[i].getIsList():
                newLines.append( str(Stmts[i].getAssignNode()) )
            elif Stmts[i].getIsForLoopBegin():
                if Stmts[i].getIsForType(): newLines.append("\n" + START_TOKEN + " " + BLOCK_SEP + ' for')
                elif Stmts[i].getIsForAllType(): newLines.append("\n" + START_TOKEN + " " + BLOCK_SEP + ' forall')
                newLines.append(str(Stmts[i].getAssignNode()))
            elif Stmts[i].getIsForLoopEnd():
                newLines.append(str(Stmts[i].getAssignNode()))
            
            elif Stmts[i].getIsIfElseBegin():
                newLines.append("\n" + START_TOKEN + " " + BLOCK_SEP + ' if')
                newLines.append( str(Stmts[i].getAssignNode()) )
            else:
                if Type(Stmts[i].getAssignNode()) == ops.EQ:
                    usedVars = usedVars.union( GetAttributeVars(Stmts[i].getAssignNode()) )
                newLines.append(str(Stmts[i].getAssignNode()))
                
        newLines.append( end )
        return newLines, list(usedVars)


    def recordUsedVar(self, varList):
        assert type(varList) in [set, list], "AsymSDL.recordUsedVar: expected a list or set type."
        if self.__currentFunc != None:
            if self.__funcUsedVar.get( self.__currentFunc ) == None:
                self.__funcUsedVar[ self.__currentFunc ] = set() # create new set iff the first time
            self.__funcUsedVar[ self.__currentFunc ] = self.__funcUsedVar[ self.__currentFunc ].union(varList)
        return
    
    def constructSDL(self, config):
        noChangeList = []
        # process original TYPES section to see what we should add to noChangeList (str, int or GT types)    
        for i, j in self.typesH.items():
            t = j.getType()
            if t in [types.ZR, types.listZR, types.Int, types.listInt, types.Str, types.listStr, types.GT]: 
                noChangeList.append(i)
        # JAA: commented out for benchmarking    
        #print("Initial noChangeList: ", noChangeList)
        #(Stmts, Types, depList, depListNoExp, infList, infListNoExp)
        userFuncLines = []
        if len(self.userFuncList) > 0:
            for userFuncs in self.userFuncList:
                # JAA: commented out for benchmarking                
                #print("processing user defined func: ", userFuncs)
                userFuncData = self.__getFuncLines(userFuncs)
                _userFuncLines = userFuncData[0]
                noChangeList  = list(set(noChangeList).union( userFuncData[1] ))
                userFuncLines.append( _userFuncLines )
        
        # update the generator lists if there's a generator in the list
        for i in noChangeList:
            if i in self.generatorLines.keys():
                # strip from the data structures
                self.generatorLines[ i ] = None
                self.groupInfo['G1'] = self.groupInfo['G1'].difference( [i] )
                self.groupInfo['G2'] = self.groupInfo['G2'].difference( [i] )
                self.groupInfo['both'] = self.groupInfo['both'].difference( [i] ) 
 
        newLinesSe = []
        newLinesS = []
        newLinesK = []
        entireSDL = sdl.getLinesOfCode()
        transFuncRes = {}
        Input = {}
        for funcName in config.functionOrder:
            if funcName in self.transFuncGen.keys():
                #print("<===== processing %s =====>" % funcName)
                self.__currentFunc = funcName
                transFuncRes[ funcName ] = transformFunction(entireSDL, funcName, self.transFuncGen[ funcName ], self.groupInfo, noChangeList, self.generatorLines)
                #print("<===== processing %s =====>" % funcName)
                
        # obtain results
        newLinesT = transformTypes(self.typesH, self.groupInfo)
        if hasattr(config, "extraSetupFuncName"):
            newLinesSe = transFuncRes.get( config.extraSetupFuncName )
        if hasattr(config, 'setupFuncName'):   
            newLinesS  = transFuncRes.get( config.setupFuncName )
        elif hasattr(config, 'keygenFuncName'):
            newLinesK  = transFuncRes.get( config.keygenFuncName )
        
        # transform body of SDL scheme
        if config.schemeType == PKENC:
            for funcName in config.functionOrder:
                if funcName in self.transFunc.keys():
                    #print("<===== processing %s =====>" % funcName)
                    self.__currentFunc = funcName
                    transFuncRes[ funcName ] = transformFunction(entireSDL, funcName, self.transFunc[ funcName ], self.groupInfo, noChangeList)
                    #print("<===== processing %s =====>" % funcName)
            newLinesK = transFuncRes.get( config.keygenFuncName )
            newLines2 = transFuncRes.get( config.encryptFuncName )
            newLines3 = transFuncRes.get( config.decryptFuncName )
                
        elif config.schemeType == PKSIG:
            for funcName in config.functionOrder:
                if funcName in self.transFunc.keys():
                    #print("<===== processing %s =====>" % funcName)
                    self.__currentFunc = funcName
                    transFuncRes[ funcName ] = transformFunction(entireSDL, funcName, self.transFunc[ funcName ], self.groupInfo, noChangeList, self.generatorLines) 
                    #print("<===== processing %s =====>" % funcName)
                
            newLinesK = transFuncRes.get( config.keygenFuncName )
            newLines2 = transFuncRes.get( config.signFuncName )
            newLines3 = transFuncRes.get( config.verifyFuncName )
        
        # prune generators not used in the scheme 
        usedGenerators = []
        for i in self.groupInfo['usedVars']:
            if i in self.generatorMap:
                # actual generator
                usedGenerators.append(i)
        deleteMe = list(set(self.generatorMap).difference(usedGenerators))

        if len(deleteMe) > 0:
            print("Always Prune Generators: ", deleteMe)
            newLinesSe = self.__prune(newLinesSe, deleteMe)
            newLinesS  = self.__prune(newLinesS, deleteMe)
            newLinesK  = self.__prune(newLinesK, deleteMe)
            newLines2  = self.__prune(newLines2, deleteMe)
            newLines3  = self.__prune(newLines3, deleteMe)
        else:
            print("No unused generators to prune!")

        if hasattr(config, 'enablePKprune') and config.enablePKprune and config.schemeType == PKSIG:
            # 1. get new pk list if defined in scheme
            origPKList = self.__getOriginalPK(config.keygenPubVar, newLinesSe + newLinesS + newLinesK)
            # 2. find out where pk was originally defined
            (defInFuncName, varInf) = getVarNameEntryFromAssignInfo(self.assignInfo, config.keygenPubVar)
            # 3. split pk into two new public keys (sPK, and vPK)
            if len(origPKList) > 0:
                pkData = self.optimizePK(config, origPKList)
                (sPub, vPub, newSignPK, newVerifyPK, newSignPKexp, newVerifyPKexp) = pkData

                # apply PKSIG optimizations to pk
                newVarNames = []
                newVarNodes = []
                if newSignPK != None:
                    newVarNames += [sPub]
                    newVarNodes += [newSignPK]
                if newVerifyPK != None:
                    newVarNames += [vPub]
                    newVarNodes += [newVerifyPK]
#                    newVarNames = [sPub, vPub]
#                    newVarNodes = [newSignPK, newVerifyPK]
                #print("Public Key defined in ", defInFuncName)
                if defInFuncName == "setup":
                    newLinesS = self.__updatePKList(config.keygenPubVar, newVarNodes, newVarNames, newLinesS)
                elif defInFuncName == "keygen":
                    newLinesK = self.__updatePKList(config.keygenPubVar, newVarNodes, newVarNames, newLinesK)

                # sPub => keygen AND sign
                # vPub => verify
                if defInFuncName != "keygen" and newSignPK != None:
                    newLinesK = self.__updatePKExpand(config.keygenPubVar, newSignPKexp, sPub, newLinesK)

                if newSignPK != None:
                    newLines2 = self.__updatePKExpand(config.keygenPubVar, newSignPKexp, sPub, newLines2)
                if newVerifyPK != None:
#                    print("Actual Verify PK: ", newVerifyPKexp.getRight().listNodes)
                    newLines3 = self.__updatePKExpand(config.keygenPubVar, newVerifyPKexp, vPub, newLines3)
            
        return newLinesT, newLinesSe, newLinesS, newLinesK, newLines2, newLines3, userFuncLines

    def __updatePKList(self, targetVar, newVarNodes, newVarNames, newLinesK):
        nodeLines2 = []
        replacedNewPK = False 
        for node in newLinesK:
            if Type(node) == ops.EQ:
                if str(node.left) == targetVar: # found
                    nodeLines2.extend(newVarNodes)
                    replacedNewPK = True
                    continue
                if str(node.left) == outputKeyword and replacedNewPK:
                    sv = SubstituteVar(targetVar, newVarNames)
                    sdl.ASTVisitor(sv).preorder(node)
            nodeLines2.append( node )
        return nodeLines2

    def __updatePKExpand(self, targetVar, newVarNode, newVarName, newLines):
        nodeLines2 = []
        replacedNewPK = False 
        for node in newLines:
            if Type(node) == ops.EQ:
                if str(node.left) == targetVar: # found
                    nodeLines2.append(newVarNode)
                    continue
                if str(node.left) == inputKeyword:
                    sv = SubstituteVar(targetVar, newVarName)
                    sdl.ASTVisitor(sv).preorder(node)
            nodeLines2.append( node )
        return nodeLines2

    def optimizePK(self, config, origPK):
        #print("origPK :", origPK) # JAA debug
        if len(origPK) > 0:
            signUsedVars   = []
            signVars       = self.__funcUsedVar.get(config.signFuncName)
            if signVars != None:
                for i in signVars:
                    if i in origPK: signUsedVars.append(i)

            keygenVars       = self.__funcUsedVar.get(config.keygenFuncName)
            #print("keygenVars: ", keygenVars)
            if keygenVars != None:
                for i in keygenVars:
                    if i in origPK:
                        if i not in signUsedVars: signUsedVars.append(i)
            signUsedVars.sort()
            
            verifyUsedVars = []
            verifyVars     = self.__funcUsedVar.get(config.verifyFuncName)
            if verifyVars != None:
                for i in verifyVars:
                    if i in origPK: verifyUsedVars.append(i)
            verifyUsedVars.sort()
            
            asymDataTypePK = {}
            if self.__aPKdict != None:
                for i in self.__aPKdict:
                    if i in verifyUsedVars:
                        asymDataTypePK[i] = self.__aPKdict[i]
                #print("verifyUsedVars: ", verifyUsedVars)
                #print("sym PK => ", list(self.__sPKdict.keys()))
                #print("asym PK => ", list(asymDataTypePK.keys()))
                #print("estimated  sym:  ", estimateSize(self.__sPKdict, symmetric_curves['SS1536']))        
                #print("estimated asym: ", estimateSize(asymDataTypePK, asymmetric_curves['BN256']))
            
            sPub = "s"+config.keygenPubVar
            vPub = "v"+config.keygenPubVar
            newSignPK = None
            newSignPKexp = None
            if len(signUsedVars) > 0:
                newSignPK      = self.__createListNode(sPub, signUsedVars)
                newSignPKexp   = self.__createExpandNode(sPub, signUsedVars)
            newVerifyPK = None
            newVerifyPKexp = None
            if len(verifyUsedVars) > 0:
                newVerifyPK    = self.__createListNode(vPub, verifyUsedVars)
                newVerifyPKexp = self.__createExpandNode(vPub, verifyUsedVars)

            
        return (sPub, vPub, newSignPK, newVerifyPK, newSignPKexp, newVerifyPKexp)
            
    def __prune(self, nodeLines, deleteMeList):
        nodeLines2 = []

        if not nodeLines:
            return nodeLines2

        for node in nodeLines:
            if Type(node) == ops.EQ:
                if str(node.left) in deleteMeList:
                    if self.verbose: print("Delete line: ", node.left)
                    continue
                else: # check right side
                    contain = DelAnyVarInList(deleteMeList) 
                    sdl.ASTVisitor(contain).preorder( node.right )
                    if len(contain.foundVar) > 0 and self.verbose: print("Deleted ", contain.foundVar)
            if self.verbose: print("line: ", node)
            nodeLines2.append( node )
        return nodeLines2
    
    def __getOriginalPK(self, varPK, funcs):
        for node in funcs:
            if Type(node) == ops.EQ:
                if str(node.left) == varPK and Type(node.right) == ops.LIST:
                    newList = list(node.right.listNodes)
                    #print("__getOriginalPK : ", newList)
                    return newList
        return []       
    
    def __createListNode(self, name, varList):
        _list = BinaryNode(ops.LIST)
        _list.listNodes = list(varList)
        return BinaryNode(ops.EQ, BinaryNode(name), _list)
    
    def __createExpandNode(self, name, varList):
        _list = BinaryNode(ops.EXPAND)
        _list.listNodes = list(varList)
        return BinaryNode(ops.EQ, BinaryNode(name), _list)

"""
Aymmetric Assumption SDL class takes as input the assignment info from the SDL, new group info, type assignments,
the new generators for the scheme and other functional details.
AsymSDL mechanically converts the symmetric scheme to asymmetric based on all the inferred information.
"""
class AsymAssumpSDL:
    def __init__(self, options, assignInfo, groupInfo, typesH, generatorLines, transFunc, transFuncGen, deps, varmap):
        self.assignInfo     = assignInfo
        self.groupInfo      = copy.deepcopy(groupInfo)
        self.groupInfo['myAsymSDL'] = self # this is for recording used vars in each function
        self.generatorMap   = list(self.groupInfo['generatorMapG1'].values()) + list(self.groupInfo['generatorMapG2'].values()) 
        self.typesH         = copy.deepcopy(typesH)
        self.generatorLines = copy.deepcopy(generatorLines)
        self.transFunc      = transFunc
        self.transFuncGen   = transFuncGen
        self.userFuncList   = options['userFuncList']
        self.deps           = deps
        self.varmap         = varmap

        if options['computeSize']:
            self.__computeSize = True
            if options.get('asymPK') != None: self.__aPKdict = options['asymPK']            
            else: self.__aPKdict = None
            if options.get('symPK') != None: self.__sPKdict = options['symPK']
            else: self.__sPKdict = None
        else:
            self.__computeSize = False
            self.__aPKdict = None
            self.__sPKdict = None            
        self.verbose        = groupInfo['verbose']
        self.__currentFunc    = None
        self.__funcUsedVar    = {}

    def __getFuncLines(self, funcName):
        usedVars = set()
        if funcName != LATEX_HEADER:
            funcConfig = sdl.getVarInfoFuncStmts( funcName )
            Stmts = funcConfig[0]
            funcName = "func:" + funcName
        else:
            Latex = self.assignInfo[LATEX_HEADER]
            Stmts = {}
            for i,j in Latex.items():
                Stmts[ int(j.getLineNo()) ] = j

        begin = "BEGIN :: " + funcName
        end   = "END :: " + funcName            
        
        lines = list(Stmts.keys())
        lines.sort()
        newLines = [begin]
        for index, i in enumerate(lines):
            assert type(Stmts[i]) == sdl.VarInfo, "transformFunction: blockStmts must be VarInfo Objects."
            if LATEX_HEADER in funcName:
                newLines.append( Stmts[i].getLineStrKey() + " := " + Stmts[i].getLineStrValue() )
                continue
            if Stmts[i].getIsExpandNode() or Stmts[i].getIsList():
                newLines.append( str(Stmts[i].getAssignNode()) )
            elif Stmts[i].getIsForLoopBegin():
                if Stmts[i].getIsForType(): newLines.append("\n" + START_TOKEN + " " + BLOCK_SEP + ' for')
                elif Stmts[i].getIsForAllType(): newLines.append("\n" + START_TOKEN + " " + BLOCK_SEP + ' forall')
                newLines.append(str(Stmts[i].getAssignNode()))
            elif Stmts[i].getIsForLoopEnd():
                newLines.append(str(Stmts[i].getAssignNode()))
            
            elif Stmts[i].getIsIfElseBegin():
                newLines.append("\n" + START_TOKEN + " " + BLOCK_SEP + ' if')
                newLines.append( str(Stmts[i].getAssignNode()) )
            else:
                if Type(Stmts[i].getAssignNode()) == ops.EQ:
                    usedVars = usedVars.union( GetAttributeVars(Stmts[i].getAssignNode()) )
                newLines.append(str(Stmts[i].getAssignNode()))
                
        newLines.append( end )
        return newLines, list(usedVars)


    def recordUsedVar(self, varList):
        assert type(varList) in [set, list], "AsymSDL.recordUsedVar: expected a list or set type."
        if self.__currentFunc != None:
            if self.__funcUsedVar.get( self.__currentFunc ) == None:
                self.__funcUsedVar[ self.__currentFunc ] = set() # create new set iff the first time
            self.__funcUsedVar[ self.__currentFunc ] = self.__funcUsedVar[ self.__currentFunc ].union(varList)
        return
    
    def constructSDL(self, config):
        noChangeList = []
        # process original TYPES section to see what we should add to noChangeList (str, int or GT types)    
        for i, j in self.typesH.items():
            t = j.getType()
            if t in [types.ZR, types.listZR, types.Int, types.listInt, types.Str, types.listStr, types.GT]: 
                noChangeList.append(i)
        # JAA: commented out for benchmarking    
        #print("Initial noChangeList: ", noChangeList)
        #(Stmts, Types, depList, depListNoExp, infList, infListNoExp)
        userFuncLines = []
        if len(self.userFuncList) > 0:
            for userFuncs in self.userFuncList:
                # JAA: commented out for benchmarking                
                #print("processing user defined func: ", userFuncs)
                userFuncData = self.__getFuncLines(userFuncs)
                _userFuncLines = userFuncData[0]
                noChangeList  = list(set(noChangeList).union( userFuncData[1] ))
                userFuncLines.append( _userFuncLines )
        
        # update the generator lists if there's a generator in the list
        for i in noChangeList:
            if i in self.generatorLines.keys():
                # strip from the data structures
                self.generatorLines[ i ] = None
                self.groupInfo['G1'] = self.groupInfo['G1'].difference( [i] )
                self.groupInfo['G2'] = self.groupInfo['G2'].difference( [i] )
                self.groupInfo['both'] = self.groupInfo['both'].difference( [i] ) 
 
        newLinesSe = []
        newLinesS = []
        entireSDL = sdl.getLinesOfCode()
        transFuncRes = {}
        Input = {}
        for funcName in config.functionOrder:
            if funcName in self.transFuncGen.keys():
                print("<===== 1 processing %s =====>" % funcName)
                self.__currentFunc = funcName
                transFuncRes[ funcName ] = transformFunctionAssump(entireSDL, funcName, self.transFuncGen[ funcName ], self.groupInfo, noChangeList, self.deps[1], self.varmap, self.generatorLines)
                print("<===== 1 processing %s =====>" % funcName)
                
        # obtain results
        newLinesT = transformTypes(self.typesH, self.groupInfo)
        if hasattr(config, "extraSetupFuncName"):
            newLinesSe = transFuncRes.get( config.extraSetupFuncName )
        if hasattr(config, 'assumpSetupFuncName'):   
            newLinesS  = transFuncRes.get( config.assumpSetupFuncName )

        # transform body of SDL scheme
        if (config.schemeType == PKENC):
            print("PKENC assumption")
            for funcName in config.functionOrder:
                if funcName in self.transFunc.keys():
                    print("<===== 2 processing PKENC %s =====>" % funcName)
                    self.__currentFunc = funcName
                    transFuncRes[ funcName ] = transformFunctionAssump(entireSDL, funcName, self.transFunc[ funcName ], self.groupInfo, noChangeList, self.deps[1], self.varmap)
                    print("<===== 2 processing PKENC %s =====>" % funcName)
            newLinesA = transFuncRes.get( config.assumpFuncName )
                
        elif config.schemeType == PKSIG:
            print("PKSIG assumption")
            for funcName in config.functionOrder:
                if funcName in self.transFunc.keys():
                    print("<===== processing %s =====>" % funcName)
                    self.__currentFunc = funcName
                    #transFuncRes[ funcName ] = transformFunction(entireSDL, funcName, self.transFunc[ funcName ], self.groupInfo, noChangeList, self.generatorLines) 
                    transFuncRes[ funcName ] = transformFunctionAssump(entireSDL, funcName, self.transFunc[ funcName ], self.groupInfo, noChangeList, self.deps[1], self.varmap)
                    print("<===== processing %s =====>" % funcName)
                
            newLinesA = transFuncRes.get( config.assumpFuncName )
        
        # prune generators not used in the scheme 
        usedGenerators = []
        for i in self.groupInfo['usedVars']:
            if i in self.generatorMap:
                # actual generator
                usedGenerators.append(i)
        deleteMe = list(set(self.generatorMap).difference(usedGenerators))
                
        if len(deleteMe) > 0:
            #print("Pruning Generators:\t", deleteMe)
            newLinesSe = self.__prune(newLinesSe, deleteMe)
            newLinesS  = self.__prune(newLinesS, deleteMe)
            newLinesA  = self.__prune(newLinesA, deleteMe)

        return newLinesT, newLinesSe, newLinesS, newLinesA, userFuncLines

    def __prune(self, nodeLines, deleteMeList):
        nodeLines2 = []

        if not nodeLines:
            return nodeLines2

        for node in nodeLines:
            if Type(node) == ops.EQ:
                if str(node.left) in deleteMeList:
                    if self.verbose: print("Delete line: ", node.left)
                    continue
                else: # check right side
                    contain = DelAnyVarInList(deleteMeList) 
                    sdl.ASTVisitor(contain).preorder( node.right )
                    if len(contain.foundVar) > 0 and self.verbose: print("Deleted ", contain.foundVar)
            if self.verbose: print("line: ", node)
            nodeLines2.append( node )
        return nodeLines2
    
    def __createListNode(self, name, varList):
        _list = BinaryNode(ops.LIST)
        _list.listNodes = list(varList)
        return BinaryNode(ops.EQ, BinaryNode(name), _list)
    
    def __createExpandNode(self, name, varList):
        _list = BinaryNode(ops.EXPAND)
        _list.listNodes = list(varList)
        return BinaryNode(ops.EQ, BinaryNode(name), _list)

        
# temporary placement
def NaiveEvaluation(solutionList, preference):
    trueCount = 0
    falseCount = 0
    resMap = {}
    for tupl in solutionList:
        (k, v) = tupl
        if v == True: trueCount += 1
        elif v == False: falseCount += 1
        else: sys.exit("z3 results have been tampered with.")
        resMap[ k ] = v
    
    if preference in [SHORT_SECKEYS, SHORT_PUBKEYS, SHORT_CIPHERTEXT, SHORT_SIGNATURE]:
        return {True:'G1', False:'G2'}, resMap
    
    if trueCount >= falseCount: 
        G1 = True; G2 = False
    elif falseCount > trueCount:
        G1 = False; G2 = True

    return { G1:'G1', G2:'G2' }, resMap

# def DeriveGeneralSolution(groupMap, resultMap, xorMap, info):
#     #print("<===== Deriving Solution from Results =====>")
#     G1_deps = set()
#     G2_deps = set()
#     pairingInfo = {}
#     pairingInfo[G1Prefix] = []
#     pairingInfo[G2Prefix] = []
#     for i in info['G1_lhs'][0] + info['G1_rhs'][0]:
#         # get the z3 var for it
#         z3Var = xorMap.get(i) # gives us an alphabet
#         # look up value in resultMap
#         varValue = resultMap.get(z3Var)
#         # get group
#         group = groupMap.get(varValue)
#         if i in info['G1_lhs'][0]: deps = info['G1_lhs'][1].get(i)
#         else: deps = info['G1_rhs'][1].get(i)
#         deps = list(deps); deps.append(i) # var name to the list
#         if group == 'G1': G1_deps = G1_deps.union(deps); pairingInfo[G1Prefix].append(i)
#         elif group == 'G2': G2_deps = G2_deps.union(deps); pairingInfo[G2Prefix].append(i)
#     #print("<===== Deriving Solution from Results =====>")
#     both = G1_deps.intersection(G2_deps)
#     G1 = G1_deps.difference(both)
#     G2 = G2_deps.difference(both)
#     #print("Both G1 & G2: ", both)
#     #print("Just G1: ", G1)
#     #print("Just G2: ", G2)
#     return { 'G1':G1, 'G2':G2, 'both':both, 'pairing':pairingInfo }

def DeriveSpecificSolution(resultDict, xorMap, info):  #groupMap, resultMap, xorMap, info):
    #print("<===== Deriving Specific Solution from Results =====>")
    G1_deps = set()
    G2_deps = set()
    both_groups = set()
    resultMap = {}
    newSol = {}
    for tupl in resultDict:
        (k, v) = tupl
        resultMap[ k ] = v
    pairingInfo = {}
    pairingInfo[G1Prefix] = []
    pairingInfo[G2Prefix] = []
    for i in info['G1_lhs'][0] + info['G1_rhs'][0]:
        # get the z3 var for it
        z3Var = xorMap.get(i) # gives us an alphabet
        # look up value in resultMap (TODO: change to group directly)
        group = resultMap.get(z3Var)
        # get group
        #if varValue == True: group = 'G1'
        #else: group = 'G2'
        
        if i in info['G1_lhs'][0]:
            deps = info['G1_lhs'][1].get(i)
        else:
            deps = info['G1_rhs'][1].get(i)
        deps = list(deps) # convert to a list (in case, it was a set)
        deps.append(i) # var name to the list
        newSol[i] = group
        if group == 'G1':
            G1_deps = G1_deps.union(deps)
            pairingInfo[G1Prefix].append(i)
        elif group == 'G2':
            G2_deps = G2_deps.union(deps)
            pairingInfo[G2Prefix].append(i)
        elif group == 'both':
            both_groups = both_groups.union(deps)

    #print("<===== Deriving Specific Solution from Results =====>")
    both = G1_deps.intersection(G2_deps)
    if len(both_groups) > 0:
        both = both.union(both_groups)
    G1 = G1_deps.difference(both)
    G2 = G2_deps.difference(both)
    ###print("Both G1 & G2: ", both)
    ###print("Just G1: ", G1)
    ###print("Just G2: ", G2)
    return { 'G1':G1, 'G2':G2, 'both':both, 'pairing':pairingInfo, 'newSol':newSol }


def findVarInfo(var, varTypes):
    if var.find(LIST_INDEX_SYMBOL) != -1:
        v = var.split(LIST_INDEX_SYMBOL) 
        vName = v[0] 
#        vRef  = v[-1] # get last argument
#        levelsOfIndirection = len(v[1:])
#        print("vName :", vName)
#        print("type info :", varTypes.get(vName).getType())
#        print("vRef :", vRef)
#        print("levels :", levelsOfIndirection)
        return varTypes.get(vName)
        
def assignTraceback(assignInfo, generators, varTypes, listVars, constraintList):
    varProp = []
    data = {}
    # get variable names from all pairing
    for i in listVars:
        #print("var name := ", i) # JAA debug
        var = i
        buildMap(assignInfo, generators, varTypes, varProp, var, constraintList)
        data[i] = set(varProp)
        varProp = []

#JAA debug    
#    for i in listVars:
#        print("key: ", i, ":=>", data[i])
#    print("varProp for ", listVars[0], ": ", varProp)
    return data

        
def buildMap(assignInfo, generators, varTypes, varList, var, constraintList):
    removeList = []
    if (not set(var).issubset(generators)):
        #print("var keys: ", var) # JAA debug
        (name, varInf) = getVarNameEntryFromAssignInfo(assignInfo, var)
        if(name == None): 
            if varInf != None: pass #print("Var : ", varInf.getVarDepsNoExponents())
            elif var.find(LIST_INDEX_SYMBOL) != -1: varInf = findVarInfo(var, varTypes)
            return
        l = list(varInf.getVarDepsNoExponents())
        #print("var:", var, ", output: ", l) # JAA debug
        if var in l: l.remove(var)
        if G1Prefix in l: l.remove(G1Prefix)
            
        # prune 'l' here
        for i in l:
            #print("name: ", i) # uncomment for ckrs09 error
            typeI = sdl.getVarTypeFromVarName(i, None, True)
            #print("getVarTypeFromVarName:  ", i,":", typeI) # JAA debug
            if typeI == types.NO_TYPE:
                node = BinaryNode(ops.ATTR)
                node.setAttribute(i)
                #print("getVarNameFromListIndices req node: ", node)
                (funcName , newVarName) = getVarNameFromListIndices(assignInfo, varTypes, node, True)
                if newVarName != None: 
                    #print("newVarName := ", newVarName)
                    resultVarName = sdl.getVarTypeFromVarName(newVarName, None, True)
                    #print("second attempt: ", newVarName, ":", resultVarName)
                    varList.append(newVarName)              
                else:
                    pass
#                    print("JAA: ADDING to varList: ", i)
#                    varList.append(i)
            elif typeI in [types.G1]:
                varList.append(i)
            elif typeI in [types.ZR, types.list, types.pol]: #types.Str,
                (name, varInf) = getVarNameEntryFromAssignInfo(assignInfo, i)
                if varInf.getIsUsedInHashCalc():
                    #print("adding", i, "to the list")
                    varList.append(str(i))
                    constraintList.append(str(var))
                continue
            else:
                pass
#                print("TODO: missing a case in buildMap: ", typeI)
                
#        varList.extend(l)
        varsToCheck = list(l)
        for i in varsToCheck:
            lenBefore = len(varList)
            buildMap(assignInfo, generators, varTypes, varList, i, constraintList)
            lenAfter  = len(varList)
            if lenBefore == lenAfter:
                node = BinaryNode(ops.ATTR)
                node.setAttribute(i)
                #print("Node :=>", node)
                (funcName, string) = getVarNameFromListIndices(assignInfo, varTypes, node, True)
                if string != None: varList.append(string)

#        for i in removeList:
#            print("REMOVING: ", i)
#            print("varList: ", varList)
            
    return

def getVarCount(assignInfo, varName):
    (name, varObj) = getVarNameEntryFromAssignInfo(assignInfo, varName)
    for_loop_obj = varObj.getOutsideForLoopObj()
    if for_loop_obj:
        # see the value
        var = for_loop_obj.getEndVal()
        # check if it's a var or number
        try:
            varInt = int(var)
            return varInt
        except:
            # must be a variable
            (name, varObj2) = getVarNameEntryFromAssignInfo(assignInfo, var)
            try:
                varInt = int(varObj2.getAssignNode().getRight().getAttribute())
                return varInt
            except:
                sys.exit("'%s' not defined as an integer! Fix your SDL and try again.\n" % var)
    return 1

def countCommonGenerators(countMap, pk_list, var_list, var_map, assignInfo):
    for i in var_list:
        for j in var_map[i]:
            if j in pk_list:
                if j not in countMap:
                    # add getCount(j) => looks up 'j' var object to see if it's in a loop or not
                    countMap[j] = getVarCount(assignInfo, j)
                else:
                    countMap[j] += getVarCount(assignInfo, j)
    # print("Final Count map: ", countMap)
    return


class Generators:
    def __init__(self, info):
        self.generators = []
        self.genLines = {}
        self.genDict = {}
        self.info = info
        
    def extractGens(self, stmt, _types):
        lines = list(stmt.keys())
        lines.sort()
        for i in lines:
            if type(stmt[i]) == sdl.VarInfo and stmt[i].getHasRandomness() and Type(stmt[i].getAssignNode()) == ops.EQ:
                t = stmt[i].getAssignVar()
                if _types.get(t) == None:
                    typ = stmt[i].getAssignNode().right.left.attr
    #                print("Retrieved type directly: ", typ)
                else:
                    typ = _types[t].getType()
                if typ == types.G1:
                    if (stmt[i].getOutsideForLoopObj() != None): inForLoop = True
                    else: inForLoop = False
                    # JAA comment out for benchmarking
                    if self.info['verbose']: print(i, ": ", typ, " :=> ", stmt[i].getAssignNode(), ", loop :=> ", inForLoop)
                    if not inForLoop: 
                        self.generators.append(str(stmt[i].getAssignVar()))
                    else:
                        listRef = stmt[i].getAssignVar().split(LIST_INDEX_SYMBOL)[0]
                        if self.info['verbose']: print("Found generator in for loop: ", listRef)
                        self.generators.append(listRef)
                        self.genDict[ listRef ] = str(stmt[i].getAssignVar()) #, str(stmt[i].getAssignNode()))   # str(stmt[i].getOutsideForLoopObj())
#                        startLine = stmt[i].getOutsideForLoopObj().getStartLineNo()
#                        endLine = stmt[i].getOutsideForLoopObj().getEndLineNo()+1
#                        newLines = sdl.getLinesOfCodeFromLineNos(list(range(startLine, endLine)))
#                        print("ForLoop content:\n", newLines)
#                        print("Stmt Interest: ", stmt[i].getAssignNode())
        return

    def setupNewGens(self):
        """derive generators used by the scheme using the following rules:
        1. first generator is selected as the base generator, "g". We split into two. 1 in G1 and other in G2.
        2. second generator and thereafter are defined in terms of base generator, g in both groups as follows (DH):
             h = random(ZR)
             hG1 = gG1 ^ h
             hG2 = gG2 ^ h
        3. TODO: need a way to prune which setup generators are used (a kind of optimization)
        """
        #genLines = []
        genMapG1 = {}
        genMapG2 = {}
    
        if len(self.generators) == 0:
            sys.exit("The scheme selects no generators in setup? Please try again.\n")    
        base_gen = self.generators[0]
        self.base_gen = base_gen
        # split the first generator
        base_genG1 = base_gen + G1Prefix
        base_genG2 = base_gen + G2Prefix
        baseG1 = BinaryNode(base_genG1)
        baseG2 = BinaryNode(base_genG2)

        self.genLines[ base_gen ] = []
        self.genLines[ base_gen ].append(BinaryNode(ops.EQ, baseG1, createTree("random(", "G1", None))) # base_genG1 + " := random(G1)")
        self.genLines[ base_gen ].append(BinaryNode(ops.EQ, baseG2, createTree("random(", "G2", None))) # base_genG2 + " := random(G2)")
        
        genMapG1[ base_gen ] = base_genG1
        genMapG2[ base_gen ] = base_genG2
        self.info['baseGeneratorG1'] = base_genG1
        self.info['baseGeneratorG2'] = base_genG2
        
        genOfList = self.genDict.keys()
        for j in range(1, len(self.generators)):
            i = self.generators[j]
            iNode = BinaryNode(i)
            expG1 = BinaryNode(ops.EXP, BinaryNode.copy(baseG1), BinaryNode.copy(iNode))
            expG2 = BinaryNode(ops.EXP, BinaryNode.copy(baseG2), BinaryNode.copy(iNode))
            if i not in genOfList: 
                # generator itself is not a list
                self.genLines[ i ] = []
                self.genLines[ i ].append(BinaryNode(ops.EQ, iNode, createTree("random(", "ZR", None))) # i + " := random(ZR)")
                self.genLines[ i ].append(BinaryNode(ops.EQ, BinaryNode(i + G1Prefix), expG1)) # i + G1Prefix + " := " + base_genG1 + " ^ " + i)
                self.genLines[ i ].append(BinaryNode(ops.EQ, BinaryNode(i + G2Prefix), expG2)) # i + G2Prefix + " := " + base_genG2 + " ^ " + i)
                
                genMapG1[ i ] = i + G1Prefix
                genMapG2[ i ] = i + G2Prefix
            elif i in genOfList:
                #print("setupNewGens: handle list => ", i)
                oldI = self.genDict[ i ] # 0 : old i
                self.genLines[ oldI ] = []
                self.genLines[ oldI ].append(BinaryNode(ops.EQ, iNode, createTree("random(", "ZR", None))) # (i + " := random(ZR)")
                self.genLines[ oldI ].append(BinaryNode(ops.EQ, BinaryNode(oldI.replace(i, i + G1Prefix)), expG1)) # (oldI.replace(i, i + G1Prefix) + " := " + base_genG1 + " ^ " + i)
                self.genLines[ oldI ].append(BinaryNode(ops.EQ, BinaryNode(oldI.replace(i, i + G2Prefix)), expG2)) # (oldI.replace(i, i + G2Prefix) + " := " + base_genG2 + " ^ " + i)
                genMapG1[ i ] = i + G1Prefix
                genMapG2[ i ] = i + G2Prefix                
            else: #elif i in genCond:
                pass
                #print("setupNewGens: handle conditionals => ", i)
                
#        print("....Start New Generators...")
#        for line in self.genLines:
#            print(line)
#        print("....End New Generators...")
        return (genMapG1, genMapG2)

    def getGens(self):
        return self.generators    
    
    def getGenLines(self):
        return self.genLines
        
def assignVarOccursInBoth(varName, info):
    """determines if varName occurs in the 'both' set. For varName's that have a '#' indicator, we first split it
    then see if arg[0] is in the 'both' set."""
    if varName.find(LIST_INDEX_SYMBOL) != -1:
        varNameStrip = varName.split(LIST_INDEX_SYMBOL)[0]
    else:
        varNameStrip = None
    if varName in info['both']:
        return True
    elif varNameStrip != None and varNameStrip in info['both']:
        return True
    return False

def assignVarOccursInG1(varName, info):
    """determines if varName occurs in the 'G1' set. For varName's that have a '#' indicator, we first split it
    then see if arg[0] is in the 'G1' set."""
    if varName.find(LIST_INDEX_SYMBOL) != -1:
        varNameStrip = varName.split(LIST_INDEX_SYMBOL)[0]
    else:
        varNameStrip = None
    if varName in info['G1']:
        return True
    elif varNameStrip != None and varNameStrip in info['G1']:
        return True
    return False

def assignVarOccursInG2(varName, info):
    """determines if varName occurs in the 'G2' set. For varName's that have a '#' indicator, we first split it
    then see if arg[0] is in the 'G2' set."""    
    if varName.find(LIST_INDEX_SYMBOL) != -1:
        varNameStrip = varName.split(LIST_INDEX_SYMBOL)[0]
    else:
        varNameStrip = None
    if varName in info['G2']:
        return True
    elif varNameStrip != None and varNameStrip in info['G2']:
        return True
    return False


def assignVarIsGenerator(varName, info):
    generatorList = info['generators']
    return varName in generatorList

def handleListTypeRefs(varTypes, ref, info, isForBoth, groupType):
    global oldListTypeRefs, newListTypeRefs
    changeBack = None
    refDetails = ref.split(LIST_INDEX_SYMBOL)
    length = len(refDetails)
    if length == 2: # one level of indirection var#<int>
        refName = refDetails[0]
        refStr  = refDetails[1]
        if refStr.isdigit(): refNum = int(refDetails[1])
        else: return ref.replace(refName, refName + str(groupType))
    elif length == 3: # two level of indirection...var#*#<int>
        refName = refDetails[0]
        refStr  = refDetails[-1]
        if refStr.isdigit(): refNum = int(refDetails[-1]) # refNum 
        # look for "varName#*" type def
        #print("oldListTypeRefs: ", oldListTypeRefs.keys())
        searchRE = refName + "#." # try to match
        for i in oldListTypeRefs.keys():
            result = re.search(searchRE, i)
            if result:
                changeBack = ref[:-2] # cut off last two characters '#<int>'
                refName = result.group(0) # update the refName
                break

    else:
        print("JAA: can't handle reference lists of length %s yet." % length)
        return False
    oldVar = oldListTypeRefs.get(refName)
    if(oldVar != None): oldVar = oldVar[refNum]
    else: return ref
    
    if assignVarIsGenerator(oldVar, info) or assignVarOccursInBoth(oldVar, info):
       # look for either G1 or G2
       if groupType == types.G1: newRef = newListTypeRefs.get(refName).index(oldVar + G1Prefix)
       elif groupType == types.G2: newRef = newListTypeRefs.get(refName).index(oldVar + G2Prefix)
    else:
        # means either G1 or G2, we don't have to look for "_G?" extensions
        newRef = newListTypeRefs.get(refName).index(oldVar)
    
    if changeBack != None: refName = changeBack #TODO: handle this better in the future
    newRefName = refName + "#" + str(newRef)
    return newRefName

def prune(_list):
    # remove redundancies in list
    _list2 = list(set(_list))
    _list3 = []
    for i in _list2:
        if i.find(sdl.LIST_INDEX_SYMBOL) != -1:
            # chop off the '#' in the case of list references
            _list3.append(i.split(sdl.LIST_INDEX_SYMBOL)[0])
        else:
            _list3.append(i)
    # return the pruned list
    return _list3

def assignNewVar(assignVar, suffix):
    if assignVar.find(sdl.LIST_INDEX_SYMBOL) != -1:
        assignVar0 = assignVar.split(sdl.LIST_INDEX_SYMBOL)[0]
        return assignVar.replace(assignVar0, assignVar0 + suffix)
    return assignVar + suffix

def updateAllForBoth(node, assignVar, varInfo, info, changeLeftVar=True, noChangeList=[]):
    newLine1 = updateAllForG1(node, assignVar, varInfo, info, changeLeftVar, noChangeList)
    newLine2 = updateAllForG2(node, assignVar, varInfo, info, changeLeftVar, noChangeList)
    return [newLine1, newLine2]

def updateAllForG1(node, assignVar, varInfo, info, changeLeftVar, noChangeList=[]):
    varTypes = info['varTypes']
    varDeps = varInfo.getVarDepsNoExponents()
    new_node2 = BinaryNode.copy(node)
    # 1. assignVar
    if changeLeftVar: new_assignVar = assignNewVar(assignVar, G1Prefix) # new_assignVar = assignVar + G1Prefix
    else: new_assignVar = str(assignVar)
    sdl.ASTVisitor( SubstituteVar(assignVar, new_assignVar) ).preorder( new_node2 )
    info['generatorMapG1'][assignVar] = new_assignVar
    #info['usedVars'] = info['usedVars'].union([new_assignVar])
    # see if it is initCall:
    if varInfo.getInitCall() or varInfo.getHasRandomness():
        # make change and return here
        sdl.ASTVisitor( SubstituteVar('', str(types.G1), initChange=True) ).preorder( new_node2 )
        info['newTypes'][new_assignVar] = types.G1
        return new_node2

    info['myAsymSDL'].recordUsedVar(varDeps)                
    
    prunedList = prune(noChangeList)
    newVarDeps = set(varDeps).difference(prunedList, Gtypes)
    for i in newVarDeps:
        new_i = i + G1Prefix
        updatedRefAlready = False
        if i.find(sdl.LIST_INDEX_SYMBOL) != -1: 
            newRef = handleListTypeRefs(varTypes, i, info, changeLeftVar, types.G1)
            if newRef == False: print("ERROR in handleListTypeRefs"); return
            elif newRef == i: continue # meaning no change in reference 
            else: new_i = newRef; updatedRefAlready = True
        
        if not updatedRefAlready:
            v = varTypes.get(i)
            if v != None: v = v.getType()
            else: print("FIX: no type for G1: ", i); sys.exit(0)
            # prune (as a second effort)
            if v in [types.ZR, types.listZR, types.Int, types.listInt, types.Str, types.listStr]: 
                continue

        sdl.ASTVisitor( SubstituteVar(i, new_i) ).preorder( new_node2 )
        info['generatorMapG1'][i] = new_i
        info['usedVars'] = info['usedVars'].union([new_i])
        info['myAsymSDL'].recordUsedVar([new_i])
        info['newTypes'][new_i] = types.G1
    #print("\n\tChanged: ", new_node2, end="")
    return new_node2

def updateAllForG2(node, assignVar, varInfo, info, changeLeftVar, noChangeList=[]):
    varTypes = info.get('varTypes')  
    varDeps = varInfo.getVarDepsNoExponents()  
    new_node2 = BinaryNode.copy(node)
    # 1. assignVar
    if changeLeftVar: new_assignVar = assignNewVar(assignVar, G2Prefix) # new_assignVar = assignVar + G2Prefix
    else: new_assignVar = str(assignVar)
    sdl.ASTVisitor( SubstituteVar(assignVar, new_assignVar) ).preorder( new_node2 )
    info['generatorMapG2'][assignVar] = new_assignVar    
    #info['usedVars'] = info['usedVars'].union([new_assignVar])    
    # see if it is initCall:
    if varInfo.getInitCall() or varInfo.getHasRandomness():
        # make change and return here
        sdl.ASTVisitor( SubstituteVar('', str(types.G2), initChange=True) ).preorder( new_node2 )
        info['newTypes'][new_assignVar] = types.G2        
        return new_node2
    
    info['myAsymSDL'].recordUsedVar(varDeps)                
        
    prunedList = prune(noChangeList)
    newVarDeps = set(varDeps).difference(prunedList, Gtypes)
    for i in newVarDeps:
        new_i = i + G2Prefix
        updatedRefAlready = False
        if i.find(sdl.LIST_INDEX_SYMBOL) != -1: # detect references such as <var>#<int> which are treated like indirect pointers
            newRef = handleListTypeRefs(varTypes, i, info, changeLeftVar, types.G2)
            if newRef == False: print("ERROR in handleListTypeRefs"); return
            elif newRef == i: continue # meaning no change in reference
            else: new_i = newRef; updatedRefAlready = True
            
        if not updatedRefAlready:   
            v = varTypes.get(i)
            if v != None: v = v.getType()
            else: print("FIX: no type for G2: ", i); sys.exit(0)            
            # prune (as a second effort)
            if v in [types.ZR, types.listZR, types.Int, types.listInt, types.Str, types.listStr]: 
                continue
        sdl.ASTVisitor( SubstituteVar(i, new_i) ).preorder( new_node2 )
        info['generatorMapG2'][i] = new_i
        info['usedVars'] = info['usedVars'].union([new_i])
        info['myAsymSDL'].recordUsedVar([new_i])
        info['newTypes'][new_i] = types.G2        
    #print("\n\tChanged: ", new_node2, end="")
    return new_node2

def updateForLists(varInfo, assignVar, info):
    global oldListTypeRefs, newListTypeRefs
    newList = []
    inBoth = info['both']
    orig_list = varInfo.getAssignNode().getRight().listNodes
    oldListTypeRefs[ str(assignVar) ] = list(orig_list) # record the original list

    for i in orig_list:
        if i in inBoth or assignVarIsGenerator(i, info):
            newList.extend([i + G1Prefix, i + G2Prefix])
        else:
            newList.append(i)
    new_node = BinaryNode.copy(varInfo.getAssignNode())
    new_node.right.listNodes = newList
    newListTypeRefs[ str(assignVar) ] = list(newList) # record the updates
    return new_node

def updateForPairing(varInfo, info, noChangeList):
    node = BinaryNode.copy(varInfo.getAssignNode())
    tme = TestForMultipleEq()
    sdl.ASTVisitor(tme).preorder(node)
    if tme.multiple:
        gen = GetEquqlityNodes()
        sdl.ASTVisitor( gen ).preorder(node)
        listOfNodes = gen.getNodes()
        for i in listOfNodes:
            tmp = applyPairingUpdate(info, i, noChangeList) # pass reference to eq_tst nodes
        return node
    return applyPairingUpdate(info, node, noChangeList)

def applyPairingUpdate(info, node, noChangeList):
    sp = SubstitutePairings(info, noChangeList)
    sdl.ASTVisitor( sp ).preorder( node )
    info['usedVars'] = info['usedVars'].union(sp.getUsedGens())
    info['myAsymSDL'].recordUsedVar(GetAttributeVars(node)) # sp.getUsedVars())    
    if info['verbose']: print("\n\t Pre techs: ", node, end="")
    sdl.ASTVisitor( MaintainOrder(info) ).preorder( node )    
    # combining pairing logic a bit.
    while True:
        tech6 = PairInstanceFinderImproved()
        sdl.ASTVisitor(tech6).preorder( node )
        if tech6.testForApplication(): 
            tech6.makeSubstitution( node )
        else:
            break

    if info['verbose']: print("\n\t Changed: ", node)
    return node

def print_sdl(verbose, *args):
    if verbose:
        print("<===== new SDL =====>")    
        for block in args:
            for i in block:
                print(i)
            print("\n\n")
        print("<===== new SDL =====>")
    return
    

def writeConfig(filename, *args):
    f = open(filename, 'w')
    for block in args:
        for line in block:
            if type(line) == list:
                for subLine in line:
                    f.write(str(subLine) + "\n")
                if len(line) > 0: f.write('\n')
            else:
                f.write(str(line) + "\n")
        if len(block) > 0: f.write('\n') # in case block = [] (empty)
    f.close()
    return
    
