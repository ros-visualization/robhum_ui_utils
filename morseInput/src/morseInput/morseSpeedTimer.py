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
            
