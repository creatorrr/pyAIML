from core_aiml.kernel import Kernel

try:
    input = raw_input
except NameError:
    pass

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
