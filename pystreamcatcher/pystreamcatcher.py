#!/usr/bin/env python

from threading import Thread
from urllib.parse import urlparse
import os.path
import sys
import time
import http.client

_value_stream_url = None
_value_output_file = None
_value_timeout = None
keepGoing = True

def stderr (someString = ""):
  print(someString, file=sys.stderr)

def printUsageString ():
  stderr("Usage: %s <mandatory_options>" % sys.argv[0])
  stderr("Description: %s records the contents of an HTTP stream into a file for an arbitrary length of time" % sys.argv[0])
  stderr()
  stderr("Mandatory arguments to long options are mandatory for short options too.")
  stderr("  -t, --time <seconds>       [MANDATORY] capture stream for <seconds> number of seconds")
  stderr("  -u, --url  <URL>           [MANDATORY] capture from the specified <URL>")
  stderr("  -f, --file <filename>      [MANDATORY] save the captured stream into <filename>")
  stderr("  -h, -?, --help             display this help message and then exit")
  stderr()
  stderr("Exit status:")
  stderr(" 0  if OK,")
  stderr(" 1  if not OK (further explanation [usually] provided).")
  stderr()
  stderr("Suggest features or report bugs to jpsutton@gmail.com")
  stderr()
  stderr("LICENSE: This code is licensed under the GNU General Public License, Version 2 ONLY.")

def die (errorMsg):
  stderr("*** Error: %s" % errorMsg)
  stderr()
  printUsageString()
  exit(1)


def printHelpExit ():
  printUsageString()
  exit(0)

def processArgs ():
  global _value_stream_url, _value_output_file, _value_timeout
  _flag_skip_next_arg = False

  if len(sys.argv) < 2:
    die("You must pass at least one file as an argument")
  
  possibleArgs = [
    { "required": True,  "possibleOption": ("-t", "--time"),       "valueReference": "_value_timeout" },
    { "required": True,  "possibleOption": ("-u", "--url"),        "valueReference": "_value_stream_url" },
    { "required": True,  "possibleOption": ("-f", "--file"),       "valueReference": "_value_output_file" },
    { "required": False, "possibleOption": ("-h", "-?", "--help"), "valueReference": None, "argFunction": printHelpExit },
  ]
  
  for index in range(1, len(sys.argv)):
    if _flag_skip_next_arg == True:
      _flag_skip_next_arg = False
      continue
    
    arg = sys.argv[index]
    
    noneMatched = True
    
    for possibleArg in possibleArgs:
      if arg in possibleArg["possibleOption"]:
        if possibleArg["valueReference"] is not None:
          _flag_skip_next_arg = True
          globals()[possibleArg["valueReference"]] = sys.argv[index + 1]
        if "argFunction" in possibleArg and possibleArg["argFunction"] is not None:
          possibleArg["argFunction"]()
          
        noneMatched = False
        break
    
    if noneMatched:
      pass #Note: implement this block for default argument processing

  for arg in possibleArgs:
    if arg["required"] and "valueReference" in arg:
      if globals()[arg["valueReference"]] is None:
        die("you must pass the %s option" % str(arg["possibleOption"]))
    

class StreamThread (Thread):
  def __init__ (self, streamURL, fileName):
    self.streamURL = streamURL
    self.filename = fileName
    Thread.__init__(self)

  def run (self):
     parsedURL = urlparse(self.streamURL)
     hostname = parsedURL.netloc
     streamPath = parsedURL.path
     conn = http.client.HTTPConnection(hostname)
     conn.request("GET", streamPath)
     response = conn.getresponse()

     if os.path.exists(self.filename):
       sys.stderr.write("ERROR: the file/folder %s already exists\n" % self.filename)
       exit(1)

     with open(self.filename, "wb") as fileHandle:
       while keepGoing:
         if response is not None:
           data = response.read(1024)

           if len(data) > 0:
             fileHandle.write(data)
             #print("Streamer: wrote 1024 bytes... %s" % str(data))
         else:
           break

processArgs()
streamer = StreamThread(_value_stream_url, _value_output_file)
streamer.start()
time.sleep(int(_value_timeout))
keepGoing = False
