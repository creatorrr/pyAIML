pyAIML
======

**NOTE: This repo has been cloned from sourceforge. Credits follow.**

PyAIML -- The Python AIML Interpreter

Original Author: Cort Stratton (cort@users.sourceforge.net)
Original Source Code: http://pyaiml.sourceforge.net/

Contributor: Chloe Parkes (@MissMaximas)

**CHANGE LOG**

This copy of AIML has been converted to Python3. Bear with me,
it still isn't tested. That's on my TODO list 

There's a brief example of patterns in the aiml/ folder,
if you make any changes in here, please don't push them
up to this repository as these are purely for manual testing.

pyAIML
------

PyAIML is an interpreter for AIML (the Artificial Intelligence Markup
Language), implemented entirely in standard Python.  It strives for
simple, austere, 100% compliance with the AIML 1.0.1 standard, no less
and no more.

This is currently pre-alpha software.  Use at your
own risk!

For information on the state of development, including 
the current level of AIML 1.0.1 compliance, see the
SUPPORTED_TAGS.txt file.

Quick & dirty example (There's a run.py file, just execute that otherwise):

```python

# The Kernel object is the public interface to
# the AIML interpreter.
k = Kernel()

# Use the 'learn' method to load the contents
# of an AIML file into the Kernel.
k.learn("aiml/*.aiml")

# Use the 'respond' method to compute the response
# to a user's input string.  respond() returns
# the interpreter's response, which in this case
# we ignore.

# Loop forever, reading user input from the command
# line and printing responses.
while True:
    print(k.respond(input("> ")))
```
