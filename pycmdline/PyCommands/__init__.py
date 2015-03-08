#!/usr/bin/env python

import os

builtin_commands = dict()

class BuiltinCommand:
  command = None

  def __repr__ (self):
    return "<BuiltinCommand '%s'>" % self.command

  @staticmethod
  def complete (text, line, begidx, endidx):
    options = list()

    for name in list(builtin_commands.copy().keys()):
      if not text or name.startswith(text):
        options.append(name)
    return options

  @staticmethod
  def run (*args):
    pass

def addBuiltin (cls):
  builtin_commands[cls.command] = cls

for name in os.listdir(os.path.dirname(os.path.realpath(__file__))):
  if name.endswith(".py"):
    __import__("PyCommands.%s" % name.replace(".py", ""))

