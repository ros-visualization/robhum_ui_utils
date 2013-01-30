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
        
        # ------ Instance Vars Available Through Getters/Setters ------------

        # Frequency of the tone:        
        self.frequency = 300; # Hz
        
        self.setSpeed(3.3);
        self.automaticMorse = True;
        self.recentDots = 0;
        self.recentDashes = 0;
        
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
        
    def numRecentDots(self):
        return self.recentDots;
    
    def numRecentDashes(self):
        return self.recentDashes;

    def setSpeed(self, dotsPlusPausePerSec):
        '''
        Sets speed at which automatic dots and dashes are
        generated. Units are Herz. One cycle is a single
        dot, followed by the pause that separates two dots.
        Since that pause is standardized to be equal to 
        a dot length, one can think of the speed as the
        number times the letter "i" is generated per second.
        
        The higher the number, the faster the dots/dashes are
        generated. Default is 3.3.
        
        @param speed: rate at which dots or dashes are produced in automatic mode.
        @type speed: float
        '''
        self.dotDuration = 1.0/(2*dotsPlusPausePerSec);
        self.dashDuration = 3*self.dotDuration;
        self.interSigPauseDots = self.dotDuration;
        self.interSigPauseDashes = 1.5 * self.dotDuration;
        
        self.interLetterTime = 3.0*self.dotDuration;
        self.interWordTime   = 7.0*self.dotDuration;
        
    def getInterLetterTime(self):
        '''
        Return the minimum amount of silence time required
        for the system to conclude that the Morse code equivalent
        of a letter has been generated. I.e.: end-of-letter pause.
        '''
        return self.interLetterTime;
    
    def getInterWordTime(self):
        '''
        Return the minimum amount of silence time required
        for the system to conclude that a word has ended.
        I.e.: end-of-word pause.
        '''
        return self.interWordTime;

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
                        
            while self.parent.keepRunning:
            
                while self.parent.morseDotEvent.is_set():    
                
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
                    else:
                        # Auto dot generation: pause for
                        # the inter-dot period:
                        time.sleep(self.parent.interSigPauseDots);
                        
                self.parent.recentDots = numDots;
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
            
            while self.parent.keepRunning:
                while self.parent.morseDashEvent.is_set():
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
                    else:
                        # Auto dot generation: pause for
                        # the inter-dash period:
                        time.sleep(self.parent.interSigPauseDashes);
                    
                self.parent.recentDashes = numDashes;
                # Get ready for the next request for dashes sequences:
                numDashes = 0;
                self.parent.morseDashEvent.wait();
                    
if __name__ == "__main__":
    
    generator = MorseGenerator();

    # Initially: not automatic:
    generator.setAutoMorse(False);

    generator.startMorseSeq(Morse.DOT);
    time.sleep(1);
    generator.startMorseSeq(Morse.DASH);
    time.sleep(1);
    print("Dots: %d. Dashes: %d" % (generator.numRecentDots(), generator.numRecentDashes()));
    
    generator.setAutoMorse(True);

    generator.startMorseSeq(Morse.DOT);
    time.sleep(1);
    generator.stopMorseSeq();
    time.sleep(0.5);

    generator.startMorseSeq(Morse.DASH);
    time.sleep(1);
    generator.stopMorseSeq();
    time.sleep(1.5);    
    print("Dots: %d. Dashes: %d" % (generator.numRecentDots(), generator.numRecentDashes()));

    generator.setSpeed(6.0); #Hz
    generator.startMorseSeq(Morse.DOT);
    time.sleep(1);
    generator.stopMorseSeq();
    time.sleep(0.5);    

    generator.startMorseSeq(Morse.DASH);
    time.sleep(1);
    generator.stopMorseSeq();
    time.sleep(0.5);    
    print("Dots: %d. Dashes: %d" % (generator.numRecentDots(), generator.numRecentDashes()));
    
    generator.setSpeed(12.0); #Hz
    generator.startMorseSeq(Morse.DOT);
    time.sleep(1);
    generator.stopMorseSeq();
    time.sleep(0.5);    

    generator.startMorseSeq(Morse.DASH);
    time.sleep(1);
    generator.stopMorseSeq();
    time.sleep(0.5);    
    print("Dots: %d. Dashes: %d" % (generator.numRecentDots(), generator.numRecentDashes()));
    
    generator.stopMorseGenerator();
    
    