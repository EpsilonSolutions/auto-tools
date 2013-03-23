# batch parser provides majority of the functionality for parsing bv files and the mechanics of the 
# techniques for generating an optimized batch equation (tech 2, 3, 4 and simplifying products, etc.)
# 

from pyparsing import *
from SDLang import *
from VarInfo import *
from VarType import *
from ForLoop import *
from IfElseBranch import *
import string,sys

objStack = []
currentFuncName = NONE_FUNC_NAME
ASSIGN_KEYWORDS = ['input', 'output']
astNodes = []
assignInfo = {}
varNamesToFuncs_All = {}
varNamesToFuncs_Assign = {}
forLoops = {}
ifElseBranches = {}
varDepList = {}
varDepListNoExponents = {}
varInfList = {}
varInfListNoExponents = {}
varsThatProtectM = {}
varTypes = {}
algebraicSetting = None
startLineNo_ForLoop = None
startLineNo_IfBranch = None
startLineNo_ElseBranch = None
startLineNos_Functions = {}
endLineNos_Functions = {}
functionNameOrder = []
inputOutputVars = []
linesOfCode = None
getVarDepInfListsCalled = getVarsThatProtectMCalled = False
TYPE, CONST, PRECOMP, OTHER, TRANSFORM = 'types', 'constant', 'precompute', 'other', 'transform'
ARBITRARY_FUNC = 'func:'
MESSAGE, SIGNATURE, PUBLIC, LATEX, SETTING = 'message','signature', 'public', 'latex', 'setting'
# qualifier (means only one instance of that particular keyword exists)
SAME, DIFF = 'one', 'many'
publicVarNames = []
secretVarNames = []

builtInTypes = {}
builtInTypes["DeriveKey"] = types.str
builtInTypes["SymEnc"] = types.str
builtInTypes["SymDec"] = types.str
builtInTypes["strToId"] = types.listZR
builtInTypes["createPolicy"] = types.object
builtInTypes["getAttributeList"] = types.listStr
builtInTypes["calculateSharesDict"] = types.symmap
builtInTypes["calculateSharesList"] = types.list
builtInTypes["prune"] = types.list
builtInTypes["getCoefficients"] = types.symmap

def createNode(s, loc, toks):
    print('createNode => ', toks)
    return BinaryNode(toks[0])

# convert 'attr < value' to a binary tree based on 'or' and 'and'
def parseNumConditional(s, loc, toks):
    print("print: %s" % toks)
    return BinaryNode(toks[0])

def debugParser(s, loc, toks):
    print("debug info: %s" % toks)
    return toks
        
def pushFirst( s, loc, toks ):
    if debug >= levels.some:
       print("Pushing first =>", toks[0])
    objStack.append( toks[0] )

def pushError(s, loc, toks ):
    if debug >= levels.some: print("Pushing all => ", toks)
    if len(toks) == 3:
        objStack.append( toks[1] )
        objStack.append( toks[0] )
    else:
        print("'error()' token not well-formed.")

def checkCount(s, loc, toks):
    cnt = len(toks)
    objStack.append( str(cnt) )

def pushFunc(s, loc, toks):
    if debug >= levels.some: print("found a function: ", toks[0])
    objStack.append( FUNC_SYMBOL + toks[0] )

# Implements language parser for our signature descriptive language (SDL) and returns
# a binary tree (AST) representation of valid SDL statements.
class SDLParser:
    def __init__(self, verbose=False):
        self.finalPol = self.getBNF()
        self.verbose = verbose

    def getBNF(self):
        AndOp = Literal("and")
        lpar = Literal("(").suppress() | Literal("{").suppress()
        rpar = Literal(")").suppress() | Literal("}").suppress()
        rcurly = Literal("}").suppress()
        
        Comment = Literal("#") + restOfLine
        MulOp = Literal("*")
        DivOp = Literal("/")
        Concat = Literal("|")
        ExpOp = Literal("^")
        AddOp = Literal("+")
        SubOp = Literal("-")        
        Equality = Literal("==") # | Word("<>", max=1)
        Assignment =  Literal(":=")
        Pairing = Literal("e(") # Pairing token
        Hash = Literal("H(") # TODO: provide a way to specify arbitrary func. calls
        Random = Literal("random(")
        Prod = Literal("prod{") # dot product token
        For = Literal("for{")
        ForAll = Literal("forall{")
        Sum = Literal("sum{")
        ProdOf = Literal("on")
        ForDo = Literal("do") # for{x,y} do y
        SumOf = Literal("of")
        IfCond = Literal("if {") | Literal("elseif {")
        ElseCond = Literal("else") 
        List  = Literal("list{") | Literal("expand{") | Literal("symmap{") # represents a list
        MultiLine = Literal(";") + Optional(Literal("\\n").suppress())
        funcName = Word(alphanums + '_')
        blockName = Word(alphanums + '_:')
        BeginAndEndBlock = CaselessLiteral(START_TOKEN) | CaselessLiteral(END_TOKEN)
        BlockSep   = Literal(BLOCK_SEP)
        ErrorName  = Literal("error(") 

        # captures the binary operators allowed (and, ^, *, /, +, |, ==)        
        BinOp = MultiLine | AndOp | ExpOp | MulOp | DivOp | SubOp | AddOp | Concat | Equality
        # captures order of parsing token operators
        Token = Equality | AndOp | ExpOp | MulOp | DivOp | SubOp | AddOp | ForDo | ProdOf | SumOf | IfCond | Concat | Assignment | MultiLine
        Operator = Token 
        #Operator = OperatorAND | OperatorOR | Token

        # describes an individual leaf node
        leafNode = Word(alphanums + '_-#\\?').setParseAction( createNode )
        expr = Forward()
        term = Forward()
        factor = Forward()
        atom = (BeginAndEndBlock + BlockSep + blockName.setParseAction( pushFirst ) ).setParseAction( pushFirst ) | \
               (ErrorName + sglQuotedString + ')').setParseAction( pushError ) | \
               (Hash + expr + ',' + expr + rpar).setParseAction( pushFirst ) | \
               (Pairing + expr + ',' + expr + rpar).setParseAction( pushFirst ) | \
               (Prod + expr + ',' + expr + rcurly).setParseAction( pushFirst ) | \
               (ForAll + expr + rcurly).setParseAction( pushFirst ) | \
               (For + expr + ',' + expr + rcurly).setParseAction( pushFirst ) | \
               (Sum + expr + ',' + expr + rcurly).setParseAction( pushFirst ) | \
               (Random + leafNode + rpar).setParseAction( pushFirst ) | \
               (List + delimitedList(leafNode).setParseAction( checkCount ) + rcurly).setParseAction( pushFirst ) | \
               (funcName + '(' + delimitedList(leafNode).setParseAction( checkCount ) + ')').setParseAction( pushFunc ) | \
               (IfCond + expr + rpar).setParseAction( pushFirst ) | \
               (ElseCond ).setParseAction( pushFirst ) | \
               lpar + expr + rpar | (leafNode).setParseAction( pushFirst )

        # Represents the order of operations (^, *, |, ==)
        # Place more value on atom [ ^ factor}, so gets pushed on the stack before atom [ = factor], right?
        # In other words, adds order of precedence to how we parse the string. This means we are parsing from right
        # to left. a^b has precedence over b = c essentially
        #factor << atom + ZeroOrMore( ( ExpOp + factor ).setParseAction( pushFirst ) )
        factor << atom + ZeroOrMore( ( BinOp + factor ).setParseAction( pushFirst ) )
        
        term = atom + ZeroOrMore((Operator + factor).setParseAction( pushFirst ))
        # define placeholder set earlier with a 'term' + Operator + another term, where there can be
        # more than zero or more of the latter. Once we find a term, we first push that into
        # the stack, then if ther's an operand + term, then we first push the term, then the Operator.
        # so on and so forth (follows post fix notation).
        expr << term + ZeroOrMore((Operator + term).setParseAction( pushFirst ))
        # final bnf object
        finalPol = expr#.setParseAction( debugParser )
        finalPol.ignore( Comment )
        return finalPol
    
    # method for evaluating stack assumes operators have two operands and pops them accordingly
    def evalStack(self, stack, line_number):
        global currentFuncName, forLoops, startLineNo_ForLoop, startLineNos_Functions
        global endLineNos_Functions, ifElseBranches, startLineNo_IfBranch, startLineNo_ElseBranch
        global functionNameOrder

        op = stack.pop()
        if debug >= levels.some:
            print("op: %s" % op)
        if op in ["+","-","*", "/","^", ":=", "==", "e(", "for{", "do","prod{", "on", "sum{", "of", "|", "and", ";"]:
            op2 = self.evalStack(stack, line_number)
            op1 = self.evalStack(stack, line_number)
            return createTree(op, op1, op2)
        elif op in ["H("]:
            op2 = self.evalStack(stack, line_number)
            op1 = self.evalStack(stack, line_number)
            return createTree(op, op1, op2)
        elif op in ["list{", "expand{", "symmap{"]:
            ops = []
            cnt = self.evalStack(stack, line_number)
