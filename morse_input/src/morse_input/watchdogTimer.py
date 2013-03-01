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


import sys
import time

from python_qt_binding import QtCore, QtGui;
from QtCore import QTimer;
from QtGui import QApplication;

class WatchdogTimer(QTimer):
    
    def __init__(self, timeout=1, callback=None, callbackArg=None, selfTest=False):
        '''
        Create watchdog.
        @param timeout: number of seconds that are set each time the timer is kicked.
        @type timeout: float
        @param callback: callable to invoke when timer expires.
        @type callback: Python callable
        @param callbackArg: any argument to pass to the callback
        @type callbackArg: any
        @param selfTest: set to true if testing the class
        @type selfTest: boolean
        '''
        super(WatchdogTimer,self).__init__();
        # Use leading underscore to avoid
        # overwriting parent's 'timeout' signal.
        # Internally, work with milliseconds:
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
        '''
        (Re)-start the timer
        @param _timeout: timeout in seconds
        @type _timeout: float
        @param callback: Python callable to invoke when timer expires.
        @type callback: callable
        @param callbackArg: argument to pass to callback
        @type callbackArg: any
        '''
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
