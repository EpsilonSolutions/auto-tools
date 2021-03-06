from SDLParser import *
#from outsrctechniques import AbstractTechnique,Technique1,Technique2,Technique3,FindT1,SubstituteVar
from outsrctechniques import *
import config
import sys

CTprime = Enum('T0', 'T1', 'T2') # T2 is for RCCA security

techMap = {1:Technique1, 2:Technique2, 3:Technique3}
debug = False

varNameLeftSideNoBlindedVarsCounter = 0
varNameLeftSideBlindedVarsCounter = 0

# 1. Get the assignment that protects the message in encrypt
# 2. find this variable in the decrypt routine and retrieve a program slice that affects M (potentially the entire routine)
# 3. identify all the lines that perform pairings in that slice of decrypt
# 4. try our best to combine pairings where appropriate then apply rewriting rules to move as much info into pairing as possible
# 5. iterate through each pairing line and move things in distribute so that they all look like this: e(a^b, c^d) * e(e^f,g^h) * ...

# description: should return a list of VarObjects that make up the new
# 

def getStrProdDecomposedBlindedVars(decomposedBlindedVars, cur_list):
    global varNameLeftSideBlindedVarsCounter

    varNameLeftSide = config.varNameLeftSideBlindedVars

    for exp in decomposedBlindedVars:
        outputString = varNameLeftSide + str(varNameLeftSideBlindedVarsCounter) + " := "
        varNameLeftSideBlindedVarsCounter += 1
        outputString += str(exp) + "\n"
        cur_list.append(outputString)

def getStrProdDecomposedNoBlindedVars(decomposedNoBlindedVars):
    global varNameLeftSideNoBlindedVarsCounter

    varNameLeftSide = config.varNameLeftSideNoBlindedVars

    outputString = varNameLeftSide + str(varNameLeftSideNoBlindedVarsCounter) + " := "
    varNameLeftSideNoBlindedVarsCounter += 1

    for exp in decomposedNoBlindedVars:
        outputString += str(exp) + " * "

    lenString = len(outputString)
    lenSubtractString = len(" * ")
    outputString = outputString[0:(lenString - lenSubtractString)]

    return outputString

def distillDecomposedExpressionsList(decomposedExpressionsList, varsThatAreBlinded):
    retListBlindedVars = []
    retListNoBlindedVars = []

    for exp in decomposedExpressionsList:
        listOfBlindedVarsUsed = doesThisStatementUseBlindedVars(exp, varsThatAreBlinded)
        if (len(listOfBlindedVarsUsed) == 0):
            retListNoBlindedVars.append(exp)
        else:
            retListBlindedVars.append(exp)

    return (retListBlindedVars, retListNoBlindedVars)

def getDecomposedExpressionsListRecursive(parentNode, node, retNodesList):
    if (node.type == ops.MUL):
        retNodesList.append(node.left)
        getDecomposedExpressionsListRecursive(node, node.right, retNodesList)
    else:
        retNodesList.append(parentNode.right)

def getDecomposedExpressionsList(assignNode, listOfBlindedVarsUsed):
    path_applied = []
    decomposedExpression = SimplifySDLNode(assignNode, path_applied)
    retNodesList = []
    getDecomposedExpressionsListRecursive(None, decomposedExpression.right, retNodesList)
    return retNodesList

def dropListIndexForStringArg(stringArg):
    if (stringArg.count(LIST_INDEX_SYMBOL) == 0):
        return stringArg

    listIndexPos = stringArg.find(LIST_INDEX_SYMBOL)
    return stringArg[0:listIndexPos]

