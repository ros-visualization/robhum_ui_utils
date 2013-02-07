
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
                
        # Fill the text labels:
        morseSorted = sorted(morseSheetDict.keys());
        colCount = self.morseCodeGrid.columnCount();
        rowCount = self.morseCodeGrid.rowCount();
        keyIndex = 0;
        letterLists = [string.lowercase, string.digits, string.punctuation];
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
                
        
        
        