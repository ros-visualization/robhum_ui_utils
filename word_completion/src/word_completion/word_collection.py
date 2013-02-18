#!/usr/bin/env python

import array;
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../../lib"));
from ternarytree import TernarySearchTree;

# TODO: 
#  - get ternarytree.so into lib subdir during setup. Make that work for Cygwin as well.


# ABC, DEF, GHI, JKL, MNO, PQR, STUV, WXYZ
#  A    D    G    J    M    P     S    W
#
class WordCollection(TernarySearchTree):
    '''
    Word lookup based on a Patricia tree (a.k.a. Radix Tree, a.k.a. Trie data structure).
    This data structure is efficiently searchable by the prefix of words. Such a prefix search takes
    a string prefix, and returns all dictionary words that begin with that prefix.

    This class ingests rank/word pair files in a given directory. The ranks are intended
    to be relative usage frequencies. The class manages these frequency ranks.

    Public methods: 

      - add(word)
      - contains(word)
      - prefix_search(prefix)
      - rank(word)
    '''

    DEFAULT_USER_DICT_FILE_NAME = "dictUserRankAndWord.txt";
    USER_DICT_FILE_PATH = None;
    
    def __init__(self, dictDir=None, userDictFilePath=None):
        '''
        Keep track of a Python dict mapping from word to
        its frequency rank, of the total number of entries, and
        the number of word files ingested from disk.
        @param dictDir: full path to directory that contains the dictionary files. If None, a 
                        built-in dictionary of 6000 words is used.
        @type dictDir: string
        @param userDictFilePath: full path to within a user dictionary. That file must be organized like
                        the other dictionary files.
        @type userDictFilePath: string  
        '''
        super(WordCollection, self).__init__();
        if dictDir is None:
            self.dictDir = os.path.join(os.path.dirname(__file__), "dict_files");
        else:
            self.dictDir = dictDir;
            
        if userDictFilePath is None:
            WordCollection.USER_DICT_FILE_PATH = os.path.join(self.dictDir, WordCollection.DEFAULT_USER_DICT_FILE_NAME)
        else:
            WordCollection.USER_DICT_FILE_PATH = userDictFilePath;
            
        self.realWordToFrequencyRanks = {};
        self.numEntries = 0;
        self.numDictFilesIngested = 0;
        self.createDictStructureFromFiles();
    
    def createDictStructureFromFiles(self):
        '''
        Goes through the self.dictDir directory on disk, and reads all the
        files there. Each file must be a list of whitespace-separated
        frequency-rank / word pairs. Assumes that self.dictDir is set to directory
        of dictionary files.
        @raise ValueError: if a rank in any of the files cannot be read as an integer.
        '''
        for rankAndWordListFileName in os.listdir(self.dictDir):
            with open(os.path.realpath(os.path.join(self.dictDir, rankAndWordListFileName))) as fd:
                self.numDictFilesIngested += 1;
                # Pull the entire rank[\t]word list into memory as one string:
                rankAndWordLists = fd.read();
                for line in rankAndWordLists.splitlines():
                    if len(line) == 0:
                        continue;
                    # Make one whitespace split to get the rank and the word:
                    try:
                        (rank, word) = line.split(None, 1);
                    except:
                        raise ValueError("Word file file %s contains a line that does not contain a numeric rank, followed by a word: '%s'" %
                                         (rankAndWordListFileName, line));                        
                    try:
                        rankInt = int(rank);
                    except ValueError:
                        raise ValueError("Word file %s contains a line with a non-numeric rank %s" %
                                         (rankAndWordListFileName, rank));
                    self.insert(word, rankInt);
                    
    def addToUserDict(self, newWord, rankInt=0):
        '''
        Given a word, checks whether the word is already in 
        the in-memory dictionary. If so, does nothing and returns False;
        Else appends the word to dict_files/dictUserRankAndWord.txt
        with the provided rank; then returns True
        @param newWord: word to be added to the user dictionary.
        @type newWord: string
        @param rankInt: frequency rank of the word. Rank 0 is most important; 1 is
        second-most important, etc. OK to have ties.
        @type rankInt: int
        '''
        # Ensure that the word is not unicode:
        newWord = newWord.encode("UTF-8");
        if self.contains(newWord):
            return False;
        with open(os.path.realpath(WordCollection.USER_DICT_FILE_PATH), 'a') as fd:
            fd.write(str(rankInt) + "\t" + newWord + "\n");
        # Update the current in-memory tree to include the word as well:
        self.insert(newWord, rankInt);
        return True;
                    
                    

    def insert(self, word, rankInt=None):
        '''
        Insert one word into the word collection.
        @param word: word to insert.
        @type word: string
        @param rankInt: Optionally the frequency rank of the word. If None, no rank is recorded,
            and subsequent calls to the rank() method will fail. 
        @type rankInt: int
        @raise ValueError: if word is not valid or empty. 
        '''
        if not self.contains(word):
            self.numEntries += 1;
        self.add(word);
        if rankInt is not None:
            self.realWordToFrequencyRanks[word.encode('UTF-8')] = rankInt;
        
    def rank(self, word):
        '''
        Return the frequency rank of the given word in the collection. I is
        an error to request the rank of a word that is not in the collection,
        or of a word whose rank was never specified in an ingestion file or
        as part of an insert() call.
        @param word: the word whose frequency rank is requested.
        @type word: string
        @raise KeyError: if word or rank are not present in the word collection. 
        '''
        return self.realWordToFrequencyRanks[word.encode('UTF-8')];

    def prefix_search(self, word, cutoffRank=None):
        '''
        Returns all dictionary entries that begin with the string word.
        If the optional cutoffRank is specified, it limits the length of the
        returned list to include only the top cutoffRank words. Example, if
        cutoffRank=5, only the five most highly ranked dictionary entries 
        are returned. Also, if cutoffRank is specified, the returned list
        is sorted by decreasing word rank. If cutoffRank is not specified,
        or is None, the returned list is unsorted.
        @param word: prefix to search by.
        @type word: string.
        @param cutoffRank: Number of most highly ranked dictionary entries to return in rank-sorted order.
        @type cutoffRank: int
        '''
        
        if cutoffRank is not None:
            if not isinstance(cutoffRank, int):
                raise TypeError("Parameter cutoffRank for prefix_search must be an integer.");
        
        matchingWords = super(WordCollection, self).prefix_search(word); 
        # The underlying tree traversal implementation seems to return
        # all the words in the tree that start with the first letter of 'word'.
        # Keep only the ones that really start with word:
        finalWords = [];
        for candidate in matchingWords:
            if self.startsWith(candidate,word):
                finalWords.append(candidate);
        if cutoffRank is not None:
            # sort by rank:
            finalWords.sort(key=self.rank);
            return finalWords[:cutoffRank]
        return finalWords;
          
    def startsWith(self, word, prefix):
        '''
        True if word starts with, or is equal to prefix. Else False. 
        @param word: word to examine.
        @type word: string.
        @param prefix: string that word is required to start with for a return of True
        @type prefix: string
        '''
        if len(prefix) > len(word):
            return False;
        wordFoundFrag = word[:len(prefix)];
        return word[:len(prefix)] == prefix;
            
    def __len__(self):
        '''
        Return number of words in the collection.
        '''
        return self.numEntries;
      
