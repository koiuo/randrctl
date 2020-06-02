#!/usr/bin/env python

from Xlib import X, display
from Xlib.ext import randr
import os
import pwd
import subprocess

print(pwd.getpwnam('edio'))
d = display.Display(":0")
print(d)
s = d.screen()
# print(s)
window = s.root.create_window(0, 0, 1, 1, 1, s.root_depth)

for uid in [1000]:
    os.seteuid(uid)
    p = subprocess.Popen('whoami', stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
    print("\n".join(map(lambda bytes: str(bytes), p.stdout.readlines())))


