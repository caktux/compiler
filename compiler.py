#!/usr/bin/python
import re, sys, os
from parser import *

# All functions go here
#
# Entries go in a format:
#
# [ val, inputcount, outputcount, code ]

funtable = [
    ['+', 2, 1, ['<1>','<0>','ADD'] ],
    ['-', 2, 1, ['<1>','<0>','SUB'] ],
    ['*', 2, 1, ['<1>','<0>','MUL'] ],
    ['/', 2, 1, ['<1>','<0>','DIV'] ],
    ['^', 2, 1, ['<1>','<0>','EXP'] ],
    ['%', 2, 1, ['<1>','<0>','MOD'] ],
    ['#/', 2, 1, ['<1>','<0>','SDIV'] ],
    ['#%', 2, 1, ['<1>','<0>','SMOD'] ],
    ['==', 2, 1, ['<1>','<0>','EQ'] ],
    ['<', 2, 1, ['<1>','<0>','LT'] ],
    ['<=', 2, 1, ['<1>','<0>','GT','NOT'] ],
    ['>', 2, 1, ['<1>','<0>','GT'] ],
    ['>=', 2, 1, ['<1>','<0>','LT','NOT'] ],
    ['!', 1, 1, ['NOT'] ],
    ['or', 2, 1, ['<1>','<0>','DUP',4,'PC','ADD','JMPI','POP','SWAP','POP'] ],
    ['||', 2, 1, ['<1>','<0>','DUP',4,'PC','ADD','JMPI','POP','SWAP','POP'] ],
    ['and', 2, 1, ['<1>','<0>','NOT','NOT','MUL'] ],
    ['&&', 2, 1, ['<1>','<0>','NOT','NOT','MUL'] ],
    ['xor', 2, 1, ['<1>','<0>','XOR'] ],
    ['&', 2, 1, ['<1>','<0>','AND'] ],
    ['|', 2, 1, ['<1>','<0>','OR'] ],
    ['byte', 2, 1, ['<0>','<1>','BYTE'] ],
    # Word array methods
    ['access', 2, 1, ['<0>','<1>',32,'MUL','ADD','MLOAD'] ], # arr, ind -> val
    ['arrset', 3, 0, ['<2>','<0>','<1>',32,'MUL','ADD','MSTORE'] ], # arr, ind, val
    # len (32 MUL) len*32 (MSIZE) len*32 MSIZE (SWAP) MSIZE len*32 (MSIZE ADD) MSIZE MSIZE+len*32 (1) MSIZE MSIZE+len*32 1 (SWAP SUB) MSIZE MSIZE+len*32-1 (MSTORE8) MSIZE
    ['array', 1, 1, ['<0>',32,'MUL','MSIZE','SWAP','MSIZE','ADD',1,'SWAP','SUB','MSTORE8'] ], #len -> arr
    # String array methods
    ['getch', 2, 1, ['<1>','<0>','ADD','MLOAD',255,'AND'] ], # arr, ind -> val
    ['setch', 3, 0, ['<2>','<1>','<0>','ADD','MSTORE'] ], # arr, ind, val
    # len MSIZE (SWAP) MSIZE len (MSIZE ADD) MSIZE MSIZE+len (1) MSIZE MSIZE+len 1 (SWAP SUB) MSIZE MSIZE+len-1 (MSTORE8) MSIZE
    ['string', 1, 1, ['<0>','MSIZE','SWAP','MSIZE','ADD',1,'SWAP','SUB','MSTORE8'] ], #len -> arr
    ['send', 2, 1, [0,0,0,0,0,'<1>','<0>'] ], # to, value, 0, [] -> /dev/null
    ['send', 3, 1, [0,0,0,0,'<2>','<1>','<0>'] ], # to, value, gas, [] -> /dev/null
    # MSIZE 0 MSIZE (MSTORE) MSIZE (DUP) MSIZE MSIZE (...) MSIZE MSIZE 32 <4> <3> <2> <1> <0> (CALL) MSIZE FLAG (POP) MSIZE (MLOAD) RESULT
    ['msg', 5, 1, ['MSIZE',0,'MSIZE','MSTORE','DUP',32,'<4>','<3>','<2>','<1>','<0>','CALL','POP','MLOAD'] ], # to, value, gas, data, datasize -> out32
    # <5> MSIZE (SWAP) MSIZE <5> (MSIZE SWAP) MSIZE MSIZE <5> (32 MUL) MSIZE MSIZE <5>*32 (DUP ADD 1 SWAP SUB) MSIZE MSIZE <6>*32 MEND (MSTORE8) MSIZE MSIZE <6>*32 (... CALL)
    ['msg', 6, 0, ['<5>','MSIZE','SWAP','MSIZE','SWAP',32,'MUL','DUP','ADD',1,'SWAP','SUB','MSTORE8','<4>','<3>','<2>','<1>','<0>','CALL','POP'] ], # to, value, gas, data, datasize, outsize -> out
    ['create', 4, 1, ['<3>','<2>','<1>','<0>','CREATE'] ], # value, gas, data, datasize
    ['sha3', 1, 1, [32,'MSIZE','<0>','MSIZE','MSTORE','SHA3'] ],
    ['sha3bytes', 1, 1, ['SHA3'] ],
    ['sload', 1, 1, ['<0>','SLOAD'] ],
    ['sstore', 2, 0, ['<1>','<0>','SSTORE'] ],
    ['calldataload', 1, 0, ['<0>','CALLDATALOAD'] ],
    ['id', 1, 1, ['<0>'] ],
    # 0 MSIZE (SWAP) MSIZE 0 (MSIZE) MSIZE 0 MSIZE (MSTORE) MSIZE (32 SWAP) 32 MSIZE
    ['return', 1, 0, ['<0>','MSIZE','SWAP','MSIZE','MSTORE',32,'SWAP','RETURN'] ], # returns single value
    ['return', 2, 0, ['RETURN'] ],
]

