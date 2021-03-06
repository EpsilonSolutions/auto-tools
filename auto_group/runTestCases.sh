#!/bin/bash

echo "Running BBIBE test"
python3 runAutoGroup.py --sdl schemes/bbibe04.sdl --config schemes/configBBIBE.py -o TestBBIBE --path tests/
diff tests/bbibe04_asym_ct.sdl tests/bbibe04_asym_ct_orig.sdl > bbibe_result.txt

echo "Running GentryIBE test"
python3 runAutoGroup.py --sdl schemes/gentry06.sdl --config schemes/configGIBE.py -o TestGIBE --path tests/
diff tests/gentry06_asym_ky.sdl tests/gentry06_asym_ky_orig.sdl > gibe_result.txt

echo "Running Waters09-enc test"
python3 runAutoGroup.py --sdl schemes/dse09.sdl --config schemes/configDSE.py -o TestDSE --path tests/
diff tests/dse09_asym_bothexp.sdl tests/dse09_asym_bothexp_orig.sdl > dse09_result.txt

echo "Running BGW test"
python3 runAutoGroup.py --sdl schemes/bgw05.sdl --config schemes/configBGW.py -o TestBGW --path tests/
diff tests/bgw05_asym_ky.sdl tests/bgw05_asym_ky_orig.sdl > bgw_result.txt

echo "Running CL test"
python3 runAutoGroup.py --sdl schemes/cl04.sdl --config schemes/configCL.py -o TestCL --path tests/
diff tests/cl04_asym_sig.sdl tests/cl04_asym_sig_orig.sdl > cl_result.txt

echo "Running BBSig test"
python3 runAutoGroup.py --sdl schemes/bbssig04.sdl --config schemes/configBBSig.py -o TestBBsig --path tests/
diff tests/bbssig04_asym_ky.sdl tests/bbssig04_asym_ky_orig.sdl > bbssig_result.txt

echo "Running Waters05 test"
python3 runAutoGroup.py --sdl schemes/waters05.sdl --config schemes/configWATERS05.py -o TestWATERS --path tests/
diff tests/waters05_asym_sig.sdl tests/waters05_asym_sig_orig.sdl > waters05_result.txt

echo "Running DSEsig test"
python3 runAutoGroup.py --sdl schemes/dse09sig.sdl --config schemes/configDSEsig.py -o TestDSEsig --path tests/
diff tests/dse09sig_asym_both.sdl tests/dse09sig_asym_both_orig.sdl > dse09sig_result.txt

echo "Running ACDK test"
python3 runAutoGroup.py --sdl schemes/acdk12.sdl --config schemes/configACDK.py -o TestACDK --path tests/
diff tests/acdk12_asym_bothexp.sdl tests/acdk12_asym_bothexp_orig.sdl > acdk_result.txt

##echo "Running DFA experiment"
##python3 runAutoGroup.py --sdl schemes/dfa12.sdl --config configDFA -o TimingDFA.txt -b
