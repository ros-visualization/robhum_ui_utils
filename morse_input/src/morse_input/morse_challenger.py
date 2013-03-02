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
import threading
import random
import ConfigParser
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
    from qt_comm_channel.commChannel import CommChannel
except ImportError as e:
    print(`e`);
    print("Roslib is unavailable. So your PYTHONPATH will need to include src directories for:\n" +
          "qt_dialog_service \n" +\
          "qt_comm_service");
    sys.exit();    


from morseCodeTranslationKey import codeKey;
from python_qt_binding import QtCore, QtGui, loadUi;
from QtGui import QApplication, QMainWindow, QLabel, QPixmap, QCheckBox, QColor;
from QtCore import QTimer, Qt, Signal, QRect;

class MorseChallengerSignals(CommChannel):
    focusLostInadvertently = Signal();

class MorseChallenger(QMainWindow):
    
    def __init__(self):
        super(MorseChallenger,self).__init__();
        
        self.PIXELS_TO_MOVE_PER_TIMEOUT = 3
        self.ABSOLUTE_MAX_NUM_FLOATERS  = 10;
        self.FLOATER_POINT_SIZE = 20;
        self.LETTER_CHECKBOX_NUM_COLS = 6;
        # Number of timeout cycles that detonated
        # letters stay visible:
        self.DETONATION_VISIBLE_CYCLES = 4;

        self.maxNumFloaters = 1;        
        self.lettersToUse = set();
        self.floatersAvailable = set();
        self.floatersInUse = set();
        self.bookeepingAccessLock = threading.Lock();
        # Floaters that detonated. Values are number of timeouts
        # the detonation was visible:
        self.floatersDetonated = {};
        # Used to launch new floaters at random times:
        self.cyclesSinceLastLaunch = 0;
        
        self.dialogService = DialogService();        
        self.optionsFilePath = os.path.join(os.getenv('HOME'), '.morser/morseChallenger.cfg');

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
        self.explosionPixMap = QPixmap(os.path.join(self.iconDir, 'explosion.png'));        

        CommChannel.registerSignals(MorseChallengerSignals);

        self.connectWidgets();
        
        self.generateLetterCheckBoxes();
        self.simultaneousLettersComboBox.addItems(['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']);
        self.generateFloaters();
        
        self.setFocusPolicy(Qt.ClickFocus);
        
        self.letterMoveTimer = QTimer();
        self.letterMoveTimer.setInterval(self.timerIntervalFromSpeedSlider()); # milliseconds
        self.letterMoveTimer.setSingleShot(False);
        self.letterMoveTimer.timeout.connect(self.moveLetters);
        
        # Bring options from config file:
        self.setOptions();
        
        # Styling:
        self.createColors();
        self.setStyleSheet("QWidget{background-color: %s}" % self.lightBlueColor.name());

        self.show();
        
    def connectWidgets(self):
        self.speedHSlider.valueChanged.connect(self.speedChangedAction);
        self.startPushButton.clicked.connect(self.startAction);
        self.stopPushButton.clicked.connect(self.stopAction);
        self.simultaneousLettersComboBox.currentIndexChanged.connect(self.maxNumSimultaneousFloatersAction);
        
        CommChannel.getSignal('MorseChallengerSignals.focusLostInadvertently').connect(self.reassertWindowFocus);
        
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
            font = QtGui.QFont()
            font.setFamily("Courier")
            font.setFixedPitch(True)
            font.setPointSize(self.FLOATER_POINT_SIZE);
            floaterLabel.setFont(font);

            self.floatersAvailable.add(floaterLabel);
            
    def letterCheckAction(self, checkbox, checkedOrNot):
        
        changedLetter = self.checkBoxesToLetters[checkbox];
        configedLetters = self.cfgParser.get('Main', 'letters');
        if checkedOrNot:
            self.lettersToUse.add(self.checkBoxesToLetters[checkbox]);
            configedLetters += changedLetter;
        else:
            self.lettersToUse.discard(self.checkBoxesToLetters[checkbox]);
            configedLetters.replace(changedLetter, "");
            
        self.cfgParser.set('Main', 'letters', configedLetters);
        self.saveOptions();
        
    def startAction(self):
        self.launchFloaters(1);
        self.letterMoveTimer.start();
        
    def stopAction(self):
        self.letterMoveTimer.stop();

        floatersInUseCopy = self.floatersInUse.copy();
        for floater in floatersInUseCopy:
            self.decommissionFloater(floater);
            
    def maxNumSimultaneousFloatersAction(self, newNum):
        # New Combo box picked: 0-based:
        self.maxNumFloaters = newNum + 1;
        try:
            self.cfgParser.set('Main','numLettersTogether', str(newNum));
            self.saveOptions();
        except AttributeError:
            # At startup cfgParser won't exist yet. Ignore:
            pass
        
    def speedChangedAction(self, newSpeed):
        #self.letterMoveTimer.setInterval(newSpeed * 100); # msec.
        self.letterMoveTimer.setInterval(self.timerIntervalFromSpeedSlider(newSpeed)); # msec.
        self.cfgParser.set('Main','letterSpeed', str(newSpeed));
        self.saveOptions();
        
    def keyPressEvent(self, keyEvent):
        letter = keyEvent.text();
        self.letterLineEdit.setText(letter);
        matchingFloaters = {};
        # Find all active floaters that have the pressed key's letter:
        for floater in self.floatersInUse: 
            if floater.text() == letter:
                floaterY = floater.y();
                try:
                    matchingFloaters[floaterY].append(floater);
                except KeyError:
                    matchingFloaters[floaterY] = [floater];
        if len(matchingFloaters) == 0:
            self.activateWindow();
            self.setFocus();
            return;
        # Find the lowest ones:
        lowestY = self.projectionScreenWidget.y();
        yPositions = matchingFloaters.keys();
        for floater in matchingFloaters[max(yPositions)]:
            self.decommissionFloater(floater);
        self.activateWindow();
        self.setFocus();

            
    
    def focusInEvent(self, event):
        '''
        Ensure that floaters are always on top of the app window,
        even if user changes speed slider, checkmarks, etc.:
        @param event:
        @type event:
        '''
        self.raiseAllFloaters();

    def resizeEvent(self, event):
        newWinRect = self.geometry();
        self.cfgParser.set('Appearance', 
                           'winGeometry', 
                           str(newWinRect.x()) 	+ ',' +
                           str(newWinRect.y()) 	+ ',' +
                           str(newWinRect.width()) + ',' +
                           str(newWinRect.height()));
        self.saveOptions();
        
    def raiseAllFloaters(self):
        for floater in self.floatersInUse:
            floater.raise_();
        for floater in self.floatersDetonated.keys():
            floater.raise_();
        
    def decommissionFloater(self, floaterLabel):
        floaterLabel.setHidden(True);
        # Just in case: protect removal, in case caller 
        # passes in an already decommissioned floater:
        try:
            self.floatersInUse.remove(floaterLabel);
        except KeyError:
            pass
        # Adding a floater twice is not an issue,
        # b/c floatersAvailable is a set:
        self.floatersAvailable.add(floaterLabel);
    
    def timerIntervalFromSpeedSlider(self, newSpeed=None):
        if newSpeed is None:
            newSpeed = self.speedHSlider.value();
        return 1000 - newSpeed;
            
    def randomLetters(self, numLetters):
        if len(self.lettersToUse) == 0:
            self.dialogService.showErrorMsg("You must turn on a checkmark for at least one letter.");
            return None;
        lettersToDeploy = [];
        for i in range(numLetters):
            letter = random.sample(self.lettersToUse, 1);
            lettersToDeploy.extend(letter);
        return lettersToDeploy;
    
    def moveLetters(self):
        self.cyclesSinceLastLaunch += 1;
        # Did floater detonate during previous timeout?:
        detonatedFloaters = self.floatersDetonated.keys();
        for detonatedFloater in detonatedFloaters:
            self.floatersDetonated[detonatedFloater] += 1;
            if self.floatersDetonated[detonatedFloater] > self.DETONATION_VISIBLE_CYCLES:
                self.decommissionFloater(detonatedFloater);
                del self.floatersDetonated[detonatedFloater];
        
        remainingFloaters = self.floatersDetonated.keys();
        for floaterLabel in self.floatersInUse:
            if floaterLabel in remainingFloaters:
                continue;
            geo = floaterLabel.geometry();
            newY = geo.y() + self.PIXELS_TO_MOVE_PER_TIMEOUT;
            if newY > self.height():
                newY = self.height();
                self.detonate(floaterLabel);
            floaterLabel.move(geo.x(), newY);
            
        # Done advancing each floater. Is it time to start a new floater?
        numFloatersToLaunch = self.maxNumFloaters - len(self.floatersInUse) + len(self.floatersDetonated);   
        if numFloatersToLaunch > 0:
             # Use the following commented lines if you want the launching of
             # new floaters to be random, e.g. between 2 and 10 timeout intervals:
