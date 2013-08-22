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


import subprocess;
import time;
import os;
import signal;
import threading;
from datetime import datetime;
from watchdogTimer import WatchdogTimer;
from morseCodeTranslationKey import codeKey;

class Morse:
    DOT  = 0;
    DASH = 1;

class TimeoutReason:
    END_OF_LETTER = 0
    END_OF_WORD   = 1
    BAD_MORSE_INPUT = 2

class MorseGenerator(object):
    '''
    Manages non-UI issues for Morse code generation: Interacts with the 
    tone generator, regulates auto dot/dash generation speed.
    '''
    
    def __init__(self, callback=None):
        super(MorseGenerator, self).__init__();
        
        # ------ Instance Vars Available Through Getters/Setters ------------

        # Frequency of the tone:        
        self.frequency = 300; # Hz
        
        self.callback = callback;
        
        self.interLetterDelayExplicitlySet = False;
        self.interWordDelayExplicitlySet = False;
        # setSpeed() must be called before setting up
        # watchdog timer below:
        self.setSpeed(3.3);
        self.automaticMorse = True;
        
        self.recentDots = 0;
        self.recentDashes = 0;
        # morseResult will accumulate the dots and dashes:
        self.morseResult = '';
        self.alphaStr = '';
        self.watchdog = WatchdogTimer(timeout=self.interLetterTime, callback=self.watchdogExpired);
        
        # ------ Private Instance Vars  ------------
        
        self.morseDashEvent  = threading.Event();
        self.morseDotEvent   = threading.Event();
        self.morseStopEvent  = threading.Event();

        # Lock for regulating write-access to alpha string:
        self.alphaStrLock = threading.Lock();
        # Lock for regulating write-access to morse elements
        # delivered from the dot and dash threads:
        self.morseResultLock = threading.Lock();

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
        # We are starting a sequence of dots and dashes.
        # The Morse element can't possibly be ended until
        # stopMorseSeq() is called by mouse cursor leaving
        # a gesture button:
        self.watchdog.stop();
        # Set a thread event for which dot or dash generator are waiting:
        if morseElement == Morse.DASH:
            self.morseDashEvent.set();
        elif morseElement == Morse.DOT:
            self.morseDotEvent.set();

    def stopMorseSeq(self):
        '''
        Stop a running sequence of dots or dashes. After this call,
        use getRecentDots() or getRecentDashes() to get a count of
        Morse elements (dots or dashes) that were emitted. If automatic 
        Morse generation is disabled, it is not necessary to call this 
        method. See setAutoMorse(). Called when mouse cursor leaves
        
        '''
        if not self.keepRunning:
            raise RuntimeError("Called Morse generator method after stopMorseGenerator() was called.");
        # Clear dot and dash generation events so that the
        # generator threads will go into a wait state.
        self.morseDotEvent.clear();
        self.morseDashEvent.clear();
        # If there will now be a pause long enough
        # to indicate the end of a letter, this
        # watchdog will go off:
        if self.interLetterTime > 0:
            self.watchdog.kick(_timeout=self.interLetterTime, callbackArg=TimeoutReason.END_OF_LETTER);
        
    def abortCurrentMorseElement(self):
        self.watchdog.stop();
        self.setMorseResult('');

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
        
        @param dotsPlusPausePerSec: rate at which dots or dashes are produced in automatic mode.
        @type dotsPlusPausePerSec: float
        '''
        self.dotDuration = 1.0/(2*dotsPlusPausePerSec);
        #self.dashDuration = 3*self.dotDuration;
        self.dashDuration = 2*self.dotDuration;
        # Times between the automatically generated
        # dots and dashes:
        self.interSigPauseDots = self.dotDuration;
        self.interSigPauseDashes = self.dotDuration;
        
        # Unless client explicitly set dwell time between
        # letters and words, compute a default now:
        if not self.interLetterDelayExplicitlySet:
            # Turn automatic word segmentation off by default:
            self.interLetterTime = -1;
            # self.interLetterTime = 7.0*self.dotDuration;
        if not self.interWordDelayExplicitlySet:
            # Turn automatic word segmentation off by default:
            self.interWordTime = -1;
            #self.interWordTime   = 9.0*self.dotDuration;
        self.waitDashDotThreadsIdleTime = 0.5 * 7.0*self.dotDuration;
    
    def setInterLetterDelay(self, secs):
        '''
        Sets the time that must elapse between two letters.
        @param secs: fractional seconds
        @type secs: float
        '''
        self.interLetterTime = secs;
        # The following are commented, b/c mouse-click-controlled
        # inter-letter delay was introduced. That feature sets
        # interLetterTime to -1, which would cause bugs
        # below. The lines make sense if interLetterTime is known
        # to be positive:
        #self.watchdog.changeTimeout(self.interLetterTime);
        #self.waitDashDotThreadsIdleTime = 0.5 * self.interLetterTime;
        self.interLetterDelayExplicitlySet = True;
        
    def setInterWordDelay(self, secs):
        '''
        Sets the time that must elapse between two words.
        If negative, no word segmentation is performed.
        @param secs: fractional seconds
        @type secs: float
        '''
        self.interWordTime = secs;
        # Indicate that client explicitly set the
        # inter-word dwell time. This note will prevent
        # setSpeed() from defining its default dwell:
        self.interWordDelayExplicitlySet = True;
        
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

    def getAndRemoveAlphaStr(self):
        res = self.alphaStr;
        self.setAlphaStr('');
        return res;

    def setAlphaStr(self, newAlphaStr):
        with self.alphaStrLock:
            self.alphaStr = newAlphaStr

    def setMorseResult(self, newMorseResult):
        with self.morseResultLock:
            self.morseResult = newMorseResult;
    
    def inMidLetter(self):
        '''
        Return True if user has morsed any dots or dashes
        since the last letter or word segmentation
        '''
        return len(self.morseResult) > 0;
        
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
    
    def reallySleep(self, secs):
        '''
        Truly return only after specified time. Just using
        time.sleep() sleeps shorter if any interrupts occur during
        the sleep period.
        @param secs: fractional seconds to sleep
        @type secs: float
        '''
        sleepStop  = time.time() + secs; 
        while True:
            timeLeft = sleepStop - time.time();
            if timeLeft <= 0:
                return
            time.sleep(timeLeft)
            

    # ------------------------------ Private ---------------------

    def addMorseElements(self, dotsOrDashes, numElements):
        if dotsOrDashes == Morse.DASH:
            self.setMorseResult(self.morseResult + '-'*numElements); 
        else: # dots:
            # Catch abort-letter:
            if numElements > 7:
                self.abortCurrentMorseElement();
                return;
            self.setMorseResult(self.morseResult + '.'*numElements);

    def watchdogExpired(self, reason):

        detail = '';
        if reason == TimeoutReason.END_OF_LETTER:
            # If no Morse elements are in self.morseResult,
            # it could be because the dash or dot thread are
            # not done delivering their result. In that case,
            # set the timer again to get them idle:
            if len(self.morseResult) == 0:
                self.watchdog.kick(self.waitDashDotThreadsIdleTime);
                return;
            newLetter = self.decodeMorseLetter();
            # If Morse sequence was legal and recognized,
            # append it:
            if newLetter is not None:
                self.setAlphaStr(self.alphaStr + newLetter);
            else:
                reason = TimeoutReason.BAD_MORSE_INPUT;
                detail = self.morseResult;
            # One way or other, a letter has ended. Start the
            # timeout for a word-separation sized pause:
            if self.interWordTime > 0:
                self.watchdog.kick(_timeout=self.interWordTime, callbackArg=TimeoutReason.END_OF_WORD);
        elif reason == TimeoutReason.END_OF_WORD:
            # Decided to have the client decide what to do when a word ends.
            # The commented code would add a space:
            #self.setAlphaStr(self.alphaStr + ' ');
            pass;
        self.setMorseResult('');
        if self.callback is not None:
            self.callback(reason, detail);

    def decodeMorseLetter(self):
        try:
            letter = codeKey[self.morseResult];
            if letter == 'BS':
                letter = '\b';
            elif letter == 'NL':
                letter = '\r';
            elif letter == 'HS':
                letter = ' ';
        except KeyError:
            #print("Bad morse seq: '%s'" % self.morseResult);
            return None
        return letter;
            
    #-----------------------------
    # DotGenerator Class
    #-------------------
    
    class DotGenerator(threading.Thread):
        
        def __init__(self, parent):
            super(MorseGenerator.DotGenerator,self).__init__();
            self.parent = parent;
            self.idle = True;
        
        def isIdle(self):
            return self.idle;
        
        def run(self):
            self.genDots();
    
        def genDots(self):
            
            # Initially: wait for first dot request.
            self.parent.morseDotEvent.wait();
            # No dots generated yet:
            numDots = 0;
                        
            while self.parent.keepRunning:
            
                while self.parent.morseDotEvent.is_set():
                    
                    self.idle = False;    
                
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
                        self.parent.reallySleep(self.parent.interSigPauseDots);
                    
                self.parent.addMorseElements(Morse.DOT, numDots);
                # Get ready for the next request for dot sequences:
                numDots = 0;
                self.idle = True;
                self.parent.morseDotEvent.wait();
        
    #-----------------------------
    # DashGenerator Class
    #-------------------
            
    class DashGenerator(threading.Thread):
        
        def __init__(self, parent):
            super(MorseGenerator.DashGenerator,self).__init__();
            self.parent = parent;
            self.idle = True;

        def isIdle(self):
            return self.idle;
        
        def run(self):
            self.genDashes();
    
        def genDashes(self):
            
            # Initially: wait for first dash request.
            self.parent.morseDashEvent.wait();
            # No dashes generated yet:
            numDashes = 0;
            
            while self.parent.keepRunning:
                while self.parent.morseDashEvent.is_set():
                    
                    self.idle = False;
                    
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
                        self.parent.reallySleep(self.parent.interSigPauseDashes);
                    
                self.parent.addMorseElements(Morse.DASH, numDashes);
                # Get ready for the next request for dashes sequences:
                numDashes = 0;
                self.idle = True;
                self.parent.morseDashEvent.wait();
                    
if __name__ == "__main__":
    
    generator = MorseGenerator();

    # Initially: not automatic:
    generator.setAutoMorse(False);

#    generator.startMorseSeq(Morse.DOT);
#    time.sleep(1);
#    generator.startMorseSeq(Morse.DASH);
#    time.sleep(1);
#    print("Dots: %d. Dashes: %d" % (generator.numRecentDots(), generator.numRecentDashes()));
#    
#    generator.setAutoMorse(True);
#
#    generator.startMorseSeq(Morse.DOT);
#    time.sleep(1);
#    generator.stopMorseSeq();
#    time.sleep(0.5);
#
#    generator.startMorseSeq(Morse.DASH);
#    time.sleep(1);
#    generator.stopMorseSeq();
#    time.sleep(1.5);    
#    print("Dots: %d. Dashes: %d" % (generator.numRecentDots(), generator.numRecentDashes()));
#
#    generator.setSpeed(6.0); #Hz
#    generator.startMorseSeq(Morse.DOT);
#    time.sleep(1);
#    generator.stopMorseSeq();
#    time.sleep(0.5);    
#
#    generator.startMorseSeq(Morse.DASH);
#    time.sleep(1);
#    generator.stopMorseSeq();
#    time.sleep(0.5);    
#    print("Dots: %d. Dashes: %d" % (generator.numRecentDots(), generator.numRecentDashes()));
#    
#    generator.setSpeed(12.0); #Hz
#    generator.startMorseSeq(Morse.DOT);
#    time.sleep(1);
#    generator.stopMorseSeq();
#    time.sleep(0.5);    
#
#    generator.startMorseSeq(Morse.DASH);
#    time.sleep(1);
#    generator.stopMorseSeq();
#    time.sleep(0.5);    
#    print("Dots: %d. Dashes: %d" % (generator.numRecentDots(), generator.numRecentDashes()));

#    generator.addMorseElements(Morse.DASH, 1)
#    time.sleep(generator.interLetterTime + 0.1);
#    letterLookup = generator.decodeMorseLetter();
#    #for key in sorted(codeKey.keys()):
#    #    print(str(key) + ':' + codeKey[key])
#    if letterLookup != 't': 
#        raise ValueError("Morse 't' not recognized")
                
    