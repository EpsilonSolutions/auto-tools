''' Operators in Batch language:

* MUL, EXP - '*' for multiply,'^' for exponent
* EQ - ':=' for assignment
* EQ_TST - '==' for equality testing
* PAIR - 'e(' arg1, arg2 ')'
* CONST - 'constant' declarator?
* VARIABLE - 'variable' declarator?
* FOR - 'for{i:=1,X} do x' loop from 1 to X on statement x
* PROD - 'prod{i:=1,N} on n' apply dot product to statement n
* ARR - 'a_1' for an array, a, with index = 1
* LIST - '[ x, y, z,...]' # not implemented yet

e.g., prod{i:=1,N} on (pk_i ^ del_i) 

AST simple rules

* check constraints assignment node exists.
* check verify assignment node exists.
* check variables have appropriate assignment types.
* support batch for different messages/signers/public keys.
'''

from charm.toolbox.enum import *
import string

types = Enum('G1', 'G2', 'GT', 'ZR', 'str')
declarator = Enum('constants', 'verify')
ops = Enum('BEGIN', 'TYPE', 'AND', 'ADD', 'SUB', 'MUL', 'DIV', 'EXP', 'EQ', 'EQ_TST', 'PAIR', 'ATTR', 'HASH', 'RANDOM','FOR','DO','PROD', 'SUM', 'ON', 'OF','CONCAT', 'LIST', 'END', 'NONE')
side = Enum('left', 'right')
levels = Enum('none', 'some', 'all')
debug = levels.none

# Note: when updating the grammar, there are four places that you have to update:
# - getBNF: symbol must be represented in the grammar (w/o) breaking the other rules.
# - batchparser: evalStack routine must be able to identify the new symbol in input file.
# - ops: definition above must include symbolic representation of new construct somewhere between BEGIN and END
# - createTree: need to add a clause for the new symbol.
# - BinaryNode: need to add a clause to the __str__ routine.

# utilities over binary node structures
# list: 
# - searchNode => find a particular type of node (ops.PAIR) in a given subtree (node)

def getListNodes(subtree, parent_type, _list):
	if subtree == None: return None
	# trying to capture most probable arrangements (may need to expand for other cases)
	elif parent_type == ops.MUL:
		if subtree.type == ops.ATTR: _list.append(subtree)
		elif subtree.type == ops.EXP: _list.append(subtree)
		elif subtree.type == ops.HASH: _list.append(subtree)
		elif subtree.type == ops.PAIR: _list.append(subtree)
	elif parent_type == ops.EQ_TST:
		if subtree.type == ops.PAIR: _list.append(subtree)
		elif subtree.type == ops.ATTR: _list.append(subtree)
		elif subtree.type == ops.ON: _list.append(subtree.right)
		
	if subtree.left: getListNodes(subtree.left, subtree.type, _list)
	if subtree.right: getListNodes(subtree.right, subtree.type, _list)
	return

# checks whether a target node exists in a subtree
# note: returns True when it finds the first match 
def isNodeInSubtree(node, target):
	if node == None: return False
	else:
		if str(node) == str(target): return True
	result = isNodeInSubtree(node.left, target)
	if result: return result
	result = isNodeInSubtree(node.right, target)
	return result

# searches a subtree for a target node type
# it returns the first node that matches the target type.
# note: doesn't return all istances of a given type in the subtree
def searchNodeType(node, target_type):
	if node == None: return None
	elif node.type == target_type: return node		
	result = searchNodeType(node.left, target_type)
	if result: return result
	result = searchNodeType(node.right, target_type)		
	return result

# simplifies checking the type of a given node
def Type(node):
	if node == None: return ops.NONE
	return node.type

# short cut to creating a binary node of a given type
# with given children nodes.
def createNode(node_type, left=None, right=None):
	node = BinaryNode(node_type)
	node.left = left
	node.right = right
	return node

