# -*- coding: latin-1 -*-
from __future__ import unicode_literals

import time
from core_aiml.kernel import Kernel

###############################################################################
### Self-test functions follow         WHY ARE THESE HERE!!! RESOLVE        ###
###############################################################################
def _testTag(kern, tag, input, outputList):
    """Tests 'tag' by feeding the Kernel 'input'.  If the result
    matches any of the strings in 'outputList', the test passes.

    """
    global _numTests, _numPassed
    _numTests += 1
    print("Testing <" + tag + ">:")
    response = kern.respond(input)
    if response in outputList:
        print("PASSED")
        _numPassed += 1
        return True
    else:
        print("FAILED (response: '{0}')".format((response.encode(kern._textEncoding, 'replace'))))
        return False



k = Kernel()
k.bootstrap(learn_files="self-test.aiml")

global _numTests, _numPassed
_numTests = 0
_numPassed = 0

_testTag(k, 'bot', 'test bot', ["My name is Nameless"])

k.set_predicate('gender', 'male')
_testTag(k, 'condition test #1', 'test condition name value', ['You are handsome'])
k.set_predicate('gender', 'female')
_testTag(k, 'condition test #2', 'test condition name value', [''])
_testTag(k, 'condition test #3', 'test condition name', ['You are beautiful'])
k.set_predicate('gender', 'robot')
_testTag(k, 'condition test #4', 'test condition name', ['You are genderless'])
_testTag(k, 'condition test #5', 'test condition', ['You are genderless'])
k.set_predicate('gender', 'male')
_testTag(k, 'condition test #6', 'test condition', ['You are handsome'])

# the date test will occasionally fail if the original and "test"
# times cross a second boundary.  There's no good way to avoid
# this problem and still do a meaningful test, so we simply
# provide a friendly message to be printed if the test fails.
date_warning = """
NOTE: the <date> test will occasionally report failure even if it
succeeds.  So long as the response looks like a date/time string,
there's nothing to worry about.
"""
if not _testTag(k, 'date', 'test date', ["The date is %s" % time.asctime()]):
    print(date_warning)

_testTag(k, 'formal', 'test formal', ["Formal Test Passed"])
_testTag(k, 'gender', 'test gender', ["He'd told her he heard that her hernia is history"])
_testTag(k, 'get/set', 'test get and set', ["I like cheese. My favorite food is cheese"])
_testTag(k, 'gossip', 'test gossip', ["Gossip is not yet implemented"])
_testTag(k, 'id', 'test id', ["Your id is _global"])
_testTag(k, 'input', 'test input', ['You just said: test input'])
_testTag(k, 'javascript', 'test javascript', ["Javascript is not yet implemented"])
_testTag(k, 'lowercase', 'test lowercase', ["The Last Word Should Be lowercase"])
_testTag(k, 'person', 'test person', ['HE think i knows that my actions threaten him and his.'])
_testTag(k, 'person2', 'test person2', ['YOU think me know that my actions threaten you and yours.'])
_testTag(k, 'person2 (no contents)', 'test person2 I Love Lucy', ['YOU Love Lucy'])
_testTag(k, 'random', 'test random', ["response #1", "response #2", "response #3"])
_testTag(k, 'random empty', 'test random empty', ["Nothing here!"])
_testTag(k, 'sentence', "test sentence", ["My first letter should be capitalized."])
_testTag(k, 'size', "test size", ["I've learned %d categories" % k.num_categories()])
_testTag(k, 'sr', "test sr test srai", ["srai results: srai test passed"])
_testTag(k, 'sr nested', "test nested sr test srai", ["srai results: srai test passed"])
_testTag(k, 'srai', "test srai", ["srai test passed"])
_testTag(k, 'srai infinite', "test srai infinite", [""])
_testTag(k, 'star test #1', 'You should test star begin', ['Begin star matched: You should'])
_testTag(k, 'star test #2', 'test star creamy goodness middle', ['Middle star matched: creamy goodness'])
_testTag(k, 'star test #3', 'test star end the credits roll', ['End star matched: the credits roll'])
_testTag(k, 'star test #4', 'test star having multiple stars in a pattern makes me extremely happy',
         ['Multiple stars matched: having, stars in a pattern, extremely happy'])
_testTag(k, 'system', "test system", ["The system says hello!"])
_testTag(k, 'that test #1', "test that", ["I just said: The system says hello!"])
_testTag(k, 'that test #2', "test that", ["I have already answered this question"])
_testTag(k, 'thatstar test #1', "test thatstar", ["I say beans"])
_testTag(k, 'thatstar test #2', "test thatstar", ["I just said \"beans\""])
_testTag(k, 'thatstar test #3', "test thatstar multiple", ['I say beans and franks for everybody'])
_testTag(k, 'thatstar test #4', "test thatstar multiple", ['Yes, beans and franks for all!'])
_testTag(k, 'think', "test think", [""])
k.set_predicate("topic", "fruit")
_testTag(k, 'topic', "test topic", ["We were discussing apples and oranges"])
k.set_predicate("topic", "Soylent Green")
_testTag(k, 'topicstar test #1', 'test topicstar', ["Solyent Green is made of people!"])
k.set_predicate("topic", "Soylent Ham and Cheese")
_testTag(k, 'topicstar test #2', 'test topicstar multiple', ["Both Soylents Ham and Cheese are made of people!"])
_testTag(k, 'unicode support', u"ÔÇÉÏºÃ", [u"Hey, you speak Chinese! ÔÇÉÏºÃ"])
_testTag(k, 'uppercase', 'test uppercase', ["The Last Word Should Be UPPERCASE"])
_testTag(k, 'version', 'test version', ["PyAIML is version %s" % k.version()])
_testTag(k, 'whitespace preservation', 'test whitespace', ["Extra   Spaces\n   Rule!   (but not in here!)    But   Here   They   Do!"])

# Report test results
print("--------------------")
if _numTests == _numPassed:
    print("{0} of {1} tests passed!".format(_numPassed, _numTests))
else:
    print("{0} of {1} tests passed (see above for detailed errors)".format(_numPassed, _numTests))