def doesThisStatementUseBlindedVarsRecursive(assignNode, varsThatAreBlinded, listOfBlindedVarsUsed):
    if (assignNode.left != None):
        doesThisStatementUseBlindedVarsRecursive(assignNode.left, varsThatAreBlinded, listOfBlindedVarsUsed)

    if (assignNode.right != None):
        doesThisStatementUseBlindedVarsRecursive(assignNode.right, varsThatAreBlinded, listOfBlindedVarsUsed)

    try:
        listNodes = assignNode.listNodes
    except:
        listNodes = []

    if (len(listNodes) > 0):
        for listNode in listNodes:
            if (dropListIndexForStringArg(listNode) in varsThatAreBlinded):
                listOfBlindedVarsUsed.append(dropListIndexForStringArg(listNode))
    else:
        if ( (assignNode.type == ops.ATTR) and (dropListIndexForStringArg(str(assignNode)) in varsThatAreBlinded) ):
            listOfBlindedVarsUsed.append(dropListIndexForStringArg(str(assignNode)))

def doesThisStatementUseBlindedVars(assignNode, varsThatAreBlinded):
    if (str(assignNode.left) == config.inputVarName):
        return []
    if (str(assignNode.left) == config.outputVarName):
        return []
    if (assignNode.right.type == ops.EXPAND):
        return []
    if (str(assignNode.left) in varsThatAreBlinded):
        sys.exit("doesThisStatementUseBlindedVars in transform.py:  variable on left side of the assignment statement currently being considered is actually one of the variables that have been blinded, which means there's been a reassignment of the same variable (not allowed in SDL).")

    listOfBlindedVarsUsed = []
    doesThisStatementUseBlindedVarsRecursive(assignNode.right, varsThatAreBlinded, listOfBlindedVarsUsed)
    return listOfBlindedVarsUsed

def transform(varsThatAreBlinded, verbosity=False):
    global AssignInfo
    partDecCT = { CTprime.T0: None, CTprime.T1: None, CTprime.T2: None, config.M:None, 'dec_op':None }
    print("Building partially decrypted CT: ", partDecCT)
    AssignInfo = getAssignInfo()

#    encrypt_block = AssignInfo['encrypt']
    decrypt_block = AssignInfo['decrypt']
    # 1 get output line for keygen 
    # 2 get the reference and list definition (e.g., vars of secret key)
    # 3 see which ones appear in transform and mark them as needing to be blinded
    #keygen = "keygen"
    keygen = config.keygenFuncName
    (stmtsKg, typesKg, depListKg, depListKgNoExponents, infListKg, infListKgNoExponents) = getFuncStmts(keygen)
    outputKgLine = getLineNoOfOutputStatement(keygen)
    secret = config.keygenSecVar
    # secret = str(stmtsKg[outputKgLine].getAssignNode().right)
    print("output :=>", secret)
    secretVars = AssignInfo[keygen][secret].getAssignNode().right
    print("list :=>", secretVars.listNodes)

    if Type(secretVars) == ops.LIST:
        secretList = secretVars.listNodes
    elif Type(secretVars) == ops.ATTR:
        secretList = [secretVars]
    else:
        sys.exit("ERROR: invalid structure definition in", keygen)    
    
    (stmtsEnc, typesEnc, depListEnc, depListEncNoExponents, infListEnc, infListEncNoExponents) = getFuncStmts("encrypt")
    (stmtsDec, typesDec, depListDec, depListDecNoExponents, infListDec, infListDecNoExponents) = getFuncStmts("decrypt")
    partDecCT[config.M] = typesDec[config.M].getType()

    finalSecretList = []
    for i in secretList:
        for k,v in depListDec.items():
            if  i in v: finalSecretList.append(i); break
    
    print("INFO: Variables in Keygen that need to be blinded: ", finalSecretList)

    print("\n<=== Encrypt ===>") 
    # first step is to identify message and how its protected   
    t0_var = None
    linesEnc = list(stmtsEnc.keys())
    linesEnc.sort()
    for i in linesEnc:
        print(i, ": ", stmtsEnc[i].getAssignNode())      
        if stmtsEnc[i].getProtectsM():
            n = stmtsEnc[i].getAssignNode()
            print("\t=> protects message!")
            print("\t=> assign node : T0 :=>", n.left)
            t0_var = stmtsEnc[i]
            partDecCT[CTprime.T0] = stmtsEnc[i] # record T0
            print("\t=> object: ", t0_var.getAssignVar(), t0_var.getVarDeps())
        if stmtsEnc[i].getHasRandomness():
            print("\t=> has randomness!")
    print("<=== END ===>")
    
    traverseBackwards(stmtsDec, identifyT2, partDecCT)
    T0_sdlObj, T2_sdlObj, output_sdlObj, transform_output_sdlObj = createLOC(partDecCT)
    
