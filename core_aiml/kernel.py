# -*- coding: latin-1 -*-
"""This file contains the public interface to the aiml module."""
import copy
import glob
import os
import random
import re
import string
import sys
import time
import threading
import xml.sax

from core_aiml import aiml_parser
from core_aiml import default_subs
from core_aiml import utils
from core_aiml.pattern_mgr import PatternMgr
from core_aiml.word_sub import WordSub


# Python2 Compatability
try:
    from configparser import ConfigParser
except ImportError:
    import ConfigParser


class Kernel:
    # module constants
    _global_sessionID = "_global"  # key of the global session (duh)
    _max_history_size = 10  # maximum length of the _inputs and _responses lists
    _max_recursion_depth = 100  # maximum number of recursive <srai>/<sr> tags before the response is aborted.
    # special predicate keys
    _input_history = "_inputHistory"     # keys to a queue (list) of recent user input
    _output_history = "_outputHistory"   # keys to a queue (list) of recent responses.
    _input_stack = "_inputStack"         # Should always be empty in between calls to respond()

    def __init__(self):
        self._verbose_mode = True
        self._version = "PyAIML 0.8.6"
        self._brain = PatternMgr()
        self._respondLock = threading.RLock()
        self._textEncoding = "utf-8"

        # set up the sessions
        self._sessions = {}
        self._add_session(self._global_sessionID)

        # Set up the bot predicates
        self._botPredicates = {}
        self.set_bot_predicate("name", "Nameless")

        # set up the word substitutors (subbers):
        self._subbers = {"gender": WordSub(default_subs.defaultGender),
                         "person": WordSub(default_subs.defaultPerson),
                         "person2": WordSub(default_subs.defaultPerson2),
                         "normal": WordSub(default_subs.defaultNormal)}

        # set up the element processors
        self._elementProcessors = {
            "bot": self._process_bot,
            "condition": self._process_condition,
            "date": self._process_date,
            "formal": self._process_formal,
            "gender": self._process_gender,
            "get": self._process_get,
            "gossip": self._process_gossip,
            "id": self._process_id,
            "input": self._process_input,
            "javascript": self._process_javascript,
            "learn": self._process_learn,
            "li": self._process_li,
            "lowercase": self._process_lowercase,
            "person": self._process_person,
            "person2": self._process_person2,
            "random": self._process_random,
            "text": self._process_text,
            "sentence": self._process_sentence,
            "set": self._process_set,
            "size": self._process_size,
            "sr": self._process_sr,
            "srai": self._process_srai,
            "star": self._process_star,
            "system": self._process_system,
            "template": self._process_template,
            "that": self._process_that,
            "thatstar": self._process_thatstar,
            "think": self._process_think,
            "topicstar": self._process_topicstar,
            "uppercase": self._process_uppercase,
            "version": self._process_version,
        }

    def bootstrap(self, brain_file=None, learn_files=[], commands=[]):
        """Prepare a Kernel object for use.

        If a brainFile argument is provided, the Kernel attempts to
        load the brain at the specified filename.

        If learnFiles is provided, the Kernel attempts to load the
        specified AIML files.

        Finally, each of the input strings in the commands list is
        passed to respond().

        """
        start = time.clock()
        if brain_file:
            self.load_brain(brain_file)

        # learnFiles might be a string, in which case it should be
        # turned into a single-element list.
        learns = learn_files
        try:
            learns = [learn_files + ""]
        except:
            pass
        for file in learns:
            self.learn(file)

        # ditto for commands
        cmds = commands
        try:
            cmds = [commands + ""]
        except:
            pass
        for cmd in cmds:
            print(self._respond(cmd, self._global_sessionID))

        if self._verbose_mode:
            print("Kernel bootstrap completed in {0} seconds".format((time.clock() - start)))

    def verbose(self, isVerbose=True):
        """Enable/disable verbose output mode."""
        self._verbose_mode = isVerbose

    def version(self):
        """Return the Kernel's version string."""
        return self._version

    def num_categories(self):
        """Return the number of categories the Kernel has learned."""
        # there's a one-to-one mapping between templates and categories
        return self._brain.num_templates()

    def reset_brain(self):
        """Reset the brain to its initial state.

        This is essentially equivilant to:
            del(kern)
            kern = aiml.Kernel()

        """
        del self._brain
        self.__init__()

    def load_brain(self, filename):
        """Attempt to load a previously-saved 'brain' from the
        specified filename.

        NOTE: the current contents of the 'brain' will be discarded!

        """
        if self._verbose_mode:
            print("Loading brain from {0}...".format(filename))
        start = time.clock()
        self._brain.restore(filename)
        if self._verbose_mode:
            end = time.clock() - start
            print("done ({0} categories in {1} seconds)".format(self._brain.num_templates(), end))

    def save_brain(self, filename):
        """Dump the contents of the bot's brain to a file on disk."""
        if self._verbose_mode:
            print("Saving brain to {0}...".format(filename))
        start = time.clock()
        self._brain.save(filename)
        if self._verbose_mode:
            print("done ({0} seconds)".format(time.clock() - start))

    def get_predicate(self, name, sessionID=_global_sessionID):
        """Retrieve the current value of the predicate 'name' from the
        specified session.

        If name is not a valid predicate in the session, the empty
        string is returned.

        """
        try:
            return self._sessions[sessionID][name]
        except KeyError:
            return ""

    def set_predicate(self, name, value, sessionID=_global_sessionID):
        """Set the value of the predicate 'name' in the specified
        session.

        If sessionID is not a valid session, it will be created. If
        name is not a valid predicate in the session, it will be
        created.

        """
        self._add_session(sessionID)  # add the session, if it doesn't already exist.
        self._sessions[sessionID][name] = value

    def get_bot_predicate(self, name):
        """Retrieve the value of the specified bot predicate.

        If name is not a valid bot predicate, the empty string is returned.

        """
        try:
            return self._botPredicates[name]
        except KeyError:
            return ""

    def set_bot_predicate(self, name, value):
        """Set the value of the specified bot predicate.

        If name is not a valid bot predicate, it will be created.

        """
        self._botPredicates[name] = value
        # Clumsy hack: if updating the bot name, we must update the
        # name in the brain as well
        if name == "name":
            self._brain.set_bot_name(self.get_bot_predicate("name"))

    def set_text_encoding(self, encoding):
        """Set the text encoding used when loading AIML files (Latin-1, UTF-8, etc.)."""
        self._textEncoding = encoding

    def load_subs(self, filename):
        """Load a substitutions file.

        The file must be in the Windows-style INI format (see the
        standard ConfigParser module docs for information on this
        format).  Each section of the file is loaded into its own
        substituter.

        """
        in_file = file(filename)
        parser = ConfigParser()
        parser.readfp(in_file, filename)
        in_file.close()
        for s in parser.sections():
            # Add a new WordSub instance for this section.  If one already
            # exists, delete it.
            if self._subbers.get(s):
                del(self._subbers[s])
            self._subbers[s] = WordSub()
            # iterate over the key,value pairs and add them to the subber
            for k, v in parser.items(s):
                self._subbers[s][k] = v

    def _add_session(self, sessionID):
        """Create a new session with the specified ID string."""
        if self._sessions.get(sessionID, False):
            return
        # Create the session.
        self._sessions[sessionID] = {
            # Initialize the special reserved predicates
            self._input_history: [],
            self._output_history: [],
            self._input_stack: []
        }

    def _delete_session(self, sessionID):
        """Delete the specified session."""
        if self._sessions.get(sessionID):
            self._sessions.pop(sessionID)

    def get_session_data(self, sessionID=None):
        """Return a copy of the session data dictionary for the
        specified session.

        If no sessionID is specified, return a dictionary containing
        *all* of the individual session dictionaries.

        """
        s = None
        if sessionID is not None:
            try:
                s = self._sessions[sessionID]
            except KeyError:
                s = {}
        else:
            s = self._sessions
        return copy.deepcopy(s)

    def learn(self, filename):
        """Load and learn the contents of the specified AIML file.

        If filename includes wildcard characters, all matching files
        will be loaded and learned.

        """
        for f in glob.glob(filename):
            if self._verbose_mode:
                print("Loading {0}...".format(f))
            start = time.clock()
            # Load and parse the AIML file.
            parser = aiml_parser.create_parser()
            handler = parser.getContentHandler()
            handler.set_encoding(self._textEncoding)
            try:
                parser.parse(f)
            except xml.sax.SAXParseException as msg:
                sys.stderr.write("\nFATAL PARSE ERROR in file {0}:\n{1}\n".format(f, msg))
                continue
            # store the pattern/template pairs in the PatternMgr.
            for key, tem in handler.categories.items():
                # TODO: Put back into TUPLE
                pattern, that, topic = key
                self._brain.add(pattern, that, topic, tem)
            # Parsing was successful.
            if self._verbose_mode:
                print("done ({0} seconds)".format((time.clock() - start)))

    def respond(self, input, sessionID=_global_sessionID):
        """Return the Kernel's response to the input string."""
        if len(input) == 0:
            return ""

        # ensure that input is a unicode string
        try:
            input = input.decode(self._textEncoding, 'replace')
        except UnicodeError:
            pass
        except AttributeError:
            pass

        # prevent other threads from stomping all over us.
        self._respondLock.acquire()

        # Add the session, if it doesn't already exist
        self._add_session(sessionID)

        # split the input into discrete sentences
        sentences = utils.sentences(input)
        final_response = ""
        for s in sentences:
            # Add the input to the history list before fetching the
            # response, so that <input/> tags work properly.
            input_history = self.get_predicate(self._input_history, sessionID)
            input_history.append(s)
            while len(input_history) > self._max_history_size:
                input_history.pop(0)
            self.set_predicate(self._input_history, input_history, sessionID)

            # Fetch the response
            response = self._respond(s, sessionID)

            # add the data from this exchange to the history lists
            output_history = self.get_predicate(self._output_history, sessionID)
            output_history.append(response)
            while len(output_history) > self._max_history_size:
                output_history.pop(0)
            self.set_predicate(self._output_history, output_history, sessionID)

            # append this response to the final response.
            final_response += (response + "  ")
        final_response = final_response.strip()

        assert(len(self.get_predicate(self._input_stack, sessionID)) == 0)

        # release the lock and return
        self._respondLock.release()
        try:
            return final_response
        except UnicodeError:
            return final_response

    # This version of _respond() just fetches the response for some input.
    # It does not mess with the input and output histories.  Recursive calls
    # to respond() spawned from tags like <srai> should call this function
    # instead of respond().
    def _respond(self, input, sessionID):
        """Private version of respond(), does the real work."""
        if len(input) == 0:
            return ""

        # guard against infinite recursion
        input_stack = self.get_predicate(self._input_stack, sessionID)
        if len(input_stack) > self._max_recursion_depth:
            if self._verbose_mode:
                sys.stderr.write("WARNING: maximum recursion depth exceeded (input='{0}')".format(input))
            return ""

        # push the input onto the input stack
        input_stack = self.get_predicate(self._input_stack, sessionID)
        input_stack.append(input)
        self.set_predicate(self._input_stack, input_stack, sessionID)

        # run the input through the 'normal' subber
        subbed_input = self._subbers['normal'].sub(input)

        # fetch the bot's previous response, to pass to the match()
        # function as 'that'.
        output_history = self.get_predicate(self._output_history, sessionID)
        try:
            that = output_history[-1]
        except IndexError:
            that = ""
        subbed_that = self._subbers['normal'].sub(that)

        # fetch the current topic
        topic = self.get_predicate("topic", sessionID)
        subbed_topic = self._subbers['normal'].sub(topic)

        # Determine the final response.
        response = ""
        elem = self._brain.match(subbed_input, subbed_that, subbed_topic)
        if elem is None:
            if self._verbose_mode:
                sys.stderr.write("WARNING: No match found for input: {0}\n".format(input))
        else:
            # Process the element into a response string.
            response += self._process_element(elem, sessionID).strip()
            response += " "
        response = response.strip()

        # pop the top entry off the input stack.
        input_stack = self.get_predicate(self._input_stack, sessionID)
        input_stack.pop()
        self.set_predicate(self._input_stack, input_stack, sessionID)

        return response

    def _process_element(self, elem, sessionID):
        """Process an AIML element.

        The first item of the elem list is the name of the element's
        XML tag.  The second item is a dictionary containing any
        attributes passed to that tag, and their values.  Any further
        items in the list are the elements enclosed by the current
        element's begin and end tags; they are handled by each
        element's handler function.

        """
        try:
            handler_func = self._elementProcessors[elem[0]]
        except:
            # Oops -- there's no handler function for this element
            # type!
            if self._verbose_mode:
                err = "WARNING: No handler found for <{0}> element\n".format(elem[0])
                sys.stderr.write(err)
            return ""
        return handler_func(elem, sessionID)

