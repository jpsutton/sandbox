#!/usr/bin/env python

import os, sys
from PyCommands import *

class builtin_exit (BuiltinCommand):
  command = "exit"

  @staticmethod
  def complete (text, line, begidx, endidx):
    return list()

  @staticmethod
  def run (exitcode = 0):
    return os._exit(exitcode)

addBuiltin(builtin_exit)