#    traverseLines(stmtsDec, identifyMessage, ans)
    print("Results =>", partDecCT)
    t2 = partDecCT[CTprime.T2].getAssignVar()
    if t2 == "T2": # in other words, this is something we just added to dec, then 
        print("Dep list =>", t2)
        depListDec[t2] = partDecCT[CTprime.T2].getVarDeps()
        print("new dep list for t1 :=>", depListDec[t2])
    else:
        print("Dep list for non T1 case =>", t2, depListDec[t2])

    # program slice for t1 (including the t1 assignment line)
    last_line = partDecCT[CTprime.T2].getLineNo()
    t2_slice = {'depList':depListDec[t2], 'lines':[last_line], 'block':decrypt_block }
    traverseBackwards(stmtsDec, programSliceT2, t2_slice)
    t2_slice['lines'].sort()
    transform = t2_slice['lines']
    print("Optimize these lines: ", transform) 
    print("<===\tTransform Slice\t===>") 
    traverseForwards(stmtsDec, printStmt, t2_slice)
    print("<===\tEND\t===>") 

    # rewrite pairing equations 
    print("Rewrite pairing equations....")   
    traverseBackwards(stmtsDec, applyRules, t2_slice)
    
    allLines = getLinesOfCode()
    last_line = len(allLines) + 1
    cur_line = last_line
    
    transformVarInfos = [ ]
    transformVarInfos.extend(t2_slice['lines'])
    print("Current transform LOCs: ", transformVarInfos)

    # add statements to new transform block
    traverseForwards(stmtsDec, printStmt, t2_slice)


    # get function prologue for decrypt
    transformIntro = "BEGIN :: func:%s\n" % config.transformFunctionName
    cur_list = [transformIntro]
    startLineNo = getLineNoOfInputStatement("decrypt")-1
    endLineNo   = getLineNoOfOutputStatement("decrypt")+1
    intro = list(range(startLineNo, transformVarInfos[0]))
    transformVarInfos = intro + transformVarInfos
    print("New LOCs: ", intro) 
    transformOutro = "END :: func:%s\n" % config.transformFunctionName
    
    print("Delete these lines: ", transformVarInfos)
    
    newObj = [T0_sdlObj, T2_sdlObj, output_sdlObj, transform_output_sdlObj]
    newFunc = config.transformFunctionName # 'transform' string
#    AssignInfo[newFunc] = {}
    for i in range(len(transformVarInfos)):
        ref = transformVarInfos[i]
        if stmtsDec.get(ref):
            # do substitution here

            deleteMe = stmtsDec[ref].getAssignNode()

            ASTVisitor( SubstituteVar(config.keygenSecVar, config.keygenSecVar + config.blindingSuffix) ).preorder( stmtsDec[ref].getAssignNode() )             
            listOfBlindedVarsUsed = doesThisStatementUseBlindedVars(stmtsDec[ref].getAssignNode(), varsThatAreBlinded)
            if (len(listOfBlindedVarsUsed) == 0):
                cur_list.append(str(stmtsDec[ref].getAssignNode()) + "\n")
                cur_line += 1
            else:
                decomposedExpressionsList = getDecomposedExpressionsList(stmtsDec[ref].getAssignNode(), listOfBlindedVarsUsed)
                (decomposedBlindedVars, decomposedNoBlindedVars) = distillDecomposedExpressionsList(decomposedExpressionsList, varsThatAreBlinded)
                cur_list.append(getStrProdDecomposedNoBlindedVars(decomposedNoBlindedVars) + "\n")
                cur_line += 1
                getStrProdDecomposedBlindedVars(decomposedBlindedVars, cur_list)
                cur_line += len(decomposedBlindedVars)
                #for decomposedExpression in decomposedExpressionsList:
                    #cur_list.append(str(decomposedExpression) + "\n")
                    #cur_line += 1

    
    for o in range(len(newObj)):
        if newObj[o] != None:
            c = cur_line + o
            transformVarInfos.append(c)
            cur_list.append(str(newObj[o]) + "\n")
