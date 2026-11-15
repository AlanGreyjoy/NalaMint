#!/usr/bin/env python3
"""Add or remove an extension UUID in org.cinnamon enabled-extensions.  Usage: tools/extlist.py add|remove UUID"""
import ast
import subprocess
import sys

action, uuid = sys.argv[1], sys.argv[2]
raw = subprocess.run(["gsettings", "get", "org.cinnamon", "enabled-extensions"],
                     capture_output=True, text=True, check=True).stdout.strip()
current = ast.literal_eval(raw.removeprefix("@as ").strip())
if action == "add" and uuid not in current:
    current.append(uuid)
elif action == "remove":
    current = [u for u in current if u != uuid]
subprocess.run(["gsettings", "set", "org.cinnamon", "enabled-extensions", str(current)], check=True)
print(f"enabled-extensions: {current}")