#            print("count: ", cnt)
            for i in range(int(cnt)):
                ops.append(self.evalStack(stack, line_number))
            newList = createTree(op, None, None)
            ops.reverse()
            newList.listNodes = list(ops)
            return newList
        elif op in ["random(", "forall{"]: # one argument
            op1 = self.evalStack(stack, line_number)
            return createTree(op, op1, None)
        elif op in ["if {", "elseif {"]:
            op1 = self.evalStack(stack, line_number)
            return createTree(op, op1, None)
        elif op in ["else"]:
            startLineNo_ElseBranch = line_number
            lenIfElseBranches = len(ifElseBranches[currentFuncName])
            ifElseBranches[currentFuncName][lenIfElseBranches - 1].appendToElseLineNos(int(line_number))
            return createTree(op, None, None)
        elif op in ["error("]:
            op1 = self.evalStack(stack, line_number)
            return createTree(op, None, None, op1)
        elif FUNC_SYMBOL in op:
            ops = []
            cnt = self.evalStack(stack, line_number)
            if self.verbose: print("func name: ", op.split(FUNC_SYMBOL)[1])
            for i in range(int(cnt)):
                ops.append(self.evalStack(stack, line_number))
            newList = createTree(op, None, None, op.split(FUNC_SYMBOL)[1])
            ops.reverse()
            newList.listNodes = list(ops)
            return newList
        elif op in [START_TOKEN, END_TOKEN]: # start and end block lines
            op1 = self.evalStack(stack, line_number)
            if (op1.startswith(DECL_FUNC_HEADER) == True):
                if (op == START_TOKEN):
                    currentFuncName = op1[len(DECL_FUNC_HEADER):len(op1)]
                    if (currentFuncName in startLineNos_Functions):
                        sys.exit("SDLParser.py found multiple START_TOKEN declarations for the same function name.")
                    startLineNos_Functions[currentFuncName] = line_number
                    functionNameOrder.append(currentFuncName)
                elif (op == END_TOKEN):
                    if (currentFuncName in endLineNos_Functions):
                        sys.exit("SDLParser.py found multiple END_TOKEN declarations for the same function.")
                    endLineNos_Functions[currentFuncName] = line_number
                    currentFuncName = NONE_FUNC_NAME
            elif (op1 == TYPES_HEADER):
                if (op == START_TOKEN):
                    currentFuncName = TYPES_HEADER
                    if (currentFuncName in startLineNos_Functions):
                        sys.exit("SDLParser.py found multiple TYPES_HEADER start token declarations.")
                    startLineNos_Functions[currentFuncName] = line_number
                elif (op == END_TOKEN):
                    if (currentFuncName in endLineNos_Functions):
                        sys.exit("SDLParser.py found multiple TYPES_HEADER end token declarations.")
                    endLineNos_Functions[currentFuncName] = line_number
                    currentFuncName = NONE_FUNC_NAME
            elif (op1 == FOR_LOOP_HEADER):
                if (op == START_TOKEN):
                    startLineNo_ForLoop = line_number
                elif (op == END_TOKEN):
                    startLineNo_ForLoop = None
                    lenForLoops = len(forLoops[currentFuncName])
                    if (forLoops[currentFuncName][lenForLoops - 1].getEndLineNo() != None):
                        sys.exit("Ending line number of one of the for loops was set prematurely.")
                    forLoops[currentFuncName][lenForLoops - 1].setEndLineNo(int(line_number))
            elif (op1 == IF_BRANCH_HEADER):
                if (op == START_TOKEN):
                    startLineNo_IfBranch = line_number
                elif (op == END_TOKEN):
                    startLineNo_IfBranch = None
                    lenIfElseBranches = len(ifElseBranches[currentFuncName])
                    if (ifElseBranches[currentFuncName][lenIfElseBranches - 1].getEndLineNo() != None):
                        sys.exit("Ending line number of one of the if-else branches was set prematurely.")
                    ifElseBranches[currentFuncName][lenIfElseBranches - 1].setEndLineNo(int(line_number))
            return createTree(op, op1, None)
        else:
            # Node value
            return op
    
    # main loop for parser. 1) declare new stack, then parse the string (using defined BNF) to extract all
    # the tokens from the string (not used for anything). 3) evaluate the stack which is in a post
    # fix format so that we can pop an OR, AND, ^ or = nodes then pull 2 subsequent variables off the stack. Then,
    # recursively evaluate those variables whether they are internal nodes or leaf nodes, etc.
    def parse(self, line, line_number=0):
        # use lineCtr to track line of code.
        global objStack
        del objStack[:]
        try:
            tokens = self.finalPol.parseString(line)
            if debug >= levels.some:
                print("stack =>", objStack)
            object = self.evalStack(objStack, line_number)
            if len(objStack) > 0 or object == False:
                raise TypeError("Invalid SDL Expression!")
            return object
        except:
            print("Invalid SDL Expression found at line #%d: '%s'" % (line_number, line))
            exit(-1)
        if len(objStack) > 0:
            raise TypeError("Invalid SDL Expression!")
        return None

# valid keywords
signer_mode  = Enum('single', 'multi', 'ring')
LINE_DELIM, COMMENT = ';', '#'


def clean(arr):
    return [i.strip() for i in arr]

def handle(lines, target):
    if target == LATEX:
        code = {}; EQ = ':='
        for line in lines:
            line = line.rstrip()
            if line.find(EQ) != -1:
                x = line.split(EQ)
                lhs, rhs = x[0].strip(), x[1].strip()
                code [ lhs ] = rhs
        print("latex =>", code)
        return code
    
    # parse as usual
    parser = BatchParser()
    if type(lines) != list:
        return parser.parse(lines)

    if (target in [CONST, TRANSFORM, PUBLIC, SIGNATURE, MESSAGE]) or (ARBITRARY_FUNC in target):
        # parse differently 'a, b, etc.\n'
        _ast = []
        for line in lines:
            l = line.split(',')
            _ast = [i.strip() for i in l]
        print(target, " =>", _ast)
        return _ast
    elif target == TYPE:
        _ast = {}
        for line in lines:
            ast_node = parser.parse(line)
            # make sure it's an assignment node
            # otherwise, ignore the node
            if ast_node.type == ops.EQ:
                left = str(ast_node.left)
                right = str(ast_node.right)
                _ast[ left ] = right
        print(target, " =>", _ast)
        return _ast
    elif target == PRECOMP:
        indiv_ast = {}
        batch_ast = {}
        for line in lines:
            ast_node = parser.parse(line)
            # make sure it's an assignment node
            # otherwise, ignore the node
            if ast_node.type == ops.EQ:
                left = ast_node.left
                right = ast_node.right
                indiv_ast[ left ] = right
                batch_ast[ BinaryNode.copy(left) ] = BinaryNode.copy(right)
        #print(target, " =>", indiv_ast)
        return (indiv_ast, batch_ast)
    return None

debugs = levels.none

def parseFile(filename):
    fd = open(filename, 'r')
    ast = {TYPE: None, CONST: None, PRECOMP: None, TRANSFORM: None, 
           MESSAGE: None, SIGNATURE: None, PUBLIC: None, LATEX: None, 
           OTHER: [] }
    AcceptedEnclosures = [TYPE, CONST, PRECOMP, TRANSFORM, MESSAGE, SIGNATURE, PUBLIC, LATEX]
    # parser = BatchParser()
    code = fd.readlines(); i = 1
    inStruct = (False, None)
    queue = []
    for line in code:
        if len(line.strip()) == 0 or line[0] == COMMENT:
            continue
        elif line.find(BLOCK_SEP) != -1: # parse differently
            token = clean(line.split(BLOCK_SEP))
            if token[0] == START_TOKEN and (token[1] in AcceptedEnclosures or ARBITRARY_FUNC in token[1]):
                inStruct = (True, token[1])
                if debugs == levels.all: print("Got a section!!!")
                continue
            elif inStruct[0]:
                # continue until we reach an end token, then
                # test if end token matches the start token, if so can handle queue 
                key = token[1]
                if token[0] == END_TOKEN and inStruct[1] == key:
                    ast[ key ] = handle(queue, key)
                    if debugs == levels.all:
                        print("section =>", key)
                        # print("queue =>", queue)
                        # print("result =>", ast[key])
                    # check for global syntax error and exit
                    queue = [] # tmp remove everything
                    inStruct = (False, None)  
            else:
                print("Syntax Error while parsing section: ", line)

        else: # if not, keep going and assume that we can safely add lines to queue
            if inStruct[0]:
                if line.find(LINE_DELIM) != -1: # if a ';' exists in string then we can probably split into two
                    queue.extend(line.split(LINE_DELIM))
                else:
                    queue.append(line)
            elif len(line.strip()) == 0 or line[0] == COMMENT:
                if debugs == levels.all:
                    print(line)
                continue
            else:
                if debugs == levels.all: 
                    print("Not in a type enclosure: ", line)
                result = handle(line, None)
                #print("result =>", result)
                #print("type =>", type(result))
                ast[ OTHER ].append(result)                
                
    fd.close()
    return ast

def getEndLineNoOfForLoop(funcName, lineNo):
    if (funcName not in forLoops):
        sys.exit("getEndLineNoOfForLoop in SDLParser.py:  function name parameter passed in is not in forLoops.")

    returnLineNo = 0

    for currentForLoopObj in forLoops[funcName]:
        startingLineNo = currentForLoopObj.getStartLineNo()
        endingLineNo = currentForLoopObj.getEndLineNo()
        if ( (startingLineNo > lineNo) or (endingLineNo < lineNo) ):
            continue

        if (returnLineNo != 0):
            sys.exit("getEndLineNoOfForLoop in SDLParser.py:  found multiple for loops that contain the line number parameter passed in.")

        returnLineNo = endingLineNo

    return returnLineNo

def getVarTypeFromVarName(varName, functionNameArg_TieBreaker, failSilently=False, forListMember=False):
    if ( (type(varName) is not str) or (len(varName) == 0) ):
        if (failSilently == True):
            return types.NO_TYPE
        else:
            sys.exit("getVarTypeFromVarName in SDLParser.py:  received invalid varName parameter.")

    retVarType = types.NO_TYPE
    retFunctionName = None

    outputKeywordDisagreement = False

    for funcName in varTypes:
        for currentVarName in varTypes[funcName]:
            if (currentVarName != varName):
                continue

            currentVarType = varTypes[funcName][currentVarName].getType()
            if (retVarType == types.NO_TYPE):
                retVarType = currentVarType
                retFunctionName = funcName
                continue
            if (funcName == TYPES_HEADER):
                continue
            if (retFunctionName == TYPES_HEADER):
                retVarType = currentVarType
                retFunctionName = funcName
                continue
            if (currentVarType == retVarType):
                continue
            if (varName != outputKeyword):
                if (failSilently == True):
                    return types.NO_TYPE
                else:
                    sys.exit("getVarTypeFromVarName in SDLParser.py:  found mismatching variable type information for variable name passed in.")
            if (retFunctionName == functionNameArg_TieBreaker):
                continue
            if (funcName == functionNameArg_TieBreaker):
                retVarType = currentVarType
                retFunctionName = funcName
                continue
            #sys.exit("getVarTypeFromVarName in SDLParser.py:  found mismatching types for output keyword, but neither of the function names recorded for each instance matches the function name tiebreaker passed in.")
            outputKeywordDisagreement = True
            continue

    if (outputKeywordDisagreement == True):
        if (retFunctionName != functionNameArg_TieBreaker):
            if (failSilently == True):
                return types.NO_TYPE
            else:
                sys.exit("getVarTypeFromVarName in SDLParser.py:  there was a disagreement on the type of the output keyword, and the function chosen was not the same as the tiebreaker passed in.")

    if (forListMember == True):
        if ( (retVarType == types.listG1) or (retVarType == types.G1) ):
            return types.G1
        if ( (retVarType == types.listG2) or (retVarType == types.G2) ):
            return types.G2
        if ( (retVarType == types.listGT) or (retVarType == types.GT) ):
            return types.GT
        if ( (retVarType == types.listZR) or (retVarType == types.ZR) ):
            return types.ZR
        if ( (retVarType == types.listStr) or (retVarType == types.str) ):
            return types.str
        return types.NO_TYPE

    if ( (retVarType != types.NO_TYPE) or (varName.count(LIST_INDEX_SYMBOL) != 1) ):
        return retVarType

    varNameSplit = varName.split(LIST_INDEX_SYMBOL)
    return getVarTypeFromVarName(varNameSplit[0], functionNameArg_TieBreaker, False, True)

