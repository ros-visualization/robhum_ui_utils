#!/usr/bin/env python

# To do:
# - Save settings, like window size in $HOME/.morse  
# - Options dialog:
#    * Morse speed
#    * Use cursor constraint yes/no
#    * Inter-letter and inter-word time
#    * Speak vs. type
#    * dwell-pause
# - Publish package


import sys
import os

from gesture_buttons.gesture_button import GestureButton
from gesture_buttons.gesture_button import FlickDirection

from qt_comm_channel.commChannel import CommChannel

from morseToneGeneration import MorseGenerator
from morseToneGeneration import Morse
from morseToneGeneration import TimeoutReason

from python_qt_binding import loadUi;
from python_qt_binding import QtGui;
from python_qt_binding import QtCore;
#from word_completion.word_collection import WordCollection;
from QtGui import QApplication, QMainWindow, QMessageBox, QWidget, QCursor, QHoverEvent, QColor, QIcon;
from QtCore import QPoint, Qt, QTimer, QEvent, Signal; 

# Dot/Dash RGB: 0,179,240


class Direction:
    HORIZONTAL = 0
    VERTICAL   = 1

class MorseInputSignals(CommChannel):
    letterDone = Signal(int);

class MorseInput(QMainWindow):
    '''
    Manages all UI interactions with the Morse code generation.
    '''
    
    MORSE_BUTTON_WIDTH = 100; #px
    MORSE_BUTTON_HEIGHT = 100; #px
    
    SUPPORT_BUTTON_WIDTHS = 80; #px: The maximum Space and Backspace button widths.
    SUPPORT_BUTTON_HEIGHTS = 80; #px: The maximum Space and Backspace button heights.
    
    MOUSE_UNCONSTRAIN_TIMEOUT = 300; # msec
    
    def __init__(self):
        super(MorseInput,self).__init__();

        CommChannel.registerSignals(MorseInputSignals);
        
        # Find QtCreator's XML file in the PYTHONPATH, and load it:
        currDir = os.path.realpath(__file__);
        relPathQtCreatorFile = "qt_files/morseInput/morseInput.ui";
        qtCreatorXMLFilePath = self.findFile(relPathQtCreatorFile);
        if qtCreatorXMLFilePath is None:
            raise ValueError("Can't find QtCreator user interface file %s" % relPathQtCreatorFile);
        # Make QtCreator generated UI a child if this instance:
        loadUi(qtCreatorXMLFilePath, self);
        self.setWindowTitle("Morser: Semi-automatic Morse code input");
        
        # Get a morse generator that manages all Morse 
        # generation and timing:
        self.morseGenerator = MorseGenerator(MorseInput.letterCompleteNotification);
        self.morseGenerator.setSpeed(1.7);

        # Create the gesture buttons for dot/dash/space/backspace:
        self.insertGestureButtons();
        GestureButton.setFlicksEnabled(False);
        
        self.connectWidgets();
        
        # Set cursor to hand icon while inside Morser:
        self.morseCursor = QCursor(Qt.OpenHandCursor);
        QApplication.setOverrideCursor(self.morseCursor);
        #QApplication.restoreOverrideCursor()
        
        # Init capability of constraining cursor to
        # move only virtically and horizontally:
        self.initCursorContrainer();
        
        # Styling:
        self.createColors();
        self.setStyleSheet("QWidget{background-color: %s}" % self.lightBlueColor.name());

        self.show();

        # Monitor mouse, so that we can constrain mouse movement to
        # vertical and horizontal (must be set after the affected
        # widget(s) are visible):
        #self.setMouseTracking(True)
        self.centralWidget.installEventFilter(self);
        self.centralWidget.setMouseTracking(True)

    def initCursorContrainer(self):
        self.constrainCursorInHotZone = False; #********
        self.recentMousePos = None;
        self.currentMouseDirection = None;
        # Timer that frees the cursor from
        # vertical/horizontal constraint every few
        # milliseconds, unless mouse keeps moving:
        self.mouseUnconstrainTimer = QTimer();
        self.mouseUnconstrainTimer.setInterval(MorseInput.MOUSE_UNCONSTRAIN_TIMEOUT);
        self.mouseUnconstrainTimer.setSingleShot(True);
        self.mouseUnconstrainTimer.timeout.connect(self.unconstrainTheCursor);

    def createColors(self):
        self.grayBlueColor = QColor(89,120,137);  # Letter buttons
        self.lightBlueColor = QColor(206,230,243); # Background
        self.darkGray      = QColor(65,88,101);   # Central buttons
        self.wordListFontColor = QColor(62,143,185); # Darkish blue.
        self.purple        = QColor(147,124,195); # Gesture button pressed
        
        
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
        iconDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'icons')
        self.dotButton.setIcon(QIcon(os.path.join(iconDir, 'dot.png'))); 
        self.dotButton.setText("");
        # Don't have button assume the pressed-down color when 
        # clicked:
        self.dotButton.setFocusPolicy(Qt.NoFocus);
        self.dotButton.setMinimumHeight(MorseInput.MORSE_BUTTON_HEIGHT);
        self.dotButton.setMinimumWidth(MorseInput.MORSE_BUTTON_WIDTH);
        self.dotAndDashHLayout.addWidget(self.dotButton);

        self.dotAndDashHLayout.addStretch();
        
        self.dashButton = GestureButton('dash');
        self.dashButton.setIcon(QIcon(os.path.join(iconDir, 'dash.png')));
        self.dashButton.setText("");
        # Don't have button assume the pressed-down color when 
        # clicked:
        self.dashButton.setFocusPolicy(Qt.NoFocus);
        self.dashButton.setMinimumHeight(MorseInput.MORSE_BUTTON_HEIGHT);
        self.dashButton.setMinimumWidth(MorseInput.MORSE_BUTTON_WIDTH);
        self.dotAndDashHLayout.addWidget(self.dashButton);
        
        self.eowButton = GestureButton('Space');
        # Don't have button assume the pressed-down color when 
        # clicked:
        self.eowButton.setFocusPolicy(Qt.NoFocus);
        self.eowButton.setMaximumWidth(MorseInput.SUPPORT_BUTTON_WIDTHS)        
        self.eowButton.setMinimumHeight(MorseInput.SUPPORT_BUTTON_HEIGHTS)        
        self.endOfWordButtonHLayout.addWidget(self.eowButton);

        self.backspaceButton = GestureButton('Backspace');
        # Don't have button assume the pressed-down color when 
        # clicked:
        self.backspaceButton.setFocusPolicy(Qt.NoFocus);
        self.backspaceButton.setMaximumWidth(MorseInput.SUPPORT_BUTTON_WIDTHS)
        self.backspaceButton.setMinimumHeight(MorseInput.SUPPORT_BUTTON_HEIGHTS)
        self.backspaceHLayout.addWidget(self.backspaceButton);
        
        
    def connectWidgets(self):
        CommChannel.getSignal('GestureSignals.buttonEnteredSig').connect(self.buttonEntered);
        CommChannel.getSignal('GestureSignals.buttonExitedSig').connect(self.buttonExited);
        CommChannel.getSignal('MorseInputSignals.letterDone').connect(self.letterCompleteNotification);
    
    def buttonEntered(self, buttonObj):
        if buttonObj == self.dotButton:
            self.morseGenerator.startMorseSeq(Morse.DOT);
        elif buttonObj == self.dashButton:
            self.morseGenerator.startMorseSeq(Morse.DASH);
        elif buttonObj == self.eowButton:
            #****
            buttonObj.animateClick();
            print "End of word"
            #****
        elif buttonObj == self.backspaceButton:
            #****
            buttonObj.animateClick();
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

    @staticmethod
    def letterCompleteNotification(reason):
        self.letterCompleteSignal.emit(reason);

    @QtCore.Slot(int)
    def printLetter(self, reason):
        alpha = self.morseGenerator.getAndRemoveAlpha()
        if reason == TimeoutReason.END_OF_WORD:
            alpha += ' '; 
        print("Alpha:'%s'", alpha);

    def exit(self):
        self.morseGenerator.stopMorseGenerator();

if __name__ == '__main__':

    app = QApplication(sys.argv);
    #QApplication.setStyle(QCleanlooksStyle())
    morser = MorseInput();
    app.exec_();
    morser.exit();
    sys.exit();
    
