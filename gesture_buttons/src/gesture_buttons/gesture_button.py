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
    import roslib; roslib.load_manifest('gesture_buttons');
    ROS_AVAILABLE = True;
except ImportError:
    ROS_AVAILABLE = False;

import sys;
import time;
import math;

from python_qt_binding import QtCore, QtGui
from QtCore import QCoreApplication, QEvent, QEventTransition, QObject, QPoint, QSignalTransition, QState, QStateMachine, QTimer, Signal, SIGNAL, Slot, Qt
from QtGui import QApplication, QCursor, QPushButton, QWidget, QHoverEvent, QMouseEvent

try:
    from qt_comm_channel.commChannel import CommChannel;
except ImportError as e:
    print(`e`);
    print("Roslib is unavailable. So your PYTHONPATH will need to include:\n" +
          "qt_comm_channel/src");
    sys.exit();    



class GestureSignals(CommChannel):

    # Signals emitted when GestureButton user flicks up and down, left-right, etc:
    flickSig = Signal(QPushButton, int);
    
    # Signal emitted when the button is first entered. Subsequent
    # flicks will not re-send this signal.
    buttonEnteredSig = Signal(QPushButton);  
    
    # Signal emitted when the button is left for good, that is
    # when return for a flick is possible.
    buttonExitedSig = Signal(QPushButton);
    
    #*********************
#    def __init__(self):
#        super(GestureSignals, self).__init__()
#        self.flickSig;
#        self.buttonEnteredSig;
#        self.buttonExitedSig;
    #*********************        

class FlickDirection:
    NORTH = 0;
    SOUTH = 1;
    EAST  = 2;
    WEST  = 3;

    legalValues = [NORTH, SOUTH, EAST, WEST];
    
    @staticmethod
    def toString(flickDirection):
        if flickDirection == FlickDirection.EAST:
            return "<EAST>";
        elif flickDirection == FlickDirection.NORTH:
            return "<NORTH>";
        elif flickDirection == FlickDirection.SOUTH:
            return "<SOUTH>";
        elif flickDirection == FlickDirection.WEST:
            return "<WEST>";
        else:
            raise ValueError("Value other than a FlickDirection passed to FlickDirection.toString()");

        
# Unused
class FlickDeterminationDone(QEvent):
    
    # Get a new event type that is shared among
    # all the instances of this class:
    userEventTypeID = QEvent.registerEventType();
    
    def __init__(self):
        '''
        Create a new instance of FlickDeterminationDone. The
        event type will always be the constant FlickDeterminationDone.eventType 
        '''
        super(FlickDeterminationDone, self).__init__(QEvent.Type(FlickDeterminationDone.userEventTypeID));

