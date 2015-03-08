#!/usr/bin/env python

import os, sys
from PyCommands import *

class builtin_cd (BuiltinCommand):
  command = "cd"

  @staticmethod
  def complete (text, line, begidx, endidx):
    options = list()
    curpath = os.getcwd()
    prefix = line.replace("cd ", "", 1)
    other = text

    if prefix.find("/") != -1:
      parts = prefix.split("/")
      curpath = os.path.join(*([curpath] + parts[0:-1]))
      other = parts[-1]

    for name in os.listdir(curpath):
      if other and not name.startswith(other): continue
      fullpath = os.path.join(curpath, name)
      
      if os.path.isdir(fullpath):
        options.append("%s/" % name)
        
    return options

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
