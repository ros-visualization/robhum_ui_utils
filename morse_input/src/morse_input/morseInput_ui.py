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


# To do:
# - Volume control
# - Somewhere (moveEvent()?_: ensure that no overlap of morse win with active window.
#      If so, show error msg.  (Just put into Doc
# - Occasional X error: output in startup window, and cursor runs into dot/dash buttons.

# Doc:
#   - Abort if mouse click in rest zone.
#   - Left click to suspend beeping and cursor contraint and timing measure
#   - Right click: recenter cursor
#   - Prefs in $HOME/.morser/morser.cfg
#   - Cheat sheet (Menu)
#   - Options window
#   - Crosshair blinks yellow when word separation detected.
#   - If output gibberish, and you know your Morse was good, *lower* inter letter dwell time
#
# Needed PYTHONPATH:
#   /opt/ros/fuerte/lib/python2.7/dist-packages:/home/paepcke/fuerte/stacks/robhum_ui_utils:/home/paepcke/fuerte/stacks/robhum_ui_utils/gesture_buttons/src:/opt/ros/fuerte/stacks/python_qt_binding/src:/home/paepcke/fuerte/stacks/robhum_ui_utils/qt_comm_channel/src:/home/paepcke/fuerte/stacks/robhum_ui_utils/qt_dialog_service/src:/home/paepcke/fuerte/stacks/robhum_ui_utils/virtual_keyboard/src:

# Dash/Dot blue value: 35,60,149

try:
    import roslib; roslib.load_manifest('morse_input');
    ROS_AVAILABLE = True;
except ImportError:
    ROS_AVAILABLE = False;

import sys
import os
import re
import fcntl
import ConfigParser
from functools import partial

try:
    from gesture_buttons.gesture_button import GestureButton
    from gesture_buttons.gesture_button import FlickDirection
    from qt_comm_channel.commChannel import CommChannel
    from qt_dialog_service.qt_dialog_service import DialogService
    from virtual_keyboard.virtual_keyboard import VirtualKeyboard
except ImportError as e:
    print(`e`);
    print("Roslib is unavailable. So your PYTHONPATH will need to include src directories for:\n" +
          "gesture_buttons \n" +
          "qt_comm_channel \n" +
          "qt_dialog_service \n" +
          "virtual_keyboard \n");
    sys.exit();    


from morseToneGeneration import MorseGenerator
from morseToneGeneration import Morse
from morseToneGeneration import TimeoutReason

from morseCheatSheet import MorseCheatSheet;

from morseSpeedTimer import MorseSpeedTimer;


from python_qt_binding import loadUi;
from python_qt_binding import QtGui;
from python_qt_binding import QtCore;
#from word_completion.word_collection import WordCollection;
from QtGui import QApplication, QMainWindow, QMessageBox, QWidget, QCursor, QHoverEvent, QColor, QIcon;
from QtGui import QMenuBar, QToolTip, QLabel, QPixmap, QRegExpValidator;
from QtCore import QPoint, Qt, QTimer, QEvent, Signal, QCoreApplication, QRect, QRegExp; 

# Dot/Dash RGB: 0,179,240

class OutputType:
    TYPE  = 0
    SPEAK = 1

class Direction:
    HORIZONTAL = 0
    VERTICAL   = 1

class Crosshairs:
    CLEAR    = 0
    YELLOW   = 1
    GREEN    = 2
    RED      = 3

class PanelExpansion:
    LESS = 0
    MORE = 1
    
class MorseInputSignals(CommChannel):
    letterDone = Signal(int,str);
    panelCollapsed = Signal(int,int,int,int);

