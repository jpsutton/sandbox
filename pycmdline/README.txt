================================================
  pycmdline
================================================

This project attempts to combine the usefulness and convenience of the Python interpreter with that of the OS shell.  Commands entered will take the following precedence:
  * Built-in handlers called "PyCommands" (e.g., "cd", "exit", "whatis")
  * OS executables (any executable on the PATH)
  * Python statements

Pycmdline is in a very early, even experimental, stage of development.  Tab-completion works for some scenarios but will be improved.  Piping has not been implemented yet but is planned.