# binds a string representation of the operation to 
# the symbolic representation (Enums) above 
def createTree(op, node1, node2):
    if(op == "^"):
        node = BinaryNode(ops.EXP)
    elif(op == "*"):
        node = BinaryNode(ops.MUL)
    elif(op == "+"):
        node = BinaryNode(ops.ADD)
    elif(op == "-"):
        node = BinaryNode(ops.SUB)
    elif(op == ":="):
        node = BinaryNode(ops.EQ)
    elif(op == "=="):
        node = BinaryNode(ops.EQ_TST)
    elif(op == "e("):
        node = BinaryNode(ops.PAIR)
    elif(op == "H("):
        node = BinaryNode(ops.HASH)
    elif(op == "prod{"):
        node = BinaryNode(ops.PROD)
    elif(op == "on"):
        # can only be used in conjunction w/ PROD (e.g. PROD must precede it)        
        node = BinaryNode(ops.ON)
    elif(op == "for{"):
    	node = BinaryNode(ops.FOR)
    elif(op == "do"):
    	node = BinaryNode(ops.DO)
    elif(op == "sum{"):
    	node = BinaryNode(ops.SUM)
    elif(op == "of"):
    	node = BinaryNode(ops.OF)
    elif(op == "|"):
        node = BinaryNode(ops.CONCAT)
    elif(op == "and"):
    	node = BinaryNode(ops.AND)
    elif(op == "list{"):
    	node = BinaryNode(ops.LIST)
    elif(op == "random("):
    	node = BinaryNode(ops.RANDOM)
    # elif e( ... )
    else:    
        return None
    node.addSubNode(node1, node2)
    return node


class BinaryNode:
	def __init__(self, value, left=None, right=None):		
		self.negated = False	
		if(isinstance(value, str)):
			if value in ['G1', 'G2', 'GT', 'ZR', 'str']:
				self.type = ops.TYPE
				self.attr = types[value]
				self.attr_index = None
				self.delta_index = None
			else:
				self.type = ops.ATTR
				self.delta_index = None
				arr = value.split('_')
				attr = arr[0]
				# test for negation in attribute
				if attr[0] != '-': self.attr = attr
				else:
					self.attr = attr[1:]
					self.negated = True
				# handle indices 
				if len(arr) > 1: # True means a_b form
					self.attr_index = [arr[1]]
				else: # False means a and no '_' present
					self.attr_index = None
		elif value > ops.BEGIN and value < ops.END:
			self.type = value
			self.attr = None
			self.attr_index = None
			self.delta_index = None
		else:
			self.type = ops.NONE
			self.attr = None
			self.attr_index = None
			self.delta_index = None
		self.left = left
		self.right = right
#		self.delta_index = None
		
	def __str__(self):
		if self == None: return None
		elif(self.type == ops.ATTR):
			# check for negation
