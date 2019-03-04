#!/usr/bin/env python3

# This implementation inspired by https://chase-seibert.github.io/blog/2014/03/21/python-multilevel-argparse.html

# Standard Library
import argparse
import sys
import shutil
import os
import ast
import inspect

# string to use for undocumented commands/arguments
STR_UNDOCUMENTED = "FIXME: UNDOCUMENTED"

# list of types that can be safely converted from string by the ast.literal_eval method
AST_TYPES = [list, tuple, dict, set]

# Set this environment variable to help the argparse formatter wrap the lines
os.environ['COLUMNS'] = str(shutil.get_terminal_size().columns)


class MLArgParser:
    __doc__ = STR_UNDOCUMENTED

    # mapping of command arguments to descriptions (initialized in constructor)
    argDesc = None

    # mapping of lower-case commands to method names and attributes (initialized in __init_commands)
    commands = None

    # list for tracking auto-generated short options (initialized in __get_cmd_parser)
    short_options = None

    def __init__(self, level=1, parent=None, top=None):
        # indicate how many command-levels deep we are
        self.level = level

        # keep track of our parent command
        self.parent = parent

        # keep track of our top-level command
        self.top = top if level > 1 else self

        # Build a dictionary of all commands
        self.__init_commands()

        # create our top-level parser
        self.parser = argparse.ArgumentParser(
            description=self.__doc__,
            usage=(("%s " * level) + "<command> [<args>]") % tuple(sys.argv[0:level]),
            epilog=self.__get_epilog_str(),
            formatter_class=argparse.RawDescriptionHelpFormatter
        )

        self.parser.add_argument('command', help='Sub-command to run')

        # parse only the first argument after the current command
        parsed_command = self.parser.parse_args(sys.argv[level:level + 1]).command.lower()

        # make sure it's a valid command and find the corresponding callable
        command_callable = self.__get_cmd_callable(parsed_command)

        # get a dictionary representing the arguments for the command
        callable_args = self.__parse_cmd_args(command_callable)

        # invoke the callable for the command with all provided arguments
        command_callable(**callable_args)

    def __parse_cmd_args(self, command_callable):
        # intercept sub-commands
        if isinstance(command_callable, type):
            return {'level': self.level + 1, 'parent': self, 'top': self.top}

        # get a parser object for the command function
        cmd_parser = self.__get_cmd_parser(command_callable)

        # extract a list of args for the command
        func_args = vars(cmd_parser.parse_args(sys.argv[self.level + 1:]))

        # iterate through the args and remove any that weren't specified
        for key in list(func_args.keys()):
            func_args.pop(key) if func_args[key] is None else None

        return func_args

    def __get_cmd_callable(self, parsed_command):
        if parsed_command.startswith("_") or parsed_command not in list(self.commands.keys()):
            print(('Unrecognized command: %s' % parsed_command))
            self.parser.print_help()
            exit(1)

        # create a parser for the command
        return self.commands[parsed_command][1]

    def __init_commands(self):
        if self.commands:
            return

        self.commands = dict()

        for attr_name in dir(self):
            attr = getattr(self, attr_name)

            if callable(attr) and not attr_name.startswith("_"):
                self.commands[attr_name.lower()] = (attr_name, attr)

    def __get_epilog_str(self):
        # start with a header
        epilog = "available commands:\n"

        # retrieve a list of attributes in the current class (excluding dunders)
        cmd_list = list()

        # build a list of all commands with descriptions
        for (cmd_name, attr) in self.commands.values():
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

    def __get_options_for_arg(self, arg):
        # initialize short options tracker
        if not self.short_options:
            self.short_options = list()

        # underscores in argument names are uncool, so replace them with dashes
        long_option = "--%s" % arg.replace("_", "-")

        # try to define a short option if it's not already used
        short_option = "-%s" % arg[0]

        if short_option not in self.short_options:
            self.short_options.append(short_option)
            return long_option, short_option
        else:
            return long_option,

    def __get_cmd_parser(self, command_callable):
        # retrieve the arg list with type info (assumes command functions have been properly annotated a la PEP-484)
        arg_types = command_callable.__annotations__

        # calculate the number of required arguments
        optional_arg_count = 0 if not command_callable.__defaults__ else len(command_callable.__defaults__)
        required_arg_count = len(arg_types) - optional_arg_count

        # Offset the level from the one passed to the constructor (to skip parsing the previous command)
        level = self.level + 1

        # create a parser for the command and a group to track required args
        usage_str = (("%s " * level) + "[<args>]") % tuple(sys.argv[0:level])
        parser = argparse.ArgumentParser(description=command_callable.__doc__, usage=usage_str)
        req_args_grp = parser.add_argument_group("required arguments")

        # populate the parser with the arg and type information from the function
        for (arg_idx, arg) in enumerate(arg_types.keys()):
            # determine the long and/or short option names for the argument
            options = self.__get_options_for_arg(arg)

            # We can determine if *this* arg is required based on it's position in the list
            arg_required = arg_idx < required_arg_count

            # set a default description if one isn't defined
            cli_desc = self.argDesc[arg] if arg in self.argDesc else STR_UNDOCUMENTED

            # determine if we're dealing with a boolean argument
            if arg_types[arg] == bool:
                # Boolean arguments are considered flags, and are assumed False if not provided, and True if provided
                parser.add_argument(*options, help=cli_desc, required=False, action='store_true', dest=arg)
            else:
                # determine which group to place an argument in based on whether or not it's required
                grp = req_args_grp if arg_required else parser

                # determine if we need to use the ast module to parse the value
                arg_type = ast.literal_eval if arg_types[arg] in AST_TYPES else arg_types[arg]

                # add the argument to the appropriate group
                grp.add_argument(*options, help=cli_desc, type=arg_type, required=arg_required, dest=arg)

        return parser

