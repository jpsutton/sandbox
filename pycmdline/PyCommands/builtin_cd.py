#!/usr/bin/env python

import os, sys
from PyCommands import *

class builtin_cd (BuiltinCommand):
  command = "cd"

  @staticmethod
  def complete(text, line, begidx, endidx):
    return BuiltinCommand.completeFileFolder("folder", text, line, begidx, endidx)

  @staticmethod
  def run (directory="~"):
    if not directory:
      directory = "~"
    directory = os.path.expanduser(directory)
    
    if not os.path.exists(directory):
      sys.stderr.write("cd: %s: No such file or directory\n" % directory)
    elif not os.path.isdir(directory):
      sys.stderr.write("cd: %s: Not a directory\n" % directory)
    else:
      os.chdir(directory)
    

addBuiltin(builtin_cd)