#       varInfo = createVarInfo(c, newObj[o], newFunc)
#       varName = varInfo.getAssignVar()
#       AssignInfo[newFunc][varName] = varInfo
#       cur_list.append(str(varInfo.getAssignNode()))
       
    cur_list.append(transformOutro)
    appendToLinesOfCode(cur_list, last_line)
    removeRangeFromLinesOfCode(startLineNo, endLineNo)

    printLinesOfCode()
    sys.exit("testing")
    
    parseLinesOfCode(getLinesOfCode(), False)
    # Confirm that transform was added correctly by retrieving its statements 
    (stmtsTrans, typesTrans, depListTrans, depListTransNoExponents, infListTrans, infListTransNoExponents) = getFuncStmts(newFunc)

    newLines = list(stmtsTrans.keys())
    newLines.sort()
    print("<===\tNew Transform\t===>") 
    for i in newLines:
        print(i, ":", stmtsTrans[i].getAssignNode())    
    print("<===\tEND\t===>") 
    
    return finalSecretList, partDecCT

def createVarInfo(i, node, currentFuncName):
    varInfoObj = VarInfo()
    varInfoObj.setLineNo(i)
    varInfoObj.setAssignNode(node, currentFuncName, None)
    
    return varInfoObj
            
def applyRules(varInf, data):
    if varInf.getHasPairings():
        equation = varInf.getAssignNode()
        print("Found pairing: ", equation)
        code_block = data.get('block')
        path = []
        new_equation = Optimize(equation, path, code_block)
        varInf.updateAssignNode(new_equation)    
            
def printStmt(varInf, data):
    if varInf.getLineNo() in data['lines']:
        print(varInf.getLineNo(), ":", varInf.getAssignNode())

def programSliceT2(varInf, data):
    depList = data['depList']
    if varInf.getAssignVar() in depList:
        data['lines'].append(varInf.getLineNo())
    elif varInf.getVarDeps() in depList:
        data['lines'].append(varInf.getLineNo())

def identifyT2(varInf, data):
    targetFunc = 'decrypt'
    s = varInf.getAssignNode()
    if s.left.getAttribute() == 'output': 
        data['msg'] = s.right.getAttribute()
    elif data.get('msg') == s.left.getAttribute(): 
        print("Found it: ", s, varInf.varDeps) # I want non-T0 var
        t0_varname = data[CTprime.T0].getAssignNode().left.getFullAttribute()
        t2_varname = list(varInf.varDeps)
        print("t0_varname := ", t0_varname)
        t2_varname.remove(t0_varname)
        print("T0 :=>", t0_varname, t2_varname, varInf.varDeps)
        if len(t2_varname) == 1:
            # M := T0 / T1 form
            i = t2_varname[0]
            print("T2: ", AssignInfo[targetFunc][i])
            data[CTprime.T2] = AssignInfo[targetFunc][i]
            findT1 = FindT1(t0_varname)
            ASTVisitor( findT1 ).preorder( s.right )
            print("decout :=", findT1.decout_op)
            # helps determine operation for dec out
            if findT1.decout_op == ops.DIV:
                data['dec_op'] = '/'
            elif findT1.decout_op == ops.MUL:
                data['dec_op'] = '*'
            else:
                pass # seems incorrect
        else:
            # TODO: need to create a new assignment for T1 and set to common operation of remaining
            # variables
            copy_s = BinaryNode.copy(s.right)
            # find and exlcude T0
            findT1 = FindT1(t0_varname)
            ASTVisitor( findT1 ).preorder( copy_s )
            # create new stmt "T1 := operations" 
            t2_node = BinaryNode(ops.EQ, BinaryNode("T2"), findT1.T1)
            # helps determine operation for dec out            
            if findT1.decout_op == ops.DIV:
                data['dec_op'] = '/'
            elif findT1.decout_op == ops.MUL:
                data['dec_op'] = '*'
            else:
                pass # seems incorrect
            # merge changes back into original line with M
            t2_vi = varInf
            t2_vi.updateAssignNode(t2_node)
            t2_vi.getVarDeps().remove(t0_varname)