# Pseudo-variables representing opcodes
pseudovars = {
    'msg.datasize': 'CALLDATASIZE',
    'msg.sender': 'CALLER',
    'msg.value': 'CALLVALUE',
    'tx.gasprice': 'GASPRICE',
    'tx.origin': 'ORIGIN',
    'tx.gas': 'GAS',
    'contract.balance': 'BALANCE',
    'block.prevhash': 'BLK_PREVHASH',
    'block.coinbase': 'BLK_COINBASE',
    'block.timestamp': 'BLK_TIMESTAMP',
    'block.number': 'BLK_NUMBER',
    'block.difficulty': 'BLK_DIFFICULTY',
    'block.gaslimit': 'GASLIMIT',
}


# A set of methods for detecting raw values (numbers and strings) and
# converting them to integers
def frombytes(b):
    return 0 if len(b) == 0 else ord(b[-1]) + 256 * frombytes(b[:-1])

def fromhex(b):
    return 0 if len(b) == 0 else '0123456789abcdef'.find(b[-1]) + 16 * fromhex(b[:-1])

def is_numberlike(b):
    if isinstance(b,(str,unicode)):
        if re.match('^[0-9\-]*$',b):
            return True
        if b[0] in ["'",'"'] and b[-1] in ["'",'"'] and b[0] == b[-1]:
            return True
        if b[:2] == '0x':
            return True
    return False

def numberize(b):
    if b[0] in ["'",'"']:
        return frombytes(b[1:-1])
    elif b[:2] == '0x':
        return fromhex(b[2:])
    else:
        return int(b)

# Apply rewrite rules

def rewrite(ast):
    if isinstance(ast,(str,unicode)):
        return ast
    elif ast[0] == 'set':
        if ast[1][0] == 'access':
            if ast[1][1] == 'contract.storage':
                return ['sstore',rewrite(ast[1][2]),rewrite(ast[2])]
            else:
                return ['arrset',rewrite(ast[1][1]),rewrite(ast[1][2]),rewrite(ast[2])]
    elif ast[0] == 'access':
        if ast[2] == 'msg.data':
            return ['calldataload',rewrite(ast[2])]
    return map(rewrite,ast)

# Main compiler code
def arity(ast):
    if isinstance(ast,(str,unicode)): return 1
    elif ast[0] == 'set': return 0
    elif ast[0] == 'if': return 0
    elif ast[0] == 'seq': return 0
    else:
        for f in funtable:
            if ast[0] == f[0]: return f[2]

# Debugging
import random
def print_wrapper(f):
    def wrapper(*args,**kwargs):
        print args[0]
        u = f(*args,**kwargs)
        print u
        return u
    return wrapper

