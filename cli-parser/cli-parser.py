#!/usr/bin/env python3

# This implementation inspired by https://chase-seibert.github.io/blog/2014/03/21/python-multilevel-argparse.html

# Standard Library
import argparse
import sys
import pprint

class MLArgParser:
  app_description = "FIXME: UNDESCRIBED APPLICATION"

  # mapping of command arguments to descriptions
  argDesc = {
  }

  cmdList = None

  def __init__ (self):
    # create our top-level parser
    parser = argparse.ArgumentParser(
      description=self.app_description,
      usage="%s <command> [<args>]" % sys.argv[0],
      epilog=self.__make_epilog_str__(),
      formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('command', help='Subcommand to run')

    # parse_args defaults to [1:] for args, but you need to
    # exclude the rest of the args too, or validation will fail
    args = parser.parse_args(sys.argv[1:2])
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
    commandFuncArgs = vars(parser.parse_args(sys.argv[2:]))

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
    cmd_list = list()

    # build a list of all commands with descriptions
    for cmd in func_list:
      func = getattr(self, cmd)
      cmd_list.append([func.__name__, func.__doc__])

    # determine the max width for the commands column
    col_width = max(len(cmd) for cmd in list([x[0] for x in cmd_list])) + 6

    # format each command row
    for row in cmd_list:
      epilog += "  %s\n" % "".join(word.ljust(col_width) for word in row)

    return epilog + " "

  def __cmd_arg_parser__ (self, command):
    # find the function corresponding to the command, retrieve the arglist with type info (assumes command functions have been properly annotated a la PEP-484)
    func = getattr(self, command)
    func_args = func.__annotations__

    # calculate the number of required arguments; create a counter for adding them to the parser
    num_req_args = len(func_args) - (0 if not func.__defaults__ else len(func.__defaults__))
    req_counter = 0

    # create a parser for the command
    parser = argparse.ArgumentParser(description=func.__doc__, usage="%s %s [<args>]" % (sys.argv[0], command))

    # populate the parser with the arg and type information from the function (converting underscores to dashes)
    for arg in list(func_args.keys()):
      # underscores in argument names are uncool
      cli_name = "--%s" % arg.replace("_", "-")

      # set a default description if one isn't defined
      cli_desc = self.argDesc[arg] if arg in list(self.argDesc.keys()) else "FIXME: NO DESCRIPTION"

      # prefix required arg descriptions with "[REQUIRED]"
      if req_counter < num_req_args:
        cli_desc = "[REQUIRED] %s" % cli_desc

      # add the arg to the parser
      parser.add_argument(cli_name, help=cli_desc, type=func_args[arg], required=(req_counter < num_req_args))
      req_counter += 1

    return parser


