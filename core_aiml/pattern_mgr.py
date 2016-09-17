# This class implements the AIML pattern-matching algorithm described
# by Dr. Richard Wallace at the following site:
# http://www.alicebot.org/documentation/matching.html

import marshal
import pprint
import re
import string


class PatternMgr:
    # special dictionary keys
    _UNDERSCORE = 0
    _STAR = 1
    _TEMPLATE = 2
    _THAT = 3
    _TOPIC = 4
    _BOT_NAME = 5

    def __init__(self):
        self._root = {}
        self._template_count = 0
        self._bot_name = u"Nameless"
        punctuation = "\"`~!@#$%^&*()-_=+[{]}\|;:',<.>/?"
        self._puncStripRE = re.compile("[" + re.escape(punctuation) + "]")
        self._whitespaceRE = re.compile("\s+", re.LOCALE | re.UNICODE)

    def num_templates(self):
        """Return the number of templates currently stored."""
        return self._template_count

    def set_bot_name(self, name):
        """Set the name of the bot, used to match <bot name="name"> tags in
        patterns.  The name must be a single word!

        """
        # Collapse a multi-word name into a single word
        self._bot_name = unicode(string.join(name.split()))

    def dump(self):
        """Print all learned patterns, for debugging purposes."""
        pprint.pprint(self._root)

    def save(self, filename):
        """Dump the current patterns to the file specified by filename.  To
        restore later, use restore().

        """
        try:
            out_file = open(filename, "wb")
            marshal.dump(self._template_count, out_file)
            marshal.dump(self._bot_name, out_file)
            marshal.dump(self._root, out_file)
            out_file.close()
        except Exception, e:
            print "Error saving PatternMgr to file %s:" % filename
            raise Exception, e

    def restore(self, filename):
        """Restore a previously save()d collection of patterns."""
        try:
            inFile = open(filename, "rb")
            self._template_count = marshal.load(inFile)
            self._bot_name = marshal.load(inFile)
            self._root = marshal.load(inFile)
            inFile.close()
        except Exception, e:
            print "Error restoring PatternMgr from file %s:" % filename
            raise Exception, e

    def add(self, (pattern, that, topic), template):
        """Add a [pattern/that/topic] tuple and its corresponding template
        to the node tree.

        """
        # TODO: make sure words contains only legal characters
        # (alphanumerics,*,_)

        # Navigate through the node tree to the template's location, adding
        # nodes if necessary.
        node = self._root
        for word in string.split(pattern):
            key = word
            if key == u"_":
                key = self._UNDERSCORE
            elif key == u"*":
                key = self._STAR
            elif key == u"BOT_NAME":
                key = self._BOT_NAME
            if not node.has_key(key):
                node[key] = {}
            node = node[key]

        # navigate further down, if a non-empty "that" pattern was included
        if len(that) > 0:
            if not node.has_key(self._THAT):
                node[self._THAT] = {}
            node = node[self._THAT]
            for word in string.split(that):
                key = word
                if key == u"_":
                    key = self._UNDERSCORE
                elif key == u"*":
                    key = self._STAR
                if not node.has_key(key):
                    node[key] = {}
                node = node[key]

        # navigate yet further down, if a non-empty "topic" string was included
        if len(topic) > 0:
            if not node.has_key(self._TOPIC):
                node[self._TOPIC] = {}
            node = node[self._TOPIC]
            for word in string.split(topic):
                key = word
                if key == u"_":
                    key = self._UNDERSCORE
                elif key == u"*":
                    key = self._STAR
                if not node.has_key(key):
                    node[key] = {}
                node = node[key]


        # add the template.
        if not node.has_key(self._TEMPLATE):
            self._template_count += 1
        node[self._TEMPLATE] = template

    def match(self, pattern, that, topic):
        """Return the template which is the closest match to pattern. The
        'that' parameter contains the bot's previous response. The 'topic'
        parameter contains the current topic of conversation.

        Returns None if no template is found.

        """
        if len(pattern) == 0:
            return None
        # Mutilate the input.  Remove all punctuation and convert the
        # text to all caps.
        input = string.upper(pattern)
        input = re.sub(self._puncStripRE, " ", input)
        if that.strip() == u"": that = u"ULTRABOGUSDUMMYTHAT"  # 'that' must never be empty
        that_input = string.upper(that)
        that_input = re.sub(self._puncStripRE, " ", that_input)
        that_input = re.sub(self._whitespaceRE, " ", that_input)
        if topic.strip() == u"": topic = u"ULTRABOGUSDUMMYTOPIC"  # 'topic' must never be empty
        topic_input = string.upper(topic)
        topic_input = re.sub(self._puncStripRE, " ", topic_input)

        # Pass the input off to the recursive call
        pat_match, template = self._match(input.split(), that_input.split(), topic_input.split(), self._root)
        return template

    def star(self, starType, pattern, that, topic, index):
        """Returns a string, the portion of pattern that was matched by a *.

        The 'starType' parameter specifies which type of star to find.
        Legal values are:
         - 'star': matches a star in the main pattern.
         - 'thatstar': matches a star in the that pattern.
         - 'topicstar': matches a star in the topic pattern.

        """
        # Mutilate the input.  Remove all punctuation and convert the
        # text to all caps.
        input = string.upper(pattern)
        input = re.sub(self._puncStripRE, " ", input)
        input = re.sub(self._whitespaceRE, " ", input)
        if that.strip() == u"": that = u"ULTRABOGUSDUMMYTHAT"  # 'that' must never be empty
        that_input = string.upper(that)
        that_input = re.sub(self._puncStripRE, " ", that_input)
        that_input = re.sub(self._whitespaceRE, " ", that_input)
        if topic.strip() == u"": topic = u"ULTRABOGUSDUMMYTOPIC"  # 'topic' must never be empty
        topic_input = string.upper(topic)
        topic_input = re.sub(self._puncStripRE, " ", topic_input)
        topic_input = re.sub(self._whitespaceRE, " ", topic_input)

        # Pass the input off to the recursive pattern-matcher
        pat_match, template = self._match(input.split(), that_input.split(), topic_input.split(), self._root)
        if not template:
            return ""

        # Extract the appropriate portion of the pattern, based on the
        # starType argument.
        words = None
        if starType == 'star':
            pat_match = pat_match[:pat_match.index(self._THAT)]
            words = input.split()
        elif starType == 'thatstar':
            pat_match = pat_match[pat_match.index(self._THAT) + 1: pat_match.index(self._TOPIC)]
            words = that_input.split()
        elif starType == 'topicstar':
            pat_match = pat_match[pat_match.index(self._TOPIC) + 1:]
            words = topic_input.split()
        else:
            # unknown value
            raise ValueError, "starType must be in ['star', 'thatstar', 'topicstar']"

        # compare the input string to the matched pattern, word by word.
        # At the end of this loop, if foundTheRightStar is true, start and
        # end will contain the start and end indices (in "words") of
        # the substring that the desired star matched.
        foundTheRightStar = False
        start = end = j = numStars = k = 0
        for i in range(len(words)):
            # This condition is true after processing a star
            # that ISN'T the one we're looking for.
            if i < k:
                continue
            # If we're reached the end of the pattern, we're done.
            if j == len(pat_match):
                break
            if not foundTheRightStar:
                if pat_match[j] in [self._STAR, self._UNDERSCORE]:  # we got a star
                    numStars += 1
                    if numStars == index:
                        # This is the star we care about.
                        foundTheRightStar = True
                    start = i
                    # Iterate through the rest of the string.
                    for k in range(i, len(words)):
                        # If the star is at the end of the pattern,
                        # we know exactly where it ends.
                        if j + 1 == len(pat_match):
                            end = len(words)
                            break
                        # If the words have started matching the
                        # pattern again, the star has ended.
                        if pat_match[j + 1] == words[k]:
                            end = k - 1
                            i = k
                            break
                # If we just finished processing the star we cared
                # about, we exit the loop early.
                if foundTheRightStar:
                    break
            # Move to the next element of the pattern.
            j += 1

        # extract the star words from the original, unmutilated input.
        if foundTheRightStar:
            # print string.join(pattern.split()[start:end+1])
            if starType == 'star':
                return string.join(pattern.split()[start:end + 1])
            elif starType == 'thatstar':
                return string.join(that.split()[start:end + 1])
            elif starType == 'topicstar':
                return string.join(topic.split()[start:end + 1])
        else:
            return ""

    def _match(self, words, that_words, topic_words, root):
        """Return a tuple (pat, tem) where pat is a list of nodes, starting
        at the root and leading to the matching pattern, and tem is the
        matched template.

        """
        # base-case: if the word list is empty, return the current node's
        # template.
        if len(words) == 0:
            # we're out of words.
            pattern = []
            template = None
            if len(that_words) > 0:
                # If thatWords isn't empty, recursively
                # pattern-match on the _THAT node with thatWords as words.
                try:
                    pattern, template = self._match(that_words, [], topic_words, root[self._THAT])
                    if pattern:
                        pattern = [self._THAT] + pattern
                except KeyError:
                    pattern = []
                    template = None
            elif len(topic_words) > 0:
                # If thatWords is empty and topicWords isn't, recursively pattern
                # on the _TOPIC node with topicWords as words.
                try:
                    pattern, template = self._match(topic_words, [], [], root[self._TOPIC])
                    if pattern:
                        pattern = [self._TOPIC] + pattern
                except KeyError:
                    pattern = []
                    template = None
            if not template:
                # we're totally out of input.  Grab the template at this node.
                pattern = []
                try:
                    template = root[self._TEMPLATE]
                except KeyError:
                    template = None
            return pattern, template

        first = words[0]
        suffix = words[1:]

        # Check underscore.
        # Note: this is causing problems in the standard AIML set, and is
        # currently disabled.
        if root.has_key(self._UNDERSCORE):
            # Must include the case where suf is [] in order to handle the case
            # where a * or _ is at the end of the pattern.
            for j in range(len(suffix) + 1):
                suf = suffix[j:]
                pattern, template = self._match(suf, that_words, topic_words, root[self._UNDERSCORE])
                if template is not None:
                    new_pattern = [self._UNDERSCORE] + pattern
                    return (new_pattern, template)

        # Check first
        if root.has_key(first):
            pattern, template = self._match(suffix, that_words, topic_words, root[first])
            if template is not None:
                new_pattern = [first] + pattern
                return new_pattern, template

        # check bot name
        if root.has_key(self._BOT_NAME) and first == self._bot_name:
            pattern, template = self._match(suffix, that_words, topic_words, root[self._BOT_NAME])
            if template is not None:
                new_pattern = [first] + pattern
                return new_pattern, template

        # check star
        if root.has_key(self._STAR):
            # Must include the case where suf is [] in order to handle the case
            # where a * or _ is at the end of the pattern.
            for j in range(len(suffix) + 1):
                suf = suffix[j:]
                pattern, template = self._match(suf, that_words, topic_words, root[self._STAR])
                if template is not None:
                    new_pattern = [self._STAR] + pattern
                    return new_pattern, template

        # No matches were found.
        return None, None