#            print("t1_vi =>>>", t1_vi.getVarDeps())
            data[CTprime.T2] = t2_vi

def createLOC(partialCT):
    varName0 = partialCT[CTprime.T0].getAssignNode().left
    
    T0, T1, T2 = "T0", "T1", "T2"
    targetFunc = 'decrypt'    
    partialCiphertextName = config.partialCT
    T0_node = BinaryNode(ops.EQ)
    T0_node.left = BinaryNode(T0)
    T0_node.right = varName0
    
    T2_node = None    
    varName1 = partialCT[CTprime.T2].getAssignNode().left.getAttribute()
    print("varName1 :=>", varName1)
    if varName1 != T2:
        T2_node = BinaryNode(ops.EQ)
        T2_node.left = BinaryNode(T2)
        T2_node.right = AssignInfo[targetFunc][varName1].getAssignNode().left
        print("T2 node :=", T2_node)
        
    output_node = BinaryNode(ops.EQ)
    output_node.left = BinaryNode(partialCiphertextName)
    output_node.right = BinaryNode(ops.SYMMAP)
    output_node.right.listNodes = [T0, T1, T2]
    
    transform_output = BinaryNode(ops.EQ)
    transform_output.left = BinaryNode("output")
    transform_output.right = BinaryNode(partialCiphertextName) 
    
    return T0_node, T2_node, output_node, transform_output

def printHasPair(varInf, data):
    if varInf.getHasPairings():
        print("Found pairings: ", varInf.getAssignNode())

def traverseForwards(stmts, funcToCall, dataObj=None):
    assert type(stmts) == dict, "invalid stmt object!"
    lines = list(stmts.keys())
    lines.sort()
    if not dataObj: dataObj = {}
    for i in lines:
        funcToCall(stmts[i], dataObj)
    return dataObj


def traverseBackwards(stmts, funcToCall, dataObj=None):
    assert type(stmts) == dict, "invalid stmt object!"
    lines = list(stmts.keys())
    lines.sort()
    lines.reverse()
    if not dataObj: dataObj = {}
    for i in lines:
        funcToCall(stmts[i], dataObj)
    return dataObj

# figures out which optimizations apply
def Optimize(equation, path, code_block=None):
    tech_list = [1, 2, 3]
    # 1. apply the start technique to equation
    new_eq = equation
    while True:
        cur_tech = tech_list.pop()
        if debug: print("Testing technique: ", cur_tech)
        (tech, new_eq) = testTechnique(cur_tech, new_eq, code_block)
        
        if tech.applied:
            if debug: print("Technique ", cur_tech, " successfully applied.")
            path.append(cur_tech)
            tech_list = [1, 2, 3]
            continue
        else:
            if len(tech_list) == 0: break
    print("path: ", path)
    print("optimized equation: ", new_eq)
    return new_eq
        

def testTechnique(tech_option, equation, code_block=None):
    eq2 = BinaryNode.copy(equation)
        
    tech = None
    if tech_option in techMap.keys():
        tech = techMap[tech_option](code_block)
    else:
        return None
        
    # traverse equation with the specified technique
    ASTVisitor(tech).preorder(eq2)

    # return the results
    return (tech, eq2)

    
if __name__ == "__main__":
    print(sys.argv)
    sdl_file = sys.argv[1]
    sdlVerbose = False
    if len(sys.argv) > 2 and sys.argv[2] == "-v":  sdlVerbose = True
    parseFile(sdl_file, sdlVerbose)
    keygenVarList = transform(sdlVerbose)
    print("\n")
    
    
