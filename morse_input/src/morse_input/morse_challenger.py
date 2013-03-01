#!/usr/bin/env python

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

try:
    import roslib; roslib.load_manifest('morse_input');
    ROS_AVAILABLE = True;
except ImportError:
    ROS_AVAILABLE = False;

import time
import sys
import os
import random
from functools import partial

#try:
#    from morseCodeTranslationKey import codeKey;
#except ImportError as e:
#    print(`e`);
#    print("Roslib is unavailable. So your PYTHONPATH will need to include src directories for:\n" +
#          "gesture_buttons \n" +
#          "qt_comm_channel \n" +
#          "qt_dialog_service \n" +
#          "virtual_keyboard \n");
#    sys.exit();    

try:
    from qt_dialog_service.qt_dialog_service import DialogService
except ImportError as e:
    print(`e`);
    print("Roslib is unavailable. So your PYTHONPATH will need to include src directories for:\n" +
          "qt_dialog_service \n");
    sys.exit();    


from morseCodeTranslationKey import codeKey;
from python_qt_binding import QtCore, QtGui, loadUi;
from QtGui import QApplication, QMainWindow, QLabel, QPixmap, QCheckBox, QColor;
from QtCore import QTimer;

class MorseChallenger(QMainWindow):
    
    def __init__(self):
        super(MorseChallenger,self).__init__();
        
        self.PIXELS_TO_MOVE_PER_TIMEOUT = 3;
        self.ABSOLUTE_MAX_NUM_FLOATERS  = 10;
        self.FLOATER_POINT_SIZE = 16;
        self.LETTER_CHECKBOX_NUM_COLS = 6;
        # Number of timeout cycles that detonated
        # letters stay visible:
        self.DETONATION_VISIBLE_CYCLES = 4;

        self.maxNumFloaters = 1;        
        self.lettersToUse = set();
        self.floatersAvailable = set();
        self.floatersInUse = set();
        # Floaters that detonated. Values are number of timeouts
        # the detonation was visible:
        self.floatersDetonated = {};
        
        self.dialogService = DialogService();        
        
        # Load UI for Morse Challenger:
        relPathQtCreatorFileMainWin = "qt_files/morseChallenger/morseChallenger.ui";
        qtCreatorXMLFilePath = self.findFile(relPathQtCreatorFileMainWin);
        if qtCreatorXMLFilePath is None:
            raise ValueError("Can't find QtCreator user interface file %s" % relPathQtCreatorFileMainWin);
        # Make QtCreator generated UI a child of this instance:
        loadUi(qtCreatorXMLFilePath, self);
        self.windowTitle = "Morse Challenger";
        self.setWindowTitle(self.windowTitle);

        self.iconDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'icons')
        self.explosionPixMap = QPixmap(os.path.join(self.iconDir, 'explosion.jpg'));        

        self.connectWidgets();
        
        self.generateLetterCheckBoxes();
        self.generateFloaters();
        
        self.letterMoveTimer = QTimer();
        self.letterMoveTimer.setInterval(100); # milliseconds
        self.letterMoveTimer.setSingleShot(False);
        self.letterMoveTimer.timeout.connect(self.moveLetters);
        
        # Styling:
        self.createColors();
        self.setStyleSheet("QWidget{background-color: %s}" % self.lightBlueColor.name());

        self.show();
        
    def connectWidgets(self):
        self.speedHSlider.valueChanged.connect(self.speedChangedAction);
        self.startPushButton.clicked.connect(self.startAction);
        self.stopPushButton.clicked.connect(self.stopAction);
        
    def createColors(self):
        self.grayBlueColor = QColor(89,120,137);  # Letter buttons
        self.lightBlueColor = QColor(206,230,243); # Background
        self.darkGray      = QColor(65,88,101);   # Central buttons
        self.wordListFontColor = QColor(62,143,185); # Darkish blue.
        self.purple        = QColor(147,124,195); # Gesture button pressed
        
    def generateLetterCheckBoxes(self):
        self.lettersToCheckBoxes = {};
        self.checkBoxesToLetters = {};
        letters = sorted(codeKey.values());
        numRows = (len(letters) % self.LETTER_CHECKBOX_NUM_COLS) + 1;
        col = 0;
        row = 0;
        letterIndex = 0;
        while(True):
            letter = letters[letterIndex];
            checkbox = QCheckBox();
            self.lettersToCheckBoxes[letter] = checkbox;
            self.checkBoxesToLetters[checkbox] = letter;
            checkbox.setText(str(letter));
            checkbox.toggled.connect(partial(self.letterCheckAction, checkbox));
            self.letterCheckboxGridLayout.addWidget(checkbox, row, col);
            col += 1;
            if (col >= self.LETTER_CHECKBOX_NUM_COLS):
                col = 0;
                row += 1;
            letterIndex += 1;
            if letterIndex >= len(letters):
                break;
        
    def generateFloaters(self):
        for i in range(self.ABSOLUTE_MAX_NUM_FLOATERS):
            floaterLabel = QLabel();
            floaterLabel.move(0,0);
            floaterLabel.font().setPointSize(self.FLOATER_POINT_SIZE);
            self.floatersAvailable.add(floaterLabel);
            
    def letterCheckAction(self, checkbox, checkedOrNot):
        if checkedOrNot:
            self.lettersToUse.add(self.checkBoxesToLetters[checkbox]);
        else:
            self.lettersToUse.discard(self.checkBoxesToLetters[checkbox]);

    def startAction(self):
        self.launchFloaters(1);
        self.letterMoveTimer.start();
        
    def stopAction(self):
        self.letterMoveTimer.stop();
        floatersInUseCopy = self.floatersInUse.copy();
        for floater in floatersInUseCopy:
            floater.setHidden(True);
            self.floatersInUse.remove(floater);
            self.floatersAvailable.add(floater);
            
    def maxNumSimultaneousFloatersAction(self, newNum):
        self.maxNumFloaters = newNum;
        
    def speedChangedAction(self, newSpeed):
        self.letterMoveTimer.setInterval(newSpeed * 100); # msec.
            
    def randomLetters(self, numLetters):
        if len(self.lettersToUse) == 0:
            self.dialogService.showErrorMsg("You must turn on a checkmark for at least one letter.");
            return;
        return random.sample(self.lettersToUse, numLetters);
    
    def moveLetters(self):
        self.cyclesSinceLastLaunch += 1;
        for floaterLabel in self.floatersInUse:

            # Did floater detonate during previous timeout?:
            floatersDetonatedCopy = self.floatersDetonated.copy();
            for detonatedFloater in floatersDetonatedCopy.keys():
                self.floatersDetonated[detonatedFloater] += 1;
                if floatersDetonated[detonatedFloater] > self.DETONATION_VISIBLE_CYCLES:
                    detonatedFloater.setHidden(True);
                    self.floatersAvailable.add(detonatedFloater);
                    self.floatersInUse.remove(detonatedFloater);
                    self.floatersDetonated.remove(detonatedFloater);
                    
            if floaterLabel in self.floatersDetonated.keys():
                continue;
            
            geo = floaterLabel.geometry();
            newY = geo.y() + self.PIXELS_TO_MOVE_PER_TIMEOUT;
            if newY > self.height():
                newY = self.height();
                self.detonate(floaterLabel);
            geo.setY(newY)
            floaterLabel.move(geo.x(), newY);
            
        # Done advancing each floater. Is it time to start a new floater?
        if (len(self.floatersInUse) < self.maxNumFloaters) or len(self.floatersInUse) == 0:
            if self.cyclesSinceLastLaunch > random.randint(2,10):
                self.launchFloaters(self.maxNumFloaters - len(self.floatersInUse));

    def launchFloaters(self, numFloaters):
        newLetters = self.randomLetters(numFloaters);
        for letter in newLetters:
            # Pick a random horizontal location, at least 3 pixels in
            # from the left edge, and at most 3 pixels back from the right edge:
            xLoc = random.randint(3, self.projectionScreenWidget.geometry().width() - 3);
            yLoc = 0;
            self.getFloaterLabel(letter, xLoc, yLoc);
        self.cyclesSinceLastLaunch = 0;

    def getFloaterLabel(self, letter, x, y):
        label = self.floatersAvailable.pop();
        self.floatersInUse.add(label);
        label.setText(letter);
        label.move(x,y);
        label.setHidden(False);
    
    def detonate(self, floaterLabel):
        # Floater was detonated zero cycles ago:
        self.floatersDetonated[floaterLabel] = 0;
        floaterLabel.setPixmap(self.explosionPixMap);

    def findFile(self, path, matchFunc=os.path.isfile):
        if path is None:
            return None
        for dirname in sys.path:
            candidate = os.path.join(dirname, path)
            if matchFunc(candidate):
                return candidate
        return None;

    def exit(self):
        QApplication.quit();

    def closeEvent(self, event):
        QApplication.quit();
        # Bubble event up:
        event.ignore();


        
if __name__ == '__main__':

    app = QApplication(sys.argv);
    #QApplication.setStyle(QCleanlooksStyle())
    morserChallenge = MorseChallenger();
    app.exec_();
    morserChallenge.exit();
    sys.exit();
    
