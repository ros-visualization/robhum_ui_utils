#!/usr/bin/env python

import sys
import time

from python_qt_binding import QtCore, QtGui;
from QtCore import QTimer;
from QtGui import QApplication;

class WatchdogTimer(QTimer):
    
    def __init__(self, timeout=1, callback=None, callbackArg=None, selfTest=False):
        super(WatchdogTimer,self).__init__();
        # Use leading underscore to avoid
        # overwriting parent's 'timeout' signal:
        self._timeout = int(1000 * timeout);
        self.callback = callback;
        self.callbackArg = callbackArg;

        self.timedout = True;
        self.stopped  = True;
        
        self.setSingleShot(True);
        self.timeout.connect(self.timerExpiredHandler);
                
        if selfTest:
            self.runSelfTest();
            #sys.exit();

    def timedOut(self):
        return self.timedout;

    def kick(self, _timeout=None, callback=None, callbackArg=None):
        self.timedout = False;
        if _timeout is None:
            _timeout = self._timeout;
        else:
            _timeout = int(1000 * _timeout);
        if callback is not None:
            self.callback = callback;
        if callbackArg is not None:
            self.callbackArg = callbackArg;
        self.stopped  = False;
        self.start(_timeout);
        
    def stop(self):
        super(WatchdogTimer, self).stop();
        self.timedout = False;
        self.stopped  = True;
    
    def changeTimeout(self, newTimeout):
        self._timeout = int(1000 * newTimeout);
        
    def changeCallback(self, newCallback):
        self.callback = newCallback;
        
    def changeCallbackArg(self, newArg):
        self.callbackArg = newArg;
    
    def timerExpiredHandler(self):
        self.stop();
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
        self.kick();
        print("Stop test: stopped == %s" % self.stopped);
        self.kick();
        print("After kick: stopped == %s" % self.stopped);
        self.stop();
        if self.stopped:
            print("Timer successfully stopped.");
        else:
            print("Bad: timer not stopped.");
    
if __name__ == '__main__':
    
    app = QtGui.QApplication(sys.argv)
    dog = WatchdogTimer(selfTest=True)
    sys.exit(app.exec_())    