#			if self.delta_index: print("Delta index: ", self.delta_index, self.attr)
			if self.negated:
				msg = "-" + self.attr
			else:
				msg = self.attr
			if self.delta_index != None and type(self.delta_index) == list and self.attr == "delta":
				token = ""
				for t in self.delta_index:
					token += t + "#"
				msg += token[:len(token)-1]
			if self.attr_index != None and type(self.attr_index) == list:
				token = ""
				for t in self.attr_index:
					token += t + "%"
				l = len(token) 
				token = token[:l-1]
				msg += '_' + token
			return msg
		elif(self.type == ops.TYPE):
			return str(self.attr)
		else:
			left = str(self.left)
			right = str(self.right)
			
			if debug >= levels.some:
			   print("Operation: ", self.type)
			   print("Left operand: ", left, "type: ", self.left.type)
			   print("Right operand: ", right, "type: ", self.right.type)
			if(self.type == ops.EXP):
				return (left + '^' + right)
			elif(self.type == ops.MUL):
				return ('(' + left + ' * ' + right + ')')
			elif(self.type == ops.DIV):
				return ('(' + left + ' / ' + right + ')')
			elif(self.type == ops.ADD):
				return ('(' + left + ' + ' + right + ')')
			elif(self.type == ops.SUB):
				return ('(' + left + ' - ' + right + ')')
			elif(self.type == ops.EQ):
				return (left + ' := ' + right)
			elif(self.type == ops.EQ_TST):
				return (left + ' == ' + right)
			elif(self.type == ops.PAIR):
				return ('e(' + left + ',' + right + ')')
			elif(self.type == ops.HASH):
				return ('H(' + left + ',' + right + ')')
			elif(self.type == ops.PROD):
				return ('prod{' + left + ',' + right + '}')
			elif(self.type == ops.SUM):
				return ('sum{' + left + ',' + right + '}')			
			elif(self.type == ops.ON):
				 return ('(' + left + ' on ' + right + ')')
			elif(self.type == ops.FOR):
				return ('for{' + left + ',' + right + '}')
			elif(self.type == ops.RANDOM):
				return ('random(' + left + ')')
			elif(self.type == ops.DO):
				 return ( left + ' do ' + right)
			elif(self.type == ops.OF):
				 return ( left + ' of ' + right)
			elif(self.type == ops.CONCAT):
				 return (left + ' | ' + right)
			elif(self.type == ops.AND):
				 return ("{" + left + "} and {" + right + "}") 
			elif(self.type == ops.LIST):
				 listVal = ""
				 for i in self.listNodes:
				 		listVal += str(i) + ', '
				 listVal = listVal[:len(listVal)-2]
				 return 'list{' + listVal + '}'
			elif(self.type == ops.NONE):
				 return 'NONE'
				# return ( left + ' on ' + right )				
		return None
	
	def isAttrIndexEmpty(self):
		if self.attr_index != None:
			if len(self.attr_index) > 0: return False
		return True

	def getAttrIndex(self):
		return self.attr_index
	
	def setAttrIndexFromSet(self, value):
		if type(value) != set: return
		if value == None: return
		# clean contents of attr_index
		self.attr_index = list(value)
		return
	
	def setAttrIndex(self, value):
		if(self.type in [ops.ATTR, ops.HASH, ops.PAIR]):
			if self.attr_index == None: # could be a list of indices
				self.attr_index = [value]
			else:
				if not value in self.attr_index:
					self.attr_index.append(value)
			return True
		return False

	def isDeltaIndexEmpty(self):
		if self.delta_index != None:
			if len(self.delta_index) > 0: return False
		return True

	def getDeltaIndex(self):
		return self.delta_index
	
	def setDeltaIndexFromSet(self, value):
		if type(value) not in [set, list]: return
		if value == None: return
		value2 = [str(i) for i in sorted(value)]
		self.delta_index = value2
		return
	
	def setDeltaIndex(self, value):
		if(self.type in [ops.ATTR, ops.HASH, ops.PAIR]):
			value2 = str(value)
			if self.delta_index == None: # could be a list of indices
				self.delta_index = [value2]
			else:
				if not value2 in self.delta_index:
					self.delta_index.append(value2)
			return True
		return False

	def getAttribute(self):
		if (self.type == ops.ATTR):
			return self.attr
		else:
			return None
	
	def setAttribute(self, value):
		if (self.type == ops.ATTR):
			self.attr = str(value)
			return True
		return False
	
#	def getMySide(self):
#		return self.myside
	
	def getLeft(self):
		return self.left if self.left != None else None
	
	def getRight(self):
		return self.right if self.right != None else None

	def addSubNode(self, left, right):
		# set subNodes appropriately
		self.left = self.createSubNode(left) if left != None else None
		#self.left.myside = side.left
		self.right = self.createSubNode(right) if left != None else None
		#self.right.myside = side.right
		if debug == levels.all:
			print("addSubNode: ");
			print("left type =>", type(self.left), ' =>', self.left)
			print("right type =>", type(self.right), ' =>', self.right)

	def createSubNode(self, value):
		if isinstance(value, str):
			node = BinaryNode(value)		   
			return node
		return value

	@classmethod
	def copy(self, this):
		if this == None: return None
		new_node = BinaryNode(this.type)
		new_node.negated = this.negated
		new_node.attr = this.attr
		new_node.attr_index = this.attr_index
		new_node.delta_index = this.delta_index		
		# recursively call copy on left 
		new_node.left = self.copy(this.left)
		new_node.right = self.copy(this.right)		
		return new_node	

	# sets destination ref to src ref (type, attr value, and attr index)
	@classmethod
	def setNodeAs(self, dest, src):
		dest.type = src.type
		dest.attr = src.attr
		dest.negated = src.negated
		if src.attr_index:
			dest.attr_index = list(src.attr_index)
		else:
			dest.attr_index = None
		if src.delta_index:
			dest.delta_index = list(src.delta_index)
		else:
			dest.delta_index = None		
		dest.left = src.left
		dest.right = src.right
		return

	@classmethod
	def clearNode(self, dest):
		dest.type = ops.NONE
		dest.attr = None
		dest.negated = False
		dest.attr_index = None
		dest.delta_index = None
#		del dest.left, dest.right
		dest.left = None
		dest.right = None
	# only applies function on leaf nodes
	def traverse(self, function):
		# visit node then traverse left and right
		function(self.type, self)
		if(self.left == None):
			return None
		self.left.traverse(function)
		if(self.right == None):
			return None
		self.right.traverse(function)
		return None	
	
	
	
