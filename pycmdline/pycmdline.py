import os
import ast
import cmd2 as cmd
import sys
import types
import getpass
import keyword
import platform
import traceback
import appGlobals
import PyCommands

# Python 3.x support
if sys.version_info >= (3,0):
  import io
# Python 2.x support
else:
  import StringIO as io

curdir = os.getcwd()
user = getpass.getuser()
hostname = platform.node().split(".")[0]
oscommands = dict()

class Util:
  @staticmethod
  def logTraceback ():
    traceback_out = io.StringIO()
    traceback.print_exc(file=traceback_out)

    for line in traceback_out.getvalue().split("\n"):
      sys.stderr.write("ERROR: %s\n" % line)
    
class PyCmdLine (cmd.Cmd):
  prompt = ""

  # Constructor
  def __init__(self, completekey='tab', stdin=None, stdout=None):
    self.updatePrompt()

    for (key, value) in appGlobals.BUILTINS.items():
      self.copyMethod(self.__class__.do_builtin, "do_%s" % key)
      self.copyMethod(self.__class__.complete_builtin, "complete_%s" % key)

    cmd.Cmd.__init__(self, completekey, stdin, stdout)

  # Copy an instance method and give it a new name
  def copyMethod(self, orig, new_name):
    code = orig.__code__
    new_code = type(orig.__code__) (
      code.co_argcount,
      code.co_kwonlyargcount,
      code.co_nlocals,
      code.co_stacksize,
      code.co_flags,
      bytes(list(code.co_code)),
      code.co_consts,
      code.co_names,
      code.co_varnames,
      code.co_filename,
      new_name,
      code.co_firstlineno,
      code.co_lnotab,
      code.co_freevars,
      code.co_cellvars
    )

    func = types.FunctionType(
      new_code,
      orig.__globals__,
      new_name,
      orig.__defaults__,
      orig.__closure__
    )

    return setattr(self, new_name, types.MethodType(func, self))

  # List of all complete-able commands
  #def completenames (self, text, *ignored):
  #  return PyCommands.BuiltinCommand.complete(text, *ignored) + self.complete_pycmd(text, *ignored)

  # List of all complete-able python commands
  def complete_pycmd (self, text, line, begidx, endidx):
    options = list()

    for name in dir(__builtins__) + keyword.kwlist:
      if not text or name.startswith(text):
        options.append(name)
    return options

  def completedefault (self, text, line, begidx, endidx):
    if line.startswith("/"):
      return PyCommands.BuiltinCommand.completeFileFolder(None, text, line, begidx, endidx)

  # Template method for complete-able builtins (gets copied for each one at runtime)
  def complete_builtin (self, text, line, begidx, endidx):
    try:
      realFuncName = sys._getframe().f_code.co_name
      cmd = realFuncName.split("_")[1]
      return appGlobals.BUILTINS[cmd].complete(text, line, begidx, endidx)
    except:
      Util.logTraceback()

  def default(self, line):
    try:
      if line.startswith("/"):
        parts = line.split(" ")
        cmd = PyCommands.OSCommand("__last_command__", parts[0])
        parsed_args = [self.parseArgument(x) for x in parts[1:]]
        cmd.run(*tuple(parsed_args))
      else:
        self.do_py(self.parsed("py %s" % line))
    except:
      Util.logTraceback()

  # Command prompt loop
  def cmdloop(self):
    while True:
      try:
        super(self.__class__, self).cmdloop()
      except KeyboardInterrupt:
        # Handle Ctrl+C keypress
        self.stdout.write("\n")
      except:
        Util.logTraceback()

  # Update the prompt string
  def updatePrompt (self):
    curdir = os.getcwd()
    homedir = os.path.expanduser("~")

    if curdir.startswith(homedir):
      curdir = curdir.replace(homedir, "~", 1)

    self.prompt = "%s@%s :: %s >> " % (user, hostname, curdir)

  # Make sure the prompt is updated after each run
  def postcmd(self, stop, line):
    self.updatePrompt()
    return stop

  # Try to convert a string to a usable python object of some sort
  def parseArgument (self, strval):
    try:
      return ast.literal_eval(strval)
    except:
      return strval

  # Template method for running Builtin commands (gets copied for each one at runtime)
  def do_builtin (self, *args):
    try:
      realFuncName = sys._getframe().f_code.co_name
      cmd = realFuncName.split("_")[1]
      parsed_args = [self.parseArgument(x) for x in args[0].split(" ")]

      # Ignore empty arg lists
      if len(parsed_args) == 1 and parsed_args[0] == "":
        parsed_args = []

      appGlobals.BUILTINS[cmd].run(*tuple(parsed_args))
    except:
      Util.logTraceback()

# Main Method
def main ():
  PyCmdLine().cmdloop()

# Program entry point
if __name__ == "__main__":
  main()