def setVarTypeObjForTypedList(varTypeObj, listType):
    if (listType == "G1"):
        varTypeObj.setType(types.listG1)
    elif (listType == "G2"):
        varTypeObj.setType(types.listG2)
    elif (listType == "GT"):
        varTypeObj.setType(types.listGT)
    elif (listType == "ZR"):
        varTypeObj.setType(types.listZR)
    else:
        sys.exit("setVarTypeObjForTypedList in SDLParser.py:  listType passed in is not one of the supported types.")

def setVarTypeObjForList(varTypeObj, typeNode):
    if (type(typeNode).__name__ != BINARY_NODE_CLASS_NAME):
        sys.exit("setVarTypeObjForList in SDLParser.py received as input for typeNode a parameter that is not a Binary Node.")

    if (typeNode.type != ops.LIST):
        sys.exit("setVarTypeObjForList in SDLParser.py:  typeNode parameter passed in is not of type ops.LIST.")

    if ( (len(typeNode.listNodes) == 1) and (isValidType(typeNode.listNodes[0]) == True) ):
        setVarTypeObjForTypedList(varTypeObj, typeNode.listNodes[0])
    else:
        varTypeObj.setType(types.list)
        addListNodesToList(typeNode, varTypeObj.getListNodesList())

def updateVarTypes(node, i, newType=types.NO_TYPE):
    global varTypes, assignInfo

    if ( (type(newType).__name__ == ENUM_VALUE_CLASS_NAME) and (newType == types.NO_TYPE) and (currentFuncName != TYPES_HEADER) ):
        sys.exit("updateVarTypes in SDLParser.py received newType of types.NO_TYPE when currentFuncName was not TYPES_HEADER.")

    if ( (type(newType).__name__ == ENUM_VALUE_CLASS_NAME) and (newType != types.NO_TYPE) and (currentFuncName == TYPES_HEADER) ):
        sys.exit("updateVarTypes in SDLParser.py received newType unequal to types.NO_TYPE when currentFuncName was TYPES_HEADER.")

    varName = getFullVarName(node.left, True)
    if (varName in varTypes[currentFuncName]):
        sys.exit("updateVarTypes in SDLParser.py received as input a node whose full variable name is already in varTypes[currentFuncName].")

    varTypeObj = VarType()
    varTypeObj.setLineNo(i)

    if (type(newType).__name__ == BINARY_NODE_CLASS_NAME):
        if (newType.type != ops.LIST):
            sys.exit("updateVarTypes in SDLParser.py received newType that is a Binary Node, but not of type ops.LIST.")
        setVarTypeObjForList(varTypeObj, newType)
        varTypes[currentFuncName][varName] = varTypeObj
        return

    if (type(newType).__name__ != ENUM_VALUE_CLASS_NAME):
        sys.exit("updateVarTypes in SDLParser.py received newType that does not have type Binary Node or Enum Value.")

    if (newType != types.NO_TYPE):
        if (isValidType(newType) == False):
            sys.exit("updateVarTypes in SDLParser.py received as input a new type that is not one of the supported types.")

        varTypeObj.setType(newType)
        varTypes[currentFuncName][varName] = varTypeObj
        return

    varInfoObj = VarInfo()
    varInfoObj.setIsTypeEntryOnly(True)
    varInfoObj.setLineNo(i)
    if (varName in assignInfo[currentFuncName]):
        sys.exit("In updateVarTypes in SDLParser.py, found duplicate entries for variable name in TYPES_HEADER function.")

    assignInfo[currentFuncName][varName] = varInfoObj

    typeNode = node.right

    if (typeNode.type == ops.TYPE):
        varTypeObj.setType(getFullVarName(typeNode, False))
        varTypes[currentFuncName][varName] = varTypeObj
        return

    if (typeNode.type == ops.LIST):
        setVarTypeObjForList(varTypeObj, typeNode)
        varTypes[currentFuncName][varName] = varTypeObj
        return

    sys.exit("updateVarTypes in SDLParser.py was passed a node that it is not currently capable of processing.")

def checkPairingInputTypes_Symmetric(leftType, rightType):
    if ( (leftType != types.G1) and (leftType != types.G2) ):
        sys.exit("Problem with the left side of one of the pairings in the symmetric setting.")

    if ( (rightType != types.G1) and (rightType != types.G2) ):
        sys.exit("Problem with the right side of one of the pairings in the symmetric setting.")

def checkPairingInputTypes_Asymmetric(leftType, rightType):
    if (leftType != types.G1):
        sys.exit("One of the pairings in the asymmetric setting does not have a left side of type " + str(types.G1))

    if (rightType != types.G2):
        sys.exit("One of the pairings in the asymmetric setting does not have a right side of type " + str(types.G2))

def checkPairingInputTypes(node):
    if (node.type != ops.PAIR):
        sys.exit("checkPairingInputTypes in SDLParser was passed a node that is not of type " + str(ops.PAIR))

    leftType = getVarTypeInfoRecursive(node.left)
    rightType = getVarTypeInfoRecursive(node.right)

    if (algebraicSetting == SYMMETRIC_SETTING):
        checkPairingInputTypes_Symmetric(leftType, rightType)
    elif (algebraicSetting == ASYMMETRIC_SETTING):
        checkPairingInputTypes_Asymmetric(leftType, rightType)
    else:
        sys.exit("Algebraic setting is set to unsupported value (found in checkPairingInputTypes in SDLParser).")

'''
def getVarNameEntryFromAssignInfo(varName):
    retFuncName = None
    retVarInfoObj = None
    currentRetVarInfoObjIsExpandNode = False

    for funcName in assignInfo:
        for currentVarName in assignInfo[funcName]:
            if (currentVarName == varName):
                if ( (retVarInfoObj != None) or (retFuncName != None) ):
                    if (funcName != TYPES_HEADER):
                        if ( (assignInfo[funcName][currentVarName].getIsExpandNode() == True) and (currentRetVarInfoObjIsExpandNode == True) ):
                            pass
                        elif ( (assignInfo[funcName][currentVarName].getIsExpandNode() == True) and (currentRetVarInfoObjIsExpandNode == False) ):
                            pass
                        elif ( (assignInfo[funcName][currentVarName].getIsExpandNode() == False) and (currentRetVarInfoObjIsExpandNode == True) ):
                            retFuncName = funcName
                            retVarInfoObj = assignInfo[funcName][currentVarName]
                            currentRetVarInfoObjIsExpandNode = False
                        elif ( (assignInfo[funcName][currentVarName].getIsExpandNode() == False) and (currentRetVarInfoObjIsExpandNode == False) ):
                            retFuncName = funcName
                            retVarInfoObj = assignInfo[funcName][currentVarName]
                            currentRetVarInfoObjIsExpandNode = False
                    elif (retFuncName != TYPES_HEADER):
                        pass
                    elif ( (retVarInfoObj.hasBeenSet() == False) and (assignInfo[funcName][currentVarName].hasBeenSet() == True) ):
                        retFuncName = funcName
                        retVarInfoObj = assignInfo[funcName][currentVarName]
                        if (retVarInfoObj.getIsExpandNode() == True):
                            currentRetVarInfoObjIsExpandNode = True
                        else:
                            currentRetVarInfoObjIsExpandNode = False
                    elif ( (retVarInfoObj.hasBeenSet() == True) and (assignInfo[funcName][currentVarName].hasBeenSet() == False) ):
                        pass
                    else:
                        sys.exit("getVarNameEntryFromAssignInfo in SDLParser.py found multiple assignments of the same variable is assignInfo in which neither of the functions is " + str(TYPES_HEADER))
                else:
                    retFuncName = funcName
                    retVarInfoObj = assignInfo[funcName][currentVarName]
                    if (retVarInfoObj.getIsExpandNode() == True):
                        currentRetVarInfoObjIsExpandNode = True
                    else:
                        currentRetVarInfoObjIsExpandNode = False

    #if ( (retVarInfoObj == None) or (retFuncName == None) ):
        #sys.exit("getVarNameEntryFromAssignInfo in SDLParser.py could not locate entry in assignInfo of the name passed in.")

    return (retFuncName, retVarInfoObj)
'''

'''
def getNextListName(origListName, index):
    (listFuncNameInAssignInfo, listEntryInAssignInfo) = getVarNameEntryFromAssignInfo(assignInfo, origListName)
    if ( (listFuncNameInAssignInfo == None) or (listEntryInAssignInfo == None) ):
        sys.exit("Problem with return values from getVarNameEntryFromAssignInfo in getNextListName in SDLParser.py.")
    if ( (listEntryInAssignInfo.getIsList() == False) or (len(listEntryInAssignInfo.getListNodesList()) == 0) ):
        #sys.exit("Problem with list obtained from assignInfo in getNextListName in SDLParser.")
        return (None, None)

    listNodesList = listEntryInAssignInfo.getListNodesList()
    index = int(index)
    lenListNodesList = len(listNodesList)
    if (index >= lenListNodesList):
        sys.exit("getNextListName in SDLParser.py found that the index submitted as input is greater than the length of the listNodesList returned from getVarNameEntryFromAssignInfo.")

    return (listFuncNameInAssignInfo, listNodesList[index])

def hasDefinedListMembers(listName):
    (funcName, varInfoObj) = getVarNameEntryFromAssignInfo(listName)
    if ( (varInfoObj.getIsList() == True) and (len(varInfoObj.getListNodesList()) > 0) ):
        return True

    return False

def getVarNameFromListIndices(node, failSilently=False):
    if (node.type != ops.ATTR):
        if (failSilently == True):
            return (None, None)
        else:
            sys.exit("Node passed to getVarNameFromListIndex in SDLParser is not of type " + str(ops.ATTR))

    nodeAttrFullName = getFullVarName(node, False)

    if (nodeAttrFullName.find(LIST_INDEX_SYMBOL) == -1):
        if (failSilently == True):
            return (None, None)
        else:
            sys.exit("Node passed to getVarNameFromListIndex is not a reference to an index in a list.")

    nodeName = nodeAttrFullName
    nodeNameSplit = nodeName.split(LIST_INDEX_SYMBOL)
    currentListName = nodeNameSplit[0]
    nodeNameSplit.remove(currentListName)
    lenNodeNameSplit = len(nodeNameSplit)
    counter_nodeNameSplit = 0

    while (counter_nodeNameSplit < lenNodeNameSplit):
        listIndex = nodeNameSplit[counter_nodeNameSplit]
        if (listIndex.isdigit() == False):
            if (counter_nodeNameSplit == (lenNodeNameSplit - 1)):
                (tempFuncName, tempListName) = getVarNameEntryFromAssignInfo(assignInfo, currentListName)
                return (tempFuncName, currentListName)
            definedListMembers = hasDefinedListMembers(currentListName)
            if ( (definedListMembers == True) and (nodeNameSplit[counter_nodeNameSplit + 1].isdigit() == True) ):
                (currentFuncName, currentListName) = getNextListName(currentListName, nodeNameSplit[counter_nodeNameSplit + 1])
                if ( (currentFuncName == None) and (currentListName == None) ):
                    break
                counter_nodeNameSplit += 2
                continue
            else:
                (tempFuncName, tempListName) = getVarNameEntryFromAssignInfo(currentListName)
                return (tempFuncName, currentListName)
        (currentFuncName, currentListName) = getNextListName(currentListName, listIndex)
        if ( (currentFuncName == None) and (currentListName == None) ):
            break
        counter_nodeNameSplit += 1

    return (currentFuncName, currentListName)
'''