class GestureButton(QPushButton):
    
    FLICK_TIME_THRESHOLD_MASTER = 0.5; # seconds
    
    def __init__(self, label, parent=None):
        super(GestureButton, self).__init__(label, parent=parent);

        #tmpStyle = "QPushButton {background-color: red}";
        #self.setStyleSheet(tmpStyle);

        self.setFlicksEnabled(True);

        # Timer for deciding when mouse has left this
        # button long enough that even returning to this
        # button will not be counted as a flick, but as
        # a new entrance. 
        # NOTE: QTimer emits the signal "timeout()" when it
        # expires. In contrast, QBasicTimer emits a timer *event*
        # For use with state transitions, use QEventTransition
        # for QBasicTimer, but QSignalTransition for QTimer. 
        
        self.maxFlickDurationTimer = QTimer();
        self.maxFlickDurationTimer.setSingleShot(True);

        # Bit of a hack to get around a Pyside bug/missing-feature:
        # Timer used with zero delay to trigger a QSignalTransition
        # with a standard signal (no custom signals seem to work):        
        self.flickDetectDoneTrigger = QTimer();
        self.flickDetectDoneTrigger.setSingleShot(True);
        
        self.setMouseTracking(True);
        self.latestMousePos = QPoint(0,0);
        
        self.connectWidgets();
        self.initSignals();
                
        # ------------------  State Definitions ------------------
        
        # Parent state for north/south/east/west states:
        self.stateGestureActivatePending = QState();
        #self.stateGestureActivatePending.assignProperty(self, "text", "Toggle pending");
        
        # States for: mouse left button; will mouse flick back?
        self.stateNorthExit = QState(self.stateGestureActivatePending);
        self.stateSouthExit = QState(self.stateGestureActivatePending);
        self.stateEastExit  = QState(self.stateGestureActivatePending);
        self.stateWestExit  = QState(self.stateGestureActivatePending);
        
        self.stateGestureActivatePending.setInitialState(self.stateNorthExit);
        
        # State: mouse entered button area not as part of a flick:          
        self.stateEntered   = QState();
        #self.stateEntered.assignProperty(self, "text", "Entered");
        
        # State: mouse re-entered button after leaving briefly:
        self.stateReEntered = QState();
        #self.stateReEntered.assignProperty(self, "text", "Re-Entered");
        
        # State: mouse outside for longer than GestureButton.FLICK_TIME_THRESHOLD seconds: 
        self.stateIdle      = QState();
        #self.stateIdle.assignProperty(self, "text", "Idle");

        # ------------------  Transition Definitions ------------------

        # From Idle to Entered: triggered automatically by mouse entering button area:
        self.toEnteredTrans = HotEntryTransition(self, QEvent.Enter, sourceState=self.stateIdle);
        self.toEnteredTrans.setTargetState(self.stateEntered);
        
        # From Entered to GestureActivatePending: mouse cursor left button area,
        # and the user may or may not return the cursor to the button area
        # in time to trigger a flick. Transition triggered automatically by 
        # mouse leaving button area. A timer is set. If it runs to 0, 
        # a transition to Idle will be triggered. But if mouse re-enters button
        # area before the timer expires, the ReEntered state will become active: 
        self.toGAPendingTrans = TimeSettingStateTransition(self, QEvent.Leave, sourceState=self.stateEntered);
        self.toGAPendingTrans.setTargetState(self.stateGestureActivatePending);
        
        # From GestureActivatePending to ReEntered. Triggered if mouse cursor
        # re-enters button area after having left before the maxFlickDurationTimer 
        # has run down. Triggered automatically by mouse entering the button area:
        self.toReEnteredTrans = TimeReadingStateTransition(self, 
                                                           QEvent.Enter, 
                                                           self.toGAPendingTrans,
                                                           sourceState=self.stateGestureActivatePending);
        self.toReEnteredTrans.setTargetState(self.stateReEntered);

        # From GestureActivePending to Idle. Triggered by maxFlickDurationTimer running to 0
        # before mouse cursor re-entered button area after leaving. Triggered by timer that
        # is set when state GestureActivatePending is entered.
        self.toIdleTrans = HotExitTransition(self,
					     self.maxFlickDurationTimer,
					     sourceState=self.stateGestureActivatePending);
        self.toIdleTrans.setTargetState(self.stateIdle);
        
        # From ReEntered to Entered. Triggered a zero-delay timer timeout set
        # in TimeReadingStateTransition after that transition has determined 
        # whether a mouse cursor entry into the button space was a flick, or not.
        # (Note: In the PySide version
        # current at this writing, neither custom events nor custom signals
        # seem to work for triggering QEventTransaction or QSignalTransaction,
        # respectively)
        self.toEnteredFromReEnteredTrans = QSignalTransition(self.flickDetectDoneTrigger,
							     SIGNAL("timeout()"),
							     sourceState=self.stateReEntered); 
        self.toEnteredFromReEnteredTrans.setTargetState(self.stateEntered);

        # ---------------------- State Machine -------QtCore.signal--------------
                
        self.stateMachine   = QStateMachine();
        self.stateMachine.addState(self.stateGestureActivatePending);
        self.stateMachine.addState(self.stateEntered);
        self.stateMachine.addState(self.stateReEntered);
        self.stateMachine.addState(self.stateIdle);
        
        self.installEventFilter(self);
        
        self.stateMachine.setInitialState(self.stateIdle);
        self.stateMachine.start();
        
        #self.setGeometry(500, 500, 200,100);
        #self.show()
     
    # ------------------------ Public Methods -------------------------------
    
    @staticmethod
    def setFlicksEnabled(doEnable):
        '''
        Controls whether flicking in and out of buttons is enabled. 
        If flicks are enabled, then mouse-left-button signals are delayed
        for FLICK_TIME_THRESHOLD seconds. If flicks are disabled, then
        those signals are delivered immediately after the cursor leaves
        a button.
        @param doEnable: set to True if the flick feature is to be enabled. Else set to False
        @type doEnable: boolean
        '''
        if doEnable:
            GestureButton.flickEnabled = True;
            GestureButton.FLICK_TIME_THRESHOLD = GestureButton.FLICK_TIME_THRESHOLD_MASTER;
        else:
            GestureButton.flickEnabled = True;
            GestureButton.FLICK_TIME_THRESHOLD = 0.0;

    @staticmethod
    def flicksEnabled():
        '''
        Returns whether the flick feature is enabled.
        @return: True if flicking is enabled, else False.
        @rtype: boolean
        '''
        return GestureButton.flickEnabled;
    
    # ------------------------ Private Methods -------------------------------    

    def initSignals(self):
        #*******************
