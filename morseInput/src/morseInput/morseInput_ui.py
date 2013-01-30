#!/usr/bin/env python

import sys
import os

from gesture_buttons.gesture_button import GestureButton
from gesture_buttons.gesture_button import CommChannel
from gesture_buttons.gesture_button import  FlickDirection

from morseToneGeneration import MorseGenerator
from morseToneGeneration import Morse

from python_qt_binding import loadUi;
from python_qt_binding import QtGui;
from python_qt_binding import QtCore;
#from word_completion.word_collection import WordCollection;
from QtGui import QApplication, QMainWindow, QMessageBox, QWidget, QCursor;
from QtCore import QPoint, Qt; 

class MorseInput(QMainWindow):
    
    commChannel = CommChannel.getInstance();
    MORSE_BUTTON_WIDTH = 100; #px
    MORSE_BUTTON_HEIGHT = 100; #px
    
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
        # Monitor mouse, so that we can constrain mouse movement to
        # vertical and horizontal:
        self.setMouseTracking(True)
        QApplication.setOverrideCursor(QCursor(Qt.OpenHandCursor))
        #QApplication.restoreOverrideCursor()


        self.show();
        #*****************
        selfPoint00 = self.mapToParent(QPoint(0,0))
        selfX00 = selfPoint00.x();
        selfY00 = selfPoint00.y();
        
        selfPoint = self.mapToParent(self.pos())
        selfX = selfPoint.x();
        selfY = selfPoint.y();
        
        dashButtonFromGlobalPt = self.dashButtonWidget.mapFromGlobal(self.dashButtonWidget.pos());
        dashButtonFromGlX = dashButtonFromGlobalPt.x()
        dashButtonFromGlY = dashButtonFromGlobalPt.y()
        selfFromGlobalPt = self.dashButtonWidget.mapFromGlobal(self.pos())
        selfFromGlX = dashButtonFromGlobalPt.x()
        selfFromGlY = dashButtonFromGlobalPt.y()
        2+3
        
        #*****************
        
        
        
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
        
        self.dotButton.setMinimumWidth(MorseInput.MORSE_BUTTON_WIDTH);
        self.dotButton.setMinimumHeight(MorseInput.MORSE_BUTTON_HEIGHT);
        #**********************8
        dotButtonPoint = self.dotButton.mapToGlobal(QPoint(0,0));
        
        self.dashButton.setMinimumWidth(MorseInput.MORSE_BUTTON_WIDTH);
        self.dashButton.setMinimumHeight(MorseInput.MORSE_BUTTON_HEIGHT);
        dashButtonGlobalPoint = self.dashButtonWidget.mapToGlobal(QPoint(0,0));
        
        dashButtonFromGlobalPt = self.dashButtonWidget.mapFromGlobal(self.dashButtonWidget.pos());
        dashButtonFromGlX = dashButtonFromGlobalPt.x()
        dashButtonFromGlY = dashButtonFromGlobalPt.y()
        selfFromGlobalPt = self.dashButtonWidget.mapFromGlobal(self.pos())
        selfFromGlX = dashButtonFromGlobalPt.x()
        selfFromGlY = dashButtonFromGlobalPt.y()
        
        dashButtonRect = self.dashButton.rect();
        self.dashButtonLeftX  = dashButtonGlobalPoint.x();
        self.dashButtonRightX = self.dashButtonLeftX + dashButtonRect.width();
        self.dashButtonTopY   = dashButtonGlobalPoint.y();
        self.dashButtonBottomY   = self.dashButtonTopY + dashButtonRect.height();
        #**********************8        
        
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
        
    def mouseMoveEvent(self, mouseEvent):
        globalPosX = mouseEvent.globalX()
        globalPosY = mouseEvent.globalY()
        mouseEvent.cursor().setPosition(globalPosX + 300)
        10+3
        
    def exit(self):
        self.morseGenerator.stopMorseGenerator();

if __name__ == '__main__':

    app = QApplication(sys.argv);
    #QApplication.setStyle(QCleanlooksStyle())
    morser = MorseInput();
    app.exec_();
    morser.exit();
    sys.exit();
    