######################################################
# Individual element-processing functions follow     #
######################################################

    # <bot>
    def _process_bot(self, elem, sessionID):
        """Process a <bot> AIML element.

        Required element attributes:
            name: The name of the bot predicate to retrieve.

        <bot> elements are used to fetch the value of global,
        read-only "bot predicates."  These predicates cannot be set
        from within AIML; you must use the set_bot_predicate() function.

        """
        attr_name = elem[1]['name']
        return self.get_bot_predicate(attr_name)

    # <condition>
    def _process_condition(self, elem, sessionID):
        """Process a <condition> AIML element.

        Optional element attributes:
            name: The name of a predicate to test.
            value: The value to test the predicate for.

        <condition> elements come in three flavors.  Each has different
        attributes, and each handles their contents differently.

        The simplest case is when the <condition> tag has both a 'name'
        and a 'value' attribute.  In this case, if the predicate
        'name' has the value 'value', then the contents of the element
        are processed and returned.

        If the <condition> element has only a 'name' attribute, then
        its contents are a series of <li> elements, each of which has
        a 'value' attribute.  The list is scanned from top to bottom
        until a match is found.  Optionally, the last <li> element can
        have no 'value' attribute, in which case it is processed and
        returned if no other match is found.

        If the <condition> element has neither a 'name' nor a 'value'
        attribute, then it behaves almost exactly like the previous
        case, except that each <li> subelement (except the optional
        last entry) must now include both 'name' and 'value'
        attributes.

        """
        response = ""
        attr = elem[1]

        # Case #1: test the value of a specific predicate for a
        # specific value.
        if attr.get('name') and attr.get('value'):
            val = self.get_predicate(attr['name'], sessionID)
            if val == attr['value']:
                for e in elem[2:]:
                    response += self._process_element(e, sessionID)
                return response
        else:
            # Case #2 and #3: Cycle through <li> contents, testing a
            # name and value pair for each one.
            try:
                name = None
                if attr.get('name'):
                    name = attr['name']
                # Get the list of <li> elemnents
                listitems = []
                for e in elem[2:]:
                    if e[0] == 'li':
                        listitems.append(e)
                # if listitems is empty, return the empty string
                if len(listitems) == 0:
                    return ""
                # iterate through the list looking for a condition that
                # matches.
                found_match = False
                for li in listitems:
                    try:
                        li_attr = li[1]
                        # if this is the last list item, it's allowed
                        # to have no attributes.  We just skip it for now.
                        if len(li_attr.keys()) == 0 and li == listitems[-1]:
                            continue
                        # get the name of the predicate to test
                        li_name = name
                        if li_name is None:
                            li_name = li_attr['name']
                        # get the value to check against
                        liValue = li_attr['value']
                        # do the test
                        if self.get_predicate(li_name, sessionID) == liValue:
                            found_match = True
                            response += self._process_element(li, sessionID)
                            break
                    except:
                        # No attributes, no name/value attributes, no
                        # such predicate/session, or processing error.
                        if self._verbose_mode:
                            print("Something amiss -- skipping listitem", li)
                        raise
                if not found_match:
                    # Check the last element of listitems.  If it has
                    # no 'name' or 'value' attribute, process it.
                    try:
                        li = listitems[-1]
                        li_attr = li[1]
                        if not (li_attr.get('name') or li_attr.get('value')):
                            response += self._process_element(li, sessionID)
                    except:
                        # listitems was empty, no attributes, missing
                        # name/value attributes, or processing error.
                        if self._verbose_mode:
                            print("error in default listitem")
                        raise
            except:
                # Some other catastrophic cataclysm
                if self._verbose_mode:
                    print("catastrophic condition failure")
                raise
        return response

    # <date>
    @staticmethod
    def _process_date(elem, sessionID):
        """Process a <date> AIML element.

        <date> elements resolve to the current date and time.  The
        AIML specification doesn't require any particular format for
        this information, so I go with whatever's simplest.

        """
        return time.asctime()

    # <formal>
    def _process_formal(self, elem, sessionID):
        """Process a <formal> AIML element.

        <formal> elements process their contents recursively, and then
        capitalize the first letter of each word of the result.

        """
        response = ""
        for e in elem[2:]:
            response += self._process_element(e, sessionID)
        return string.capwords(response)

    # <gender>
    def _process_gender(self, elem, sessionID):
        """Process a <gender> AIML element.

        <gender> elements process their contents, and then swap the
        gender of any third-person singular pronouns in the result.
        This subsitution is handled by the aiml.WordSub module.

        """
        response = ""
        for e in elem[2:]:
            response += self._process_element(e, sessionID)
        return self._subbers['gender'].sub(response)

    # <get>
    def _process_get(self, elem, sessionID):
        """Process a <get> AIML element.

        Required element attributes:
            name: The name of the predicate whose value should be
            retrieved from the specified session and returned.  If the
            predicate doesn't exist, the empty string is returned.

        <get> elements return the value of a predicate from the
        specified session.

        """
        return self.get_predicate(elem[1]['name'], sessionID)

    # <gossip>
    def _process_gossip(self, elem, sessionID):
        """Process a <gossip> AIML element.

        <gossip> elements are used to capture and store user input in
        an implementation-defined manner, theoretically allowing the
        bot to learn from the people it chats with.  I haven't
        descided how to define my implementation, so right now
        <gossip> behaves identically to <think>.

        """
        return self._process_think(elem, sessionID)

    # <id>
    def _process_id(self, elem, sessionID):
        """ Process an <id> AIML element.

        <id> elements return a unique "user id" for a specific
        conversation.  In PyAIML, the user id is the name of the
        current session.

        """
        return sessionID

    # <input>
    def _process_input(self, elem, sessionID):
        """Process an <input> AIML element.

        Optional attribute elements:
            index: The index of the element from the history list to
            return. 1 means the most recent item, 2 means the one
            before that, and so on.

        <input> elements return an entry from the input history for
        the current session.

        """
        input_history = self.get_predicate(self._input_history, sessionID)
        try:
            index = int(elem[1]['index'])
        except:
            index = 1
        try:
            return input_history[-index]
        except IndexError:
            if self._verbose_mode:
                sys.stderr.write("No such index {0} while processing <input> element.\n".format(index))
            return ""

    # <javascript>
    def _process_javascript(self, elem, sessionID):
        """Process a <javascript> AIML element.

        <javascript> elements process their contents recursively, and
        then run the results through a server-side Javascript
        interpreter to compute the final response.  Implementations
        are not required to provide an actual Javascript interpreter,
        and right now PyAIML doesn't; <javascript> elements are behave
        exactly like <think> elements.

        """
        return self._process_think(elem, sessionID)

    # <learn>
    def _process_learn(self, elem, sessionID):
        """Process a <learn> AIML element.

        <learn> elements process their contents recursively, and then
        treat the result as an AIML file to open and learn.

        """
        filename = ""
        for e in elem[2:]:
            filename += self._process_element(e, sessionID)
        self.learn(filename)
        return ""

    # <li>
    def _process_li(self, elem, sessionID):
        """Process an <li> AIML element.

        Optional attribute elements:
            name: the name of a predicate to query.
            value: the value to check that predicate for.

        <li> elements process their contents recursively and return
        the results. They can only appear inside <condition> and
        <random> elements.  See _process_condition() and
        _process_random() for details of their usage.

        """
        response = ""
        for e in elem[2:]:
            response += self._process_element(e, sessionID)
        return response

    # <lowercase>
    def _process_lowercase(self, elem, sessionID):
        """Process a <lowercase> AIML element.

        <lowercase> elements process their contents recursively, and
        then convert the results to all-lowercase.

        """
        response = ""
        for e in elem[2:]:
            response += self._process_element(e, sessionID)
        return string.lower(response)

    # <person>
    def _process_person(self, elem, sessionID):
        """Process a <person> AIML element.

        <person> elements process their contents recursively, and then
        convert all pronouns in the results from 1st person to 2nd
        person, and vice versa.  This subsitution is handled by the
        aiml.WordSub module.

        If the <person> tag is used atomically (e.g. <person/>), it is
        a shortcut for <person><star/></person>.

        """
        response = ""
        for e in elem[2:]:
            response += self._process_element(e, sessionID)
        if len(elem[2:]) == 0:  # atomic <person/> = <person><star/></person>
            response = self._process_element(['star', {}], sessionID)
        return self._subbers['person'].sub(response)

    # <person2>
    def _process_person2(self, elem, sessionID):
        """Process a <person2> AIML element.

        <person2> elements process their contents recursively, and then
        convert all pronouns in the results from 1st person to 3rd
        person, and vice versa.  This subsitution is handled by the
        aiml.WordSub module.

        If the <person2> tag is used atomically (e.g. <person2/>), it is
        a shortcut for <person2><star/></person2>.

        """
        response = ""
        for e in elem[2:]:
            response += self._process_element(e, sessionID)
        if len(elem[2:]) == 0:  # atomic <person2/> = <person2><star/></person2>
            response = self._process_element(['star', {}], sessionID)
        return self._subbers['person2'].sub(response)

    # <random>
    def _process_random(self, elem, sessionID):
        """Process a <random> AIML element.

        <random> elements contain zero or more <li> elements.  If
        none, the empty string is returned.  If one or more <li>
        elements are present, one of them is selected randomly to be
        processed recursively and have its results returned.  Only the
        chosen <li> element's contents are processed.  Any non-<li> contents are
        ignored.

        """
        listitems = []
        for e in elem[2:]:
            if e[0] == 'li':
                listitems.append(e)
        if len(listitems) == 0:
            return ""

        # select and process a random listitem.
        random.shuffle(listitems)
        return self._process_element(listitems[0], sessionID)

    # <sentence>
    def _process_sentence(self, elem, sessionID):
        """Process a <sentence> AIML element.

        <sentence> elements process their contents recursively, and
        then capitalize the first letter of the results.

        """
        response = ""
        for e in elem[2:]:
            response += self._process_element(e, sessionID)
        try:
            response = response.strip()
            words = string.split(response, " ", 1)
            words[0] = string.capitalize(words[0])
            response = string.join(words)
            return response
        except IndexError:  # response was empty
            return ""

    # <set>
    def _process_set(self, elem, sessionID):
        """Process a <set> AIML element.

        Required element attributes:
            name: The name of the predicate to set.

        <set> elements process their contents recursively, and assign the results to a predicate
        (given by their 'name' attribute) in the current session.  The contents of the element
        are also returned.

        """
        value = ""
        for e in elem[2:]:
            value += self._process_element(e, sessionID)
        self.set_predicate(elem[1]['name'], value, sessionID)
        return value

    # <size>
    def _process_size(self, elem, sessionID):
        """Process a <size> AIML element.

        <size> elements return the number of AIML categories currently
        in the bot's brain.

        """
        return str(self.num_categories())

    # <sr>
    def _process_sr(self, elem, sessionID):
        """Process an <sr> AIML element.

        <sr> elements are shortcuts for <srai><star/></srai>.

        """
        star = self._process_element(['star', {}], sessionID)
        return self._respond(star, sessionID)

    # <srai>
    def _process_srai(self, elem, sessionID):
        """Process a <srai> AIML element.

        <srai> elements recursively process their contents, and then
        pass the results right back into the AIML interpreter as a new
        piece of input.  The results of this new input string are
        returned.

        """
        new_input = ""
        for e in elem[2:]:
            new_input += self._process_element(e, sessionID)
        return self._respond(new_input, sessionID)

    # <star>
    def _process_star(self, elem, sessionID):
        """Process a <star> AIML element.

        Optional attribute elements:
            index: Which "*" character in the current pattern should
            be matched?

        <star> elements return the text fragment matched by the "*"
        character in the current input pattern.  For example, if the
        input "Hello Tom Smith, how are you?" matched the pattern
        "HELLO * HOW ARE YOU", then a <star> element in the template
        would evaluate to "Tom Smith".

        """
        try:
            index = int(elem[1]['index'])
        except KeyError:
            index = 1
        # fetch the user's last input
        input_stack = self.get_predicate(self._input_stack, sessionID)
        input = self._subbers['normal'].sub(input_stack[-1])
        # fetch the Kernel's last response (for 'that' context)
        output_history = self.get_predicate(self._output_history, sessionID)
        try:
            that = self._subbers['normal'].sub(output_history[-1])
        except:
            that = ""  # there might not be any output yet
        topic = self.get_predicate("topic", sessionID)
        response = self._brain.star("star", input, that, topic, index)
        return response

    # <system>
    def _process_system(self, elem, sessionID):
        """Process a <system> AIML element.

        <system> elements process their contents recursively, and then
        attempt to execute the results as a shell command on the
        server.  The AIML interpreter blocks until the command is
        complete, and then returns the command's output.

        For cross-platform compatibility, any file paths inside
        <system> tags should use Unix-style forward slashes ("/") as a
        directory separator.

        """
        # build up the command string
        command = ""
        for e in elem[2:]:
            command += self._process_element(e, sessionID)

        # normalize the path to the command.  Under Windows, this
        # switches forward-slashes to back-slashes; all system
        # elements should use unix-style paths for cross-platform
        # compatibility.
        # executable,args = command.split(" ", 1)
        # executable = os.path.normpath(executable)
        # command = executable + " " + args
        command = os.path.normpath(command)

        # execute the command.
        response = ""
        try:
            out = os.popen(command)
        except RuntimeError as msg:
            if self._verbose_mode:
                err = "WARNING: RuntimeError while processing \"system\" element:\n{0}\n".format(msg)
                sys.stderr.write(err)
            return "There was an error while computing my response.  Please inform my botmaster."
        time.sleep(0.01)  # I'm told this works around a potential IOError exception.
        for line in out:
            response += line + "\n"
        response = string.join(response.splitlines()).strip()
        return response

    # <template>
    def _process_template(self, elem, sessionID):
        """Process a <template> AIML element.

        <template> elements recursively process their contents, and
        return the results.  <template> is the root node of any AIML
        response tree.

        """
        response = ""
        for e in elem[2:]:
            response += self._process_element(e, sessionID)
        return response

    # text
    def _process_text(self, elem, sessionID):
        """Process a raw text element.

        Raw text elements aren't really AIML tags. Text elements cannot contain
        other elements; instead, the third item of the 'elem' list is a text
        string, which is immediately returned. They have a single attribute,
        automatically inserted by the parser, which indicates whether whitespace
        in the text should be preserved or not.

        """
        try:
            elem[2] + ""
        except TypeError:
            raise TypeError("Text element contents are not text")

        # If the the whitespace behavior for this element is "default",
        # we reduce all stretches of >1 whitespace characters to a single
        # space.  To improve performance, we do this only once for each
        # text element encountered, and save the results for the future.
        if elem[1]["xml:space"] == "default":
            elem[2] = re.sub("\s+", " ", elem[2])
            elem[1]["xml:space"] = "preserve"
        return elem[2]

    # <that>
    def _process_that(self, elem, sessionID):
        """Process a <that> AIML element.

        Optional element attributes:
            index: Specifies which element from the output history to
            return.  1 is the most recent response, 2 is the next most
            recent, and so on.

        <that> elements (when they appear inside <template> elements)
        are the output equivilant of <input> elements; they return one
        of the Kernel's previous responses.

        """
        output_history = self.get_predicate(self._output_history, sessionID)
        index = 1
        try:
            # According to the AIML spec, the optional index attribute
            # can either have the form "x" or "x,y". x refers to how
            # far back in the output history to go.  y refers to which
            # sentence of the specified response to return.
            index = int(elem[1]['index'].split(',')[0])
        except:
            pass
        try:
            return output_history[-index]
        except IndexError:
            if self._verbose_mode:
                sys.stderr.write("No such index {0} while processing <that> element.\n".format(index))
            return ""

    # <thatstar>
    def _process_thatstar(self, elem, sessionID):
        """Process a <thatstar> AIML element.

        Optional element attributes:
            index: Specifies which "*" in the <that> pattern to match.

        <thatstar> elements are similar to <star> elements, except
        that where <star/> returns the portion of the input string
        matched by a "*" character in the pattern, <thatstar/> returns
        the portion of the previous input string that was matched by a
        "*" in the current category's <that> pattern.

        """
        try:
            index = int(elem[1]['index'])
        except KeyError:
            index = 1
        # fetch the user's last input
        input_stack = self.get_predicate(self._input_stack, sessionID)
        input = self._subbers['normal'].sub(input_stack[-1])
        # fetch the Kernel's last response (for 'that' context)
        output_history = self.get_predicate(self._output_history, sessionID)
        try:
            that = self._subbers['normal'].sub(output_history[-1])
        except:
            that = ""  # there might not be any output yet
        topic = self.get_predicate("topic", sessionID)
        response = self._brain.star("thatstar", input, that, topic, index)
        return response

    # <think>
    def _process_think(self, elem, sessionID):
        """Process a <think> AIML element.

        <think> elements process their contents recursively, and then
        discard the results and return the empty string.  They're
        useful for setting predicates and learning AIML files without
        generating any output.

        """
        for e in elem[2:]:
            self._process_element(e, sessionID)
        return ""

    # <topicstar>
    def _process_topicstar(self, elem, sessionID):
        """Process a <topicstar> AIML element.

        Optional element attributes:
            index: Specifies which "*" in the <topic> pattern to match.

        <topicstar> elements are similar to <star> elements, except
        that where <star/> returns the portion of the input string
        matched by a "*" character in the pattern, <topicstar/>
        returns the portion of current topic string that was matched
        by a "*" in the current category's <topic> pattern.

        """
        try:
            index = int(elem[1]['index'])
        except KeyError:
            index = 1
        # fetch the user's last input
        input_stack = self.get_predicate(self._input_stack, sessionID)
        input = self._subbers['normal'].sub(input_stack[-1])
        # fetch the Kernel's last response (for 'that' context)
        output_history = self.get_predicate(self._output_history, sessionID)
        try:
            that = self._subbers['normal'].sub(output_history[-1])
        except:
            that = ""  # there might not be any output yet
        topic = self.get_predicate("topic", sessionID)
        response = self._brain.star("topicstar", input, that, topic, index)
        return response

    # <uppercase>
    def _process_uppercase(self, elem, sessionID):
        """Process an <uppercase> AIML element.

        <uppercase> elements process their contents recursively, and
        return the results with all lower-case characters converted to
        upper-case.

        """
        response = ""
        for e in elem[2:]:
            response += self._process_element(e, sessionID)
        return string.upper(response)

    # <version>
    def _process_version(self, elem, sessionID):
        """Process a <version> AIML element.

        <version> elements return the version number of the AIML
        interpreter.

        """
        return self.version()
