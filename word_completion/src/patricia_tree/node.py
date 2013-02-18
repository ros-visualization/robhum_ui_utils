

class Node(object):
    
    """
    An implementation of the Trie node.
    
    """

    def __init__(self, character, smaller=None, 
                       larger=None, child=None):
        self.char = character
        self.smaller = smaller
        self.larger = larger
        self.child = child
        self.is_word = False

    def getChar(self):
        return self.char

    def setChar(self, c):
        self.char = c

    def getSmaller(self):
        return self.smaller
    
    def setSmaller(self, smaller):
        self.smaller = smaller

    def getLarger(self):
        return self.larger
    
    def setLarger(self, larger):
        self.larger = larger

    def getChild(self):
        return self.child

    def hasChild(self):
        return self.child != None
    
    def setChild(self, child):
        self.child = child

    def setIsWord(self, is_word):
        self.is_word = is_word
    
    def isEndOfWord(self):
        return self.is_word


