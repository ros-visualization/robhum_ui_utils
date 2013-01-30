#!/usr/bin/env python

from gesture_buttons.gesture_button import GestureButton
from gesture_buttons.gesture_button import CommChannel
from gesture_buttons.gesture_button import  FlickDirection

from python_qt_binding import QtGui
#from word_completion.word_collection import WordCollection;
from QtGui import QApplication, QMainWindow, QDialog, QPushButton, QTextEdit, QTextCursor, QShortcut, QErrorMessage;
from QtGui import QMessageBox, QWidget;

class MorseInput(QWidget):
    
    def __init__(self):
        super(MorseInput,self).__init__();

        self.setWindowTitle("Morse Input");        
        
        # Find QtCreator's XML file in the PYTHONPATH:
        currDir = os.path.realpath(__file__);
        relPathQtCreatorFile = "qt_files/morseInput/morseInput.ui";
        qtCreatorXMLFilePath = Utilities.findFile(relPathQtCreatorFile);
        if qtCreatorXMLFilePath is None:
            raise ValueError("Can't find QtCreator user interface file %s" % relPathQtCreatorFile);
        # Make QtCreator generated UI a child if this instance:
        QtBindingHelper.loadUi(qtCreatorXMLFilePath, self);
        


if __name__ == '__main__':
    pass
