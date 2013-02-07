

from morseCodeTranslationKey import codeKey;

from python_qt_binding import loadUi;
from python_qt_binding import QtGui;
from python_qt_binding import QtCore;
from QtGui import QDialog
#from QtCore import QPoint, Qt, QTimer, QEvent, Signal, QCoreApplication, QRect; 

class MorseCheatSheet(QDialog):
    
    def __init__(self):
        super(MorseCheatSheet,self).__init__();
        
    def initTable(self):
        relPathQtCreatorFileMorseTable = "qt_files/morseTable/morsetabledialog.ui";
        qtCreatorXMLFilePath = self.findFile(relPathQtCreatorFileMorseTable);
        if qtCreatorXMLFilePath is None:
            raise ValueError("Can't find Morse cheat sheet QtCreator user interface file %s" % relPathQtCreatorFileMorseTable);
        # Make QtCreator generated UI a child if this instance:
        loadUi(qtCreatorXMLFilePath, self);
        self.windowTitle = "Morser Cheat Sheet";
        self.setWindowTitle(self.windowTitle);
        
        # Need table letter-->morse, rather than morse-->letter,
        # which the codeKey provides. Create that:
        morseSheetDict = {};
        for keyValue in codeKeys.items:
            morseSheetDict[keyValue[1]] = keyValue[0];
                
        # Fill the text labels:
        morseSorted = sorted(morseSheetDict.keys());
        colCount = self.morseCodeGrid.columnCount();
        rowCount = self.morseCodeGrid.rowCount();
        
        