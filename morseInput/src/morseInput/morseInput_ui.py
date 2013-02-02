#!/usr/bin/env python

import sys
import os

from gesture_buttons.gesture_button import GestureButton
from gesture_buttons.gesture_button import CommChannel
from gesture_buttons.gesture_button import FlickDirection

from morseToneGeneration import MorseGenerator
from morseToneGeneration import Morse

from python_qt_binding import loadUi;
from python_qt_binding import QtGui;
from python_qt_binding import QtCore;
#from word_completion.word_collection import WordCollection;
from QtGui import QApplication, QMainWindow, QMessageBox, QWidget, QCursor, QHoverEvent, QSizePolicy;
from QtCore import QPoint, Qt, QTimer, QEvent; 

# Dot/Dash RGB: 0,179,240



class Direction:
    HORIZONTAL = 0
    VERTICAL   = 1

class MorseInput(QMainWindow):
    
    commChannel = CommChannel.getInstance();
    MORSE_BUTTON_WIDTH = 100; #px
    MORSE_BUTTON_HEIGHT = 100; #px
    SUPPORT_BUTTON_WIDTHS = 80; #px: The maximum Space and Backspace button widths.
    MOUSE_UNCONSTRAIN_TIMEOUT = 300; # msec
    
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
        self.constrainCursorInHotZone = False; #********
        
        self.connectWidgets();
        self.morseCursor = QCursor(Qt.OpenHandCursor);
        QApplication.setOverrideCursor(self.morseCursor);
        #QApplication.restoreOverrideCursor()
        self.recentMousePos = None;
        self.currentMouseDirection = None;
        # Timer that frees the cursor from
        # vertical/horizontal constraint every few
        # milliseconds, unless mouse keeps moving:
        self.mouseUnconstrainTimer = QTimer();
        self.mouseUnconstrainTimer.setInterval(MorseInput.MOUSE_UNCONSTRAIN_TIMEOUT);
        self.mouseUnconstrainTimer.setSingleShot(True);
        self.mouseUnconstrainTimer.timeout.connect(self.unconstrainTheCursor);

        self.show();
        # Monitor mouse, so that we can constrain mouse movement to
        # vertical and horizontal (must be set after the affected
        # widget(s) are visible):
        #self.setMouseTracking(True)
        self.centralWidget.installEventFilter(self);
        self.centralWidget.setMouseTracking(True)
        
    def findFile(self, path, matchFunc=os.path.isfile):
        if path is None:
            return None
        for dirname in sys.path:
            candidate = os.path.join(dirname, path)
            if matchFunc(candidate):
                return candidate
        return None;

    def insertGestureButtons(self):

        self.dotButton = GestureButton('dot');
        self.dotButton.setMinimumHeight(MorseInput.MORSE_BUTTON_HEIGHT);
        self.dotAndDashHLayout.addWidget(self.dotButton);

        self.dotAndDashHLayout.addStretch();
        
        self.dashButton = GestureButton('dash');
        self.dashButton.setMinimumHeight(MorseInput.MORSE_BUTTON_HEIGHT);
        self.dotAndDashHLayout.addWidget(self.dashButton);
        
        self.eowButton = GestureButton('Space');
        self.endOfWordButtonHLayout.addWidget(self.eowButton);

        self.backspaceButton = GestureButton('Backspace');
        self.backspaceButton.setMaximumWidth(MorseInput.SUPPORT_BUTTON_WIDTHS)
        self.backspaceHLayout.addWidget(self.backspaceButton);
        
        
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

    def eventFilter(self, target, event):
        if (event.type() == QEvent.MouseMove) or (event.type == QHoverEvent):
            if self.constrainCursorInHotZone:
                self.mouseUnconstrainTimer.stop();
                self.handleCursorConstraint(event);
        # Pass this event on to its destination (rather than filtering it):
        return False;
        
    def handleCursorConstraint(self, mouseEvent):
        
        try:
            if self.recentMousePos is None:
                # Very first time: establish a 'previous' mouse cursor position:
                self.recentMousePos = mouseEvent.globalPos();
                return;
                
            globalPosX = mouseEvent.globalX()
            globalPosY = mouseEvent.globalY()
            
            # If cursor moved while we are constraining motion 
            # vertically or horizontally, enforce that constraint now:
            if self.currentMouseDirection is not None:
                if self.currentMouseDirection == Direction.HORIZONTAL:
                    correctedCurPos = QPoint(globalPosX, self.recentMousePos.y());
                    self.recentMousePos.setX(globalPosX);
                else:
                    correctedCurPos = QPoint(self.recentMousePos.x(), globalPosY);
                    self.recentMousePos.setY(globalPosY);
                self.morseCursor.setPos(correctedCurPos);
                return;

            # Not currently constraining mouse move. Check which 
            # movement larger compared to the most recent position: x or y:
            if abs(globalPosX - self.recentMousePos.x()) > abs(globalPosY - self.recentMousePos.y()):
                self.currentMouseDirection = Direction.HORIZONTAL;
            else:
                self.currentMouseDirection = Direction.VERTICAL;
            self.recentMousePos = mouseEvent.globalPos();
        finally:
            # Set timer to unconstrain the mouse if it is
            # not moved for a while (interval is set in __init__()):
            self.mouseUnconstrainTimer.setInterval(MorseInput.MOUSE_UNCONSTRAIN_TIMEOUT);
            self.mouseUnconstrainTimer.start();
            return

    def unconstrainTheCursor(self):
        # If user is hovering inside the dot or dash button,
        # keep the hor/vert mouse move constraint going, even
        # though the timeout of no mouse movement is done:
        if self.dotButton.underMouse() or self.dashButton.underMouse():
            self.mouseUnconstrainTimer.start();
            return
        self.currentMouseDirection = None;
        self.recentMousePos = None;
        
    def exit(self):
        self.morseGenerator.stopMorseGenerator();

if __name__ == '__main__':

    app = QApplication(sys.argv);
    #QApplication.setStyle(QCleanlooksStyle())
    morser = MorseInput();
    app.exec_();
    morser.exit();
    sys.exit();
    
