#!/usr/bin/env python

import os
import sys
import subprocess
import platform
import appGlobals

def addBuiltin (ClassOrInstance):
  appGlobals.BUILTINS[ClassOrInstance.command] = ClassOrInstance

def init_builtins ():
  if len(appGlobals.BUILTINS):
    return

  for name in os.listdir(os.path.dirname(os.path.realpath(__file__))):
    if name.endswith(".py"):
      __import__("PyCommands.%s" % name.replace(".py", ""))

  print("Building OS command list...")
  delim = ';' if platform.system() == "Windows" else ':'
  pathDirs = os.environ['PATH'].split(delim)

  for directory in pathDirs:
    for name in os.listdir(directory):
      fullpath = os.path.join(directory, name)

      if os.path.isfile(fullpath):
        if platform.system() == "Windows" and name.lower().endswith(".exe"):
          name = name.lower().replace(".exe", "")
        elif not os.access(fullpath, os.X_OK):
          continue

        OSCommand(name, fullpath)

class BuiltinCommand:
  command = None

  @classmethod
  def __repr__ (cls):
    return "<BuiltinCommand '%s'>" % cls.command

  @staticmethod
  def complete (text, line, begidx, endidx):
    options = list()

    for name in list(appGlobals.BUILTINS.copy().keys()):
      if not text or name.startswith(text):
        options.append(name)
    return options

  @staticmethod
  def run (*args):
    pass

class OSCommand (BuiltinCommand):
  def __repr__(self):
    return "<OSCommand '%s'>" % self.command

  def __init__(self, command, executable):
    self.command = command
    self.executable = executable
    if command not in appGlobals.BUILTINS or appGlobals.BUILTINS[command].__class__ == self.__class__:
      addBuiltin(self)
    else:
      sys.stderr.write("WARN: overriding OS command '%s' with built-in implementation\n" % command)

  def run (self, *args):
    cmd = [self.command] + list(args)
    subprocess.call(cmd)

init_builtins()