# Right-hand-side expressions (ie. the normal kind)
#@print_wrapper
def compile_expr(ast,varhash,lc=[0]):
    # Stop keyword
    if ast == 'stop':
        return ['STOP']
    # Literals
    elif isinstance(ast,(str,unicode)):
        if is_numberlike(ast):
            return [numberize(ast)]
        elif ast in pseudovars:
            return [pseudovars[ast]]
        else:
            if ast not in varhash:
                varhash[ast] = len(varhash) * 32
            return [varhash[ast],'MLOAD']
    # Set (specifically, variables)
    elif ast[0] == 'set':
        if not isinstance(ast[1],(str,unicode)):
            raise Exception("Cannot set the value of "+str(ast[1]))
        elif ast[1] in pseudovars:
            raise Exception("Cannot set a pseudovariable!")
        else:
            if ast[1] not in varhash:
                varhash[ast[1]] = len(varhash) * 32
            return compile_expr(ast[2],varhash,lc) + [ varhash[ast[1]], 'MSTORE' ]
    # If and if/else statements
    elif ast[0] == 'if':
        f = compile_expr(stmt[1],varhash,lc)
        g = compile_expr(stmt[2],varhash,lc)
        h = compile_expr(stmt[3],varhash,lc) if len(stmt) > 3 else None
        label, ref = 'LABEL_'+str(lc[0]), 'REF_'+str(lc[0])
        lc[0] += 1
        if h: return f + [ 'NOT', ref, 'JUMPI' ] + g + [ ref, 'JUMP' ] + h + [ label ]
        else: return f + [ 'NOT', ref, 'JUMPI' ] + g + [ label ]
    # While loops
    elif ast[0] == 'while':
        f = compile_expr(stmt[1],varhash,lc)
        g = compile_expr(stmt[2],varhash,lc)
        beglab, begref = 'LABEL_'+str(lc[0]), 'REF_'+str(lc[0])
        endlab, endref = 'LABEL_'+str(lc[0]+1), 'REF_'+str(lc[0]+1)
        lc[0] += 2
        return [ beglab ] + f + [ 'NOT', endref, 'JUMPI' ] + g + [ begref, 'JUMP', endlab ]
    # Seq
    elif ast[0] == 'seq':
        o = []
        for arg in ast[1:]:
            o.extend(compile_expr(arg,varhash,lc))
        return o
    # Functions and operations
    for f in funtable:
        if ast[0] == f[0] and len(ast[1:]) == f[1]:
            if reduce(lambda x,y:x*arity(y),ast[1:],1):
                iq = f[3][:]
                oq = []
                while len(iq):
                    tok = iq.pop(0)
                    if isinstance(tok,(str,unicode)) and tok[0] == '<' and tok[-1] == '>':
                        oq.extend(compile_expr(ast[1+int(tok[1:-1])],varhash,lc))
                    else:
                        oq.append(tok)
                return oq
            else:
                raise Exception("Arity of argument mismatches for %s: %s" % (f[0], ast))
    raise Exception("invalid op: "+ast[0])

# Stuff to add once to each program
def add_wrappers(c,varhash):
    return [0,len(varhash)*32-1,'MSTORE8'] + c

# Optimizations

ops = {
    'ADD': lambda x,y: (x+y) % 2**256,
    'MUL': lambda x,y: (x*y) % 2**256,
    'SUB': lambda x,y: (x-y) % 2**256,
    'DIV': lambda x,y: x/y,
    'EXP': lambda x,y: pow(x,y,2**256),
    'AND': lambda x,y: x&y,
    'OR': lambda x,y: x|y,
    'XOR': lambda x,y: x^y
}

def multipop(li,n):
    if n > 0:
        li.pop()
        multipop(li,n-1)
    return li

def optimize(c):
    iq = c[:]    
    oq = []
    while len(iq):
        oq.append(iq.pop(0))
        if oq[-1] in ops and len(oq) >= 3:
            if isinstance(oq[-2],(int,long)) and isinstance(oq[-3],(int,long)):
                ntok = ops[oq[-1]](oq[-2],oq[-3])
                multipop(oq,3).append(ntok)
        if oq[-1] == 'JMPI' and len(oq) >= 3 and oq[-2] == 'NOT' and oq[-3] == 'NOT':
            multipop(oq,3).append('JMPI')
        if oq[-1] == 'ADD' and len(oq) >= 3 and oq[-2] == 0:
            multipop(oq,2)
        if oq[-1] in ['SUB','ADD'] and len(oq) >= 3 and oq[-3] == 0:
            ntok = oq[-2]
            multipop(oq,3).append(ntok)
    return oq
        
# Dereference labels
def assemble(c):
    iq = [x for x in c]
    mq = []
    pos = 0
    labelmap = {}
    while len(iq):
        front = iq.pop(0)
        if isinstance(front,str) and front[:6] == 'LABEL_':
            labelmap[front[6:]] = pos
        else:
            mq.append(front)
            pos += 2 if isinstance(front,str) and front[:4] == 'REF_' else 1
    oq = []
    for m in mq:
        if isinstance(m,str) and m[:4] == 'REF_':
            oq.append('PUSH')
            oq.append(labelmap[m[4:]])
        else: oq.append(m)
    return oq

def compile_to_aevm(source,optimize_flag=1):
    if isinstance(source,(str,unicode)):
        source = parse(source)
    varhash = {}
    c1 = rewrite(source)
    c2 = compile_expr(c1,varhash,[0])
    c3 = add_wrappers(c2,varhash)
    c4 = optimize(c3) if optimize_flag else c3
    return c4

def compile(source): return assemble(compile_to_aevm(source))

if len(sys.argv) >= 2:
    if os.path.exists(sys.argv[1]):
        open(sys.argv[1]).read()
        print ' '.join([str(k) for k in compile(open(sys.argv[1]).read())])
    else:
        print ' '.join([str(k) for k in compile(sys.argv[1])])
