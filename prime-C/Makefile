# PrimeC v0.3 - host-side convenience targets.
# On the calculator just run: import main

PY ?= python3

# compile ccode.py -> ccode.elf using primec.py (host CPython; the same
# compiler runs on-device under MicroPython)
elf:
	$(PY) -c "import sys; sys.path.insert(0,'.'); from primec import compile_c; \
s=open('ccode.py','rb').read().decode('utf-8'); \
a=s.find('/* PRIME-C-CODE-BEGIN */'); z=s.find('/* PRIME-C-CODE-END */'); \
open('ccode.elf','wb').write(compile_c(s[a+len('/* PRIME-C-CODE-BEGIN */'):z]))"

# run the test suite in the ARM emulator (host only)
test:
	$(PY) tests/run_tests.py

.PHONY: elf test
