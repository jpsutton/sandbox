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
  def completeFileFolder (filter, text, line, begidx, endidx):
    options = list()
    curpath = os.getcwd()
    prefix = line.split(" ")[-1]
    other = text

    if prefix.find("/") != -1:
      if prefix.startswith("/"):
        curpath = "/"

      parts = prefix.split("/")
      curpath = os.path.join(*([curpath] + parts[0:-1]))
      other = parts[-1]

    for name in os.listdir(curpath):
      if other and not name.startswith(other): continue
      fullpath = os.path.join(curpath, name)

      if os.path.isdir(fullpath):
        if filter in ("folder", None):
          options.append("%s/" % name)
      elif os.path.isfile(fullpath):
        if filter in ("file", None):
          options.append(name)

    return options

  @staticmethod
  def run (*args):
    pass

class OSCommand (BuiltinCommand):
  def __repr__(self):
    return "<OSCommand '%s'>" % self.command

  def complete(self, text, line, begidx, endidx):
    return BuiltinCommand.completeFileFolder(None, text, line, begidx, endidx)

  def __init__(self, command, executable):
    self.command = command
    self.executable = executable
    if command not in appGlobals.BUILTINS or appGlobals.BUILTINS[command].__class__ == self.__class__:
      addBuiltin(self)
    else:
      sys.stderr.write("WARN: overriding OS command '%s' with built-in implementation\n" % command)

  def run (self, *args):
    cmd = [self.executable] + list(args)
    subprocess.call(cmd)

init_builtins()