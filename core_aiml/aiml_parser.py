from xml.sax.handler import ContentHandler
from xml.sax.xmlreader import Locator
import xml.sax
import xml.sax.handler
import sys

# Python2 Compatability
try:
    str = unicode
except NameError:
    pass


class AimlParserError(Exception):
    pass


class AimlHandler(ContentHandler):

    # The legal states of the AIML parser
    _STATE_outside_aiml = 0
    _STATE_inside_aiml = 1
    _STATE_inside_category = 2
    _STATE_inside_pattern = 3
    _STATE_after_pattern = 4
    _STATE_inside_that = 5
    _STATE_after_that = 6
    _STATE_inside_template = 7
    _STATE_after_template = 8

    def __init__(self, encoding="UTF-8"):
        self.categories = {}
        self._encoding = encoding
        self._state = self._STATE_outside_aiml
        self._version = ""
        self._namespace = ""
        self._forward_compatible_mode = False
        self._current_pattern = ""
        self._current_that = ""
        self._current_topic = ""
        self._inside_topic = False
        self._current_unknown = ""  # the name of the current unknown element

        # This is set to true when a parse error occurs in a category.
        self._skip_current_category = False

        # Counts the number of parse errors in a particular AIML document.
        # query with get_num_errors().  If 0, the document is AIML-compliant.
        self._num_parse_errors = 0

        # TODO: select the proper validInfo table based on the version number.
        self._valid_info = self._validation_info101

        # This stack of bools is used when parsing <li> elements inside
        # <condition> elements, to keep track of whether or not an
        # attribute-less "default" <li> element has been found yet.  Only
        # one default <li> is allowed in each <condition> element.  We need
        # a stack in order to correctly handle nested <condition> tags.
        self._found_default_li_stack = []

        # This stack of strings indicates what the current whitespace-handling
        # behavior should be.  Each string in the stack is either "default" or
        # "preserve".  When a new AIML element is encountered, a new string is
        # pushed onto the stack, based on the value of the element's "xml:space"
        # attribute (if absent, the top of the stack is pushed again).  When
        # ending an element, pop an object off the stack.
        self._whitespace_behavior_stack = ["default"]

        self._elem_stack = []
        self._locator = Locator()
        self.setDocumentLocator(self._locator)

    def get_num_errors(self):
        "Return the number of errors found while parsing the current document."
        return self._num_parse_errors

    def set_encoding(self, encoding):
        """Set the text encoding to use when encoding strings read from XML.

        Defaults to 'UTF-8'.

        """
        self._encoding = encoding

    def _location(self):
        "Return a string describing the current location in the source file."
        line = self._locator.getLineNumber()
        column = self._locator.getColumnNumber()
        return "(line {0}, column {1})".format(line, column)

    def _push_whitespace_behavior(self, attr):
        """Push a new string onto the whitespaceBehaviorStack.

        The string's value is taken from the "xml:space" attribute, if it exists
        and has a legal value ("default" or "preserve").  Otherwise, the previous
        stack element is duplicated.

        """
        assert len(self._whitespace_behavior_stack) > 0, "Whitespace behavior stack should never be empty!"
        try:
            if attr["xml:space"] == "default" or attr["xml:space"] == "preserve":
                self._whitespace_behavior_stack.append(attr["xml:space"])
            else:
                print
                raise AimlParserError("Invalid value for xml:space attribute " + self._location())
        except KeyError:
            self._whitespace_behavior_stack.append(self._whitespace_behavior_stack[-1])

    def startElementNS(self, name, qname, attr):
        print("QNAME: ", qname)
        print("NAME: ", name)
        uri, elem = name
        if elem == "bot":
            print("name:", attr.getValueByQName("name"), "a'ite?")
        self.startElement(elem, attr)
        pass

    def startElement(self, name, attr):
        # Wrapper around _start_element, which catches errors in _start_element()
        # and keeps going.

        # If we're inside an unknown element, ignore everything until we're
        # out again.
        if self._current_unknown != "":
            return
        # If we're skipping the current category, ignore everything until
        # it's finished.
        if self._skip_current_category:
            return

        # process this start-element.
        try:
            self._start_element(name, attr)
        except AimlParserError as msg:
            # Print the error message
            sys.stderr.write("PARSE ERROR: {0}\n".format(msg))

            self._num_parse_errors += 1  # increment error count
            # In case of a parse error, if we're inside a category, skip it.
            if self._state >= self._STATE_inside_category:
                self._skip_current_category = True

    def _start_element(self, name, attr):
        if name == "aiml":
            # <aiml> tags are only legal in the OutsideAiml state
            if self._state != self._STATE_outside_aiml:
                raise AimlParserError("Unexpected <aiml> tag " + self._location())
            self._state = self._STATE_inside_aiml
            self._inside_topic = False
            self._current_topic = ""
            try:
                self._version = attr["version"]
            except KeyError:
                # This SHOULD be a syntax error, but so many AIML sets out there are missing
                # "version" attributes that it just seems nicer to let it slide.
                # raise AimlParserError, "Missing 'version' attribute in <aiml> tag "+self._location()
                # print "WARNING: Missing 'version' attribute in <aiml> tag "+self._location()
                # print "         Defaulting to version 1.0"
                self._version = "1.0"
            self._forward_compatible_mode = (self._version != "1.0.1")
            self._push_whitespace_behavior(attr)
        # Not a comments from @MissMaximass
        # Not sure about this namespace business yet...
        # try:
        # 	self._namespace = attr["xmlns"]
        # 	if self._version == "1.0.1" and self._namespace != "http://alicebot.org/2001/AIML-1.0.1":
        # 		raise AimlParserError, "Incorrect namespace for AIML v1.0.1 "+self._location()
        # except KeyError:
        # 	if self._version != "1.0":
        # 		raise AimlParserError, "Missing 'version' attribute(s) in <aiml> tag "+self._location()
        elif self._state == self._STATE_outside_aiml:
            # If we're outside of an AIML element, we ignore all tags.
            return
        elif name == "topic":
            # <topic> tags are only legal in the InsideAiml state, and only
            # if we're not already inside a topic.
            if (self._state != self._STATE_inside_aiml) or self._inside_topic:
                raise AimlParserError("Unexpected <topic> tag" + self._location())
            try:
                self._current_topic = attr['name']
            except KeyError:
                raise AimlParserError("Required \"name\" attribute missing in <topic> element " + self._location())
            self._inside_topic = True
        elif name == "category":
            # <category> tags are only legal in the InsideAiml state
            if self._state != self._STATE_inside_aiml:
                raise AimlParserError("Unexpected <category> tag " + self._location())
            self._state = self._STATE_inside_category
            self._current_pattern = ""
            self._current_that = ""
            # If we're not inside a topic, the topic is implicitly set to *
            if not self._inside_topic:
                self._current_topic = "*"
            self._elem_stack = []
            self._push_whitespace_behavior(attr)
        elif name == "pattern":
            # <pattern> tags are only legal in the InsideCategory state
            if self._state != self._STATE_inside_category:
                raise AimlParserError("Unexpected <pattern> tag " + self._location())
            self._state = self._STATE_inside_pattern
        elif name == "that" and self._state == self._STATE_after_pattern:
            # <that> are legal either inside a <template> element, or
            # inside a <category> element, between the <pattern> and the
            # <template> elements.  This clause handles the latter case.
            self._state = self._STATE_inside_that
        elif name == "template":
            # <template> tags are only legal in the AfterPattern and AfterThat
            # states
            if self._state not in [self._STATE_after_pattern, self._STATE_after_that]:
                raise AimlParserError("Unexpected <template> tag " + self._location())
            # if no <that> element was specified, it is implicitly set to *
            if self._state == self._STATE_after_pattern:
                self._current_that = "*"
            self._state = self._STATE_inside_template
            self._elem_stack.append(['template', {}])
            self._push_whitespace_behavior(attr)
        elif self._state == self._STATE_inside_pattern:
            # Certain tags are allowed inside <pattern> elements.
            if name == "bot" and attr.get("name", False) and attr["name"] == "name":
                # Insert a special character string that the PatternMgr will
                # replace with the bot's name.
                self._current_pattern += " BOT_NAME "
            else:
                raise AimlParserError(("Unexpected <{0}> tag ".format(name)) + self._location())
        elif self._state == self._STATE_inside_that:
            # Certain tags are allowed inside <that> elements.
            if name == "bot" and attr.get("name", False) and attr["name"] == "name":
                # Insert a special character string that the PatternMgr will
                # replace with the bot's name.
                self._current_that += " BOT_NAME "
            else:
                raise AimlParserError(("Unexpected <{0}> tag ".format(name)) + self._location())
        elif self._state == self._STATE_inside_template and self._valid_info.get(name, False):
            # Starting a new element inside the current pattern. First
            # we need to convert 'attr' into a native Python dictionary,
            # so it can later be marshaled.
            attrDict = {}
            for k, v in attr.items():
                # attrDict[k[1].encode(self._encoding)] = v.encode(self._encoding)
                attrDict[k] = v
            self._validate_elem_start(name, attrDict)
            # Push the current element onto the element stack.
            self._elem_stack.append([name, attrDict])
            self._push_whitespace_behavior(attr)
            # If this is a condition element, push a new entry onto the
            # foundDefaultLiStack
            if name == "condition":
                self._found_default_li_stack.append(False)
        else:
            # we're now inside an unknown element.
            if self._forward_compatible_mode:
                # In Forward Compatibility Mode, we ignore the element and its
                # contents.
                self._current_unknown = name
            else:
                # Otherwise, unknown elements are grounds for error!
                raise AimlParserError(("Unexpected <{0}> tag ".format(name)) + self._location())

    def characters(self, ch):
        # Wrapper around _characters which catches errors in _characters()
        # and keeps going.
        if self._state == self._STATE_outside_aiml:
            # If we're outside of an AIML element, we ignore all text
            return
        if self._current_unknown != "":
            # If we're inside an unknown element, ignore all text
            return
        if self._skip_current_category:
            # If we're skipping the current category, ignore all text.
            return
        try:
            self._characters(ch)
        except AimlParserError as msg:
            # Print the message
            sys.stderr.write("PARSE ERROR: {0}\n".format(msg))
            self._num_parse_errors += 1  # increment error count
            # In case of a parse error, if we're inside a category, skip it.
            if self._state >= self._STATE_inside_category:
                self._skip_current_category = True

    def _characters(self, ch):
        text = str(ch)
        if self._state == self._STATE_inside_pattern:
            # TODO: text inside patterns must be upper-case!
            self._current_pattern += text
        elif self._state == self._STATE_inside_that:
            self._current_that += text
        elif self._state == self._STATE_inside_template:
            # First, see whether the element at the top of the element stack
            # is permitted to contain text.
            try:
                parent = self._elem_stack[-1][0]
                parent_attr = self._elem_stack[-1][1]
                required, optional, can_be_parent = self._valid_info[parent]
                nonBlockStyleCondition = (
                    parent == "condition" and not (parent_attr.get("name", False) and parent_attr.get("value", False)))
                if not can_be_parent:
                    raise AimlParserError(("Unexpected text inside <{0}> element ".format(parent)) + self._location())
                elif parent == "random" or nonBlockStyleCondition:
                    # <random> elements can only contain <li> subelements. However,
                    # there's invariably some whitespace around the <li> that we need
                    # to ignore. Same for non-block-style <condition> elements (i.e.
                    # those which don't have both a "name" and a "value" attribute).
                    if len(text.strip()) == 0:
                        # ignore whitespace inside these elements.
                        return
                    else:
                        # non-whitespace text inside these elements is a syntax error.
                        raise AimlParserError(("Unexpected text inside <{0}> element ".format(parent)) +
                                              self._location())
            except IndexError:
                # the element stack is empty. This should never happen.
                raise AimlParserError("Element stack is empty while validating text " + self._location())

            # Add a new text element to the element at the top of the element
            # stack. If there's already a text element there, simply append the
            # new characters to its contents.
            try:
                text_elem_on_stack = (self._elem_stack[-1][-1][0] == "text")
            except IndexError:
                text_elem_on_stack = False
            except KeyError:
                text_elem_on_stack = False
            if text_elem_on_stack:
                self._elem_stack[-1][-1][2] += text
            else:
                self._elem_stack[-1].append(["text", {"xml:space": self._whitespace_behavior_stack[-1]}, text])
        else:
            # all other text is ignored
            pass

    def endElementNS(self, name, qname):
        uri, elem = name
        self.endElement(elem)

    def endElement(self, name):
        """Wrapper around _end_element which catches errors in _characters()
        and keeps going.

        """
        if self._state == self._STATE_outside_aiml:
            # If we're outside of an AIML element, ignore all tags
            return
        if self._current_unknown != "":
            # see if we're at the end of an unknown element.  If so, we can
            # stop ignoring everything.
            if name == self._current_unknown:
                self._current_unknown = ""
            return
        if self._skip_current_category:
            # If we're skipping the current category, see if it's ending. We
            # stop on ANY </category> tag, since we're not keeping track of
            # state in ignore-mode.
            if name == "category":
                self._skip_current_category = False
                self._state = self._STATE_inside_aiml
            return
        try:
            self._end_element(name)
        except AimlParserError as msg:
            # Print the message
            sys.stderr.write("PARSE ERROR: {0}\n".format(msg))
            self._num_parse_errors += 1  # increment error count
            # In case of a parse error, if we're inside a category, skip it.
            if self._state >= self._STATE_inside_category:
                self._skip_current_category = True

    def _end_element(self, name):
        """Verify that an AIML end element is valid in the current
        context.

        Raises an AimlParserError if an illegal end element is encountered.

        """
        if name == "aiml":
            # </aiml> tags are only legal in the InsideAiml state
            if self._state != self._STATE_inside_aiml:
                raise AimlParserError("Unexpected </aiml> tag " + self._location())
            self._state = self._STATE_outside_aiml
            self._whitespace_behavior_stack.pop()
        elif name == "topic":
            # </topic> tags are only legal in the InsideAiml state, and
            # only if _insideTopic is true.
            if self._state != self._STATE_inside_aiml or not self._inside_topic:
                raise AimlParserError("Unexpected </topic> tag " + self._location())
            self._inside_topic = False
            self._current_topic = ""
        elif name == "category":
            # </category> tags are only legal in the AfterTemplate state
            if self._state != self._STATE_after_template:
                raise AimlParserError("Unexpected </category> tag " + self._location())
            self._state = self._STATE_inside_aiml
            # End the current category.  Store the current pattern/that/topic and
            # element in the categories dictionary.
            key = (self._current_pattern.strip(), self._current_that.strip(), self._current_topic.strip())
            self.categories[key] = self._elem_stack[-1]
            self._whitespace_behavior_stack.pop()
        elif name == "pattern":
            # </pattern> tags are only legal in the InsidePattern state
            if self._state != self._STATE_inside_pattern:
                raise AimlParserError("Unexpected </pattern> tag " + self._location())
            self._state = self._STATE_after_pattern
        elif name == "that" and self._state == self._STATE_inside_that:
            # </that> tags are only allowed inside <template> elements or in
            # the InsideThat state.  This clause handles the latter case.
            self._state = self._STATE_after_that
        elif name == "template":
            # </template> tags are only allowed in the InsideTemplate state.
            if self._state != self._STATE_inside_template:
                raise AimlParserError("Unexpected </template> tag " + self._location())
            self._state = self._STATE_after_template
            self._whitespace_behavior_stack.pop()
        elif self._state == self._STATE_inside_pattern:
            # Certain tags are allowed inside <pattern> elements.
            if name not in ["bot"]:
                raise AimlParserError(("Unexpected </{0}> tag ".format(name)) + self._location())
        elif self._state == self._STATE_inside_that:
            # Certain tags are allowed inside <that> elements.
            if name not in ["bot"]:
                raise AimlParserError(("Unexpected </{0}> tag ".format(name)) + self._location())
        elif self._state == self._STATE_inside_template:
            # End of an element inside the current template.  Append the
            # element at the top of the stack onto the one beneath it.
            elem = self._elem_stack.pop()
            self._elem_stack[-1].append(elem)
            self._whitespace_behavior_stack.pop()
            # If the element was a condition, pop an item off the
            # foundDefaultLiStack as well.
            if elem[0] == "condition":
                self._found_default_li_stack.pop()
        else:
            # Unexpected closing tag
            raise AimlParserError(("Unexpected </{0}> tag ".format(name)) + self._location())

    # A dictionary containing a validation information for each AIML
    # element. The keys are the names of the elements.  The values are a
    # tuple of three items. The first is a list containing the names of
    # REQUIRED attributes, the second is a list of OPTIONAL attributes,
    # and the third is a boolean value indicating whether or not the
    # element can contain other elements and/or text (if False, the
    # element can only appear in an atomic context, such as <date/>).
    _validation_info101 = {
        "bot": (["name"], [], False),
        "condition": ([], ["name", "value"], True),  # can only contain <li> elements
        "date": ([], [], False),
        "formal": ([], [], True),
        "gender": ([], [], True),
        "get": (["name"], [], False),
        "gossip": ([], [], True),
        "id": ([], [], False),
        "input": ([], ["index"], False),
        "javascript": ([], [], True),
        "learn": ([], [], True),
        "li": ([], ["name", "value"], True),
        "lowercase": ([], [], True),
        "person": ([], [], True),
        "person2": ([], [], True),
        "random": ([], [], True),  # can only contain <li> elements
        "sentence": ([], [], True),
        "set": (["name"], [], True),
        "size": ([], [], False),
        "sr": ([], [], False),
        "srai": ([], [], True),
        "star": ([], ["index"], False),
        "system": ([], [], True),
        "template": ([], [], True),  # needs to be in the list because it can be a parent.
        "that": ([], ["index"], False),
        "thatstar": ([], ["index"], False),
        "think": ([], [], True),
        "topicstar": ([], ["index"], False),
        "uppercase": ([], [], True),
        "version": ([], [], False),
    }

    def _validate_elem_start(self, name, attr):
        """Test the validity of an element starting inside a <template>
        element.

        This function raises an AimlParserError exception if it the tag is
        invalid.  Otherwise, no news is good news.

        """
        # Check the element's attributes.  Make sure that all required
        # attributes are present, and that any remaining attributes are
        # valid options.
        required, optional, can_be_parent = self._valid_info[name]
        for a in required:
            if a not in attr and not self._forward_compatible_mode:
                raise AimlParserError(("Required \"{0}\" attribute missing in <{1}> element "
                                       .format(a, name)) + self._location())
        for a in attr:
            if a in required:
                continue
            if a[0:4] == "xml:":
                continue  # attributes in the "xml" namespace can appear anywhere
            if a not in optional and not self._forward_compatible_mode:
                raise AimlParserError(("Unexpected \"{0}\" attribute in <{1}> element "
                                       .format(a, name)) + self._location())

        # special-case: several tags contain an optional "index" attribute.
        # This attribute's value must be a positive integer.
        if name in ["star", "thatstar", "topicstar"]:
            for k, v in attr.items():
                if k == "index":
                    temp = 0
                    try:
                        temp = int(v)
                    except:
                        raise AimlParserError(("Bad type for \"{0}\" attribute (expected integer, found \"{1}\") "
                                               .format(k, v)) + self._location())
                    if temp < 1:
                        raise AimlParserError(("\"{0}\" attribute must have non-negative value "
                                               .format(k)) + self._location())

        # See whether the containing element is permitted to contain
        # subelements. If not, this element is invalid no matter what it is.
        try:
            parent = self._elem_stack[-1][0]
            parent_attr = self._elem_stack[-1][1]
        except IndexError:
            # If the stack is empty, no parent is present.  This should never
            # happen.
            raise AimlParserError(("Element stack is empty while validating <{0}> ".format(name)) + self._location())
        required, optional, can_be_parent = self._valid_info[parent]
        non_block_style_condition = (
            parent == "condition" and not (parent_attr.get("name", False) and parent_attr.get("value", False)))
        if not can_be_parent:
            raise AimlParserError(("<{0}> elements cannot have any contents ".format(parent)) + self._location())
        # Special-case test if the parent element is <condition> (the
        # non-block-style variant) or <random>: these elements can only
        # contain <li> subelements.
        elif (parent == "random" or non_block_style_condition) and name != "li":
            raise AimlParserError(("<{0}> elements can only contain <li> subelements "
                                   .format(parent)) + self._location())
        # Special-case test for <li> elements, which can only be contained
        # by non-block-style <condition> and <random> elements, and whose
        # required attributes are dependent upon which attributes are
        # present in the <condition> parent.
        elif name == "li":
            if not (parent == "random" or non_block_style_condition):
                raise AimlParserError(("Unexpected <li> element contained by <{0}> element "
                                       .format(parent)) + self._location())
            if non_block_style_condition:
                if parent_attr.get("name", False):
                    # Single-predicate condition.  Each <li> element except the
                    # last must have a "value" attribute.
                    if len(attr) == 0:
                        # This could be the default <li> element for this <condition>,
                        # unless we've already found one.
                        if self._found_default_li_stack[-1]:
                            raise AimlParserError(
                                "Unexpected default <li> element inside <condition> " + self._location())
                        else:
                            self._found_default_li_stack[-1] = True
                    elif len(attr) == 1 and "value" in attr:
                        pass  # this is the valid case
                    else:
                        raise AimlParserError("Invalid <li> inside single-predicate <condition> " + self._location())
                elif len(parent_attr) == 0:
                    # Multi-predicate condition.  Each <li> element except the
                    # last must have a "name" and a "value" attribute.
                    if len(attr) == 0:
                        # This could be the default <li> element for this <condition>,
                        # unless we've already found one.
                        if self._found_default_li_stack[-1]:
                            raise AimlParserError(
                                "Unexpected default <li> element inside <condition> " + self._location())
                        else:
                            self._found_default_li_stack[-1] = True
                    elif len(attr) == 2 and attr.get("value", False) and attr.get("name", False):
                        pass  # this is the valid case
                    else:
                        raise AimlParserError("Invalid <li> inside multi-predicate <condition> " + self._location())
        return True


def create_parser():
    """Create and return an AIML parser object."""
    parser = xml.sax.make_parser()
    handler = AimlHandler("UTF-8")
    parser.setContentHandler(handler)
    # parser.setFeature(xml.sax.handler.feature_namespaces, True)
    return parser
