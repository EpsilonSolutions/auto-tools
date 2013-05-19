import getopt
import sys, time
from batcher import sdlpath
from batcher import batchverify

time_in_ms = 1000

version  = '1.0'
help_info   = """
\t-f, --sdl  [ filename ]
\t\t: input SDL file description of signature scheme.

\t-o, --outfile  [ filename ]
\t\t: output file for SDL batch verifier.

\t-p, --proof [ no-argument ]
\t\t: generate proof of security for batch verification algorithm

\t-v, --verbose   [ no-argument ]
\t\t: enable verbose output to highest level for Batcher.

\t-t, --threshold [ no-argument ]
\t\t: measure the "cross-over" point between batch and individual verification from 0 to N.

\t-d, --precompute [ no-argument ]
\t\t: determine if there are additional variables that can be precomputed in verification equation

\t-c, --partial-codegen  [ no-argument ]
\t\t: output internal format for partial SDL required codegen (backwards compatibility).

\t-s, --strategy [ no-argument ]
\t\t: select a technique search strategy for Batcher. Pruned-BFS is only search supported.

\t-l, --library [ miracl or relic ]
\t\t: underlying crypto library being used.

\t-q, --query [ no-argument ]
\t\t: takes a test statement for debugging SDL parser

\t--path [ path/to/dir/ ]
\t\t: destination for AutoBatch output files. Default: current dir.
"""

verbose = precompute_check = threshold = codegen = proof = print_usage = print_options = False
strategy = 'bfs' # default strategy
input_file = test_statement = benchmark = None
output_file = dest_path = ""
library = 'miracl'

#print('ARGV      :', sys.argv[1:])

try:
    options, remainder = getopt.getopt(sys.argv[1:], 'o:l:cdhpvtb:s:f:', ['outfile=', 'sdl=', 'threshold', 'partial-codegen', 'proof', 'strategy=', 
                                                                    'verbose', 'library=','query', 'benchmark', 'path=', 'print', 'help'])
except:
    sys.exit("ERROR: Specified invalid arguments.")
    

for opt, arg in options:
    if opt in ('-h', '--help'):
        print_usage = True
    elif opt in ('-o', '--outfile'):
        output_file = arg
    elif opt in ('-f', '--sdl'):
        input_file = arg
    elif opt in ('-v', '--verbose'):
        verbose = True
    elif opt in ('-t', '--threshold'):
        threshold = True
    elif opt in ('-d', '--precompute'):
        precompute_check = True
    elif opt in ('-c', '--partial-codegen'):
        codegen = True
    elif opt in ('-p', '--proof'):
        proof = True
    elif opt in ('-s', '--strategy'):
        strategy = arg
    elif opt in ('-l', '--library'):
        library = arg
    elif opt in ('-q', '--query'):
        test_statement = arg
    elif opt in ('-b', '--benchmark'):
        benchmark = arg
    elif opt == '--path':
        dest_path = arg
    elif opt == '--print':
        print_options = True

if verbose:
    print('OPTIONS   :', options)
if print_usage:
    print("Batcher,", version, "\n")
    print("Arguments: ")
    print(help_info)
    sys.exit(0)
if print_options:
    print('VERSION    :', version)
    print('VERBOSE    :', verbose)
    print('SDL INPUT  :', input_file)
    print('CODEGEN    :', codegen)
    print('SDL OUTPUT :', output_file)
    print('PATH       :', dest_path)
    print('THRESHOLD  :', threshold)
    print('GEN PROOF  :', proof)
    print('STRATEGY   :', strategy)
    print('LIBRARY    :', library)
    print('REMAINING  :', remainder)

sys.exit("Need to specify SDL file.") if input_file == None else None
if dest_path != "" and dest_path[-1] != '/': dest_path += '/'

# construct the option dictionary
opts_dict = {}
opts_dict['verbose']   = verbose
opts_dict['sdl_file']  = input_file
opts_dict['out_file']  = output_file
opts_dict['codegen']   = codegen
opts_dict['threshold'] = threshold
opts_dict['proof']     = proof
opts_dict['strategy']  = strategy
opts_dict['pre_check'] = precompute_check
opts_dict['test_stmt'] = test_statement
opts_dict['library']   = library
opts_dict['benchmark'] = benchmark
opts_dict['path']      = dest_path
# execute batcher on the provided options
if benchmark != None:
    f = open(benchmark, 'a')
    start = [0.0]
    stop = [0.0]
    batchverify.run_main(opts_dict, start, stop)
    result = ((stop[0] - start[0]) * time_in_ms)
    outputString = str(result) + ","
    f.write(outputString)
    f.close()
    print("result : ", result)
else:
    batchverify.run_main(opts_dict)    
