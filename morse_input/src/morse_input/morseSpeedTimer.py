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


import time

from python_qt_binding import QtCore, QtGui;
#from QtGui import 
from QtCore import QObject

from qt_comm_channel.commChannel import CommChannel

class MorseSpeedTimer(QObject):
    
    def __init__(self, parentWin):
        super(MorseSpeedTimer,self).__init__();
        self.morseWin = parentWin;
        self.resetAll();
        self.connectWidgets();

    def connectWidgets(self):
        self.morseWin.speedMeasureClearButton.clicked.connect(self.resetAll);

    def timeMeToggled(self):
        if self.currentlyTiming:
            self.stopTiming();
        else:
            self.startTiming();
            
    def resetAll(self):
        self.numLetters = 0;
        self.numWords   = 0;
        self.timerCocked = False;
        self.setLettersLabel(0);
        self.setWordsLabel(0);
        self.setSpeedLabel(0);
        self.startTime = 0;
        self.currentlyTiming = False;
        self.timingPaused = False;
        self.morseWin.timeMeButton.setChecked(False);
        self.morseWin.blinkCrosshair(doBlink=False);

    def startTiming(self):
        self.resetAll();
        self.currentlyTiming = True;
        self.timerCocked = True;
        self.morseWin.blinkCrosshair(doBlink=True)
        CommChannel.getSignal('MorseInputSignals.letterDone').connect(self.newLetter);

    def pauseTiming(self):
        if not self.currentlyTiming:
            return;
        self.pauseStartTime = time.time();
        self.timingPaused = True;
        self.morseWin.blinkCrosshair(doBlink=True);
        
    def resumeTiming(self):
        if not self.timingPaused:
            return;
        timeResumed = time.time();
        self.startTime += (timeResumed - self.pauseStartTime);
        self.timingPaused = False;
        self.morseWin.blinkCrosshair(doBlink=False);

    def stopTiming(self):
        self.endTime = time.time();
        self.currentlyTiming = False;
        self.morseWin.blinkCrosshair(doBlink=False);

    @QtCore.Slot(int,str)
    def newLetter(self, reason, detail):
        if self.timerCocked:
            self.timerCocked = False;
            self.morseWin.blinkCrosshair(doBlink=False);
            self.startTime = time.time();
        elif self.timingPaused or not self.currentlyTiming:
            return;
            
        self.numLetters += 1;
        if self.numLetters % 5 == 0:
            self.numWords = self.numLetters / 5.0;
        speed = self.currentSpeed();
        self.setLettersLabel(self.numLetters);
        self.setWordsLabel(self.numWords);
        self.setSpeedLabel(speed);
        
    def currentSpeed(self):
        elapsedTime = time.time() - self.startTime;
        wpm = self.numWords*60.0/elapsedTime;
        return wpm;

    def setLettersLabel(self, newNum):
        self.setNumberDisplay(self.morseWin.numLettersInfoLabel, int(newNum));

    def setWordsLabel(self, newNum):
        self.setNumberDisplay(self.morseWin.numWordsInfoLabel, int(newNum));
        
    def setSpeedLabel(self, newNum):
        newNum = '%.2f' % newNum;
        self.setNumberDisplay(self.morseWin.wpmSpeedInfoLabel, newNum);
        
    def setNumberDisplay(self, labelObj, newNum):
        labelObj.setText(str(newNum));
            