def checkForListWithOneNumIndex(nodeName):
    if (nodeName.count(LIST_INDEX_SYMBOL) != 1):
        return types.NO_TYPE

    nodeNameSplit = nodeName.split(LIST_INDEX_SYMBOL)
    if (nodeNameSplit[1].isdigit() == False):
        return types.NO_TYPE

    listName = nodeNameSplit[0]

    if (TYPES_HEADER not in varTypes):
        return types.NO_TYPE

    if (listName not in varTypes[TYPES_HEADER]):
        return types.NO_TYPE

    x = varTypes[TYPES_HEADER][listName].getType()
    #print(varTypes[TYPES_HEADER][listName].getType())
    if (varTypes[TYPES_HEADER][listName].getType() != types.list):
        return types.NO_TYPE

    retVarType = types.NO_TYPE

    for currentFuncName in varTypes:
        if (currentFuncName == TYPES_HEADER):
            continue
        for currentVarName in varTypes[currentFuncName]:
            if (currentVarName != listName):
                continue

            currentVarType = varTypes[currentFuncName][currentVarName].getType()
            if (retVarType == types.NO_TYPE):
                retVarType = currentVarType
                continue
            if (retVarType == currentVarType):
                continue

            sys.exit("checkForListWithOneNumIndex in SDLParser.py:  found conflicting variable types in varTypes structure.")

    return retVarType

def getVarTypeInfoForAttr_List(node):
    (funcNameOfVar, varNameInList) = getVarNameFromListIndices(assignInfo, node)
    if ( (funcNameOfVar != None) and (varNameInList != None) ):
        if ( (funcNameOfVar in varTypes) and (varNameInList in varTypes[funcNameOfVar]) ):
            return varTypes[funcNameOfVar][varNameInList].getType()

        (outsideFunctionName, retVarInfoObj) = getVarNameEntryFromAssignInfo(assignInfo, varNameInList)
        if ( (outsideFunctionName != None) and (retVarInfoObj != None) and (outsideFunctionName in varTypes) and (varNameInList in varTypes[outsideFunctionName]) ):
            return varTypes[outsideFunctionName][varNameInList].getType()

    nodeAttrFullName = getFullVarName(node, False)

    lastAttemptAtType = checkForListWithOneNumIndex(nodeAttrFullName)
    return lastAttemptAtType

def getVarTypeInfoForAttr(node):
    nodeAttrFullName = getFullVarName(node, False)

    if (nodeAttrFullName in varTypes[currentFuncName]):
        return varTypes[currentFuncName][nodeAttrFullName].getType()

    (possibleFuncName, possibleVarInfoObj) = getVarNameEntryFromAssignInfo(assignInfo, nodeAttrFullName)
    if ( (possibleFuncName != None) and (possibleVarInfoObj != None) and (nodeAttrFullName in varTypes[possibleFuncName]) ):
        return varTypes[possibleFuncName][nodeAttrFullName].getType()

    if (nodeAttrFullName.find(LIST_INDEX_SYMBOL) != -1):
        return getVarTypeInfoForAttr_List(node)

    if (nodeAttrFullName == "1"):
        return types.ZR

    return types.NO_TYPE

def getVarTypeInfoRecursive(node):
    if (node.type == ops.RANDOM):
        retRandomType = node.left.attr
        if (str(retRandomType) not in [str(types.G1), str(types.G2), str(types.GT), str(types.ZR)]):
            sys.exit("getVarTypeInfoRecursive in SDLParser.py found a random call in which the type is not one of the supported types (" + str(types.G1) + ", " + str(types.G2) + ", " + str(types.GT) + ", and " + str(types.ZR) + ").")
        return retRandomType
    if (node.type == ops.ON):
        return getVarTypeInfoRecursive(node.right)
    if (node.type == ops.LIST):
        return node

    #TODO:  THIS MUST BE FIXED!!!!  MODEL SYMMAP AFTER LIST
    if (node.type == ops.SYMMAP):
        return types.symmap
    #TODO:  FIX THE ABOVE (SYMMAP).

    if (node.type == ops.EXP):
        return getVarTypeInfoRecursive(node.left)
    if ( (node.type == ops.ADD) or (node.type == ops.SUB) or (node.type == ops.MUL) or (node.type == ops.DIV) ):
        leftSideType = getVarTypeInfoRecursive(node.left)
        rightSideType = getVarTypeInfoRecursive(node.right)
        if (leftSideType != rightSideType):
            sys.exit("getVarTypeInfoRecursive in SDLParser.py found an operation of type ADD, SUB, MUL, or DIV in which the left and right sides were not of the same type.")
        return leftSideType
    if (node.type == ops.PAIR):
        checkPairingInputTypes(node)
        return types.GT
    if (node.type == ops.HASH):
        retHashType = node.right.attr
        if (str(retHashType) not in [str(types.ZR), str(types.G1), str(types.G2)]):
            sys.exit("getVarTypeInfoRecursive in SDLParser.py found a hash operation that does not hash to a supported hash type (" + str(types.ZR) + ", " + str(types.G1) + ", and " + str(types.G2) + ").")
        return retHashType
    if (node.type == ops.ATTR):
        return getVarTypeInfoForAttr(node)
    if (node.type == ops.EXPAND):
        return types.NO_TYPE
    if (node.type == ops.FUNC):
        currentFuncName = getFullVarName(node, False)
        if (currentFuncName in builtInTypes):
            return builtInTypes[currentFuncName]
        return types.NO_TYPE
    if (node.type == ops.EQ_TST):
        leftSideType = getVarTypeInfoRecursive(node.left)
        rightSideType = getVarTypeInfoRecursive(node.right)
        if (leftSideType != rightSideType):
            sys.exit("getVarTypeInfoRecursive in SDLParser.py found an operation of type EQ_TST in which the left and right side types were unequal.")
        return leftSideType

    print(node.type)
    sys.exit("getVarTypeInfoRecursive in SDLParser.py:  error in logic.")

def getVarTypeInfo(node, i, varName):
    retVarType = getVarTypeInfoRecursive(node.right)
    if (type(retVarType).__name__ == ENUM_VALUE_CLASS_NAME):
        if (retVarType != types.NO_TYPE):
            updateVarTypes(node, i, retVarType)
    elif (type(retVarType).__name__ == BINARY_NODE_CLASS_NAME):
        if (retVarType.type == ops.LIST):
            updateVarTypes(node, i, retVarType)

def updateVarNamesDicts(node, varNameList, dictToUpdate):
    if (type(varNameList) is not list):
        sys.exit("updateVarNamesDicts in SDLParser.py:  varNameList passed in is not of type list.")

    if (type(dictToUpdate) is not dict):
        sys.exit("updateVarNamesDicts in SDLParser.py:  dictToUpdate passed in is not of type dict.")

    if (node.right.type == ops.EXPAND):
        return

    if (len(varNameList) == 0):
        return

    for varName in varNameList:
        if (varName in dictToUpdate):
            if (currentFuncName not in dictToUpdate[varName]):
                dictToUpdate[varName].append(currentFuncName)
        else:
            dictToUpdate[varName] = []
            dictToUpdate[varName].append(currentFuncName)

def getOutputVarsDictOfFuncRecursive(retList, funcName, outputVarInfoObj):
    if (type(retList) is not list):
        sys.exit("getOutputVarsDictOfFuncRecursive in SDLParser.py:  retList parameter passed in is not of type list.")

    if ( (funcName == None) or (type(funcName) is not str) or (len(funcName) == 0) or (funcName not in assignInfo) ):
        sys.exit("getOutputVarsDictOfFuncRecursive in SDLParser.py:  problem with funcName parameter passed in.")

    if (outputVarInfoObj == None):
        sys.exit("getOutputVarsDictOfFuncRecursive in SDLParser.py:  outputVarInfoObj parameter passed in is of None type.")

    if ( ( (outputVarInfoObj.getType() == ops.LIST) or (outputVarInfoObj.getType() == ops.SYMMAP) ) and (len(outputVarInfoObj.getListNodesList()) > 0) ):
        for outputVarName in outputVarInfoObj.getListNodesList():
            if (outputVarName in retList):
                sys.exit("getOutputVarsDictOfFuncRecursive in SDLParser.py:  duplicate variable names found in retList parameter passed in to function.")

            retList.append(outputVarName)
    else:
        if (outputVarInfoObj.getAssignNode().right.type != ops.ATTR):
            #sys.exit("getOutputVarsDictOfFuncRecursive in SDLParser.py:  current outputVarInfoObj is not one of the following types:  list, symmap, or attribute.")
            return

        newOutputVarName = str(outputVarInfoObj.getAssignNode().right)

        if (newOutputVarName in retList):
            sys.exit("getOutputVarsDictOfFuncRecursive in SDLParser.py:  new output variable name just generated is already in retList parameter passed in.")

        retList.append(newOutputVarName) 

        (retFuncName, retVarInfoObj) = getVarNameEntryFromAssignInfo(assignInfo, newOutputVarName)
        if ( (retFuncName == None) or (retFuncName != funcName) or (retVarInfoObj == None) ):
            #sys.exit("getOutputVarsDictOfFuncRecursive in SDLParser.py:  problem with values returned from getVarNameEntryFromAssignInfo.")
            return

        getOutputVarsDictOfFuncRecursive(retList, funcName, retVarInfoObj)

def getInputOutputVarsDictOfFunc(funcName):
    if ( (funcName == None) or (type(funcName) is not str) or (len(funcName) == 0) ):
        sys.exit("getInputOutputVarsDictOfFunc in SDLParser.py:  problem with function name parameter passed in.")

    if (funcName not in assignInfo):
        return None
        #print(funcName)
        #sys.exit("getInputOutputVarsDictOfFunc in SDLParser.py:  function name parameter passed in is not in assignInfo.")

    if (inputKeyword not in assignInfo[funcName]):
        sys.exit("getInputOutputVarsDictOfFunc in SDLParser.py:  input keyword was not found in assignInfo[funcName].")

    if (outputKeyword not in assignInfo[funcName]):
        sys.exit("getInputOutputVarsDictOfFunc in SDLParser.py:  output keyword was not found in assignInfo[funcName].")

    inputVarInfoObj = assignInfo[funcName][inputKeyword]
    outputVarInfoObj = assignInfo[funcName][outputKeyword]

    if ( (inputVarInfoObj == None) or (outputVarInfoObj == None) ):
        sys.exit("getInputOutputVarsDictOfFunc in SDLParser.py:  either inputVarInfoObj or outputVarInfoObj was found to be of None type.")

    retDict = {inputKeyword:[], outputKeyword:[]}

    if ( (inputVarInfoObj.getIsList() == True) and (len(inputVarInfoObj.getListNodesList()) > 0) ):
        for inputVarName in inputVarInfoObj.getListNodesList():
            if (inputVarName in retDict[inputKeyword]):
                sys.exit("getInputOutputVarsDictOfFunc in SDLParser.py:  duplicate variable names found in input variable names.")

            retDict[inputKeyword].append(inputVarName)

    getOutputVarsDictOfFuncRecursive(retDict[outputKeyword], funcName, outputVarInfoObj)

    return retDict

