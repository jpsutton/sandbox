#!/usr/bin/env python3

# This implementation inspired by https://chase-seibert.github.io/blog/2014/03/21/python-multilevel-argparse.html

# Standard Library
import argparse
import sys
import shutil
import os
import ast
import inspect

STR_UNDOCUMENTED = "FIXME: UNDOCUMENTED"

# Set this environment variable to help the argparse formatter wrap the lines
os.environ['COLUMNS'] = str(shutil.get_terminal_size().columns)


class MLArgParser:
    __doc__ = STR_UNDOCUMENTED

    # mapping of command arguments to descriptions
    argDesc = {
    }

    cmdList = None

    def __init__(self, level=1, parent=None, top=None):
        # Indicate how many command-levels deep we are
        self.level = level
        self.parent = parent
        self.top = top if level > 1 else self

        # create our top-level parser
        parser = argparse.ArgumentParser(
            description=self.__doc__,
            usage=(("%s " * level) + "<command> [<args>]") % tuple(sys.argv[0:level]),
            epilog=self.__get_epilog_str(),
            formatter_class=argparse.RawDescriptionHelpFormatter
        )

        parser.add_argument('command', help='Subcommand to run')

        # parse only the first argument after the current command
        args = parser.parse_args(sys.argv[level:level + 1])
        commands = dict()

        # create a mapping of lower-case commands to function names (for case-insensitive comparison)
        for (cmd_name, attr) in self.__get_cmd_list():
            commands[cmd_name.lower()] = attr

        # make sure it's a valid command
        if args.command.startswith("_") or args.command.lower() not in list(commands.keys()):
            print(('Unrecognized command: %s' % args.command))
            parser.print_help()
            exit(1)

        # create a parser for the command
        command_callable = commands[args.command.lower()]
        parser = self.__get_cmd_parser(command_callable)

        # (1) if we get a parser back from __get_cmd_parser(), then it was a command
        # (2) otherwise, it's a sub-command that was already handled
        if parser:
            # extract a list of args for the command
            func_args = vars(parser.parse_args(sys.argv[level + 1:]))

            # iterate through the args and remove any that weren't specified
            for key in list(func_args.keys()):
                func_args.pop(key) if func_args[key] is None else None

            # invoke the callable for the command with all provided arguments
            command_callable(**func_args)

    def __get_cmd_list(self):
        if self.cmdList is None:
            self.cmdList = list()

            for attr_name in dir(self):
                attr = getattr(self, attr_name)

                if callable(attr) and not attr_name.startswith("_"):
                    self.cmdList.append((attr_name, attr))

        return self.cmdList

    def __get_epilog_str(self):
        # start with a header
        epilog = "available commands:\n"

        # retrieve a list of methods in the current class (excluding dunders)
        attr_list = self.__get_cmd_list()
        cmd_list = list()

        # build a list of all commands with descriptions
        for (cmd_name, attr) in attr_list:
            desc = inspect.getdoc(attr)

            if not desc:
                desc = STR_UNDOCUMENTED

            cmd_list.append([cmd_name, desc])

        # determine the max width for the commands column
        if len(cmd_list):
            col_width = max(len(cmd) for cmd in list([x[0] for x in cmd_list])) + 6

            # format each command row
            for row in cmd_list:
                epilog += "  %s\n" % "".join(word.ljust(col_width) for word in row)

        return epilog + " "

    def __get_cmd_parser(self, command_callable):
        # (1) find the function corresponding to the command
        # (2) retrieve the arg list with type info (assumes command functions have been properly annotated a la PEP-484)
        bool_class = True.__class__

        # Intercept and execute calls to sub-commands
        if command_callable.__class__.__name__ == "type":
            command_callable(level=self.level + 1, parent=self, top=self.top)
            return None

        func_args = command_callable.__annotations__

        # (1) calculate the number of required arguments
        # (2) create a counter for adding them to the parser
        num_req_args = len(func_args) - (0 if not command_callable.__defaults__ else len(command_callable.__defaults__))
        arg_idx = 0

        # Offset the level from the one passed to the constructor (to skip parsing the previous command)
        level = self.level + 1

        # create a parser for the command and a group to track required args
        usage_str = (("%s " * level) + "[<args>]") % tuple(sys.argv[0:level])
        parser = argparse.ArgumentParser(description=command_callable.__doc__, usage=usage_str)
        req_args_grp = parser.add_argument_group("required arguments")

        # This is a list of types that can be safely converted from string by the ast.literal_eval method
        ast_types = [list, tuple, dict, set]

        # populate the parser with the arg and type information from the function
        for arg in list(func_args.keys()):
            # underscores in argument names are uncool, so replace them with dashes
            cli_name = "--%s" % arg.replace("_", "-")

            # We can determine if *this* arg is required based on it's position in the list
            arg_required = arg_idx < num_req_args

            # set a default description if one isn't defined
            cli_desc = self.argDesc[arg] if arg in list(self.argDesc.keys()) else STR_UNDOCUMENTED

            # determine if we're dealing with a boolean argument
            if func_args[arg] == bool_class:
                # Boolean arguments are considered flags, and are assumed False if not provided, and True if provided
                parser.add_argument(cli_name, help=cli_desc, required=False, action='store_true')
            else:
                # determine which group to place an argument in based on whether or not it's required
                grp = req_args_grp if arg_required else parser

                # determine if we need to use the ast module to parse the value
                arg_type = ast.literal_eval if func_args[arg] in ast_types else func_args[arg]

                # add the argument to the appropriate group
                grp.add_argument(cli_name, help=cli_desc, type=arg_type, required=arg_required)

            arg_idx += 1

        return parser


