import base64
import os
import sys

target = sys.argv[1]
os.makedirs(os.path.dirname(target) if os.path.dirname(target) else ".", exist_ok=True)
mode = sys.argv[2]
b64data = sys.argv[3]
with open(target, mode) as f:
    f.write(base64.b64decode(b64data))
print("OK", target)
