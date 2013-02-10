#!/usr/bin/env python

# To do:
# - Word/letter dwell turn on/off, output type checkbox
# - Speed meter
# - Volume control
# - Somewhere (moveEvent()?_: ensure that no overlap of morse win with active window.
#      If so, show error msg.  
# - Running tooltip with slider values
# - Speed slider: change to range 10-60, and divide by 10 when reading
# - Take out vertical constraint; add option in options menu
# - Get new morse codes to show up in Morse list.
# - Publish package

# Doc:
#   - Abort if mouse click in rest zone.
#   - Left click to suspend beeping and cursor contraint
#   - Prefs in $HOME/.morser/morser.cfg
#   - Cheat sheet (Menu)
#   - Options window
#
# Needed PYTHONPATH:
#   /opt/ros/fuerte/lib/python2.7/dist-packages:/home/paepcke/fuerte/stacks/robhum_ui_utils:/home/paepcke/fuerte/stacks/robhum_ui_utils/gesture_buttons/src:/opt/ros/fuerte/stacks/python_qt_binding/src:/home/paepcke/fuerte/stacks/robhum_ui_utils/qt_comm_channel/src:/home/paepcke/fuerte/stacks/robhum_ui_utils/qt_dialog_service/src:/home/paepcke/fuerte/stacks/robhum_ui_utils/virtual_keyboard/src:

# Dash/Dot blue value: 35,60,149

import sys
import os
import re
import ConfigParser
from functools import partial

from gesture_buttons.gesture_button import GestureButton
from gesture_buttons.gesture_button import FlickDirection

from qt_comm_channel.commChannel import CommChannel
from qt_dialog_service.qt_dialog_service import DialogService

from morseToneGeneration import MorseGenerator
from morseToneGeneration import Morse
from morseToneGeneration import TimeoutReason

from morseCheatSheet import MorseCheatSheet;

from virtual_keyboard.virtual_keyboard import VirtualKeyboard

from python_qt_binding import loadUi;
from python_qt_binding import QtGui;
from python_qt_binding import QtCore;
#from word_completion.word_collection import WordCollection;
from QtGui import QApplication, QMainWindow, QMessageBox, QWidget, QCursor, QHoverEvent, QColor, QIcon;
from QtGui import QMenuBar, QToolTip, QLabel, QPixmap;
from QtCore import QPoint, Qt, QTimer, QEvent, Signal, QCoreApplication, QRect; 

# Dot/Dash RGB: 0,179,240

class OutputType:
    TYPE  = 0
    SPEAK = 1

class Direction:
    HORIZONTAL = 0
    VERTICAL   = 1

class MorseInputSignals(CommChannel):
    letterDone = Signal(int,str);