def updateInputOutputVars(varsDepList):
    global inputOutputVars

    if (type(varsDepList) is not list):
        sys.exit("updateInputOutputVars in SDLParser.py:  varsDepList parameter passed in is not of type list.")

    if (len(varsDepList) == 0):
        return

    for varDep in varsDepList:
        if (varDep.find(LIST_INDEX_SYMBOL) != -1):
            sys.exit("updateInputOutputVars in SDLParser.py:  found variable dependency of either input or output statement that contains a list index symbol.")
        if (varDep not in inputOutputVars):
            inputOutputVars.append(varDep)

def updateHashArgNames_Entries(resultingHashInputArgNames):
    if (len(resultingHashInputArgNames) == 0):
        return

    for funcName in assignInfo:
        for varName in assignInfo[funcName]:
            if (varName not in resultingHashInputArgNames):
                continue

            assignInfo[funcName][varName].setIsUsedInHashCalc(True)

def updateAssignInfo(node, i):
    global assignInfo, forLoops, ifElseBranches, varNamesToFuncs_All, varNamesToFuncs_Assign

    assignInfo_Func = assignInfo[currentFuncName]

    currentForLoopObj = None
    if (startLineNo_ForLoop != None):
        lenForLoops = len(forLoops[currentFuncName])
        currentForLoopObj = forLoops[currentFuncName][lenForLoops - 1]

    currentIfElseBranch = None
    if (startLineNo_IfBranch != None):
        lenIfElseBranches = len(ifElseBranches[currentFuncName])
        currentIfElseBranch = ifElseBranches[currentFuncName][lenIfElseBranches - 1]

    varName = getFullVarName(node.left, True)
    varNameWithoutIndices = getVarNameWithoutIndices(node.left)

    updateVarNamesDicts(node, [varNameWithoutIndices], varNamesToFuncs_All)
    updateVarNamesDicts(node, [varNameWithoutIndices], varNamesToFuncs_Assign)

    resultingVarDeps = []
    resultingHashInputArgNames = []

    if (varName in assignInfo_Func):
        if ( (assignInfo_Func[varName].hasBeenSet() == True) and (varName != outputVarName) ):
            sys.exit("Found multiple assignments of same variable name within same function.")
        assignInfo_Func[varName].setLineNo(i)
        (resultingVarDeps, resultingHashInputArgNames) = assignInfo_Func[varName].setAssignNode(assignInfo, node, currentFuncName, currentForLoopObj, currentIfElseBranch)
    else:
        varInfoObj = VarInfo()
        varInfoObj.setLineNo(i)
        (resultingVarDeps, resultingHashInputArgNames) = varInfoObj.setAssignNode(assignInfo, node, currentFuncName, currentForLoopObj, currentIfElseBranch)
        assignInfo_Func[varName] = varInfoObj

    updateHashArgNames_Entries(resultingHashInputArgNames)

    expandedVarDeps = expandVarNamesByIndexSymbols(resultingVarDeps)

    updateVarNamesDicts(node, expandedVarDeps, varNamesToFuncs_All)

    varNameForIO = getFullVarName(node.left, False)
    if ( (varNameForIO == inputKeyword) or (varNameForIO == outputKeyword) ):
        updateInputOutputVars(resultingVarDeps)

    if (currentForLoopObj != None):
        currentForLoopObj.appendToBinaryNodeList(node)
        currentForLoopObj.appendToVarInfoNodeList(assignInfo_Func[varName])

    if (currentIfElseBranch != None):
        currentIfElseBranch.appendToBinaryNodeDict(node, i)
        currentIfElseBranch.appendToVarInfoNodeList(assignInfo_Func[varName], i)

    getVarTypeInfo(node, i, varName)

    global algebraicSetting

    if ( (varName == ALGEBRAIC_SETTING) and (currentFuncName == NONE_FUNC_NAME) ):
        if (algebraicSetting != None):
            sys.exit("Algebraic setting has been set more than once.")
        algSettingVarDepList = assignInfo_Func[varName].getVarDeps()
        if (len(algSettingVarDepList) != 1):
            sys.exit("Wrong number of arguments specified for algebraic setting.")
        if ( (algSettingVarDepList[0] != SYMMETRIC_SETTING) and (algSettingVarDepList[0] != ASYMMETRIC_SETTING) ):
            sys.exit("Incorrect value specified for algebraic setting.")

        algebraicSetting = algSettingVarDepList[0]

def getVarDepList(funcName, varName, retVarDepList, varsVisitedSoFar, includeExponents):
    varsVisitedSoFar.append(varName)
    assignInfo_Var = assignInfo[funcName][varName]
    if (includeExponents == True):
        currentVarDepList = assignInfo_Var.getVarDeps()
    else:
        currentVarDepList = assignInfo_Var.getVarDepsNoExponents()
    for currentVarDep in currentVarDepList:
        if (currentVarDep not in retVarDepList):
            retVarDepList.append(currentVarDep)
        if ( (currentVarDep in assignInfo[funcName]) and  (currentVarDep not in varsVisitedSoFar) ):
            getVarDepList(funcName, currentVarDep, retVarDepList, varsVisitedSoFar, includeExponents)

def getVarInfList(retList, includeExponents):
    if (includeExponents == True):
        listToUse = varDepList
    else:
        listToUse = varDepListNoExponents

    for funcName in listToUse:
        for varName in listToUse[funcName]:
            currentListToUse = listToUse[funcName][varName]
            for currentVarDep in currentListToUse:
                if (varName not in retList[funcName][currentVarDep]):
                    retList[funcName][currentVarDep].append(varName)

def getVarDepInfLists():
    global varDepList, varDepListNoExponents, varInfList, varInfListNoExponents, getVarDepInfListsCalled

    for funcName in assignInfo:
        varDepList[funcName] = {}
        varInfList[funcName] = {}
        varDepListNoExponents[funcName] = {}
        varInfListNoExponents[funcName] = {}
        assignInfo_Func = assignInfo[funcName]
        for varName in assignInfo_Func:
            retVarDepList = []
            retVarDepListNoExponents = []
            getVarDepList(funcName, varName, retVarDepList, [], True)
            getVarDepList(funcName, varName, retVarDepListNoExponents, [], False)
            varDepList[funcName][varName] = retVarDepList
            varDepListNoExponents[funcName][varName] = retVarDepListNoExponents
            for retVarDep in retVarDepList:
                varInfList[funcName][retVarDep] = []
            for retVarDepNoExponents in retVarDepListNoExponents:
                varInfListNoExponents[funcName][retVarDepNoExponents] = []

    getVarInfList(varInfList, True)
    getVarInfList(varInfListNoExponents, False)
    getVarDepInfListsCalled = True

def getVarsThatProtectM():
    global varsThatProtectM

    for funcName in assignInfo:
        varsThatProtectM[funcName] = []
        assignInfo_Func = assignInfo[funcName]
        for varName in assignInfo_Func:
            assignInfo_Var = assignInfo_Func[varName]
            if (assignInfo_Var.getProtectsM() == True and varName not in ASSIGN_KEYWORDS):
                varsThatProtectM[funcName].append(varName)
    getVarsThatProtectMCalled = True

def updateForLoops(node, lineNo):
    if (startLineNo_ForLoop == None):
        sys.exit("updateForLoops function entered in SDLParser.py when startLineNo_ForLoop is set to None.")

    global forLoops

    retForLoopStruct = ForLoop()
    retForLoopStruct.updateForLoopStruct(node, startLineNo_ForLoop, currentFuncName)

    forLoops[currentFuncName].append(retForLoopStruct)

def updateIfElseBranches(node, lineNo):
    if (startLineNo_IfBranch == None):
        sys.exit("updateIfElseBranches in SDLParser.py:  function entered when startLineNo_IfBranch is set to None.")

    global ifElseBranches

    retIfElseBranchStruct = IfElseBranch()
    retIfElseBranchStruct.updateIfElseBranchStruct(node, startLineNo_IfBranch, currentFuncName)

    ifElseBranches[currentFuncName].append(retIfElseBranchStruct)

def writeLinesOfCodeToFile(outputFileName):
    outputFile = open(outputFileName, 'w')
    outputString = ""

    lineNo = 0

    for line in linesOfCode:
        lineNo += 1
        outputString += str(lineNo) + ":  " + line
        lenLine = len(line)
        if (lenLine == 0):
            outputString += "\n"
            continue
        if (line[lenLine - 1] != "\n"):
            outputString += "\n"

    outputFile.write(outputString)

    outputFile.close()

def printLinesOfCode():
    lineNo = 0

    for line in linesOfCode:
        printLine = line
        if (printLine[len(printLine) - 1] != "\n"):
            printLine += "\n"
        lineNo += 1
        print(lineNo, ":", printLine, end=" ")

def getLinesOfCodeFromLineNos(listOfLineNos):
    if ( (type(listOfLineNos) is not list) or (len(listOfLineNos) == 0) ):
        sys.exit("Problem with list of line numbers passed in to getLinesOfCodeFromLineNos in SDLParser.py.")

    retListOfCodeLines = []

    for lineNo in listOfLineNos:
        if ( (type(lineNo) is not int) or (lineNo < 1) or (lineNo > len(linesOfCode)) ):
            sys.exit("One of the line numbers passed in to getLinesOfCodeFromLineNos in SDLParser.py is invalid.")

        retListOfCodeLines.append(linesOfCode[(lineNo - 1)])

    if (len(retListOfCodeLines) == 0):
        sys.exit("getLinesOfCodeFromLineNos in SDLParser.py was unable to retrieve any lines of code.")

    return retListOfCodeLines

def getLinesOfCodeFromVarInfoObjs(listOfVarInfoObjs):
    if ( (type(listOfVarInfoObjs) is not list) or (len(listOfVarInfoObjs) == 0) ):
        sys.exit("Problem with list of VarInfo objects passed in to getLinesOfCodeFromVarInfoObjs in SDLParser.py.")

    lineNos = []

    for varInfoObj in listOfVarInfoObjs:
        if (type(varInfoObj).__name__ != VAR_INFO_CLASS_NAME):
            sys.exit("One of the list entries in list passed to getLinesOfCodeFromBinNodes in SDLParser.py is not of VarInfo type.")

        lineNos.append(varInfoObj.getLineNo())

    return getLinesOfCodeFromLineNos(lineNos)

def getLinesOfCode():
    return linesOfCode