class MorseInput(QMainWindow):
    '''
    Manages all UI interactions with the Morse code generation.
    '''
    
    MORSE_BUTTON_WIDTH = 100; #px
    MORSE_BUTTON_HEIGHT = 100; #px
    
    SUPPORT_BUTTON_WIDTHS = 80; #px: The maximum Space and Backspace button widths.
    SUPPORT_BUTTON_HEIGHTS = 80; #px: The maximum Space and Backspace button heights.
    
    MOUSE_UNCONSTRAIN_TIMEOUT = 300; # msec
    
    HEAD_TRACKER = True;
    
    def __init__(self):
        super(MorseInput,self).__init__();

        # Only allow a single instance of the Morser program to run:
        self.morserLockFile = '/tmp/morserLock.lk';
        MorseInput.morserLockFD = open(self.morserLockFile, 'w')
        try:
            # Attempt to lock the lock file exclusively, but
            # throw IOError if already locked, rather than waiting
            # for unlock (the LOCK_NB ORing):
            fcntl.lockf(MorseInput.morserLockFD, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            errMsg = "The Morser program is already running. Please quit it.\n" +\
                     "If Morser really is not running, execute 'rm %s' in a terminal window." % self.morserLockFile;
            sys.stderr.write(errMsg)
            sys.exit()
        
        # Disallow focus acquisition for the morse window.
        # Needed to prevent preserve focus on window that
        # is supposed to receive the clear text of the 
        # morse:
        self.setFocusPolicy(Qt.NoFocus);
        
        self.iconDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'icons')
        
        CommChannel.registerSignals(MorseInputSignals);
        
        # Find QtCreator's XML file in the PYTHONPATH, and load it:
        currDir = os.path.realpath(__file__);
        
        # Load UI for Morse input:
        relPathQtCreatorFileMainWin = "qt_files/morseInput/morseInput.ui";
        qtCreatorXMLFilePath = self.findFile(relPathQtCreatorFileMainWin);
        if qtCreatorXMLFilePath is None:
            raise ValueError("Can't find QtCreator user interface file %s" % relPathQtCreatorFileMainWin);
        # Make QtCreator generated UI a child if this instance:
        loadUi(qtCreatorXMLFilePath, self);
        self.windowTitle = "Morser: Semi-automatic Morse code input";
        self.setWindowTitle(self.windowTitle);
        
        # Load UI for Morse options dialog:
        relPathQtCreatorFileOptionsDialog = "qt_files/morserOptions/morseroptions.ui";
        qtCreatorXMLFilePath = self.findFile(relPathQtCreatorFileOptionsDialog);
        if qtCreatorXMLFilePath is None:
            raise ValueError("Can't find QtCreator user interface file %s" % relPathQtCreatorFileOptionsDialog);
        # Make QtCreator generated UI a child if this instance:
        self.morserOptionsDialog = loadUi(qtCreatorXMLFilePath);
        
        # Load UI for Morse Cheat Sheet:
        self.morseCheatSheet = MorseCheatSheet(self);
        
        self.dialogService = DialogService();

        # Get a morse generator that manages all Morse 
        # generation and timing:
        self.morseGenerator = MorseGenerator(callback=MorseInput.letterCompleteNotification);
        
        # Get virtual keyboard that can 'fake' X11 keyboard inputs:
        self.virtKeyboard = VirtualKeyboard();
        
        # setOptions() needs to be called after instantiation
        # of morseGenerator, so that we can obtain the generator's
        # defaults for timings:
        self.optionsFilePath = os.path.join(os.getenv('HOME'), '.morser/morser.cfg');
        self.setOptions();

        # Create the gesture buttons for dot/dash/space/backspace:
        self.insertGestureButtons();
        GestureButton.setFlicksEnabled(False);
        
        self.installMenuBar();
        self.installStatusBar();

        # Get a speed measurer (must be defined before
        # call to connectWidgets():
        self.speedMeasurer = MorseSpeedTimer(self);
        
        self.connectWidgets();
        self.cursorEnteredOnce = False;

        # Set cursor to hand icon while inside Morser:
        self.morseCursor = QCursor(Qt.OpenHandCursor);
        QApplication.setOverrideCursor(self.morseCursor);
        #QApplication.restoreOverrideCursor()
        
        self.blinkTimer = None;
        self.flashTimer = None;
        
        # Init capability of constraining cursor to
        # move only virtically and horizontally:
        self.initCursorConstrainer();
        
        # Don't allow editing of the ticker tape:
        self.tickerTapeLineEdit.setFocusPolicy(Qt.NoFocus);
        # But allow anything to be placed inside programmatically:
        tickerTapeRegExp = QRegExp('.*');
        tickerTapeValidator = QRegExpValidator(tickerTapeRegExp);
        self.tickerTapeLineEdit.setValidator(tickerTapeValidator);
        
        # Deceleration readout is floating point with up to 2 digits after decimal:
        cursorDecelerationRegExp = QRegExp(r'[\d]{1}[.]{1}[\d]{1,2}$');
        cursorDecelerationValidator = QRegExpValidator(cursorDecelerationRegExp);
        self.morserOptionsDialog.cursorDecelerationReadoutLineEdit.setValidator(cursorDecelerationValidator);
        
        self.expandPushButton.setFocusPolicy(Qt.NoFocus);
        
        # Styling:
        self.createColors();
        self.setStyleSheet("QWidget{background-color: %s}" % self.lightBlueColor.name());

        # Power state: initially on:
        self.poweredUp = True;
        
        self.show();

        # Compute global x positions of dash/dot buttons facing
        # towards the rest area:
        self.computeInnerButtonEdges();
        
        # Monitor mouse, so that we can constrain mouse movement to
        # vertical and horizontal (must be set after the affected
        # widget(s) are visible):
        #self.setMouseTracking(True)
        self.centralWidget.installEventFilter(self);
        self.centralWidget.setMouseTracking(True)
        
    def initCursorConstrainer(self):
        self.recentMousePos = None;
        self.currentMouseDirection = None;
        self.enableConstrainVertical = False;
        # Holding left mouse button inside the Morse
        # window will suspend cursor constraining,
        # if it is enabled. Letting go of the button
        # will re-enable constraints. This var
        # keeps track of suspension so mouse-button-up
        # knows whether to re-instate constraining:
        self.cursorContraintSuspended = False;
        
        # Timer that frees the cursor from
        # vertical/horizontal constraint every few
        # milliseconds, unless mouse keeps moving:
        self.mouseUnconstrainTimer = QTimer();
        self.mouseUnconstrainTimer.setInterval(MorseInput.MOUSE_UNCONSTRAIN_TIMEOUT);
        self.mouseUnconstrainTimer.setSingleShot(True);
        self.mouseUnconstrainTimer.timeout.connect(self.unconstrainTheCursor);

    def computeInnerButtonEdges(self):
        # Remember the X position of the global-screen right 
        # edge of the dot button for reference in the event filter:
        localGeo = self.dotButton.geometry();
        dotButtonGlobalPos = self.mapToGlobal(QPoint(localGeo.x() + localGeo.width(),
                                                     localGeo.y()));
        self.dotButtonGlobalRight = dotButtonGlobalPos.x();
        # Remember the X position of the global-screen left 
        # edge of the dash button for reference in the event filter:
        localGeo = self.dashButton.geometry();
        dashButtonGlobalPos = self.mapToGlobal(QPoint(localGeo.x(), localGeo.y()));
        self.dashButtonGlobalLeft = dashButtonGlobalPos.x();
        
        # Remember global location of the central point in the rest zone:
        self.crosshairLabel.setMaximumHeight(11); # Height of crosshair icon
        self.crosshairLabel.setMaximumWidth(11);  # Width of crosshair icon
        # Compute the location of the crosshair in the center of
        # the rest area. The addition of 20 pixels to the Y-coordinate
        # accounts for Ubuntu's title bar at the top of the display,
        # which mapToGlobal() does not account for:
        self.centralRestGlobalPos = self.mapToGlobal(self.crosshairLabel.pos() + QPoint(0,20)); 

    def startCursorConstraint(self):
        self.constrainCursorInHotZone = True;
        
    def stopCursorConstraint(self):
        self.constrainCursorInHotZone = False;
        self.mouseUnconstrainTimer.stop();

    def createColors(self):
        self.grayBlueColor = QColor(89,120,137);  # Letter buttons
        self.lightBlueColor = QColor(206,230,243); # Background
        self.darkGray      = QColor(65,88,101);   # Central buttons
        self.wordListFontColor = QColor(62,143,185); # Darkish blue.
        self.purple        = QColor(147,124,195); # Gesture button pressed
        
        
    def findFile(self, path, matchFunc=os.path.isfile):
        if path is None:
            return None
        for dirname in sys.path:
            candidate = os.path.join(dirname, path)
            if matchFunc(candidate):
                return candidate
        return None;

    def insertGestureButtons(self):

        self.dotButton = GestureButton('dot');
        self.dotButton.setIcon(QIcon(os.path.join(self.iconDir, 'dot.png'))); 
        self.dotButton.setText("");
        # Don't have button assume the pressed-down color when 
        # clicked:
        self.dotButton.setFocusPolicy(Qt.NoFocus);
        self.dotButton.setMinimumHeight(MorseInput.MORSE_BUTTON_HEIGHT);
        self.dotButton.setMinimumWidth(MorseInput.MORSE_BUTTON_WIDTH);
        self.dotAndDashHLayout.addWidget(self.dotButton);
                                                
        self.dotAndDashHLayout.addStretch();
        
        # Crosshair:
        self.crosshairPixmapClear  = QPixmap(os.path.join(self.iconDir, 'crosshairEmpty.png'));
        self.crosshairPixmapGreen  =  QPixmap(os.path.join(self.iconDir, 'crosshairGreen.png'));
        self.crosshairPixmapYellow =  QPixmap(os.path.join(self.iconDir, 'crosshairYellow.png'));
        self.crosshairPixmapRED    =  QPixmap(os.path.join(self.iconDir, 'crosshairRed.png'));
        self.crosshairLabel = QLabel();
        self.crosshairLabel.setPixmap(self.crosshairPixmapClear);
        self.crosshairLabel.setText("");
        self.dotAndDashHLayout.addWidget(self.crosshairLabel);
        
        self.dotAndDashHLayout.addStretch();
        
        self.dashButton = GestureButton('dash');
        self.dashButton.setIcon(QIcon(os.path.join(self.iconDir, 'dash.png')));
        self.dashButton.setText("");
        # Don't have button assume the pressed-down color when 
        # clicked:
        self.dashButton.setFocusPolicy(Qt.NoFocus);
        self.dashButton.setMinimumHeight(MorseInput.MORSE_BUTTON_HEIGHT);
        self.dashButton.setMinimumWidth(MorseInput.MORSE_BUTTON_WIDTH);
        self.dotAndDashHLayout.addWidget(self.dashButton);
        
        self.eowButton = GestureButton('Space');
        self.eowButton.setAutoRepeat(True);
        # Don't have button assume the pressed-down color when 
        # clicked:
        self.eowButton.setFocusPolicy(Qt.NoFocus);
        self.eowButton.setMaximumWidth(MorseInput.SUPPORT_BUTTON_WIDTHS)        
        self.eowButton.setMinimumHeight(MorseInput.SUPPORT_BUTTON_HEIGHTS)        
        self.endOfWordButtonHLayout.addWidget(self.eowButton);

        self.backspaceButton = GestureButton('Backspace');
        self.backspaceButton.setAutoRepeat(True);
        # Don't have button assume the pressed-down color when 
        # clicked:
        self.backspaceButton.setFocusPolicy(Qt.NoFocus);
        self.backspaceButton.setMaximumWidth(MorseInput.SUPPORT_BUTTON_WIDTHS)
        self.backspaceButton.setMinimumHeight(MorseInput.SUPPORT_BUTTON_HEIGHTS)
        self.backspaceHLayout.addWidget(self.backspaceButton);
        
        self.powerPushButton.setIcon(QIcon(os.path.join(self.iconDir, 'powerIconSmall.png')));
        # Don't have button assume the pressed-down color when 
        # clicked:
        self.powerPushButton.setFocusPolicy(Qt.NoFocus);
        self.powerPushButton.setChecked(True);
        
        # Prevent focus on the two clear buttons:
        self.speedMeasureClearButton.setFocusPolicy(Qt.NoFocus);
        self.tickerTapeClearButton.setFocusPolicy(Qt.NoFocus);
        self.timeMeButton.setFocusPolicy(Qt.NoFocus);
        
    def installMenuBar(self):
        exitAction = QtGui.QAction(QtGui.QIcon('exit.png'), '&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(self.close)
        
        raiseOptionsDialogAction = QtGui.QAction(QtGui.QIcon('preferences-desktop-accessibility.png'), '&Options', self)
         
        raiseOptionsDialogAction.setShortcut('Ctrl+O');
        raiseOptionsDialogAction.setStatusTip('Show options and settings')
        raiseOptionsDialogAction.triggered.connect(self.showOptions)
  
        raiseCheatSheetAction = QtGui.QAction(QtGui.QIcon('preferences-desktop-accessibility.png'), '&Cheat sheet', self)
        raiseCheatSheetAction.setShortcut('Ctrl+M')
        raiseCheatSheetAction.setStatusTip('Show Morse code cheat sheet')
        raiseCheatSheetAction.triggered.connect(self.showCheatSheet)
        
        fileMenu = self.menuBar.addMenu('&File')
        fileMenu.addAction(exitAction)
        
        editMenu = self.menuBar.addMenu('&Edit')
        editMenu.addAction(raiseOptionsDialogAction)
        
        viewMenu = self.menuBar.addMenu('&View')
        viewMenu.addAction(raiseCheatSheetAction)
        # When showing table the first time, we move it left so that it 
        # does not totally obscure the Morse window:
        self.shownCheatSheetBefore = False;      
    
    def installStatusBar(self):
        self.statusBar.showMessage("Ready to go... Remember to set focus"); 
    
        
    def connectWidgets(self):
        
        # Signal connections:
        CommChannel.getSignal('GestureSignals.buttonEnteredSig').connect(self.buttonEntered);
        CommChannel.getSignal('GestureSignals.buttonExitedSig').connect(self.buttonExited);
        CommChannel.getSignal('MorseInputSignals.letterDone').connect(self.deliverInput);
        CommChannel.getSignal('MorseInputSignals.panelCollapsed').connect(self.adjustMainWindowHeight);

        # Main window:
        self.timeMeButton.pressed.connect(self.speedMeasurer.timeMeToggled);
        self.tickerTapeClearButton.clicked.connect(self.tickerTapeClear);
        self.powerPushButton.pressed.connect(self.powerToggled);
        self.expandPushButton.clicked.connect(self.togglePanelExpansion);
        
        # Options dialog:
        self.morserOptionsDialog.cursorConstraintCheckBox.stateChanged.connect(partial(self.checkboxStateChanged,
                                                                                       self.morserOptionsDialog.cursorConstraintCheckBox));
        self.morserOptionsDialog.wordStopSegmentationCheckBox.stateChanged.connect(partial(self.checkboxStateChanged,
                                                                                           self.morserOptionsDialog.wordStopSegmentationCheckBox));
        self.morserOptionsDialog.typeOutputRadioButton.toggled.connect(partial(self.checkboxStateChanged,
                                                                               self.morserOptionsDialog.typeOutputRadioButton));
        self.morserOptionsDialog.speechOutputRadioButton.toggled.connect(partial(self.checkboxStateChanged,
                                                                                 self.morserOptionsDialog.speechOutputRadioButton));
        self.morserOptionsDialog.useTickerCheckBox.toggled.connect(partial(self.checkboxStateChanged,
                                                                           self.morserOptionsDialog.useTickerCheckBox));

        self.morserOptionsDialog.cursorDecelerationSlider.valueChanged.connect(partial(self.sliderStateChanged,
                                                                                       self.morserOptionsDialog.cursorDecelerationSlider));
        self.morserOptionsDialog.keySpeedSlider.valueChanged.connect(partial(self.sliderStateChanged,
                                                                             self.morserOptionsDialog.keySpeedSlider));
        self.morserOptionsDialog.interLetterDelaySlider.valueChanged.connect(partial(self.sliderStateChanged,
                                                                                     self.morserOptionsDialog.interLetterDelaySlider));
        self.morserOptionsDialog.interWordDelaySlider.valueChanged.connect(partial(self.sliderStateChanged,
                                                                                   self.morserOptionsDialog.interWordDelaySlider));

        self.morserOptionsDialog.savePushButton.clicked.connect(self.optionsSaveButton);
        self.morserOptionsDialog.cancelPushButton.clicked.connect(self.optionsCancelButton);
        
        self.morserOptionsDialog.cursorDecelerationReadoutLineEdit.editingFinished.connect(partial(self.sliderReadoutModified,
                                                                                                   self.morserOptionsDialog.cursorDecelerationSlider));
        self.morserOptionsDialog.cursorDecelerationReadoutLineEdit.returnPressed.connect(partial(self.sliderReadoutModified,
                                                                                                 self.morserOptionsDialog.cursorDecelerationSlider));
        self.morserOptionsDialog.keySpeedReadoutLineEdit.editingFinished.connect(partial(self.sliderReadoutModified,
                                                                                         self.morserOptionsDialog.keySpeedSlider));
        self.morserOptionsDialog.keySpeedReadoutLineEdit.returnPressed.connect(partial(self.sliderReadoutModified,
                                                                                       self.morserOptionsDialog.keySpeedSlider));
        self.morserOptionsDialog.letterDwellReadoutLineEdit.editingFinished.connect(partial(self.sliderReadoutModified,
                                                                                            self.morserOptionsDialog.interLetterDelaySlider));
        self.morserOptionsDialog.letterDwellReadoutLineEdit.returnPressed.connect(partial(self.sliderReadoutModified,
                                                                                           self.morserOptionsDialog.interLetterDelaySlider));
        self.morserOptionsDialog.wordDwellReadoutLineEdit.editingFinished.connect(partial(self.sliderReadoutModified,
                                                                                          self.morserOptionsDialog.interWordDelaySlider));
        self.morserOptionsDialog.wordDwellReadoutLineEdit.returnPressed.connect(partial(self.sliderReadoutModified,
                                                                                       self.morserOptionsDialog.interWordDelaySlider));
        
    def expandMorePanel(self, expansion):
        '''
        Expand or hide the main window's bottom panel, which holds the speed meter.
        @param expansion: expand vs. hide
        @type expansion: PanelExpansion
        '''
        if expansion == PanelExpansion.LESS:
            self.expandPushButton.setIcon(QIcon(os.path.join(self.iconDir, 'plusSign.png')));
            self.speedMeasureWidget.setHidden(True);
            # Remember this state in configuration:
            self.cfgParser.set('Appearance','morePanelExpanded',str(False));
            newMainWinGeo = self.getAdjustedWinGeo(-1 * self.speedMeasureWidget.geometry().height());
            MorseInputSignals.getSignal('MorseInputSignals.panelCollapsed').emit(newMainWinGeo.x(),
                                                                                 newMainWinGeo.y(),
                                                                                 newMainWinGeo.width(),
                                                                                 newMainWinGeo.height());
        else:
            self.expandPushButton.setIcon(QIcon(os.path.join(self.iconDir, 'minusSign.png')));
            self.speedMeasureWidget.setHidden(False);
            self.cfgParser.set('Appearance','morePanelExpanded',str(True));

    def getAdjustedWinGeo(self, pixels):
        '''
        Given a positive or negative number of pixels,
        return a rectangle that is respectively higher or
        shorter than the current main window.
        @param pixels: number of pixels to add or subtract from the height
        @type pixels: int
        @return: new rectangle
        @rtype: QRect
        '''
        geo = self.geometry();
        newHeight = geo.height() + pixels;
        newGeo = QRect(geo.x(), geo.y(), geo.width(), newHeight);
        return newGeo;

    @QtCore.Slot(int,int,int,int)
    def adjustMainWindowHeight(self, x,y,width,height):
        '''
        Given a rectangle, adjust the main window dimensions
        to take that shape.
        @param x: 
        @type x: int
        @param y: 
        @type y: int
        @param width: 
        @type width: int
        @param height: 
        @type height: int
        '''
        self.setMaximumHeight(self.geometry().height() - self.speedMeasureWidget.geometry().height());

    def togglePanelExpansion(self):
        if self.speedMeasureWidget.isVisible():
            self.expandMorePanel(PanelExpansion.LESS);
        else:
            self.expandMorePanel(PanelExpansion.MORE);
        
    def showOptions(self):
        self.morserOptionsDialog.show();
    
    def showCheatSheet(self):
        self.morseCheatSheet.show();
        if not self.shownCheatSheetBefore:
            cheatSheetGeo = self.morseCheatSheet.geometry();
            cheatSheetGeo.moveLeft(200);
            self.morseCheatSheet.setGeometry(cheatSheetGeo);
            self.shownCheatSheetBefore = True;
    
    def setOptions(self):
        
        self.optionsDefaultDict = {
                    'outputDevice'             : str(OutputType.TYPE),
                    'letterDwellSegmentation'  : str(True),
                    'wordDwellSegmentation'    : str(True),
                    'constrainCursorInHotZone' : str(False),
                    'keySpeed'                 : str(1.7),
                    'cursorDeceleration'       : str(0.5),
                    'interLetterDwellDelay'    : str(self.morseGenerator.getInterLetterTime()),
                    'interWordDwellDelay'      : str(self.morseGenerator.getInterWordTime()),
                    'winGeometry'              : '100,100,350,350',
                    'useTickerTape'            : str(True),
                    'morePanelExpanded'        : str(True),
                    }

        self.cfgParser = ConfigParser.SafeConfigParser(self.optionsDefaultDict);
        self.cfgParser.add_section('Morse generation');
        self.cfgParser.add_section('Output');
        self.cfgParser.add_section('Appearance');
        self.cfgParser.read(self.optionsFilePath);
        
        mainWinGeometry = self.cfgParser.get('Appearance', 'winGeometry');
        # Get four ints from the comma-separated string of upperLeftX, upperLeftY,
        # Width,Height numbers:
        try:
            nums = mainWinGeometry.split(',');
            self.setGeometry(QRect(int(nums[0].strip()),int(nums[1].strip()),int(nums[2].strip()),int(nums[3].strip())));
        except Exception as e:
            self.dialogService.showErrorMsg("Could not set window size; config file spec not grammatical: %s. (%s" % (mainWinGeometry, `e`));
        
        self.setCursorDeceleration(self.cfgParser.getfloat('Morse generation', 'cursorDeceleration'));
        
        self.morseGenerator.setInterLetterDelay(self.cfgParser.getfloat('Morse generation', 'interLetterDwellDelay'));
        self.morseGenerator.setInterWordDelay(self.cfgParser.getfloat('Morse generation', 'interWordDwellDelay'));
        self.morseGenerator.setSpeed(self.cfgParser.getfloat('Morse generation', 'keySpeed'));
        
        self.constrainCursorInHotZone = self.cfgParser.getboolean('Morse generation', 'constrainCursorInHotZone');
        self.outputDevice = self.cfgParser.getint('Output', 'outputDevice');
        self.letterDwellSegmentation = self.cfgParser.getboolean('Morse generation', 'letterDwellSegmentation');
        self.letterDwellSegmentation = self.cfgParser.getboolean('Morse generation', 'wordDwellSegmentation');

        self.useTickerTape = self.cfgParser.getboolean('Output', 'useTickerTape');
        
        self.panelExpanded = self.cfgParser.getboolean('Appearance', 'morePanelExpanded');
        if self.panelExpanded:
            self.expandMorePanel(PanelExpansion.MORE);
        else:
            self.expandMorePanel(PanelExpansion.LESS);

        # Make the options dialog reflect the options we just established:
        # Path to Morser options file:
        self.initOptionsDialogFromOptions();

    def initOptionsDialogFromOptions(self):

        # Cursor constraint:
        self.morserOptionsDialog.cursorConstraintCheckBox.setChecked(self.cfgParser.getboolean('Morse generation', 'constrainCursorInHotZone'));
        
        # Automatic word segmentation:
        enableWordSegmentation = self.cfgParser.getboolean('Morse generation', 'wordDwellSegmentation');
        self.morserOptionsDialog.wordStopSegmentationCheckBox.setChecked(enableWordSegmentation);
        if not enableWordSegmentation:
            self.morserOptionsDialog.interWordDelaySlider.setEnabled(False);
            self.morserOptionsDialog.wordDwellReadoutLineEdit.setEnabled(False);
        
        # Output to X11 vs. Speech:    
        self.morserOptionsDialog.typeOutputRadioButton.setChecked(self.cfgParser.getint('Output', 'outputDevice')==OutputType.TYPE);
        self.morserOptionsDialog.speechOutputRadioButton.setChecked(self.cfgParser.getint('Output', 'outputDevice')==OutputType.SPEAK);


        # Cursor deceleration:
        cursorDeceleration = self.cfgParser.getfloat('Morse generation', 'cursorDeceleration');
        self.morserOptionsDialog.cursorDecelerationSlider.setValue(int(cursorDeceleration * 100));
        # Readout for the cursor deceleration:
        self.morserOptionsDialog.cursorDecelerationReadoutLineEdit.setText(str(cursorDeceleration));
        
        # Key speed slider:
        self.morserOptionsDialog.keySpeedSlider.setValue(int(10*self.cfgParser.getfloat('Morse generation', 'keySpeed')));
        # Init the readout of the speed slider:
        self.morserOptionsDialog.keySpeedReadoutLineEdit.setText(str(self.morserOptionsDialog.keySpeedSlider.value()));
        
        # Dwell time that indicates end of Morse letter:
        interLetterSecs = self.cfgParser.getfloat('Morse generation', 'interLetterDwellDelay');
        self.morserOptionsDialog.interLetterDelaySlider.setValue(int(interLetterSecs*1000.)); # inter-letter dwell slider is in msecs
        # Init the readout of the letter dwell slider:
        self.morserOptionsDialog.letterDwellReadoutLineEdit.setText(str(self.morserOptionsDialog.interLetterDelaySlider.value()));
        
        # Dwell time that indicates end of word:
        interWordSecs = self.cfgParser.getfloat('Morse generation', 'interWordDwellDelay');
        self.morserOptionsDialog.interWordDelaySlider.setValue(int(interWordSecs*1000.));     # inter-word dwell slider is in msecs
        # Init the readout of the word dwell slider:
        self.morserOptionsDialog.wordDwellReadoutLineEdit.setText(str(self.morserOptionsDialog.interWordDelaySlider.value()));
        self.morserOptionsDialog.useTickerCheckBox.setChecked(self.cfgParser.getboolean('Output', 'useTickerTape'));
    
    def sliderReadoutModified(self, slider):
        if slider == self.morserOptionsDialog.cursorDecelerationSlider:
            slider.setValue(int(float(self.morserOptionsDialog.cursorDecelerationReadoutLineEdit.text()) * 100.0));
        elif slider == self.morserOptionsDialog.keySpeedSlider:
            slider.setValue(int(self.morserOptionsDialog.keySpeedReadoutLineEdit.text()));
        elif slider == self.morserOptionsDialog.interLetterDelaySlider:
            slider.setValue(int(self.morserOptionsDialog.letterDwellReadoutLineEdit.text()));
        elif slider == self.morserOptionsDialog.interWordDelaySlider:
            slider.setValue(int(self.morserOptionsDialog.wordDwellReadoutLineEdit.text()));
        else:
            raise ValueError("Expecting one of the options slider objects.")
        slider.setFocus();

            
    def checkboxStateChanged(self, checkbox, newState):
        '''
        Called when any of the option dialog's checkboxes change:
        @param checkbox: the affected checkbox
        @type checkbox: QCheckBox
        @param newState: the new state, though Qt docs are cagey about what this means: an int of some kind.
        @type newState: QCheckState
        '''
        checkboxNowChecked = checkbox.isChecked();
        if checkbox == self.morserOptionsDialog.cursorConstraintCheckBox:
            self.cfgParser.set('Morse generation','constrainCursorInHotZone',str(checkboxNowChecked));
            self.constrainCursorInHotZone = checkboxNowChecked; 
        elif checkbox == self.morserOptionsDialog.useTickerCheckBox:
            self.cfgParser.set('Output','useTickerTape', str(checkboxNowChecked));
            self.useTickerTape = checkboxNowChecked;
        elif checkbox == self.morserOptionsDialog.wordStopSegmentationCheckBox:
            self.cfgParser.set('Morse generation', 'wordDwellSegmentation', str(checkboxNowChecked));
            self.cfgParser.set('Morse generation', 'interWordDwellDelay', str(self.morserOptionsDialog.interWordDelaySlider.value()/1000.));
            # Enable or disable the inter word delay slider and text box if
            # word dwell is enabled, and vice versa:
            if checkboxNowChecked:
                self.morserOptionsDialog.interWordDelaySlider.setEnabled(True);
                self.morserOptionsDialog.wordDwellReadoutLineEdit.setEnabled(True);
                self.morseGenerator.setInterWordDelay(int(self.morserOptionsDialog.wordDwellReadoutLineEdit.text())/1000.0);
            else:
                self.morserOptionsDialog.interWordDelaySlider.setEnabled(False);
                self.morserOptionsDialog.wordDwellReadoutLineEdit.setEnabled(False);
                # Disable word segmentation:
                self.morseGenerator.setInterWordDelay(-1);
        elif checkbox == self.morserOptionsDialog.typeOutputRadioButton:
            self.cfgParser.set('Output', 'outputDevice', str(OutputType.TYPE));
            #**************
            pass
            #**************
        elif checkbox == self.morserOptionsDialog.speechOutputRadioButton:
            self.cfgParser.set('Output', 'outputDevice', str(OutputType.SPEAK));
            #**************
            pass
            #**************
        else:
            raise ValueError('Unknown checkbox: %s' % str(checkbox));


    def sliderStateChanged(self, slider, newValue):
        #slider.setToolTip(str(newValue));
        #QToolTip.showText(slider.pos(), str(newValue), slider, slider.geometry())
        if slider == self.morserOptionsDialog.cursorDecelerationSlider:
            newValue = newValue/100.0
            # Update readout:
            self.morserOptionsDialog.cursorDecelerationReadoutLineEdit.setText(str(newValue));
            self.cfgParser.set('Morse generation', 'cursorDeceleration', str(newValue));
            self.setCursorDeceleration(newValue);
        elif slider == self.morserOptionsDialog.keySpeedSlider:
            # Update readout:
            self.morserOptionsDialog.keySpeedReadoutLineEdit.setText(str(newValue));
            # Speed slider goes from 1 to 6, but QT is set to 
            # have it go from 1 to 60, because fractional intervals
            # are not allowed. So, scale the read value:
            newValue = newValue/10.0
            self.cfgParser.set('Morse generation', 'keySpeed', str(newValue));
            self.morseGenerator.setSpeed(newValue);
        elif  slider == self.morserOptionsDialog.interLetterDelaySlider:
            self.morserOptionsDialog.letterDwellReadoutLineEdit.setText(str(newValue));
            valInSecs = newValue/1000.;
            self.cfgParser.set('Morse generation', 'interLetterDwellDelay', str(valInSecs));
            self.morseGenerator.setInterLetterDelay(valInSecs);
        elif  slider == self.morserOptionsDialog.interWordDelaySlider:
            self.morserOptionsDialog.wordDwellReadoutLineEdit.setText(str(newValue));
            valInSecs = newValue/1000.;
            self.cfgParser.set('Morse generation', 'interWordDwellDelay', str(valInSecs));
            self.morseGenerator.setInterWordDelay(valInSecs);
        
    def setCursorDeceleration(self, newValue):
        '''
        Change deceleration multiplier for cursor movement inside the 
        rest zone. Value should vary between 0.001 and 1.0
        @param newValue: multiplier that decelerates cursor.
        @type newValue: float.
        '''
        self.cursorAcceleration = newValue;
        
    def optionsSaveButton(self):
        try:
            # Does the config dir already exist? If not
            # create it:
            optionsDir = os.path.dirname(self.optionsFilePath);
            if not os.path.isdir(optionsDir):
                os.makedirs(optionsDir, 0777);
            with open(self.optionsFilePath, 'wb') as outFd:
                self.cfgParser.write(outFd);
        except IOError as e:
            self.dialogService.showErrorMsg("Could not save options: %s" % `e`);
            
        self.morserOptionsDialog.hide();
        
    def optionsCancelButton(self):
        '''
        Undo option changes user played with while
        option box was open.
        '''
        self.morserOptionsDialog.hide();
        self.cfgParser.read(self.optionsFilePath);
        self.initOptionsDialogFromOptions();
        
    def buttonEntered(self, buttonObj):
        if not self.poweredUp:
            return;
        if buttonObj == self.dotButton:
            self.morseGenerator.startMorseSeq(Morse.DOT);
        elif buttonObj == self.dashButton:
            self.morseGenerator.startMorseSeq(Morse.DASH);
        elif buttonObj == self.eowButton:
            buttonObj.animateClick();
            self.outputLetters(' ');
        elif buttonObj == self.backspaceButton:
            buttonObj.animateClick();
            self.outputBackspace();
        
    def buttonExited(self, buttonObj):
        if buttonObj == self.dotButton:
            self.morseGenerator.stopMorseSeq();
        elif buttonObj == self.dashButton:
            self.morseGenerator.stopMorseSeq();

    def eventFilter(self, target, event):

        eventType = event.type();
        
        if eventType == QEvent.Enter:
            # The first time cursor ever enters the Morse
            # window do the following:
            if not self.cursorEnteredOnce:
                # Get the Morse windows X11 window ID saved,
                # so that we can later activate it whenever
                # the cursor leaves the Morse window.
                # First, make the Morse window active: 
                self.virtKeyboard.activateWindow(windowTitle=self.windowTitle);
                self.virtKeyboard.saveActiveWindowID('morseWinID');
                # Also, initialize the keyboard destination:
                self.virtKeyboard.saveActiveWindowID('keyboardTarget');
                self.cursorEnteredOnce = True;
                
            # Remember X11 window that is active as we
            # enter the application window, but don't remember
            # this morse code window, if that was the active one:
            self.virtKeyboard.saveActiveWindowID('currentActiveWindow');
            #***********
            # For testing cursor enter/leave focus changes:
            #currentlyActiveWinID = self.virtKeyboard._getWinIDSafely_('currentActiveWindow');
            #morseWinID = self.virtKeyboard._getWinIDSafely_('morseWinID');
            #print("Morse win: %s. Curr-active win: %s" % (morseWinID, currentlyActiveWinID))
            #***********
            if not self.virtKeyboard.windowsEqual('morseWinID', 'currentActiveWindow'):
                self.virtKeyboard.saveActiveWindowID('keyboardTarget');
            #***************
            #print("Keyboard target: %s" % self.virtKeyboard._getWinIDSafely_('keyboardTarget'));
            #***************
            self.virtKeyboard.activateWindow(retrievalKey='keyboardTarget');

        elif eventType == QEvent.Leave:
            self.virtKeyboard.activateWindow(retrievalKey='morseWinID');
        #if (eventType == QEvent.MouseMove) or (event == QHoverEvent):
        elif eventType == QEvent.MouseMove:
            if self.constrainCursorInHotZone:
                self.mouseUnconstrainTimer.stop();
                self.handleCursorConstraint(event);
        # Pass this event on to its destination (rather than filtering it):
        return False;

    def moveEvent(self, event):
        '''
        Called when window is repositioned. Need to 
        recompute the cashed global-x positions of 
        the right-side dot button, and the left-side
        dash button.
        @param event: move event
        @type event: QMoveEvent 
        '''
        self.computeInnerButtonEdges();

    def mousePressEvent(self, mouseEvent):
        
        if (mouseEvent.button() != Qt.LeftButton):
            return;
        
        # Re-activate the most recently active X11 window 
        # to ensure the letters are directed to the 
        # proper window, and not this morse window:
        self.virtKeyboard.activateWindow('keyboardTarget');
        if self.cursorInRestZone(mouseEvent.pos()):
            self.morseGenerator.abortCurrentMorseElement();
        
        # Release cursor constraint while mouse button is pressed down.
        if self.constrainCursorInHotZone:    
            self.stopCursorConstraint();
            self.cursorContraintSuspended = True;
            
        # Pause speed timing, if it's running:
        self.speedMeasurer.pauseTiming();

        mouseEvent.accept();

    def mouseReleaseEvent(self, mouseEvent):

        # If right button is the one that was released,
        # re-center the mouse to the crosshair. This is
        # needed with the head mouse tracker to re-calibrate
        # where it thinks the cursor is located:
        if mouseEvent.button() == Qt.RightButton:
            self.morseCursor.setPos(self.centralRestGlobalPos);

        if self.cursorContraintSuspended:
            self.cursorContraintSuspended = False;
            self.startCursorConstraint();
        # Resume speed timing, (if it was paused:
        self.speedMeasurer.resumeTiming();

    def resizeEvent(self, event):
        newMorseWinRect = self.geometry();
        self.cfgParser.set('Appearance', 
                           'winGeometry', 
                           str(newMorseWinRect.x()) 	+ ',' +
                           str(newMorseWinRect.y()) 	+ ',' +
                           str(newMorseWinRect.width()) + ',' +
                           str(newMorseWinRect.height()));
        self.optionsSaveButton();
        # Update cache of button edge and rest area positions:
        self.computeInnerButtonEdges();

    def cursorInRestZone(self, pos):
        # Button geometries are local, so convert the
        # given global position:
        localPos = self.mapFromGlobal(pos);
        
        dotButtonGeo  = self.dotButton.geometry();
        dashButtonGeo = self.dashButton.geometry();
        return localPos.x() > dotButtonGeo.right() and\
               localPos.x() < dashButtonGeo.left() and\
               localPos.y() > dotButtonGeo.top()   and\
               localPos.y() < dotButtonGeo.bottom();
    
    def cursorInButton(self, buttonObj, pos, tolerance=0):
        '''
        Return True if given position is within the given button object.
        An optional positive or negative tolerance is added to the
        button dimensions. This addition allows for caller to compensate
        for cursor drift by 'blurring' the true button edges.
        @param buttonObj: QPushButton or derivative to check.
        @type buttonObj: QPushButton
        @param pos: x/y coordinate to test
        @type pos: QPoint
        @param tolerance: number of pixels the cursor may be outside the button, yet still be reported as inside.
        @type tolerance: int
        '''
        # Button geometries are local, so convert the
        # given global position:
        buttonGeo = buttonObj.geometry();
        globalButtonPos = self.mapToGlobal(QPoint(buttonGeo.x() + tolerance,
                                                  buttonGeo.y() + tolerance));
        globalGeo = QRect(globalButtonPos.x(), globalButtonPos.y(), buttonGeo.width(), buttonGeo.height());
        return globalGeo.contains(pos);
        
    def handleCursorConstraint(self, mouseEvent):
        '''
        Manages constraining the cursor to vertical/horizontal. Caller is
        responsible for checking that cursor constraining is wanted. This
        method assumes so.
        @param mouseEvent: mouse move event that needs to be addressed
        @type mouseEvent: QMouseEvent
        '''
        
        try:
            if self.recentMousePos is None:
                # Very first time: establish a 'previous' mouse cursor position:
                self.recentMousePos = mouseEvent.globalPos();
                self.headTrackerCursorDrift = 0;
                return;
                
            globalPosX = mouseEvent.globalX()
            globalPosY = mouseEvent.globalY()
            globalPos  = QPoint(globalPosX, globalPosY);
            localPos   = mouseEvent.pos();
            
            # If we were already within the dot or dash button
            # before this new mouse move, and the new mouse
            # position is still inside that button, then keep
            # the mouse at the inner edge of the respective button.
            # ('Inner edge' means facing the resting zone):
            oldInDot  = self.cursorInButton(self.dotButton, self.recentMousePos);
            oldInDash = self.cursorInButton(self.dashButton, self.recentMousePos);
            newInDot  = self.cursorInButton(self.dotButton, globalPos, tolerance=1);
            newInDash = self.cursorInButton(self.dashButton, globalPos, tolerance=0);
            
            oldInButton = oldInDot or oldInDash;
            newInButton = newInDot or newInDash;
            
            # Mouse moving within one of the buttons? If
            # so, keep mouse at the button's inner edge
            # (facing the rest zone):
            if newInButton:
                if newInDot:
                    # The '-1' moves the cursor slightly left into
                    # the Dot button, rather than keeping it right on
                    # the edge. This is to avoid the cursor seemingej
                    # To 'bounce' off the right dot button border back
                    # into the dead zone. The pixel is the drop shadow
                    # on the right side of the dot button. The '+12' places
                    # the hand cursor a bit below the crosshair, so that 
                    # color flashes of the crosshair can be seen:
                    self.morseCursor.setPos(self.dotButtonGlobalRight-1, self.centralRestGlobalPos.y() + 12);
                elif newInDash:
                    self.morseCursor.setPos(self.dashButtonGlobalLeft+1, self.centralRestGlobalPos.y() + 12);
                return;
            
            # Only constrain while in rest zone (central empty space), or
            # inside the dot or dash buttons:
            if not (self.cursorInRestZone(globalPos) or newInButton):
                return;
            
            # If cursor moved while we are constraining motion 
            # vertically or horizontally, enforce that constraint now:
            if self.currentMouseDirection is not None:
                if self.currentMouseDirection == Direction.HORIZONTAL:
                    cursorMove = globalPosX - self.recentMousePos.x();
                    correctedGlobalX = self.recentMousePos.x() + int(cursorMove * self.cursorAcceleration);
                    correctedCurPos = QPoint(correctedGlobalX, self.centralRestGlobalPos.y() + 12);
                    self.recentMousePos.setX(correctedGlobalX);
                else:
                    cursorMove = globalPosY - self.recentMousePos.y();
                    correctedGlobalY = self.recentMousePos.y() + int(cursorMove * self.cursorAcceleration);
                    correctedCurPos = QPoint(self.recentMousePos.x(), correctedGlobalPosY);
                    self.recentMousePos.setY(correctedGlobalPosY);
                self.morseCursor.setPos(correctedCurPos);
                return;

            # Not currently constraining mouse move. To init, check which 
            # movement larger compared to the most recent position: x or y:
            # Only constraining horizontally?
            # Constraint is horizontal, even if there is any initial vertical movement.
            if (not self.enableConstrainVertical) or abs(globalPosX - self.recentMousePos.x()) > abs(globalPosY - self.recentMousePos.y()):
                self.currentMouseDirection = Direction.HORIZONTAL;
            else:
                self.currentMouseDirection = Direction.VERTICAL;
            self.recentMousePos = mouseEvent.globalPos();
        finally:
            # Set timer to unconstrain the mouse if it is
            # not moved for a while (interval is set in __init__()).
            # If we are not constraining horizontally and vertically
            # then don't set the timeout:            if self.enableConstrainVertical:
            if self.enableConstrainVertical:
                self.mouseUnconstrainTimer.setInterval(MorseInput.MOUSE_UNCONSTRAIN_TIMEOUT);
                self.mouseUnconstrainTimer.start();
            return

    def unconstrainTheCursor(self):
        # If user is hovering inside the dot or dash button,
        # keep the hor/vert mouse move constraint going, even
        # though the timeout of no mouse movement is done:
        if self.dotButton.underMouse() or self.dashButton.underMouse():
            self.mouseUnconstrainTimer.start();
            return
        self.currentMouseDirection = None;
        self.recentMousePos = None;

    @staticmethod
    def letterCompleteNotification(reason, details=''):
        '''
        Called from MorseGenerator when one letter has
        become available, or when a dwell end-of-letter,
        or dwell end-of-word was detected. Sends a signal
        and returns right away.
        @param reason: indicator whether regular letter, or end of word.
        @type reason: TimeoutReason
        '''
        MorseInputSignals.getSignal('MorseInputSignals.letterDone').emit(reason, details);

    @QtCore.Slot(int,str)
    def deliverInput(self, reason, detail):
        alpha = self.morseGenerator.getAndRemoveAlphaStr()
        if reason == TimeoutReason.END_OF_WORD:
            alpha += ' '; 
            self.outputLetters(alpha);
            # Give very brief indication that word boundary detected:
            self.flashCrosshair(crossHairColor=Crosshairs.YELLOW);
        elif reason == TimeoutReason.END_OF_LETTER:
            self.outputLetters(alpha);
        elif reason == TimeoutReason.BAD_MORSE_INPUT:
            self.statusBar.showMessage("Bad Morse input: '%s'" % detail, 4000); # milliseconds

    def outputLetters(self, lettersToSend):
        if self.outputDevice == OutputType.TYPE:
            for letter in lettersToSend:
                # Write to the local ticker tape:
                self.tickerTapeAppend(letter);
                # Then write to the X11 window in focus:
                if letter == '\b':
                    self.outputBackspace();
                elif letter == '\r':
                    self.outputNewline();
                else:
                    #print(letter);
                    self.virtKeyboard.typeTextToActiveWindow(letter);
        elif self.outputDevice == OutputType.SPEAK:
            print("Speech not yet implemented.");

    def outputBackspace(self):
        self.virtKeyboard.typeControlCharToActiveWindow('BackSpace');
        # Also output to the ticker tape if appropriate:
        self.tickerTapeAppend('\b');
        
    def outputNewline(self):
        self.virtKeyboard.typeControlCharToActiveWindow('Linefeed');
        # Also output to the ticker tape if appropriate:
        self.tickerTapeAppend('\r');

    def tickerTapeSet(self, text):
        self.tickerTapeLineEdit.setText(text);
        
    def tickerTapeClear(self, dummy):
        self.tickerTapeSet('');

    def tickerTapeAppend(self, text):
        if not self.useTickerTape:
            return;
        if text == '\b':
            # The backspace() method on QLineEdit doesn't work.
            # Maybe because we disallow focus on the widget to 
            # avoid people thinking they can edit. So work 
            # around this limitation:
            #self.tickerTapeLineEdit.backspace();
            tickerContent = self.tickerTapeLineEdit.text();
            if len(tickerContent) == 0:
                return;
            self.tickerTapeSet(tickerContent[:-1]);
        elif text == '\r':
            self.tickerTapeSet(self.tickerTapeLineEdit.text() + '\\n');
        else:
            self.tickerTapeSet(self.tickerTapeLineEdit.text() + text);
    
    def showCrossHair(self, crossHairColor):
        if crossHairColor == Crosshairs.CLEAR:
            self.crosshairLabel.setPixmap(self.crosshairPixmapClear);
        elif crossHairColor == Crosshairs.GREEN:
            self.crosshairLabel.setPixmap(self.crosshairPixmapGreen);
        elif crossHairColor == Crosshairs.YELLOW:
            self.crosshairLabel.setPixmap(self.crosshairPixmapYellow);
        elif crossHairColor == Crosshairs.RED:
            self.crosshairLabel.setPixmap(self.crosshairPixmapRed);
        else:
            raise ValueError("Crosshairs are available in clear, green, yellow, and red.")
        self.crosshairLabel.setVisible(True);
       
    def hideCrossHair(self):
        self.crosshairLabel.hide();
       
    def flashCrosshair(self, crossHairColor=Crosshairs.CLEAR):
        if self.flashTimer is not None:
            return;
        self.flashTimer = QTimer(self);
        self.flashTimer.setSingleShot(True);
        self.flashTimer.setInterval(250); # msecs
        self.showCrossHair(crossHairColor);
        self.flashTimer.timeout.connect(partial(self.restoreCrosshair, Crosshairs.CLEAR));
        self.flashTimer.start();
        
    def restoreCrosshair(self, crossHairColor=Crosshairs.CLEAR):
        '''
        Show the crosshair with the given color. Stop the flash timer.
        This is a timeout method. Used by flashCrosshair().
        @param crossHairColor:
        @type crossHairColor:
        '''
        self.flashTimer.stop();
        self.flashTimer = None;
        self.showCrossHair(crossHairColor);
       
    def blinkCrosshair(self, doBlink=True, crossHairColor=Crosshairs.CLEAR):
        if doBlink:
            # If timer already going, don't start a second one:
            if self.blinkTimer is not None:
                return;
            self.blinkTimer = QTimer(self);
            self.blinkTimer.setSingleShot(False);
            self.blinkTimer.setInterval(500); # msecs
            self.crosshairBlinkerOn = True;
            self.blinkTimer.timeout.connect(partial(self.toggleBlink, crossHairColor));
            self.blinkTimer.start();
        else: 
            try:
                self.blinkTimer.stop();
            except:
                pass
            self.blinkTimer = None;
            self.showCrossHair(crossHairColor);

    def toggleBlink(self, crossHairColor):
        '''
        If alternates between crosshair on and off.
        This is a timeout method. Used by blinkCrosshair()
        @param crossHairColor:
        @type crossHairColor:
        '''
        if self.crosshairBlinkerOn:
            self.hideCrossHair();
            self.crosshairBlinkerOn = False;
        else:
            self.showCrossHair(crossHairColor);
            self.crosshairBlinkerOn = True;
                                      
    def powerToggled(self):
        if self.poweredUp:
            self.dotButton.setEnabled(False);
            self.dashButton.setEnabled(False);
            self.eowButton.setEnabled(False);
            self.backspaceButton.setEnabled(False);
            self.poweredUp = False;
        else:
            self.dotButton.setEnabled(True);
            self.dashButton.setEnabled(True);
            self.eowButton.setEnabled(True);
            self.backspaceButton.setEnabled(True);
            self.poweredUp = True;
    
    def exit(self):
        self.cleanup();
        QApplication.quit();

    def closeEvent(self, event):
        self.cleanup();
        QApplication.quit();
        # Bubble event up:
        event.ignore();

    def cleanup(self):
        try:
            self.morserOptionsDialog.close();
            self.morseGenerator.stopMorseGenerator();
        except:
            # Best effort:
            pass

if __name__ == '__main__':

    app = QApplication(sys.argv);
    #QApplication.setStyle(QCleanlooksStyle())
    try:
        morser = MorseInput();
        app.exec_();
        morser.exit();
    finally:
        try:
          fcntl.lockf(MorseInput.morserLockFD, fcntl.LOCK_UN)
        except IOError:
          print ("Could not release Morser lock.")
    sys.exit();
    