# ---------------------------------------------  Subclass TelPadEncodedWordCollection -----------------      
      
class TelPadEncodedWordCollection(WordCollection):
    '''
    Instances behave as the superclass WordCollection. However, all added words
    are encoded as if entered via a telephone pad. Each letter group of the telephone
    pad is represented by its first letter. Example: "and" --> "amd" (phone buttons 1,5,2).
    <p>
    The class can thus be used to search words by entering for each real word's letters 'c'
    the first letter of the telephone pad that contains 'c'. For word input, clients need 
    not concern themselves with this encoding. That transformation occurs automatically.
    <p>
    However, calls to search_prefix() or contains() must encode the real words with the
    encoded version. Thus, instead of calling myColl.contains("and"), the client would 
    call myColl.contains("amd"). Method encodeWord() takes a real word and returns the
    encoded version.
    <p>
    Method search_prefix() will usually contain a larger number of 'remaining possible words'
    than a regular WordCollection. This is because the mapping from encoded to real words is
    one-to-many.  
    '''
    
    symbolToEnc = {
                   'ABC' : 'a',
                   'DEF' : 'd',
                   'GHI' : 'g',
                   'JKL' : 'j',
                   'MNO' : 'm',
                   'PQR' : 'p',
                   'STUV': 's',
                   'WXYZ': 'w'
                   }
    
    encToSymbol = {'a' : 'ABC',
                   'd' : 'DEF',
                   'g' : 'GHI',
                   'j' : 'JKL',
                   'm' : 'MNO',
                   'p' : 'PQR',
                   's' : 'STUV',
                   'w' : 'WXYZ'
                   }
    
    alphabet = {
                'a' : 'a',
                'b' : 'a',
                'c' : 'a',
                'd' : 'd',
                'e' : 'd',
                'f' : 'd',
                'g' : 'g',
                'h' : 'g',
                'i' : 'g',
                'j' : 'j',
                'k' : 'j',
                'l' : 'j',
                'm' : 'm',
                'n' : 'm',
                'o' : 'm',
                'p' : 'p',
                'q' : 'p',
                'r' : 'p',
                's' : 's',
                't' : 's',
                'u' : 's',
                'v' : 's',
                'w' : 'w',
                'x' : 'w',
                'y' : 'w',
                'z' : 'w'
                }
    
    def __init__(self):
        '''
        Maintain a data structure that maps each encoded word
        to all the possible equivalent real words. We call these
        multiple words 'collisions.'
        '''
        self.encWordToRealWords = {};
        super(TelPadEncodedWordCollection, self).__init__();
    
    def prefix_search(self, encWord):
        '''
        Prefix search operates as for the WordCollection superclass, but takes
        as input a telephone pad encoded prefix. Returns an array of all real
        words that could complete the given prefix.  
        @param encWord: the encoded prefix
        @type encWord: string
        @raise ValueError: if the mapping from encoded words to collisions is corrupted. Never caused by caller. 
        '''
        if len(encWord) == 0:
            return [];
        # Get the normal Patricia tree matching set, which consists of
        # encWords:
        encMatches = super(TelPadEncodedWordCollection, self).prefix_search(encWord);
        
        # But each encoded word, might match to multiple real words. Build
        # that larger list:
        realWordMatches = [];
        for encWord in encMatches:
            try:
                realWordCollisions = self.encWordToRealWords[encWord];
            except KeyError:
                raise ValueError("An encoded tel pad word did not have a mapping to at least one real word: %s" % encWord);
            realWordMatches.extend(realWordCollisions);
        return realWordMatches;
    
    def encodeTelPadLabel(self, label):
        '''
        Given a string label as seen on the JBoard button pad,
        return the single letter that represents the group of
        label chars in this class. Ex: "ABC" returns symbolToEnc["ABC"] == 'a'.
        @param label: Group of chars on a JBoard (more or less telephone pad): 
        @type label: string
        @raise KeyError: if passed-in button label is not a true button label. 
        '''
        return TelPadEncodedWordCollection.symbolToEnc[label];
    
    def decodeTelPadLabel(self, encLetter):
        '''
        Given the encoding of a button label, return the
        original label. Ex.: 'a' ==> 'ABC', 's' ==> 'STUV'
        @param encLetter: label encoding.
        @type encLetter: string
        @raise KeyError: if passed-in letter is not an encoded label. 
        '''
        return TelPadEncodedWordCollection.encToSymbol[encLetter];
        
    def encodeWord(self, word):
        '''
        Given a real word, return its telephone pad encoded equivalent.
        @param word: the real word to encode. 
        @type word: string
        @return: the encoded equivalent string.
        '''
        translation = array.array('c', word);
        for i, char in enumerate(word.lower()):
            try:
                translation[i] = TelPadEncodedWordCollection.alphabet[char];
            except KeyError:
                # Char is not an alpha char (e.g. digit, or apostrophe):
                translation[i] = char;
        return translation.tostring();
    
    
    def insert(self, newRealWord, newRankInt):
        '''
        Takes a real, that is unencoded word, encodes it, and
        inserts it into the (in-memory) tree. Updates the mapping from encoded
        words to their collisions.
        @param newRealWord: the unencoded word to insert.
        @type newRealWord: string
        @param newRankInt: the new word's frequency rank.
        @type newRankInt: int
        @raise ValueError: if the encoded-word to collisions data structure is corrupted. Not caused by caller. 
        '''
        newEncWord = self.encodeWord(newRealWord);
        super(TelPadEncodedWordCollection, self).insert(newEncWord);
        self.realWordToFrequencyRanks[newRealWord] = newRankInt;
        try:
            existingCollisions = self.encWordToRealWords[newEncWord];
        except KeyError:
            existingCollisions = [];
        # Insert the new real word into the existing list of collisions,
        # since newEncWord maps to newRealWord. Preserving high-to-low ranking order:
        if len(existingCollisions) == 0:
            existingCollisions.append(newRealWord);
            self.encWordToRealWords[newEncWord] = [newRealWord];
        else:
            for (pos, realCollisionWord) in enumerate(existingCollisions):
                
                # If this same realWord was inserted before then we are done:
                if (realCollisionWord == newRealWord):
                    return;
    
                # Get rank of the existing collision realWord:
                try:
                    realCollisionWordRank = self.realWordToFrequencyRanks[realCollisionWord]; 
                except KeyError:
                    raise ValueError("Data structure that maps telephone-pad-encoded words to lists of true words should contain %s, but does not." % realCollisionWord);
                if newRankInt <= realCollisionWordRank:
                    existingCollisions.insert(pos, newRealWord);
                    self.encWordToRealWords[newEncWord] = existingCollisions;
                    return;
                
                existingCollisions.append(newRealWord);
                self.encWordToRealWords[newEncWord] = existingCollisions;

    def addToUserDict(self, newRealWord, rankInt=0):
        '''
        Given an unencoded word, checks whether the word is already in 
        the in-memory dictionary. If so, does nothing and returns False;
        Else appends the word to dict_files/dictUserRankAndWord.txt
        with the provided rank; then returns True
        @param newRealWord: word to be added to the user dictionary.
        @type newRealWord: string
        @param rankInt: frequency rank of the word. Rank 0 is most important; 1 is
        second-most important, etc. OK to have ties.
        '''
        # Ensure that the word is not unicode:
        newRealWord = newRealWord.encode("UTF-8");
        newEncWord  = self.encodeWord(newRealWord);
        if self.contains(newEncWord):
            return False;
        with open(os.path.realpath(WordCollection.USER_DICT_FILE_PATH), 'a') as fd:
            fd.write(str(rankInt) + "\t" + newRealWord + "\n");
        # Update the current in-memory tree to include the word as well:
        self.insert(newRealWord, rankInt);
        return True;