def getAssignInfo():
    return assignInfo

def getVarTypes():
    return varTypes

def getForLoops():
    return forLoops

def getIfElseBranches():
    return ifElseBranches

def getVarNamesToFuncs_All():
    return varNamesToFuncs_All

def getVarNamesToFuncs_Assign():
    return varNamesToFuncs_Assign

def externalGetVarDepList():
    return varDepList

def removeFromLinesOfCode(linesToRemove):
    global linesOfCode

    if (type(linesToRemove) is not list):
        sys.exit("removeFromLinesOfCode in SDLParser.py was passed an argument for linesToRemove that is not a list.")

    if (linesOfCode == None):
        sys.exit("removeFromLinesOfCode in SDLParser.py called before linesOfCode is set.")

    newLinesOfCode = []

    for indexInLinesOfCode in range(0, len(linesOfCode)):
        lineNo = indexInLinesOfCode + 1
        if (lineNo not in linesToRemove):
            newLinesOfCode.append(linesOfCode[indexInLinesOfCode])

    linesOfCode = newLinesOfCode

#    parseLinesOfCode(linesOfCode, False)

def removeRangeFromLinesOfCode(startLineNo, endLineNo):
    global linesOfCode

    if ( (type(startLineNo) is not int) or (startLineNo < 1) ):
        sys.exit("removeRangeFromLinesOfCode in SDLParser.py received input for starting line number that is invalid.")

    if ( (type(endLineNo) is not int) or (endLineNo < 1) ):
        sys.exit("removeRangeFromLinesOfCode in SDLParser.py received input for ending line number that is invalid.")

    if (startLineNo > endLineNo):
        sys.exit("removeRangeFromLinesOfCode in SDLParser.py received a starting line number that is greater than the ending line number.")

    if (linesOfCode == None):
        sys.exit("removeRangeFromLinesOfCode in SDLParser.py called before linesOfCode is set.")

    newLinesOfCode = []

    for indexInLinesOfCode in range(0, len(linesOfCode)):
        lineNo = indexInLinesOfCode + 1
        if ( (lineNo < startLineNo) or (lineNo > endLineNo) ):
            newLinesOfCode.append(linesOfCode[indexInLinesOfCode])

    linesOfCode = newLinesOfCode

#    parseLinesOfCode(linesOfCode, False)

def appendToLinesOfCode(linesToAdd, lineNumberToAddTo):
    global linesOfCode

    if (type(linesToAdd) is not list):
        sys.exit("appendToLinesOfCode in SDLParser.py received input for linesToAdd that is not a list.")

    if ( (type(lineNumberToAddTo) is not int) or (lineNumberToAddTo < 1) ):
        sys.exit("appendToLinesOfCode in SDLParser.py received input for lineNumberToAddTo that is invalid.")

    lenLinesOfCode = len(linesOfCode)

    if (lineNumberToAddTo > (lenLinesOfCode + 1)):
        sys.exit("appendToLinesOfCode in SDLParser.py received input for lineNumberToAddTo that is greater than the maximum size allowed.")

    newLinesOfCode = []

    if (lineNumberToAddTo > 1):
        for indexInLinesOfCode in range(0, (lineNumberToAddTo - 1)):
            newLinesOfCode.append(linesOfCode[indexInLinesOfCode])

    for lineToAdd in linesToAdd:
        newLinesOfCode.append(lineToAdd)

    if (lineNumberToAddTo == (lenLinesOfCode + 1)):
        linesOfCode = newLinesOfCode
        return

    for indexInLinesOfCode in range( (lineNumberToAddTo - 1), lenLinesOfCode):
        newLinesOfCode.append(linesOfCode[indexInLinesOfCode])

    linesOfCode = newLinesOfCode

#    parseLinesOfCode(linesOfCode, False)

def substituteOneLineOfCode(line, lineNo):
    if ( (type(line) is not str) or (len(line) == 0) ):
        sys.exit("substituteOneLineOfCode in SDLParser.py:  problem with line parameter passed in.")

    if ( (type(lineNo) is not int) or (lineNo < 1) ):
        sys.exit("substituteOneLineOfCode in SDLParser.py:  problem with line number parameter passed in.")

    removeFromLinesOfCode([lineNo])

    appendToLinesOfCode([line], lineNo)

def getLineNoOfInputStatement(funcName):
    if ( (type(funcName) is not str) or (len(funcName) == 0) ):
        sys.exit("getLineNoOfInputStatement in SDLParser.py received as input for function name an invalid parameter.")

    if (funcName not in assignInfo):
        print(funcName)
        sys.exit("Function name passed in to getLineNoOfInputStatement in SDLParser.py is not in assignInfo.")

    if (inputKeyword not in assignInfo[funcName]):
        sys.exit("Function corresponding to function name passed in to getLineNoOfInputStatement in SDLParser.py does not have any assignment statements with the input keyword.")

    return assignInfo[funcName][inputKeyword].getLineNo()

def getLineNoOfOutputStatement(funcName):
    if ( (type(funcName) is not str) or (len(funcName) == 0) ):
        sys.exit("getLineNoOfOutputStatement in SDLParser.py received as input for function name an invalid parameter.")

    if (funcName not in assignInfo):
        sys.exit("Function name passed in to getLineNoOfOutputStatement in SDLParser.py is not in assignInfo.")

    if (outputKeyword not in assignInfo[funcName]):
        sys.exit("Function corresponding to function name passed in to getLineNoOfOutputStatement in SDLParser.py does not have any assignment statements with the output keyword.")

    return assignInfo[funcName][outputKeyword].getLineNo()

def getStartLineNoOfFunc(funcName):
    if ( (type(funcName) is not str) or (len(funcName) == 0) or (funcName not in startLineNos_Functions) ):
        sys.exit("Function name passed in to getStartLineNoOfFunc in SDLParser.py is invalid.")

    return startLineNos_Functions[funcName]

def getEndLineNoOfFunc(funcName):
    if ( (type(funcName) is not str) or (len(funcName) == 0) or (funcName not in endLineNos_Functions) ):
        sys.exit("Function name passed in to getEndLineNoOfFunc in SDLParser.py is invalid.")

    return endLineNos_Functions[funcName]

# NEW SDL PARSER
def parseFile2(filename, verbosity, ignoreCloudSourcing=False):
    global linesOfCode

    fd = open(filename, 'r')
    linesOfCode = fd.readlines()
    if (ignoreCloudSourcing == False):
        parseLinesOfCode(linesOfCode, verbosity)
    else:
        parseLinesOfCode(linesOfCode, verbosity, ignoreCloudSourcing)
       
    fd.close()

def getAstNodes():
    return astNodes

def getInputOutputVars():
    return inputOutputVars

def getPublicVarNames():
    return publicVarNames

def getSecretVarNames():
    return secretVarNames

def getFunctionNameOrder():
    return functionNameOrder

def addIOVarNamesToList(retList, IOVarNames):
    if (type(retList) is not list):
        sys.exit("addIOVarNamesToList in SDLParser.py:  retList parameter passed in is not of type list.")

    if ( (type(IOVarNames) is not dict) or (inputKeyword not in IOVarNames) or (outputKeyword not in IOVarNames) or (type(IOVarNames[inputKeyword]) is not list) or (type(IOVarNames[outputKeyword]) is not list) ):
        sys.exit("addIOVarNamesToList in SDLParser.py:  problem with IOVarNames parameter passed in.")

    for currentInputVarName in IOVarNames[inputKeyword]:
        if (currentInputVarName not in retList):
            retList.append(currentInputVarName)

    for currentOutputVarName in IOVarNames[outputKeyword]:
        if (currentOutputVarName not in retList):
            retList.append(currentOutputVarName)

def updatePublicVarNames():
    global publicVarNames

    for currentPubVarName in masterPubVars:
        if (currentPubVarName not in publicVarNames):
            publicVarNames.append(currentPubVarName)

        (retFuncName, retVarInfoObj) = getVarNameEntryFromAssignInfo(assignInfo, currentPubVarName)
        if ( (retFuncName == None) or (retVarInfoObj == None) ):
            print(currentPubVarName)
            sys.exit("updatePublicVarNames in SDLParser.py:  at least one None value returned from getVarNameEntryFromAssignInfo called on one of the master public variable names.")

        getOutputVarsDictOfFuncRecursive(publicVarNames, retFuncName, retVarInfoObj)

    encryptFuncIOVarNames = getInputOutputVarsDictOfFunc(encryptFuncName)
    if (encryptFuncIOVarNames == None):
        sys.exit("updatePublicVarNames in SDLParser.py:  value returned from getInputOutputVarsDictOfFunc(encryptFuncName) is of None type.")
    if (M in encryptFuncIOVarNames[inputKeyword]):
        encryptFuncIOVarNames[inputKeyword].remove(M)
    addIOVarNamesToList(publicVarNames, encryptFuncIOVarNames)

    transformFuncIOVarNames = getInputOutputVarsDictOfFunc(transformFunctionName)
    if (transformFuncIOVarNames != None):
        addIOVarNamesToList(publicVarNames, transformFuncIOVarNames)

def updateSecretVarNames():
    global secretVarNames

    for currentSecVarName in masterSecVars:
        if ( (currentSecVarName not in secretVarNames) and (currentSecVarName not in publicVarNames) ):
            secretVarNames.append(currentSecVarName)

        (retFuncName, retVarInfoObj) = getVarNameEntryFromAssignInfo(assignInfo, currentSecVarName)
        if ( (retFuncName == None) or (retVarInfoObj == None) ):
            sys.exit("updateSecretVarNames in SDLParser.py:  problems with values returned from getVarNameEntryFromAssignInfo.")

        #if ( (retVarInfoObj.getIsList() == False) and (currentSecVarName not in secretVarNames) and (currentSecVarName not in publicVarNames) ):
            #secretVarNames.append(currentSecVarName)

        getOutputVarsDictOfFuncRecursive(secretVarNames, retFuncName, retVarInfoObj)

        varsToRemove = []

        for currentSecVarName in secretVarNames:
            if (currentSecVarName in publicVarNames):
                if (currentSecVarName in varsToRemove):
                    sys.exit("updateSecretVarNames in SDLParser.py:  duplicate variable name found in secretVarNames.")

                varsToRemove.append(currentSecVarName)

        for varToRemove in varsToRemove:
            secretVarNames.remove(varToRemove)

