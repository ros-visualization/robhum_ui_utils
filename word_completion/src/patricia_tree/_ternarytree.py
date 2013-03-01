from node import Node

class TernarySearchTree(object):

    """
    Implementation of a Trie data structure.
    In computer science, a trie, or prefix tree, 
    is an ordered tree  data structure that is used to 
    store an associative array where the keys are usually
    strings. Unlike a binary search tree, no node in the tree
    stores the key associated with that node; instead, its
    position in the tree shows what key it is associated with.
    All the descendants of a node have a common prefix of the
    string associated with that node, and the root is associated
    with the empty string. Values are normally not associated
    with every node, only with leaves and some inner nodes that
    correspond to keys of interest.
    Reference: http://en.wikipedia.org/wiki/Trie
    """

    WILDCARD = '?'

    def __init__(self):
        self.root = None
        self._size = 0

    @property
    def size(self):
        return self._size

    def add(self, word):
        """Add a word to the tree.
        @raises: ValueError if word is not valid or empty
        """

        if word is None or len(word) < 1:
            raise ValueError("word cannot be empty")
        node = self._insert(self.root, word, 0)
        self._size += 1
        if self.root is None:
           self.root = node

    def contains(self, word):
        """Return True if word is contained in the tree. False otherwise
        """

        if word is None or len(word) < 1:
            raise ValueError("word cannot be empty")
        node = self._search(self.root, word, 0)
        return node != None and node.isEndOfWord()

    def remove(self, word):
        """Remove a word from the tree, if it exists.
           Return True if the word has been found and removed, False otherwise.
        """
        if word is None or len(word) < 1:
            raise ValueError("word cannot be empty")
        node = self._remove(self.root, word, 0)
        if node.isEndOfWord():
            return True
        return False

    def patternMatch(self, pattern, results):
        """Scan the tree to search words matching to the 'pattern'.
            'results' must be a list."""

        if pattern is None or len(pattern) < 1:
            raise ValueError("invalid pattern")
        if results is None:
            raise ValueError("invalid sequence")
        
        self._internal_pattern_match(self.root, pattern, 0, results)

    def prefix_search(self, prefix, results):
        """ Scan the tree to search words starting with 'prefix'.
            'results' must be a list."""

        if prefix is None or len(prefix) < 1:
            raise ValueError("invalid prefix")
        if results is None:
            raise ValueError("invalid sequence")
        found = self._search(self.root, prefix, 0)
        #if found.isEndOfWord():
        #    results.append(prefix)
        self._inorder_traversal(found, results, prefix[:-1])

    def _search(self, node, word, index):
        """ Internal method: used to look through the tree.
            If we want to find a word, 'hello', then we 
            first check the first character: 'h'.
            We try to find the node containing the 'h' character in the tree, 
            beginning from the root node.
            If we find it, then we can check its child or siblings, 
            and in siblings' siblings, and so on....
            If we don't find it, then None is returned."""

        if word is None or len(word) < 1:
            raise ValueError("invalid word")
        if node is None:
            return None
        c = word[index]
        # if the character matches, then we continue in the child
        if(c == node.getChar()):
            # if there are still other characters to check
            if(index + 1 < len(word)):
                node = self._search(node.getChild(), word, index +1)
        elif(c < node.getChar()):  # go left
            node = self._search(node.getSmaller(), word, index)
        else: # go right
            node = self._search(node.getLarger(), word, index)

        return node

    def _insert(self, node, word, index):
        """ Internal method to insert a word in the tree.
            We use the same criteria as used in the _search method.
        """
        if word is None or len(word) < 1:
            raise ValueError("invalid word")
        c = word[index]
        if node is None:
            node = Node(c)
        # se non esiste ancora la radice
        # restituiamo immediatamente il nuovo nodo
        # print word
        if c == node.getChar():
            if (index +1) < len(word):
                #print "CHILD", node.getChild()
                node.setChild(self._insert(node.getChild(), word, index +1))
            else:
                node.setIsWord(True)
        elif c < node.getChar():
            node.setSmaller(self._insert(node.getSmaller(), word, index))
        else:
            node.setLarger(self._insert(node.getLarger(), word, index))
        return node

    def _remove(self, node, word, index):
        #TODO: to continue....
        if word is None or len(word) < 1:
            raise ValueError("invalid word")
        if node is None:
            return None
        c = word[index]
        if(c == node.getChar()):
            if(index +1 < len(word)):
                pass
                

    def _inorder_traversal(self, node, results, prefix):
        if node is None:
            return
        #print prefix, node.getChar()
        self._inorder_traversal(node.getSmaller(), results, prefix)
        if node.isEndOfWord():
            results.append(prefix + node.getChar())
        
        self._inorder_traversal(node.getChild(), results, prefix + node.getChar())
        self._inorder_traversal(node.getLarger(), results, prefix )

    def _internal_pattern_match(self, node, pattern, index, results):
        if node == None:
            return
        c = pattern[index]
        if c == self.WILDCARD or c < node.getChar():
            self._internal_pattern_match(node.getSmaller(), pattern, index, 
                                         results)
        if c == self.WILDCARD or c == node.getChar():
            if (index + 1) < len(pattern):
                self._internal_pattern_match(node.getChild(), pattern, 
                                             index+1, results)
            elif node.isEndOfWord():
                results.append(node.getWord())
        if c == self.WILDCARD or c > node.getChar():
            self._internal_pattern_match(node.getLarger(), pattern, index, 
                                         results)


    def _find_prefix(self, first_tok, second_tok):
        _prefix = ""
        for e1, e2 in zip(first_tok, second_tok):
            if e1 == e2:
                _prefix += e1
            else:
                break
        return _prefix

    def print_level(self, node=None):
        # utility method: it prints out 
        # @node's neighbors
        if node is None:
            return
        else:
            print node.getSmaller(), node.getChar(), node.getLarger()
            self.print_level(node.getSmaller())
            self.print_level(node.getLarger())
        
        
