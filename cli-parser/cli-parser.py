#!/usr/bin/env python3

# This implementation inspired by https://chase-seibert.github.io/blog/2014/03/21/python-multilevel-argparse.html

# Standard Library
import argparse
import sys
import shutil
import os
import ast

# Set this environment variable to help the argparse formatter wrap the lines
os.environ['COLUMNS'] = str(shutil.get_terminal_size().columns)

class MLArgParser:
  description = "FIXME: UNDESCRIBED APPLICATION"

  # mapping of command arguments to descriptions
  argDesc = {
  }

  cmdList = None

  def __init__ (self, level=1, parent=None, top=None):
    # Indicate how many command-levels deep we are
    self.level = level
    self.parent = parent
    self.top = top if level > 1 else self
    
    # create our top-level parser
    parser = argparse.ArgumentParser(
      description=self.description,
      usage=(("%s " * level) + "<command> [<args>]") % tuple(sys.argv[0:level]),
      epilog=self.__make_epilog_str__(),
      formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('command', help='Subcommand to run')

    # parse_args defaults to [1:] for args, but you need to exclude the rest of the args too, or validation will fail
    args = parser.parse_args(sys.argv[level:level + 1])
    commands = dict()

    # create a mapping of lower-case commands to function names (for case-insensitive comparison)
    for cmd in self.__command_list__():
      commands[cmd.lower()] = cmd

    # make sure it's a valid command
    if args.command.startswith("__") or args.command.lower() not in list(commands.keys()):
      print(('Unrecognized command: %s' % args.command))
      parser.print_help()
      exit(1)

    # create a parser for the command and parse the arguments for the command
    command = commands[args.command.lower()]
    parser = self.__cmd_arg_parser__(command)
    
    # if we get None back from __cmd_arg_parser__, then this was a sub-command that was executed already
    if parser is None:
      return
    
    commandFuncArgs = vars(parser.parse_args(sys.argv[level + 1:]))

    # Iterate through the args and remove any that weren't specified
    for key in list(commandFuncArgs.keys()):
      if commandFuncArgs[key] is None:
        commandFuncArgs.pop(key)

    # use dispatch pattern to invoke method with same name
    getattr(self, command)(**commandFuncArgs)

  def __command_list__ (self):
    if self.cmdList is None:
      self.cmdList = [func for func in dir(self) if callable(getattr(self, func)) and not func.startswith("_")]

    return self.cmdList

  def __make_epilog_str__ (self):
    # start with a header
    epilog="available commands:\n"

    # retrieve a list of methods in the current class (excluding dunders)
    func_list = self.__command_list__()
    #print(func_list)
    cmd_list = list()

    # build a list of all commands with descriptions
    for cmd in func_list:
      #print("DEBUG: evaluating function %s" % cmd)
      func = getattr(self, cmd)

      if func.__class__.__name__ == "method":
        desc = func.__doc__ if func.__doc__ else "FIXME: UNDOCUMENTED COMMAND"
        cmd_list.append([func.__name__, desc])
      elif func.__class__.__name__ == "type":
        cmd_list.append([cmd, " " + func.description])


    # determine the max width for the commands column
    col_width = max(len(cmd) for cmd in list([x[0] for x in cmd_list])) + 6

    # format each command row
    for row in cmd_list:
      epilog += "  %s\n" % "".join(word.ljust(col_width) for word in row)

    return epilog + " "

  def __cmd_arg_parser__ (self, command):
    # find the function corresponding to the command, retrieve the arglist with type info (assumes command functions have been properly annotated a la PEP-484)
    func = getattr(self, command)
    
    # Intercept and execute calls to sub-commands
    if func.__class__.__name__ == "type":
      func(level=self.level + 1, parent=self, top=self.top)
      return None

    func_args = func.__annotations__

    # calculate the number of required arguments; create a counter for adding them to the parser
    num_req_args = len(func_args) - (0 if not func.__defaults__ else len(func.__defaults__))
    
    # This counter needs to start at -1 to account for the unlisted help flag
    req_counter = -1

    # create a parser for the command
    level = self.level + 1
    parser = argparse.ArgumentParser(description=func.__doc__, usage=(("%s " * level) + "[<args>]") % tuple(sys.argv[0:level]))
    requiredArgsGroup = parser.add_argument_group("required arguments")

    # This is a list of types that can be safely converted from string by the ast.literal_eval method
    ast_types = [ list, tuple, dict, set ]

    # populate the parser with the arg and type information from the function (converting underscores to dashes)
    for arg in list(func_args.keys()):
      # underscores in argument names are uncool, so replace them with dashes
      cli_name = "--%s" % arg.replace("_", "-")
      
      # We can determine if *this* arg is required based on it's position in the list
      arg_required = req_counter < num_req_args

      # set a default description if one isn't defined
      cli_desc = self.argDesc[arg] if arg in list(self.argDesc.keys()) else "FIXME: NO DESCRIPTION"

      # determine if we're dealing with a boolean argument
      if func_args[arg] == True.__class__:
        # Boolean arguments are considered flags, and are assumed False if not provided, and True if provided
        parser.add_argument(cli_name, help=cli_desc, required=False, action='store_true')
      else:
        # determine which group to place an argument in based on whether or not it's required
        grp = requiredArgsGroup if arg_required else parser

        # determine if we need to use the ast module to parse the value
        arg_type = ast.literal_eval if func_args[arg] in ast_types else func_args[arg]
        
        # add the argument to the appropriate group
        grp.add_argument(cli_name, help=cli_desc, type=arg_type, required=arg_required)
        
      req_counter += 1

    return parser


