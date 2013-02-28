#!/usr/env python

# Software License Agreement (BSD License)
#
# Copyright (c) 2013, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of the Willow Garage nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE


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
    
    
