import re
import os

with open( 'setup.py', 'r') as f:
	txt = f.read()

for vers in txt.split("\n"):
	vers = vers.strip();
	if (vers.startswith("version")):
		break;

n=float(vers.split('=')[1])+0.001
nv="version="+ str(n)

ntxt = txt.replace(vers, nv);

print("Update version from: ", vers, "to: ", nv)

with open('setup.py.BAK', 'w') as f:
	f.write(txt);
with open('setup.py', 'w') as f:
	f.write(ntxt);
with open('colabexts/version.txt', 'w') as f:
	f.write(nv);
