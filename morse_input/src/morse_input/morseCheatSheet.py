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



import string

from morseCodeTranslationKey import codeKey;

from python_qt_binding import loadUi;
from python_qt_binding import QtGui;
from python_qt_binding import QtCore;
from QtGui import QDialog
#from QtCore import QPoint, Qt, QTimer, QEvent, Signal, QCoreApplication, QRect; 

class MorseCheatSheet(QDialog):
    
    def __init__(self, parent=None):
        super(MorseCheatSheet,self).__init__(parent);
        self.parent = parent;
        self.initTable();
        
    def initTable(self):
        relPathQtCreatorFileMorseTable = "qt_files/morseTable/morsetabledialog.ui";
        qtCreatorXMLFilePath = self.parent.findFile(relPathQtCreatorFileMorseTable);
        if qtCreatorXMLFilePath is None:
            raise ValueError("Can't find Morse cheat sheet QtCreator user interface file %s" % relPathQtCreatorFileMorseTable);
        # Make QtCreator generated UI a child if this instance:
        loadUi(qtCreatorXMLFilePath, self);
        self.windowTitle = "Morser Cheat Sheet";
        self.setWindowTitle(self.windowTitle);
        
        # Need table letter-->morse, rather than morse-->letter,
        # which the codeKey provides. Create that:
        morseSheetDict = {};
        for keyValue in codeKey.items():
            morseSheetDict[keyValue[1]] = keyValue[0];
                
        # Get string with just the punctuation letters for which we
        # have Morse:
        punctuation = '';
        for punctLetter in string.punctuation:
            if morseSheetDict.has_key(punctLetter):
                punctuation += punctLetter;
        
        # Special characters:
        specialChars = ['BS','NL', 'HS'];
        
        # Fill the text labels:
        colCount = self.morseCodeGrid.columnCount();
        rowCount = self.morseCodeGrid.rowCount();
        keyIndex = 0;
        letterLists = [string.lowercase, string.digits, punctuation, specialChars];
        currentList = 0;
        for col in range(colCount):
            for row in range(rowCount):
                labelTxt = letterLists[currentList][keyIndex] + ": " + morseSheetDict[letterLists[currentList][keyIndex]]
                labelObj = self.morseCodeGrid.itemAtPosition(row, col);
                labelObj.widget().setText(labelTxt);
                keyIndex += 1
                if keyIndex >= len(letterLists[currentList]):
                    currentList += 1;
                    keyIndex = 0;
                    if currentList >= len(letterLists):
                        return;
                
        
        
        