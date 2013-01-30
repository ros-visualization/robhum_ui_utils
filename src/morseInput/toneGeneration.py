#!/usr/bin/env python

import subprocess;
import time;
import os;
import signal;
import threading;

class Morse:
    DOT  = 0;
    DASH = 1;

class ToneGenerator(threading.Thread):
    
    def __init__(self):
        super(ToneGenerator, self).__init__();
        
        # ------ Public Instance Vars  ------------
        self.frequency      = 300; # Hz
        self.dotDuration    = 0.15; # seconds
        self.dashDuration   = 0.30; # seconds
        self.interSigPause  = 0.03; # seconds
        self.automaticMorse = False;
        
        # ------ Private Instance Vars  ------------
        self.autoMorseRunning   = False;
        
        self.morseDashEvent = threading.Event();
        self.morseDotEvent = threading.Event();
        self.morseStopEvent  = threading.Event();

        # Set to False to stop thread:        
        self.keepRunning = True;


    # ------------------------------ Public Methods ---------------------

    def startMorseSeq(self, morseElement):
        if morseElement == Morse.DASH:
            self.morseDashEvent.set();
        elif morseElement == Morse.DOT:
            self.morseDotEvent.set();

    def stopMorseSeq(self):
        self.morseDotEvent.clear();
        self.morseDashEvent.clear();

    def stopGenerator(self):
        self.keepRunning = False;
        
    # ------------------------------ Private Methods ---------------------
    def run(self):
        while self.keepRunning:
            time.sleep(1);

    def genDot(self):
        
        self.morseDotEvent.wait();
        numDots = 0;
        
        while self.morseDotEvent.is_set():
            
            # Stop thread altogether?
            if not self.keepRunning:
                return;
            
            proc = subprocess.Popen(['speaker-test', "--test", "sine", "--frequency", str(self.frequency)],stdout=subprocess.PIPE);
            time.sleep(self.dotDuration);
            os.kill(proc.pid, signal.SIGUSR1)
            
            numDots += 1;
            if not self.automaticMorse:
                self.morseDotEvent.clear();
                self.recentDots = numDots;
            else:
                time.sleep(self.interSigPause);
                
            numDots = 0;
            self.morseDotEvent.wait();
        
    def genDash(self):
        self.morseDashEvent.wait();
        numDots = 0;
        
        while self.morseDotEvent.is_set():
            
            # Stop thread altogether?
            if not self.keepRunning:
                return;
            
            proc = subprocess.Popen(['speaker-test', "--test", "sine", "--frequency", str(self.frequency)],stdout=subprocess.PIPE);
            time.sleep(self.dashDuration);
            os.kill(proc.pid, signal.SIGUSR1)
            
            numDots += 1;
            if not self.automaticMorse:
                self.morseDashEvent.clear();
                self.recentDashes = numDots;
            else:
                time.sleep(self.interSigPause);
                
            numDashes = 0;
            self.morseDashEvent.wait();
                    
if __name__ == "__main__":
    
    toneGenerator = ToneGenerator();
    toneGenerator.start();
    toneGenerator.startMorseSeq(Morse.DOT, True);
    time.sleep(2);
    toneGenerator.stopMorseSeq();
    toneGenerator.stopGenerator();
    
    