def parseLinesOfCode(code, verbosity, ignoreCloudSourcing=False):
    global varTypes, assignInfo, forLoops, currentFuncName, varDepList, varInfList, varsThatProtectM
    global algebraicSetting, startLineNo_ForLoop, startLineNos_Functions, endLineNos_Functions
    global getVarDepInfListsCalled, getVarsThatProtectMCalled, astNodes, varNamesToFuncs_All
    global varNamesToFuncs_Assign, ifElseBranches, startLineNo_IfBranch, startLineNo_ElseBranch
    global inputOutputVars, varDepListNoExponents, varInfListNoExponents, functionNameOrder
    global publicVarNames, secretVarNames

    astNodes = []
    varTypes = {}
    assignInfo = {}
    varNamesToFuncs_All = {}
    varNamesToFuncs_Assign = {}
    forLoops = {}
    ifElseBranches = {}
    currentFuncName = NONE_FUNC_NAME
    varDepList = {}
    varDepListNoExponents = {}
    varInfList = {}
    varInfListNoExponents = {}
    varsThatProtectM = {}
    algebraicSetting = None
    startLineNo_ForLoop = None
    startLineNo_IfBranch = None
    startLineNo_ElseBranch = None
    startLineNos_Functions = {}
    endLineNos_Functions = {}
    functionNameOrder = []
    inputOutputVars = []
    getVarDepInfListsCalled = False
    getVarsThatProtectMCalled = False
    publicVarNames = []
    secretVarNames = []

    parser = SDLParser()
    lineNumberInCode = 0 
    for line in code:
        lineNumberInCode += 1
        if len(line.strip()) > 0 and line[0] != '#':
            node = parser.parse(line, lineNumberInCode)
            astNodes.append(node)
            if verbosity: print("sdl: ", lineNumberInCode, node)

            if (type(node) is str):
                print(node)

            if (node.type == ops.EQ):
                if (currentFuncName not in varTypes):
                    varTypes[currentFuncName] = {}

                if (currentFuncName not in assignInfo):
                    assignInfo[currentFuncName] = {}

                if (currentFuncName not in forLoops):
                    forLoops[currentFuncName] = []

                if (currentFuncName not in ifElseBranches):
                    ifElseBranches[currentFuncName] = []

                if (currentFuncName == TYPES_HEADER):
                    updateVarTypes(node, lineNumberInCode)
                else:
                    updateAssignInfo(node, lineNumberInCode)
            elif (node.type == ops.FOR):
                updateForLoops(node, lineNumberInCode)
            elif (node.type == ops.IF):
                updateIfElseBranches(node, lineNumberInCode)
        else:
            astNodes.append(BinaryNode(ops.NONE))
            if verbosity: print("sdl: ", lineNumberInCode)

    getVarDepInfLists()
    getVarDepInfListsCalled = True

    getVarsThatProtectM()
    getVarsThatProtectMCalled = True

    if (ignoreCloudSourcing == False):
        updatePublicVarNames()
        updateSecretVarNames()

def getFuncStmts(funcName):
    if getVarDepInfListsCalled == False: 
        sys.exit("ERROR: Need to call getVarDepInfLists()")
    
    if (funcName not in assignInfo):
        sys.exit("ERROR: Function name passed to getFuncStmts in SDLParser.py as input does not exist in assignInfo.")

    if (funcName not in varTypes):
        sys.exit("ERROR: Function name passed to getFuncStmts in SDLParser.py as input does not exist in varTypes.")

    if (funcName not in varDepList):
        sys.exit("ERROR: Function name passed to getFuncStmts in SDLParser.py as input does not exist in varDepList.")

    if (funcName not in varDepListNoExponents):
        sys.exit("ERROR: Function name passed to getFuncStmts in SDLParser.py as input does not exist in varDepListNoExponents.")

    if (funcName not in varInfList):
        sys.exit("ERROR: Function name passed to getFuncStmts in SDLParser.py as input does not exist in varInfList.")

    if (funcName not in varInfListNoExponents):
        sys.exit("ERROR: Function name passed to getFuncStmts in SDLParser.py as input does not exist in varInfListNoExponents.")

    retDict = {}

    for currentVarName in assignInfo[funcName]:
        currentVarInfoObj = assignInfo[funcName][currentVarName]
        lineNoKey = currentVarInfoObj.getLineNo()
        if (lineNoKey in retDict):
            sys.exit("getFuncStmts in SDLParser.py found multiple VarInfo objects in assignInfo in same function that have the same line number.")
        retDict[lineNoKey] = currentVarInfoObj

    return (retDict, varTypes[funcName], varDepList[funcName], varDepListNoExponents[funcName], varInfList[funcName], varInfListNoExponents[funcName])

# Perform some type checking here?
# rules: find constants, verify, variable definitions
def astParser(astList):
    constants = []
    verify_eq = None
    variables = {}
    
    for i in astList:
        s = str(i.left)
        if s == 'constant':
            constants.append(str(i.right))
        elif s == 'verify':
            verify_eq = i
        else:
            variables[s] = str(i.right)

    return (constants, verify_eq, variables)

class ASTIterator:
    def __init__(self, _node, _type):
        self.cur_node = _node
        self.of_type = _type
    
    def __iter__(self):
        # if we've found a match
        if self.cur_node.type == _type:
            return self.cur_node
        else:
            self.cur_node = self.cur_node.right
    
    def next(self):
        if self.cur_node:
            raise StopIteration
        else:
            self.cur_node = _node.right

# decorator for selecting which operation to call on 
# each node visit...
class dispatch(object):
    def __init__(self, target=None):
#        print("initialized dispatcher...")
        self.target = target
        self.default = 'visit'        
        #self.meths = {}; 
        self.hit = 0
    
    def __call__(self, visitor, *args):
        def wrapped_func(*args):
            try:
                name = str(args[0].type)
                #print("dispatch for => visit_", name.lower())
                func_name = 'visit_' + name.lower()
                if hasattr(visitor, 'cache') and visitor.cache.get(func_name) == None:
                    meth = getattr(visitor, func_name, self.default)
                    if meth == self.default:
                        meth = getattr(visitor, self.default)
                    visitor.cache[func_name] = meth # cache for next call
                    return meth(*args)
                else:
                    # call cached function
                    self.hit += 1
                    # print("hitting cache: ", self.hit) 
                    return visitor.cache[func_name](*args)
            except Exception as e:
                print(e)

        return wrapped_func(*args)

class ASTVisitor(object):
    def __init__(self, visitor):    
        self.visitor = visitor
        if not hasattr(self.visitor, 'visit'):
            raise Exception("No generic visit method defined in AST operation class")
        if not hasattr(self.visitor, 'cache'):
            self.visitor.cache = {} # for caching funcs
        # pointers to other parts of the tree
        # allows for keeping track of where we are in
        # AST.

    @dispatch
    def visit(self, visitor, node, info):
        """Generic visit function or sub nodes"""
        return
        
    def preorder(self, root_node, parent_node=None, sib_node=None, pass_info=None):
        if root_node == None: return None
        # if parent_node == None: parent_node = root_node
        info = { 'parent': parent_node, 'sibling': sib_node }
        if pass_info and type(pass_info) == dict: 
            #print("special info passed: ", pass_info)
            info.update(pass_info) 

        result = self.visit(self.visitor, root_node, info) 

        # allow other information to be passed between visitation of nodes
        if result == None: result = pass_info # if no knew information is added from the last visitation then
        elif type(result) == dict and type(pass_info) == dict: result.update(pass_info) # they passed something else back, so we add to pass_info
        elif type(result) == dict and pass_info == None: pass # no need to update result dict
        else: assert False, "can ONLY return dictionaries from visit methods." # should raise an exception here
        
        self.preorder(root_node.left, root_node, root_node.right, result)
        self.preorder(root_node.right, root_node, root_node.left, result)
    
    # TODO: need to think about how to pass information when we perform the bottom up tree traversal.
    def postorder(self, root_node, parent_node=None, sib_node=None, pass_info=None):
        if root_node == None: return None
        # if parent_node == None: parent_node = root_node
        info = { 'parent': parent_node, 'sibling': sib_node }
        self.postorder(root_node.left, root_node, root_node.right)
        self.postorder(root_node.right, root_node, root_node.left)
        self.visit(self.visitor, root_node, info)
    
    # TODO: think about how to pass info when traversing in order. 
    def inorder(self, root_node, parent_node=None, sib_node=None, pass_info=None):
        if root_node == None: return None
        # if parent_node == None: parent_node = root_node        
        info = { 'parent': parent_node, 'sibling': sib_node }
        self.inorder(root_node.left, root_node, root_node.right)
        self.visit(self.visitor, root_node, info)
        self.inorder(root_node.right, root_node, root_node.left)


def addAsChildNodeToParent(data, target_node):
    if data['parent'].right == data['sibling']:
        data['parent'].left = target_node
    else:
        data['parent'].right = target_node              

        
# for single signer scenario only
class CombineVerifyEq:
    def __init__(self, constants, variables):
        self.consts = constants
        self.vars = variables
    
    def visit(self, node, data):
        pass
    
    def visit_eq_tst(self, node, data):
        # distribute prod to left and right side
        if node.left.type != ops.EQ:
            prodL = self.newProdNode()
            prodL.right = node.left
            node.left = prodL
        
        if node.right.type != ops.EQ:
            prodR = self.newProdNode()
            prodR.right = node.right
            node.right = prodR
                    
    def visit_attr(self, node, data):
        if data['parent'].type in [ops.PROD, ops.EQ]:
            return
        if not self.isConstant(node):
            node.setAttrIndex('z') # add index to each attr that isn't constant
    
    def newProdNode(self):
        p = BatchParser()
        new_node = p.parse("prod{z:=0, N} on x")
        return new_node

    def isConstant(self, node):
        if self.consts:        
            for n in self.consts:
                if n == node.getAttribute(): return True            
            #if n.getAttribute() == node.getAttribute(): return True
        return False

class CVForMultiSigner:
    def __init__(self, var_types, sig_vars, pub_vars, msg_vars, setting):
        self.vars = var_types
        if pub_vars:
            assert type(pub_vars) == list, "public vars needs to be in a list"
            self.pub  = pub_vars # list of variable names
        else:
            self.pub = None
            
        if sig_vars:
            assert type(sig_vars) == list, "signature vars need to be in a list"
            self.sig  = sig_vars # list of variable names
        else:
            self.sig = None
            
        if msg_vars:
            assert type(msg_vars) == list, "message vars need to be in a list"
            self.msg  = msg_vars
        else:
            self.msg = None
        self.setting = setting

        #TODO: process setting to determine whether we qualify for single or multi-signer mode
        self.sigKey = 'z'; self.sigEnd = setting[SIGNATURE]
        self.pubEnd = None
