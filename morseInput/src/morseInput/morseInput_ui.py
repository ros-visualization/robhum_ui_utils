#!/usr/bin/env python

import sys
import os

from gesture_buttons.gesture_button import GestureButton
from gesture_buttons.gesture_button import CommChannel
from gesture_buttons.gesture_button import  FlickDirection

from morseToneGeneration import MorseGenerator
from morseToneGeneration import Morse

from python_qt_binding import loadUi
from python_qt_binding import QtGui
#from word_completion.word_collection import WordCollection;
from QtGui import QApplication, QMainWindow, QDialog, QPushButton, QTextEdit, QTextCursor, QShortcut, QErrorMessage;
from QtGui import QMessageBox, QWidget;

class MorseInput(QMainWindow):
    
    commChannel = CommChannel.getInstance();
    
    def __init__(self):
        super(MorseInput,self).__init__();
        
        # Find QtCreator's XML file in the PYTHONPATH:
        currDir = os.path.realpath(__file__);
        relPathQtCreatorFile = "qt_files/morseInput/morseInput.ui";
        qtCreatorXMLFilePath = self.findFile(relPathQtCreatorFile);
        if qtCreatorXMLFilePath is None:
            raise ValueError("Can't find QtCreator user interface file %s" % relPathQtCreatorFile);
        # Make QtCreator generated UI a child if this instance:
        loadUi(qtCreatorXMLFilePath, self);
        self.setWindowTitle("Morse Input");
        
        self.morseGenerator = MorseGenerator();   
        self.morseGenerator.setSpeed(1.7);   

        self.insertGestureButtons();
        GestureButton.setFlicksEnabled(False);
        
        self.connectWidgets();
        
        self.show();
        
    def findFile(self, path, matchFunc=os.path.isfile):
        if path is None:
            return None
        for dirname in sys.path:
            candidate = os.path.join(dirname, path)
            if matchFunc(candidate):
                return candidate
        return None;

    def insertGestureButtons(self):
        self.dotButton = GestureButton('dot', parent=self.dotButtonWidget);
        self.dashButton = GestureButton('dash', parent=self.dashButtonWidget);
        self.eowButton = GestureButton('End of Word', parent=self.endOfWordButtonWidget);
        self.backspaceButton = GestureButton('Backspace', parent=self.backspaceButtonWidget);
        
    def connectWidgets(self):
        MorseInput.commChannel.buttonEnteredSig.connect(self.buttonEntered);
        MorseInput.commChannel.buttonExitedSig.connect(self.buttonExited);
    
    def buttonEntered(self, buttonObj):
        if buttonObj == self.dotButton:
            self.morseGenerator.startMorseSeq(Morse.DOT);
        elif buttonObj == self.dashButton:
            self.morseGenerator.startMorseSeq(Morse.DASH);
        elif buttonObj == self.eowButton:
            #****
            print "End of word"
            #****
        elif buttonObj == self.backspaceButton:
            #****
            print "Backspace"
            #****
        
    def buttonExited(self, buttonObj):
        if buttonObj == self.dotButton:
            self.morseGenerator.stopMorseSeq();
        elif buttonObj == self.dashButton:
            self.morseGenerator.stopMorseSeq();
        
    def exit(self):
        self.morseGenerator.stopMorseGenerator();

if __name__ == '__main__':

    app = QApplication(sys.argv);
    #QApplication.setStyle(QCleanlooksStyle())
    morser = MorseInput();
    app.exec_();
    morser.exit();
    sys.exit();
    