#        self.signals = GestureSignals();        
#        CommChannel.getInstance().registerSignals(self.signals);
        #CommChannel.getInstance().registerSignals(GestureSignals);
        CommChannel.registerSignals(GestureSignals);

        #*******************
        
    
    def connectWidgets(self):
        #self.maxFlickDurationTimer.timeout.connect(self.flickThresholdExceeded);
        pass;
    
    def eventFilter(self, target, event):
        if target == self and (event.__class__ == QMouseEvent):
            self.latestMousePos = event.pos();
        return False;
    
#    def mouseMoveEvent(self, mouseEvent):
#        self.latestMousePos = mouseEvent.pos();
#        super(GestureButton, self).mouseMoveEvent(mouseEvent);
    
    @Slot(QPushButton)
    def flickThresholdExceeded(self):
        print "Flick opportunity over."
        return False;

    def findClosestButtonBorder(self):
        '''
        Retrieves current mouse position, which is assumed to have been
        saved in the gesture button's lastMousePos instance variable by 
        a mouseMove signal handler or event filter. Compares this mouse position with the 
        four button borders. Returns a FlickDirection to indicate which
        border is closest to the mouse. All this uses global coordinates.
        @return: FlickDirection member.
        @raise ValueError: if minimum distance cannot be determined. 
        '''
        # Global mouse position:
        mousePos = self.mapToGlobal(self.latestMousePos)
        # Get: (upperLeftGlobal_x, upperLeftGlobal_y, width, height):
        gestureButtonRect = self.geometry()
        # Recompute upper left and lower right in global coords
        # each time, b/c window may have moved:
        topLeftPtGlobal = self.mapToGlobal(gestureButtonRect.topLeft());
        bottomRightPtGlobal = self.mapToGlobal(gestureButtonRect.bottomRight());
        # Do mouse coord absolute value compare with button edges,
        # because the last recorded mouse event is often just still
        # inside the button when this 'mouse left' signal arrives:
        distMouseFromTop = math.fabs(mousePos.y() - topLeftPtGlobal.y())
        distMouseFromBottom = math.fabs(mousePos.y() - bottomRightPtGlobal.y())
        distMouseFromLeft = math.fabs(mousePos.x() - topLeftPtGlobal.x())
        distMouseFromRight = math.fabs(mousePos.x() - bottomRightPtGlobal.x())
        minDist = min(distMouseFromTop, distMouseFromBottom, distMouseFromLeft, distMouseFromRight)
        if minDist == distMouseFromTop:
            return FlickDirection.NORTH
        elif minDist == distMouseFromBottom:
            return FlickDirection.SOUTH
        elif minDist == distMouseFromLeft:
            return FlickDirection.WEST
        elif minDist == distMouseFromRight:
            return FlickDirection.EAST
        else:
            raise ValueError("Failed to compute closest button border.")


    def __str__(self):
        if self.text() is not None:
            return self.text();
        else:
            return "<noLabel>";
        
  
# --------------------------  Specialized States ---------------------------

        
# --------------------------  Specialized Transitions ---------------------------        
        
class HotEntryTransition(QEventTransition):
    '''
    Tansition handling entry into this button from
    an idle state.
    '''
    
    def __init__(self, gestureButtonObj, event, sourceState=None):
        super(HotEntryTransition, self).__init__(gestureButtonObj, event, sourceState=sourceState);
        self.gestureButtonObj = gestureButtonObj;
        
    def onTransition(self, wrappedEventObj):
        '''
        First entry to button from an idle state (as opposed to
        from a re-entry (i.e. flick activity) state.
        @param wrappedEventObj: Entry event
        @type wrappedEventObj: QWrappedEvent
        '''
        try:
            super(HotEntryTransition, self).onTransition(wrappedEventObj);
        except TypeError:
            # Printing this will Segfault. Though this branch
            # should not execute if Qt passes in the properly typed wrappedEventObj:
            # It is supposed to be a QEvent, but sometimes comes as QListWidgetItem:
            #print "Type error in HotEntryXition: expected wrappedEventObj, got QListWidgetItem: " + str(wrappedEventObj.text())
            pass
        CommChannel.getSignal('GestureSignals.buttonEnteredSig').emit(self.gestureButtonObj);

class HotExitTransition(QSignalTransition):
    
    def __init__(self, gestureButtonObj, timerObj, sourceState=None):
        super(HotExitTransition, self).__init__(timerObj, SIGNAL("timeout()"), sourceState=sourceState);
        self.gestureButtonObj = gestureButtonObj;
        
    def onTransition(self, wrappedEventObj):
        super(HotExitTransition, self).onTransition(wrappedEventObj);
        CommChannel.getSignal('GestureSignals.buttonExitedSig').emit(self.gestureButtonObj); 