if __name__ == "__main__":
    
    myDict = WordCollection();
    
#    # Test word-to-tie-alphabet mapping:
#    print myDict.encodeWord('andreas');
#    
    # Test underlying Patricia tree facility:
#    dictTree = TernarySearchTree()
#    dictTree.add("hello");
#    dictTree.add("hell");
#    print dictTree.prefix_search("he")
#    dictTree.add("hillel")
#    print dictTree.prefix_search("he") # bug: returns hello,hell, and hillel
    
    # Test WordCollection ingestion from file:
#    myDict.createDictStructureFromFiles();
#    print str(myDict.contains("hello"));
#    print str(myDict.prefix_search("hell"));
#    myDict.add("hillel");
#    print str(myDict.prefix_search("he"))
#    print str(myDict.prefix_search("he", cutoffRank=5));
#    print str(myDict.prefix_search("hel", cutoffRank=5));
#    print "Rank of 'hello': " + str(myDict.rank("hello"));
#    print "Num entries: " + str(len(myDict));

    # Test Unicode issues:
    myDict.createDictStructureFromFiles();
    print "'Ne' yields: " + str(myDict.prefix_search('Ne'));
    print "'New' yields: " + str(myDict.prefix_search('New'));
    
    
#    # Test tel pad dictionary:
#    myTelDict = TelPadEncodedWordCollection();
#    print myTelDict.prefix_search(myTelDict.encodeWord("hello"));
#    print myTelDict.prefix_search("dgspjaw");
#    print str(len(myTelDict));
#    print str(myTelDict.size)
#    print "Num of files: " + str(myTelDict.numDictFilesIngested);
