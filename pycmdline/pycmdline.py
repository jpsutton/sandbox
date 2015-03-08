import os
import ast
import cmd
import sys
import getpass
import keyword
import platform
import traceback
import subprocess

import PyCommands

if sys.version_info >= (3,0):
  import io
else:
  import StringIO as io

curdir = os.getcwd()
user = getpass.getuser()
hostname = platform.node().split(".")[0]
oscommands = dict()

def build_oscommands ():
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
        
        oscommands[name] = fullpath

class Util:
  @staticmethod
  def logTraceback ():
    traceback_out = io.StringIO()
    traceback.print_exc(file=traceback_out)

    for line in traceback_out.getvalue().split("\n"):
      sys.stderr.write("ERROR: %s\n" % line)

  @staticmethod
  def findProgramInPath (progname):
    if progname in oscommands:
      return oscommands[progname]
    
    delim = ';' if platform.system() == "Windows" else ':'
    pathDirs = os.environ['PATH'].split(delim)

    for dir in pathDirs:
      searchFile = os.path.join(dir, progname)

      if os.path.exists(searchFile):
        oscommands[progname] = searchFile
        return searchFile

  @staticmethod
  def parse (strval):
    try:
      return ast.literal_eval(strval)
    except:
      return strval
    
class PyCmdLine (cmd.Cmd):
  prompt = ""
  command = None
  args = None
  line = None

  def __init__(self, completekey='tab', stdin=None, stdout=None):
    cmd.Cmd.__init__(self, completekey, stdin, stdout)
    self.updatePrompt()

  def completenames(self, text, *ignored):
    return self.complete_oscmd(text, *ignored) + PyCommands.BuiltinCommand.complete(text, *ignored) + self.complete_pycmd(text, *ignored)
  
  def completedefault (self, text, line, begidx, endidx):
    command = line.split(" ")[0]
    cmdType = self.getCommandType(command)
    if cmdType == "builtin":
      return PyCommands.builtin_commands[command].complete(text, line, begidx, endidx)
    if cmdType == "oscommand":
      return self.complete_oscmd(text, line, begidx, endidx)
      
  def complete_oscmd (self, text, line, begidx, endidx):
    options = list()
    
    for name in list(oscommands.keys()):
      if not text or name.startswith(text):
        options.append(name)
    return options
    
  def getCommandType (self, command):
    if command == "":
      return "noop"
    elif command in ("noop", "builtin", "oscommand", "python"):
      return ""
    elif command in PyCommands.builtin_commands:
      return "builtin"
    elif command.startswith("!") or Util.findProgramInPath(command):
      return "oscmd"
    else:
      return "pycmd"

  def complete_pycmd (self, text, line, begidx, endidx):
    options = list()

    for name in dir(__builtins__) + keyword.kwlist:
      if not text or name.startswith(text):
        options.append(name)
    return options

  def cmdloop(self, intro=None):
    while True:
      try:
        cmd.Cmd.cmdloop(self, intro)
      except KeyboardInterrupt:
        # Handle Ctrl+C keypress
        self.stdout.write("\n")
  
  def precmd(self, line):
    self.line = line.strip(" ")
    
    if line.startswith("@"):
      self.line = self.line[1:]
      return "python %s" % self.line
    
    parts = line.split(" ")
    self.command = parts[0]
    self.args = parts[1:]
    
    return ("%s %s" % (self.getCommandType(self.command), line)).lstrip()
  
  def updatePrompt (self):
    curdir = os.getcwd()

    if curdir.startswith(os.path.expanduser("~")):
      curdir = curdir.replace(os.path.expanduser("~"), "~", 1)

    self.prompt = "%s@%s :: %s >> " % (user, hostname, curdir)

  def postcmd(self, stop, line):
    self.updatePrompt()
    return stop

  def do_noop (self, *args):
    pass
    
  def do_builtin (self, *args):
    try:
      parsed_args = [Util.parse(x) for x in self.args]
      PyCommands.builtin_commands[self.command].run(*parsed_args)
    except:
      Util.logTraceback()
    
  def do_oscmd (self, *args):
    try:
      oscommand = [Util.findProgramInPath(self.command)] + self.args
      subprocess.call(oscommand)
    except:
      Util.logTraceback()
    
  def do_pycmd (self, *args):
    try:
      exec(self.line.replace("pycmd ", "", 1))
    except NameError:
      sys.stderr.write("%s: command not found\n" % self.command)
    except:
      Util.logTraceback()

def main ():
  print("Building OS command list...")
  build_oscommands()
  PyCmdLine().cmdloop()


if __name__ == "__main__":
  main()