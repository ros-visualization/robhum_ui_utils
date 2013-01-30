#!/usr/bin/env python

import subprocess;
import time;
import os;
import signal;
import threading;

class Morse:
    DOT  = 0;
    DASH = 1;

class MorseGenerator(object):
    
    def __init__(self):
        super(MorseGenerator, self).__init__();
        
        # ------ Public Instance Vars  ------------
        self.frequency      	 = 300; # Hz
        self.dotDuration    	 = 0.15; # seconds = 15ms
        self.dashDuration   	 = 0.30; # seconds = 300ms
        self.speed          	 = 33.0;   # Hz
        # Duration of one dot plus time of one cycle as specified by speed:
        self.interSigPauseDots   = self.dotDuration + 1.0/self.speed       # 180ms
        # Duration of one half dash plus time of one cycle as specified by speed:        
        self.interSigPauseDashes = self.dashDuration/2.0 + 1.0/self.speed  # 180ms
        self.automaticMorse      = False;
        
        # ------ Private Instance Vars  ------------
        
        self.morseDashEvent  = threading.Event();
        self.morseDotEvent   = threading.Event();
        self.morseStopEvent  = threading.Event();

        # Set to False to stop thread:        
        self.keepRunning = True;
        
        self.dotGenerator  = MorseGenerator.DotGenerator(self).start();
        self.DashGenerator = MorseGenerator.DashGenerator(self).start();

    # ------------------------------ Public Methods ---------------------

    def startMorseSeq(self, morseElement):
        '''
        Start a sequence of dots or dashes. If auto-morse is False,
        only one dot or dash is produced per call. Else a dashes or
        dots are produced at an adjustable speed until stopMorseSeq()
        is called. Use setAutoMorse() to control whether single-shot
        or automatic sequences are produced. Use setSpeed() to set
        the speed at which the signals are generated.
        
        After stopMorseSeq() is called, use getRecentDots() or 
        getRecentDashes() return the number of dots or dashes that
        were generated.
        
        @param morseElement: whether to produce dots or dashes
        @type morseElement: Morse enum
        '''
        
        if not self.keepRunning:
            raise RuntimeError("Called Morse generator method after stopMorseGenerator() was called.");

        # Set a thread event for which dot or dash generator are waiting:
        if morseElement == Morse.DASH:
            self.morseDashEvent.set();
        elif morseElement == Morse.DOT:
            self.morseDotEvent.set();

    def stopMorseSeq(self):
        '''
        Stop a running sequence of dots or dashes. After this call,
        use getRecentDots() or getRecentDashes() to get a count of
        signals that were emitted. If automatic Morse generation is
        disabled, it is not necessary to call this method. See
        setAutoMorse().
        '''
        if not self.keepRunning:
            raise RuntimeError("Called Morse generator method after stopMorseGenerator() was called.");
        # Clear dot and dash generation events so that the
        # generator tasks will go into a wait state.
        self.morseDotEvent.clear();
        self.morseDashEvent.clear();

    def stopMorseGenerator(self):
        '''
        Stop the entire generator. All threads are killed.
        Subsequent calls to startMorseSeq() or stopMorseSeq() 
        generate exceptions.
        '''
        self.keepRunning = False;
        # Ensure that the dot and dash generators
        # get out of the wait state to notice that
        # they are supposed to terminate:
        self.morseDashEvent.set();
        self.morseDotEvent.set();
        
    def setAutoMorse(self, yesNo):
        '''
        Determine whether dots and dashes are generated one at
        a time each time startMorseSeq() is called, or whether 
        each call generates sequences of signals until stopMorseGenerator()
        is called.
        @param yesNo:
        @type yesNo:
        '''
        self.automaticMorse = yesNo;
        
    def setSpeed(self, speed):
        '''
        Set speed at which automatic dots and dashes are
        generated. Units are Herz. Default is ~33Hz. The
        higher the number, the faster the dots/dashes are
        generated. This is equivalent to controlling the
        time between successive dots or dashes.
        @param speed: rate at which dots or dashes are produced in automatic mode.
        @type speed: float
        '''
        self.speed = speed;
        #***********
        self.dotDuration    	 = 0.10; # seconds = 15ms
        self.dashDuration   	 = 0.20; # seconds = 300ms
        #***********
        self.interSigPauseDots   = self.dotDuration + 1.0/self.speed;
        self.interSigPauseDashes = self.dashDuration/2.0 + 1.0/self.speed;                
                
    # ------------------------------ Private ---------------------

    #-----------------------------
    # DotGenerator Class
    #-------------------
    
    class DotGenerator(threading.Thread):
        
        def __init__(self, parent):
            super(MorseGenerator.DotGenerator,self).__init__();
            self.parent = parent;
        
        def run(self):
            self.genDots();
    
        def genDots(self):
            
            # Initially: wait for first dot request.
            self.parent.morseDotEvent.wait();
            # No dots generated yet:
            numDots = 0;
            
            while self.parent.morseDotEvent.is_set():
                
                # Stop thread altogether?
                if not self.parent.keepRunning:
                    return;
                
                # Use Alsa utils speaker tester to produce sound:
                proc = subprocess.Popen(['speaker-test', 
                                         "--test", "sine", 
                                         "--frequency", str(self.parent.frequency)],
                                        stdout=subprocess.PIPE); # suppress speaker-test display output
                time.sleep(self.parent.dotDuration);
                os.kill(proc.pid, signal.SIGUSR1)
                
                numDots += 1;
                if not self.parent.automaticMorse:
                    # Not doing automatic dot generation.
                    # So clear the dot event that controls out
                    # loop. That would otherwise happen 
                    # in self.parent.stopMorseSequence(), which
                    # clients call:
                    self.parent.morseDotEvent.clear();
                    self.parent.recentDots = numDots;
                else:
                    # Auto dot generation: pause for
                    # the inter-dot period:
                    time.sleep(self.parent.interSigPauseDots);
                
                # Get ready for the next request for dot sequences:
                numDots = 0;
                self.parent.morseDotEvent.wait();
        
    #-----------------------------
    # DashGenerator Class
    #-------------------
            
    class DashGenerator(threading.Thread):
        
        def __init__(self, parent):
            super(MorseGenerator.DashGenerator,self).__init__();
            self.parent = parent;
        
        def run(self):
            self.genDashes();
    
        def genDashes(self):
            
            # Initially: wait for first dash request.
            self.parent.morseDashEvent.wait();
            # No dashes generated yet:
            numDashes = 0;
            
            while self.parent.morseDashEvent.is_set():
                
                # Stop thread altogether?
                if not self.parent.keepRunning:
                    return;
                
                # Speaker-test subprocess will run until we kill it:
                proc = subprocess.Popen(['speaker-test', 
                                         "--test", "sine", 
                                         "--frequency", str(self.parent.frequency)],
                                        stdout=subprocess.PIPE); # Suppress print output
                time.sleep(self.parent.dashDuration);
                os.kill(proc.pid, signal.SIGUSR1)
                
                numDashes += 1;
                if not self.parent.automaticMorse:
                    # Not doing automatic dash generation.
                    # So clear the dash event that controls out
                    # loop. That would otherwise happen 
                    # in self.parent.stopMorseSequence(), which
                    # clients call:
                    self.parent.morseDashEvent.clear();
                    self.parent.recentDashes = numDashes;
                else:
                    # Auto dot generation: pause for
                    # the inter-dash period:
                    time.sleep(self.parent.interSigPauseDashes);
                    
                # Get ready for the next request for dashes sequences:
                numDashes = 0;
                self.parent.morseDashEvent.wait();
                    
if __name__ == "__main__":
    
    generator = MorseGenerator();

    # Initially: not automatic:
    generator.startMorseSeq(Morse.DOT);
    time.sleep(1);
    generator.startMorseSeq(Morse.DASH);
    time.sleep(1);
    
    generator.setAutoMorse(True);

    generator.startMorseSeq(Morse.DOT);
    time.sleep(1);
    generator.stopMorseSeq();
    time.sleep(0.5);

    generator.startMorseSeq(Morse.DASH);
    time.sleep(1);
    generator.stopMorseSeq();
    time.sleep(1.5);    

    generator.setSpeed(3000.0); #Hz
    generator.startMorseSeq(Morse.DOT);
    time.sleep(1);
    generator.stopMorseSeq();
    time.sleep(0.5);    

    generator.startMorseSeq(Morse.DASH);
    time.sleep(1);
    generator.stopMorseSeq();
    time.sleep(0.5);    
    
    generator.stopMorseGenerator();
    
    