#            if self.cyclesSinceLastLaunch > random.randint(2,10):
#                self.launchFloaters(self.maxNumFloaters - len(self.floatersInUse));
             self.launchFloaters(numFloatersToLaunch);
        # Launching floaters deactivates the main window, thereby losing the keyboard focus.
        # We can't seem to reassert that focus within this timer interrupt service routine.
        # So, issue a signal that will do it after return:
        CommChannel.getSignal('MorseChallengerSignals.focusLostInadvertently').emit();
                
    def launchFloaters(self, numFloaters):
        newLetters = self.randomLetters(numFloaters);
        if newLetters is None:
            return;
        for letter in newLetters:
            # Pick a random horizontal location, at least 3 pixels in
            # from the left edge, and at most 3 pixels back from the right edge:
            screenGeo = self.projectionScreenWidget.geometry();
            appWinGeo = self.geometry();
            appWinX   = appWinGeo.x();
            # Random number among all the application window's X coordinates:
            xLoc = random.randint(appWinX + 3, appWinX + screenGeo.width() - 3);
            yLoc = appWinGeo.y();
            self.getFloaterLabel(letter, xLoc, yLoc);
        self.cyclesSinceLastLaunch = 0;

    def getFloaterLabel(self, letter, x, y):
        try:
            label = self.floatersAvailable.pop();
            label.clear();
        except KeyError:
            return None;
        self.floatersInUse.add(label);
        label.setText(letter);
        label.move(x,y);
        label.setHidden(False);
    
    def detonate(self, floaterLabel):
        # Floater was detonated zero cycles ago:
        self.floatersDetonated[floaterLabel] = 0;
        floaterLabel.clear();
        floaterLabel.setPixmap(self.explosionPixMap);

    def findFile(self, path, matchFunc=os.path.isfile):
        if path is None:
            return None
        for dirname in sys.path:
            candidate = os.path.join(dirname, path)
            if matchFunc(candidate):
                return candidate
        return None;

    def reassertWindowFocus(self):
        self.window().activateWindow();
        self.raise_();
        self.raiseAllFloaters();

    def setOptions(self):
        
        self.optionsDefaultDict = {
                    'letters'             : "",
                    'letterSpeed'         : str(10),
                    'numLettersTogether'  : str(0),
                    'winGeometry'         : '100,100,700,560',
                    }

        self.cfgParser = ConfigParser.SafeConfigParser(self.optionsDefaultDict);
        self.cfgParser.add_section('Main');
        self.cfgParser.add_section('Appearance');
        self.cfgParser.read(self.optionsFilePath);
        
        mainWinGeometry = self.cfgParser.get('Appearance', 'winGeometry');
        # Get four ints from the comma-separated string of upperLeftX, upperLeftY,
        # Width,Height numbers:
        try:
            nums = mainWinGeometry.split(',');
            self.setGeometry(QRect(int(nums[0].strip()),int(nums[1].strip()),int(nums[2].strip()),int(nums[3].strip())));
        except Exception as e:
            self.dialogService.showErrorMsg("Could not set window size; config file spec not grammatical: %s. (%s" % (mainWinGeometry, `e`));
        
        letterSpeed = self.cfgParser.getint('Main', 'letterSpeed');
        self.speedHSlider.setValue(letterSpeed);
        #self.speedChangedAction(letterSpeed);
        self.letterMoveTimer.setInterval(self.timerIntervalFromSpeedSlider()); # milliseconds
        
        numLettersTogether = self.cfgParser.getint('Main', 'numLettersTogether');
        self.simultaneousLettersComboBox.setCurrentIndex(numLettersTogether);
        
        lettersToUse = self.cfgParser.get('Main', 'letters');
        for letter in lettersToUse:
            self.lettersToCheckBoxes[letter].setChecked(True);
  
    def saveOptions(self):
        try:
            # Does the config dir already exist? If not
            # create it:
            optionsDir = os.path.dirname(self.optionsFilePath);
            if not os.path.isdir(optionsDir):
                os.makedirs(optionsDir, 0777);
            with open(self.optionsFilePath, 'wb') as outFd:
                self.cfgParser.write(outFd);
        except IOError as e:
            self.dialogService.showErrorMsg("Could not save options: %s" % `e`);

        
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
    
