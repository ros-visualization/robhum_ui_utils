#!/usr/env python

import os
import re
import urllib

# This is a throw-away module. Used once to pull a
# dictionary of the highest ranked 6000 English words
# from search queries. Hard-coded paths. Would need
# generalization if re-used.

def pullFirst1000FromWeb():
    f = urllib.urlopen("http://www.insightin.com/esl/1000.php")
    page = f.read()
    f.close()
    #outFile = os.open(os.getenv("HOME") + "/dldev/EclipseWorkspaces/JBoard/src/JBoard/dict_files/dict" + str(i) + ".html", 'w')
    outFileName = "C:/Users/paepcke/dldev/EclipseWorkspaces/JBoard/src/JBoard/dict_files/dict1000.html";
    outFile = open(outFileName, "w")
    outFile.write(page)
    outFile.close();
    print "Did " + str(i)
    
def pullRestFromWeb():
    for i in range(2000,6100,100):
        f = urllib.urlopen("http://www.insightin.com/esl/" + str(i) + ".php")    
        page = f.read()
        f.close()
        #outFile = os.open(os.getenv("HOME") + "/dldev/EclipseWorkspaces/JBoard/src/JBoard/dict_files/dict" + str(i) + ".html", 'w')
        outFileName = "C:/Users/paepcke/dldev/EclipseWorkspaces/JBoard/src/JBoard/dict_files/dict" + str(i) + ".html"
        outFile = open(outFileName, "w")
        outFile.write(page)
        outFile.close();
        print "Did " + str(i)

def pullOutNumbers():
    matcher = re.compile('word=([^\n]*)\n&rank=([\d]*)')
    for i in range(2100,6100,100):    
        fIn  = open("C:/Users/paepcke/dldev/EclipseWorkspaces/JBoard/src/JBoard/dict_files/dict" + str(i) + ".html");
        fOut = open("C:/Users/paepcke/dldev/EclipseWorkspaces/JBoard/src/JBoard/dict_files/dict" + str(i) + "RankAndWord.txt", "w");
        page = fIn.read();
        for match in re.finditer(matcher, page):
            fOut.write(match.group(2) + "\t" + match.group(1) + "\n");
        fOut.close()
        fIn.close()
        print "Done " + str(i)
    
if __name__ == "__main__":
    pullFirstFromWeb();
    pullRestFromWeb();
    pullOutNumbers();
    
    
