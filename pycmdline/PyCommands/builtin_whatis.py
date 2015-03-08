#!/usr/bin/env python

import os, sys
from PyCommands import *

class builtin_whatis (BuiltinCommand):
  command = "whatis"

  @staticmethod
  def complete (text, line, begidx, endidx):
    options = list()
    
    for name in list(globals().copy().keys()):
      if not text or name.startswith(text):
        options.append(name)
    return options

  @staticmethod
  def run (strval=""):
    if strval in builtin_commands:
      exec("print(builtin_commands['%s'].__repr__())" % strval)
    elif strval:
      exec("print(repr(%s))" % strval)
    else:
      sys.stderr.write("Usage: whatis <python object>\n")

addBuiltin(builtin_whatis)