class TimeSettingStateTransition(QEventTransition):
    
    def __init__(self, gestureButtonObj, event, sourceState=None):
        super(TimeSettingStateTransition, self).__init__(gestureButtonObj, event, sourceState=sourceState);
        self.gestureButtonObj = gestureButtonObj;
        self.transitionTime = None;
        self.flickDirection = None;
    
    def onTransition(self, wrappedEventObj):
        '''
        Called when mouse cursor leaves the button area. Determine whether mouse
        left the button across the upper, lower, left, or right border. Note the
        time when this method call occurred. The time is needed later when the mouse
        possibly re-enters the button, signaling a flick.
        @param wrappedEventObj: wrapper around the event that triggered the transition. Unfortunately we 
        don't seem able to extract the corresponding mouseMove subclass event from this parameter. 
        @type wrappedEventObj: QWrappedEvent
        '''
        try:
            super(TimeSettingStateTransition, self).onTransition(wrappedEventObj);
        except TypeError:
            # Printing this will Segfault. Though this branch
            # should not execute if Qt passes in the properly typed wrappedEventObj:
            # It is supposed to be a QEvent, but sometimes comes as QListWidgetItem:
            #print "Type error in TimeSettingXition: expected wrappedEventObj, got QListWidgetItem: " + str(wrappedEventObj.text());
            pass;
        self.transitionTime = time.time();
        
        self.flickDirection = self.gestureButtonObj.findClosestButtonBorder()
        
        # Start a timer that will trigger a transition to the idle state, unless
        # the mouse returns to the button area within GestureButton.FLICK_TIME_THRESHOLD:
        self.gestureButtonObj.maxFlickDurationTimer.start(GestureButton.FLICK_TIME_THRESHOLD * 1000);
        
class TimeReadingStateTransition(QEventTransition):
    
    def __init__(self, gestureButtonObj, event, timeSettingStateTransition, sourceState=None):
        super(TimeReadingStateTransition, self).__init__(gestureButtonObj, event, sourceState=sourceState);
        self.timeSettingTransition = timeSettingStateTransition;
        self.gestureButtonObj = gestureButtonObj;
    
    def onTransition(self, eventEnumConstant):
        super(TimeReadingStateTransition, self).onTransition(eventEnumConstant);
        now = time.time();
        transitionTime = self.timeSettingTransition.transitionTime;
        if (now - transitionTime) > GestureButton.FLICK_TIME_THRESHOLD:        
            #print "Too slow"
            pass
        else:
            #print "Fast enough"
            if self.timeSettingTransition.flickDirection == FlickDirection.NORTH:
                CommChannel.getSignal('GestureSignals.flickSig').emit(self.gestureButtonObj, FlickDirection.NORTH);
            elif self.timeSettingTransition.flickDirection == FlickDirection.SOUTH:
                CommChannel.getSignal('GestureSignals.flickSig').emit(self.gestureButtonObj, FlickDirection.SOUTH);
            elif self.timeSettingTransition.flickDirection == FlickDirection.WEST:
                CommChannel.getSignal('GestureSignals.flickSig').emit(self.gestureButtonObj, FlickDirection.WEST);
            elif self.timeSettingTransition.flickDirection == FlickDirection.EAST:
                CommChannel.getSignal('GestureSignals.flickSig').emit(self.gestureButtonObj, FlickDirection.EAST);
                
        # Signal that this transition is done determining whether 
        # a ReEntry event was quick enough to be a flick. 
        # The timeout signal for this 0-delay timer will cause a 
        # transition to the Entered state. (Note: In the PySide version
        # current at this writing, neither custom events nor custom signals
        # seem to work for triggering QEventTransaction or QSignalTransaction,
        # respectively, therefore this hack using a 0-delay timer.): 
        self.gestureButtonObj.flickDetectDoneTrigger.start(0);
        
# --------------------------  Testing ---------------------------            
        
if __name__ == "__main__":
    
    @QtCore.Slot(QPushButton)
    def ackButtonEntered(buttonObj):
        print "Button entered."
        
    @QtCore.Slot(QPushButton)
    def ackButtonExited(buttonObj):
        print "Button exited."
        
    @QtCore.Slot(QPushButton,int)
    def ackButtonFlicked(buttonObj, direction):
        print "Button flicked: %s." % FlickDirection.toString(direction);
        

    app = QApplication(sys.argv);
    b = GestureButton("Foo");
    b.setFixedSize(200,250);
    enteredSig = CommChannel.getSignal('GestureSignals.buttonEnteredSig'); 
    enteredSig.connect(ackButtonEntered);
    CommChannel.getSignal('GestureSignals.buttonExitedSig').connect(ackButtonExited);
    CommChannel.getSignal('GestureSignals.flickSig').connect(ackButtonFlicked);
    b.show()
    app.exec_();
    sys.exit();
        
