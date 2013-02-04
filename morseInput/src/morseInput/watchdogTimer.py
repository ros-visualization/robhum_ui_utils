#!/usr/bin/env python

import sys
import time

from python_qt_binding import QtCore, QtGui;
from QtCore import QTimer;
from QtGui import QApplication;

class WatchdogTimer(object):
    
    def __init__(self, timeout=1000, callback=None, callbackArg=None, selfTest=False):
        self.timeout = timeout
        self.callback = callback
        self.callbackArg = callbackArg

        self.timedout = True;
        self.stopped  = True;
        
        self.timer = QTimer();
        self.timer.setSingleShot(True);
        self.timer.timeout.connect(self.timerExpiredHandler);
                
        if selfTest:
            self.runSelfTest();
            #sys.exit();
            

    def timedOut(self):
        return self.timedout;

    def kick(self, timeout=None):
        self.timedout = False;
        self.stopped  = False;
        if timeout is None:
            timeout = self.timeout;
        self.timer.start(timeout);
        
    def stop(self):
        self.timer.stop();
        self.timedout = False;
        self.stopped  = True;
    
    def changeTimeout(self, newTimeout):
        self.timeout = newTimeout;
        
    def changeCallback(self, newCallback):
        self.callback = newCallback;
        
    def changeCallbackArg(self, newArg):
        self.callbackArg = newArg;
    
    def timerExpiredHandler(self):
        if self.stopped:
            return;
        self.timedout = True;
        if self.callback is not None:
            if self.callbackArg is None:
                self.callback();
            else:
                self.callback(self.callbackArg);
            
# -----------------------------  Testing  ----------------------------

    def runSelfTest(self):
        self.changeCallback(self.testTimeoutHandler);
        self.kick();
                            
    def testTimeoutHandler(self):
        print("Timed out.");
            
    
if __name__ == '__main__':
    
    app = QtGui.QApplication(sys.argv)
    dog = WatchdogTimer(selfTest=True)
    sys.exit(app.exec_())    