class MorseInput(QMainWindow):
    '''
    Manages all UI interactions with the Morse code generation.
    '''
    
    MORSE_BUTTON_WIDTH = 100; #px
    MORSE_BUTTON_HEIGHT = 100; #px
    
    SUPPORT_BUTTON_WIDTHS = 80; #px: The maximum Space and Backspace button widths.
    SUPPORT_BUTTON_HEIGHTS = 80; #px: The maximum Space and Backspace button heights.
    
    MOUSE_UNCONSTRAIN_TIMEOUT = 300; # msec
    
    def __init__(self):
        super(MorseInput,self).__init__();

        # Disallow focus acquisition for the morse window.
        # Needed to prevent preserve focus on window that
        # is supposed to receive the clear text of the 
        # morse:
        self.setFocusPolicy(Qt.NoFocus);

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
        
        self.connectWidgets();
        self.cursorEnteredOnce = False;
        
        # Set cursor to hand icon while inside Morser:
        self.morseCursor = QCursor(Qt.OpenHandCursor);
        QApplication.setOverrideCursor(self.morseCursor);
        #QApplication.restoreOverrideCursor()
        
        # Init capability of constraining cursor to
        # move only virtically and horizontally:
        self.initCursorConstrainer();
        
        # Styling:
        self.createColors();
        self.setStyleSheet("QWidget{background-color: %s}" % self.lightBlueColor.name());

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
        iconDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'icons')
        self.dotButton.setIcon(QIcon(os.path.join(iconDir, 'dot.png'))); 
        self.dotButton.setText("");
        # Don't have button assume the pressed-down color when 
        # clicked:
        self.dotButton.setFocusPolicy(Qt.NoFocus);
        self.dotButton.setMinimumHeight(MorseInput.MORSE_BUTTON_HEIGHT);
        self.dotButton.setMinimumWidth(MorseInput.MORSE_BUTTON_WIDTH);
        self.dotAndDashHLayout.addWidget(self.dotButton);
                                                
        self.dotAndDashHLayout.addStretch();
        
        # Crosshair:
        self.crosshairLabel = QLabel();
        self.crosshairLabel.setPixmap(QPixmap(os.path.join(iconDir, 'crosshairEmpty.png')));
        self.crosshairLabel.setText("");
        self.dotAndDashHLayout.addWidget(self.crosshairLabel);
        
        self.dotAndDashHLayout.addStretch();
        
        self.dashButton = GestureButton('dash');
        self.dashButton.setIcon(QIcon(os.path.join(iconDir, 'dash.png')));
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
        
    def installMenuBar(self):
        exitAction = QtGui.QAction(QtGui.QIcon('exit.png'), '&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(self.close)
        
        raiseOptionsDialogAction = QtGui.QAction(QtGui.QIcon('preferences-desktop-accessibility.png'), '&Options', self)
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
        
        CommChannel.getSignal('GestureSignals.buttonEnteredSig').connect(self.buttonEntered);
        CommChannel.getSignal('GestureSignals.buttonExitedSig').connect(self.buttonExited);
        CommChannel.getSignal('MorseInputSignals.letterDone').connect(self.deliverInput);
    
        self.morserOptionsDialog.cursorConstraintCheckBox.stateChanged.connect(partial(self.checkboxStateChanged,
                                                                                       self.morserOptionsDialog.cursorConstraintCheckBox));
        self.morserOptionsDialog.letterStopSegmentationCheckBox.stateChanged.connect(partial(self.checkboxStateChanged,
                                                                                             self.morserOptionsDialog.letterStopSegmentationCheckBox));
        self.morserOptionsDialog.wordStopSegmentationCheckBox.stateChanged.connect(partial(self.checkboxStateChanged,
                                                                                           self.morserOptionsDialog.wordStopSegmentationCheckBox));
        self.morserOptionsDialog.typeOutputRadioButton.toggled.connect(partial(self.checkboxStateChanged,
                                                                               self.morserOptionsDialog.typeOutputRadioButton));
        self.morserOptionsDialog.speechOutputRadioButton.toggled.connect(partial(self.checkboxStateChanged,
                                                                                 self.morserOptionsDialog.speechOutputRadioButton));

        self.morserOptionsDialog.keySpeedSlider.valueChanged.connect(partial(self.sliderStateChanged,
                                                                             self.morserOptionsDialog.keySpeedSlider));
        self.morserOptionsDialog.interLetterDelaySlider.valueChanged.connect(partial(self.sliderStateChanged,
                                                                                     self.morserOptionsDialog.interLetterDelaySlider));
        self.morserOptionsDialog.interWordDelaySlider.valueChanged.connect(partial(self.sliderStateChanged,
                                                                                   self.morserOptionsDialog.interWordDelaySlider));

        self.morserOptionsDialog.savePushButton.clicked.connect(self.optionsSaveButton);
        self.morserOptionsDialog.cancelPushButton.clicked.connect(self.optionsCancelButton);
        
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
                    'interLetterDwellDelay'    : str(self.morseGenerator.getInterLetterTime()),
                    'interWordDwellDelay'      : str(self.morseGenerator.getInterWordTime()),
                    'winGeometry'              : '100,100,350,350',
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
        
        self.morseGenerator.setInterLetterDelay(self.cfgParser.getfloat('Morse generation', 'interLetterDwellDelay'));
        self.morseGenerator.setInterWordDelay(self.cfgParser.getfloat('Morse generation', 'interWordDwellDelay'));
        self.morseGenerator.setSpeed(self.cfgParser.getfloat('Morse generation', 'keySpeed'));
        
        self.constrainCursorInHotZone = self.cfgParser.getboolean('Morse generation', 'constrainCursorInHotZone');
        self.outputDevice = self.cfgParser.getint('Output', 'outputDevice');
        self.letterDwellSegmentation = self.cfgParser.getboolean('Morse generation', 'letterDwellSegmentation');
        self.letterDwellSegmentation = self.cfgParser.getboolean('Morse generation', 'wordDwellSegmentation');

        # Make the options dialog reflect the options we just established:
        self.initOptionsDialogFromOptions();

    def initOptionsDialogFromOptions(self):
        self.morserOptionsDialog.cursorConstraintCheckBox.setChecked(self.cfgParser.getboolean('Morse generation', 'constrainCursorInHotZone'));
        self.morserOptionsDialog.letterStopSegmentationCheckBox.setChecked(self.cfgParser.getboolean('Morse generation', 'letterDwellSegmentation'));
        self.morserOptionsDialog.wordStopSegmentationCheckBox.setChecked(self.cfgParser.getboolean('Morse generation', 'wordDwellSegmentation'));
        self.morserOptionsDialog.typeOutputRadioButton.setChecked(self.cfgParser.getint('Output', 'outputDevice')==OutputType.TYPE);
        self.morserOptionsDialog.speechOutputRadioButton.setChecked(self.cfgParser.getint('Output', 'outputDevice')==OutputType.SPEAK);
        self.morserOptionsDialog.keySpeedSlider.setValue(self.cfgParser.getfloat('Morse generation', 'keySpeed'));
        interLetterSecs = self.cfgParser.getfloat('Morse generation', 'interLetterDwellDelay');
        self.morserOptionsDialog.interLetterDelaySlider.setValue(int(interLetterSecs*1000.)); # inter-letter dwell is in msecs
        interWordSecs = self.cfgParser.getfloat('Morse generation', 'interWordDwellDelay');
        self.morserOptionsDialog.interWordDelaySlider.setValue(int(interWordSecs*1000.));     # inter-word dwell is in msecs
        
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
        elif checkbox == self.morserOptionsDialog.letterStopSegmentationCheckBox:
            self.cfgParser.set('Morse generation', 'letterDwellSegmentation', str(checkboxNowChecked)); #********** Checked state is 2? Use isChecked
            #**************
            pass
            #**************
        elif checkbox == self.morserOptionsDialog.wordStopSegmentationCheckBox:
            self.cfgParser.set('Morse generation', 'wordDwellSegmentation', str(checkboxNowChecked));
            #**************
            pass
            #**************
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
        if slider == self.morserOptionsDialog.keySpeedSlider:
            self.cfgParser.set('Morse generation', 'keySpeed', str(newValue));
            self.morseGenerator.setSpeed(newValue);
        elif  slider == self.morserOptionsDialog.interLetterDelaySlider:
            valInSecs = newValue/1000.;
            self.cfgParser.set('Morse generation', 'interLetterDwellDelay', str(valInSecs));
            self.morseGenerator.setInterLetterDelay(valInSecs);
        elif  slider == self.morserOptionsDialog.interWordDelaySlider:
            valInSecs = newValue/1000.;
            self.cfgParser.set('Morse generation', 'interWordDwellDelay', str(valInSecs));
            self.morseGenerator.setInterWordDelay(valInSecs);
        
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
        # Re-activate the most recently active X11 window
        # to ensure the letters are directed to the 
        # proper window, and not this morse window:
        self.virtKeyboard.activateWindow('keyboardTarget');
        if self.cursorInRestZone(mouseEvent.pos()):
            self.morseGenerator.abortCurrentMorseElement();
        
        # Release cursor constraint when mouse button is pressed down.
        if self.constrainCursorInHotZone:    
            self.stopCursorConstraint();
            self.cursorContraintSuspended = True;

        mouseEvent.accept();

    def mouseReleaseEvent(self, event):
        if self.cursorContraintSuspended:
            self.cursorContraintSuspended = False;
            self.startCursorConstraint();

    def resizeEvent(self, event):
        newMorseWinRect = self.geometry();
        self.cfgParser.set('Appearance', 
                           'winGeometry', 
                           str(newMorseWinRect.x()) 	+ ',' +
                           str(newMorseWinRect.y()) 	+ ',' +
                           str(newMorseWinRect.width()) + ',' +
                           str(newMorseWinRect.height()));
        self.optionsSaveButton();

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
    
    def cursorInButton(self, buttonObj, pos):
        '''
        Return True if given position is within the given button object.
        @param buttonObj: QPushButton or derivative to check.
        @type buttonObj: QPushButton
        @param pos: x/y coordinate to test
        @type pos: QPoint
        '''
        # Button geometries are local, so convert the
        # given global position:
        buttonGeo = buttonObj.geometry();
        globalButtonPos = self.mapToGlobal(QPoint(buttonGeo.x(),
                                                  buttonGeo.y()));
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
            newInDot  = self.cursorInButton(self.dotButton, globalPos);
            newInDash = self.cursorInButton(self.dashButton, globalPos);
            
            oldInButton = oldInDot or oldInDash;
            newInButton = newInDot or newInDash;
            
            # Mouse moving within one of the buttons? If
            # so, keep mouse at the button's inner edge
            # (facing the rest zone):
            if oldInButton and newInButton:
                if newInDot:
                    # The '-1' moves the cursor slightly left into
                    # the Dot button, rather than keeping it right on
                    # the edge. This is to avoid the cursor seemingej
                    # To 'bounce' off the right dot button border back
                    # into the dead zone. The pixel is the drop shadow
                    # on the right side of the dot button.
                    self.morseCursor.setPos(self.dotButtonGlobalRight-1, self.centralRestGlobalPos.y());
                elif newInDash:
                    self.morseCursor.setPos(self.dashButtonGlobalLeft, self.centralRestGlobalPos.y());
                return;
            
            # Only constrain while in rest zone (central empty space), or
            # inside the dot or dash buttons:
            if not (self.cursorInRestZone(globalPos) or newInButton):
                return;
            
            # If cursor moved while we are constraining motion 
            # vertically or horizontally, enforce that constraint now:
            if self.currentMouseDirection is not None:
                if self.currentMouseDirection == Direction.HORIZONTAL:
                    correctedCurPos = QPoint(globalPosX, self.centralRestGlobalPos.y());
                    self.recentMousePos.setX(globalPosX);
                else:
                    correctedCurPos = QPoint(self.recentMousePos.x(), globalPosY);
                    self.recentMousePos.setY(globalPosY);
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
        elif reason == TimeoutReason.END_OF_LETTER:
            self.outputLetters(alpha);
        elif reason == TimeoutReason.BAD_MORSE_INPUT:
            self.statusBar.showMessage("Bad Morse input: '%s'" % detail, 4000); # milliseconds

    def outputLetters(self, lettersToSend):
        if self.outputDevice == OutputType.TYPE:
            for letter in lettersToSend:
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
        
    def outputNewline(self):
        self.virtKeyboard.typeControlCharToActiveWindow('Linefeed');

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
    morser = MorseInput();
    app.exec_();
    morser.exit();
    sys.exit();
    
