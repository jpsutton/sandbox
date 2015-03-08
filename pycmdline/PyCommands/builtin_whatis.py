#!/usr/bin/env python

import os, sys
import appGlobals
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
    if strval in appGlobals.BUILTINS:
      exec("print(appGlobals.BUILTINS['%s'].__repr__())" % strval)
    elif strval:
      exec("print(repr(%s))" % strval)
    else:
      sys.stderr.write("Usage: whatis <python object>\n")

addBuiltin(builtin_whatis)