#        if setting[PUBLIC] == SAME and setting[SIGNATURE] == setting[MESSAGE]:
        if setting[ PUBLIC ] and setting[ MESSAGE ]:
            if setting[SIGNATURE] == setting[MESSAGE] and setting[PUBLIC] == SAME:
                self.signer = signer_mode.single
                self.pubKey = self.sigKey
                print("Mode: ", self.signer, "signer")
            elif setting[PUBLIC] == setting[SIGNATURE]:
            # technically multi-signer, but since there is a 
            # one-to-one mapping with sigs and public keys
            # we should just call it single signer. Equation turns out 
            # to be the same
                self.signer = signer_mode.single            
                self.pubKey = self.sigKey
                self.pubEnd = self.sigEnd
                print("Mode: multi signer") 
            elif setting[PUBLIC] != setting[SIGNATURE] and setting[PUBLIC] == SAME:
                self.signer = signer_mode.single
                self.pubKey = self.pubEnd = None
                print("Mode: ", self.signer, "signer")
            elif setting[PUBLIC] != setting[SIGNATURE]:
            # most likely multi-signer mode
                self.signer = signer_mode.multi
                self.pubKey = 'y' # reserved for different amount of signers than signatures
                self.pubEnd = setting[PUBLIC]
                print("Mode: ", self.signer, "signer")
            else:
                print("error?")
        else:
            # if None for either or both (most likely a different setting)
            if setting[SIGNATURE]:
                self.signer = signer_mode.ring
                print("Mode: ", self.signer, "signer")
           
    def visit(self, node, data):
        pass
    
    def visit_eq_tst(self, node, data):
        # distribute prod to left and right side
        if self.signer >= signer_mode.single:
            if Type(node.left) != ops.EQ and str(node.left) != '1':
                prodL = self.newProdNode(self.sigKey, self.sigEnd) # check if sig vars appear in left side?
                prodL.right = node.left
                node.left = prodL
        
            if Type(node.right) != ops.EQ and str(node.right) != '1':
                prodR = self.newProdNode(self.sigKey, self.sigEnd)
                prodR.right = node.right
                node.right = prodR
            
        # check whether the pub vars appear in left subtree
        if self.signer == signer_mode.multi:
            if Type(node.left) != ops.EQ and self.isPubInSubtree(node.left):
                prodL2 = self.newProdNode(self.pubKey, self.pubEnd)
                prodL2.right = node.left
                node.left = prodL2
            elif Type(node.right) != ops.EQ and self.isPubInSubtree(node.right):
                prodR2 = self.newProdNode(self.pubKey, self.pubEnd)
                prodR2.right = node.right
                node.right   = prodR2
        else:
            pass

                    
    def visit_attr(self, node, data):
        if data['parent'].type in [ops.PROD, ops.EQ, ops.FOR, ops.SUM]:
            return
        if self.isSig(node):
            node.setAttrIndex('z') # add index to each attr that isn't constant
        
        # handle public keys
        if self.isPub(node):
            if self.setting[PUBLIC] == SAME:
                pass
            elif self.signer == signer_mode.single:
                node.setAttrIndex('z')
            elif self.signer == signer_mode.multi:
                node.setAttrIndex('y')
                
        if self.isMsg(node) and self.setting[MESSAGE] == self.setting[SIGNATURE]:
            #print("visiting: ", node, self.setting[ MESSAGE ])
            node.setAttrIndex('z')
    
    def newProdNode(self, key=None, end=None):
        p = BatchParser()
        if key and end:
            new_node = p.parse("prod{"+key+":=0,"+end+"} on x")        
        else:
            new_node = p.parse("prod{z:=0, N} on x")
        return new_node

    def isPub(self, node):
        if self.pub:        
            for n in self.pub:
                if n == node.getAttribute(): return True            
            #if n.getAttribute() == node.getAttribute(): return True
        return False

    def isSig(self, node):
        if self.sig:        
            for n in self.sig:
                if n == node.getAttribute(): return True            
            #if n.getAttribute() == node.getAttribute(): return True
        return False

    def isMsg(self, node):
        if self.msg:        
            for n in self.msg:
                if n == node.getAttribute(): return True            
            #if n.getAttribute() == node.getAttribute(): return True
        return False

    def isPubInSubtree(self, tree):
        if tree == None: return None
        elif Type(tree) == ops.ATTR and self.isPub(tree):
            return True
        else:
            result = self.isPubInSubtree(tree.left)
            if result: return result # if True, then end search else continue
            return self.isPubInSubtree(tree.right)
            


# Focuses on simplifying dot products of the form
# prod{} on (x * y)
class SimplifyDotProducts:
    def __init__(self):
        self.rule = "Distribute dot products: "

    def getMulTokens(self, subtree, parent_type, target_type, _list):
        if subtree == None: return None
        elif parent_type == ops.EXP and Type(subtree) == ops.MUL:
            return               
        elif parent_type == ops.MUL:
            if Type(subtree) in target_type: 
                found = False
                for i in _list:
                    if isNodeInSubtree(i, subtree): found = True
                if not found: _list.append(subtree)

        if subtree.left: self.getMulTokens(subtree.left, subtree.type, target_type, _list)
        if subtree.right: self.getMulTokens(subtree.right, subtree.type, target_type, _list)
        return
    
    def visit(self, node, data):
        pass

    # visit all the ON nodes and test whether we can distribute the product to children nodes
    # e.g., prod{} on (x * y) => prod{} on x * prod{} on y    
    def visit_on(self, node, data):
        if Type(data['parent']) == ops.PAIR:
            #self.rule += "False "
            return
        #print("test: right node of prod =>", node.right, ": type =>", node.right.type)
        #print("parent type =>", Type(data['parent']))
#        _type = node.right.type
        if Type(node.right) == ops.MUL:            
            # must distribute prod to both children of mul
            r = []
            mul_node = node.right
            self.getMulTokens(mul_node, ops.NONE, [ops.EXP, ops.HASH, ops.PAIR, ops.ATTR], r)
            #for i in r:
            #    print("node =>", i)
            
            if len(r) == 0:
                pass
            elif len(r) <= 2:
            # in case we're dealing with prod{} on attr1 * attr2 
            # no need to simply further, so we can simply return
                if mul_node.left.type == ops.ATTR and mul_node.right.type == ops.ATTR:
                    return

                node.right = None
                prod_node2 = BinaryNode.copy(node)
            
            # add prod nodes to children of mul_node
                prod_node2.right = mul_node.right
                mul_node.right = prod_node2
            
                node.right = mul_node.left
                mul_node.left = node
                #self.rule += "True "
                # move mul_node one level up to replace the "on" node.
                addAsChildNodeToParent(data, mul_node)
            elif len(r) > 2:
                #print("original node =>", node)
                muls = [BinaryNode(ops.MUL) for i in range(len(r)-1)]
                prod = [BinaryNode.copy(node) for i in r]
                # distribute the products to all nodes in r
                for i in range(len(r)):
                    prod[i].right = r[i]
#                    print("n =>", prod[i])
                # combine prod nodes into mul nodes                     
                for i in range(len(muls)):
                    muls[i].left = prod[i]
                    if i < len(muls)-1:
                        muls[i].right = muls[i+1]
                    else:
                        muls[i].right = prod[i+1]
#                print("final node =>", muls[0])
                addAsChildNodeToParent(data, muls[0])                
                #self.rule += "True "
            else:
                #self.rule += "False "
                return                




def print_results(data):
    line = "-----------------------------------------------------------------------------------------------------------------------------------------\n"
    head = "Keys\t|\t\tZR\t\t|\t\tG1\t\t|\t\tG2\t\t|\t\tGT\t\t|\n"
    msmt = line + head + line
    for k in data.keys():
        if k in ['mul', 'exp', 'hash']:
            msmt += k + "\t|"
            for i in ['ZR', 'G1', 'G2', 'GT']:
                msmt += "\t\t" + "%.2f" % data[k][i] + "\t\t|"
            msmt += "\n" + line
    for k in data.keys():
        if k in ['pair', 'prng']:
            msmt += k + " => " + str(data[k]) + "  \n"
            msmt += line            
    print(msmt)
    return

def calculate_times(opcount, curve, N, debugging=False):
    result = {}
    total_time = 0.0
    for i in opcount.keys():
        if i in ['pair', 'prng']:
            result[i] = opcount[i] * curve[i]
            total_time += result[i]
        else: # probably another dictionary
            result[i] = {}
            for j in opcount[i].keys():
                result[i][j] = opcount[i][j] * curve[i][j]
                total_time += result[i][j]
    if debugging: 
        print("Measurements are recorded in milliseconds.")
        print_results(result)
        print("Total Verification Time =>", total_time)
        print("Per Signature =>", total_time / N, "\n")
    return (result, total_time / N)

def printVarDepORInfLists(listToPrint):
    for funcName in listToPrint:
        print("FUNCTION NAME:  " + funcName)
        print("\n")
        for varName in listToPrint[funcName]:
            print(varName)
            print(listToPrint[funcName][varName])
            print("\n")
        print("----------------------")

def printForLoops():
    for funcName in forLoops:
        print("FUNCTION NAME:  " + funcName)
        print("\n")
        for forLoopObj in forLoops[funcName]:
            print("Starting value:  " + str(forLoopObj.getStartVal()))
            print("Ending value:  " + str(forLoopObj.getEndVal()))
            print("Loop variable name:  " + str(forLoopObj.getLoopVar()))
            print("Starting line number:  " + str(forLoopObj.getStartLineNo()))
            print("Ending line number:  " + str(forLoopObj.getEndLineNo()))
            print("Function name:  " + str(forLoopObj.getFuncName()))
            print("Binary Nodes:")
            for binaryNode in forLoopObj.getBinaryNodeList():
                print("\t" + str(binaryNode))
            print("Note:  we also have a list of the VarInfo objects associated with each line of the for loop.")
            print("\n")

def printVarTypes():
    for funcName in varTypes:
        print("FUNCTION NAME:  " + funcName)
        print("\n")
        for varName in varTypes[funcName]:
            print(str(varName) + " -> " + str(varTypes[funcName][varName].getType()))
        print("\n")

def printFinalOutput():
    '''
    print("\n")

    print("Variable dependency list:\n")
    printVarDepORInfLists(varDepList)
    print("\n")
    print("Variable influence list:\n")
    printVarDepORInfLists(varInfList)
    print("\n")

    print("Variables that protect the message:\n")
    print(varsThatProtectM)
    print("Ayo:  can you get this information from the two data structures I have shown above?")
    print("If so, please access the message variable using the name M (defined in config.py) rather")
    print("than hard-coding 'M' so we can keep it flexible for the user.")
    print("If not, let me know so I can re-write the getVarsThatProtectM() method to make it what")
    print("you need.\n")
    print("-------------------------")
    print("\n")

    print("Variable types inferred so far (more to come soon):\n")
    printVarTypes()
    print("\n")
    print("----------------------------")
    print("\n")

    print("For loops:\n")
    printForLoops()
    print("\n")
    '''

if __name__ == "__main__":
    #print(sys.argv[1:])
    if sys.argv[1] == '-t':
        debug = levels.all
        statement = sys.argv[2]
        parser = SDLParser()
        final = parser.parse(statement)
        print("Final statement:  '%s'" % final)
        exit(0)
    else:
        parseFile2(sys.argv[1], True)
        getVarDepInfLists()
        getVarsThatProtectM()
        printFinalOutput()
        (retFuncStmts, retFuncTypes, retVarDepList, retVarDepListNoExponents, retVarInfList, retVarInfListNoExponents) = getFuncStmts("decrypt")
