#!/usr/bin/env python

# To do:
# - Save settings, like window size in $HOME/.morse  
# - Saving prefs
# - Hook up virtual keyboard
# - Catch window resize, and save it
# - Word/letter dwell turn on/off, output type checkbox
# - Speed meter
# - Backspace and abort
# - Morse table
# - Status bar with running text??
# - Volume control
# - Running tooltip with slider values
# - Publish package


import sys
import os
import ConfigParser
from functools import partial

from gesture_buttons.gesture_button import GestureButton
from gesture_buttons.gesture_button import FlickDirection

from qt_comm_channel.commChannel import CommChannel
from qt_dialog_service.qt_dialog_service import DialogService

from morseToneGeneration import MorseGenerator
from morseToneGeneration import Morse
from morseToneGeneration import TimeoutReason

from virtual_keyboard.virtual_keyboard import VirtualKeyboard

from python_qt_binding import loadUi;
from python_qt_binding import QtGui;
from python_qt_binding import QtCore;
#from word_completion.word_collection import WordCollection;
from QtGui import QApplication, QMainWindow, QMessageBox, QWidget, QCursor, QHoverEvent, QColor, QIcon;
from QtGui import QMenuBar;
from QtCore import QPoint, Qt, QTimer, QEvent, Signal, QCoreApplication; 

# Dot/Dash RGB: 0,179,240

class OutputType:
    TYPE  = 0
    SPEAK = 1

class Direction:
    HORIZONTAL = 0
    VERTICAL   = 1

class MorseInputSignals(CommChannel):
    letterDone = Signal(int);

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
        
        relPathQtCreatorFileMainWin = "qt_files/morseInput/morseInput.ui";
        qtCreatorXMLFilePath = self.findFile(relPathQtCreatorFileMainWin);
        if qtCreatorXMLFilePath is None:
            raise ValueError("Can't find QtCreator user interface file %s" % relPathQtCreatorFileMainWin);
        # Make QtCreator generated UI a child if this instance:
        loadUi(qtCreatorXMLFilePath, self);
        self.setWindowTitle("Morser: Semi-automatic Morse code input");
        
        relPathQtCreatorFileOptionsDialog = "qt_files/morserOptions/morseroptions.ui";
        qtCreatorXMLFilePath = self.findFile(relPathQtCreatorFileOptionsDialog);
        if qtCreatorXMLFilePath is None:
            raise ValueError("Can't find QtCreator user interface file %s" % relPathQtCreatorFileOptionsDialog);
        # Make QtCreator generated UI a child if this instance:
        self.morserOptionsDialog = loadUi(qtCreatorXMLFilePath);
        
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
        
        self.connectWidgets();
        
        # Set cursor to hand icon while inside Morser:
        self.morseCursor = QCursor(Qt.OpenHandCursor);
        QApplication.setOverrideCursor(self.morseCursor);
        #QApplication.restoreOverrideCursor()
        
        # Init capability of constraining cursor to
        # move only virtically and horizontally:
        self.initCursorContrainer();
        
        # Styling:
        self.createColors();
        self.setStyleSheet("QWidget{background-color: %s}" % self.lightBlueColor.name());

        self.show();

        # Monitor mouse, so that we can constrain mouse movement to
        # vertical and horizontal (must be set after the affected
        # widget(s) are visible):
        #self.setMouseTracking(True)
        self.centralWidget.installEventFilter(self);
        self.centralWidget.setMouseTracking(True)

    def initCursorContrainer(self):
        self.recentMousePos = None;
        self.currentMouseDirection = None;
        # Timer that frees the cursor from
        # vertical/horizontal constraint every few
        # milliseconds, unless mouse keeps moving:
        self.mouseUnconstrainTimer = QTimer();
        self.mouseUnconstrainTimer.setInterval(MorseInput.MOUSE_UNCONSTRAIN_TIMEOUT);
        self.mouseUnconstrainTimer.setSingleShot(True);
        self.mouseUnconstrainTimer.timeout.connect(self.unconstrainTheCursor);

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
        # Don't have button assume the pressed-down color when 
        # clicked:
        self.eowButton.setFocusPolicy(Qt.NoFocus);
        self.eowButton.setMaximumWidth(MorseInput.SUPPORT_BUTTON_WIDTHS)        
        self.eowButton.setMinimumHeight(MorseInput.SUPPORT_BUTTON_HEIGHTS)        
        self.endOfWordButtonHLayout.addWidget(self.eowButton);

        self.backspaceButton = GestureButton('Backspace');
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
  
        fileMenu = self.menuBar.addMenu('&File')
        fileMenu.addAction(exitAction)
        
        editMenu = self.menuBar.addMenu('&Edit')
        editMenu.addAction(raiseOptionsDialogAction)      
        
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
    
    def setOptions(self):
        
        self.optionsDefaultDict = {
                    'outputDevice'             : str(OutputType.TYPE),
                    'letterDwellSegmentation'  : str(True),
                    'wordDwellSegmentation'    : str(True),
                    'constrainCursorInHotZone' : str(False),
                    'keySpeed'                 : str(1.7),
                    'interLetterDwellDelay'    : str(self.morseGenerator.getInterLetterTime()),
                    'interWordDwellDelay'      : str(self.morseGenerator.getInterWordTime()),
                    }

        self.cfgParser = ConfigParser.SafeConfigParser(self.optionsDefaultDict);
        self.cfgParser.add_section('Morse generation');
        self.cfgParser.add_section('Output');
        self.cfgParser.add_section('Appearance');
        self.cfgParser.read(self.optionsFilePath);
        
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
        self.morserOptionsDialog.speechOutputRadioButton.setChecked(not self.cfgParser.getint('Output', 'outputDevice'));
        self.morserOptionsDialog.keySpeedSlider.setValue(self.cfgParser.getfloat('Morse generation', 'keySpeed'));
        interLetterSecs = self.cfgParser.getfloat('Morse generation', 'interLetterDwellDelay');
        self.morserOptionsDialog.interLetterDelaySlider.setValue(int(interLetterSecs*1000.)); # inter-letter dwell is in msecs
        interWordSecs = self.cfgParser.getfloat('Morse generation', 'interWordDwellDelay');
        self.morserOptionsDialog.interWordDelaySlider.setValue(int(interWordSecs*1000.));     # inter-word dwell is in msecs
        
    def checkboxStateChanged(self, checkbox, newState):
        '''
        Called when any of the option dialog's checkboxes change:
        @param checkbox:
        @type checkbox:
        @param newState:
        @type newState:
        '''
        if checkbox == self.morserOptionsDialog.cursorConstraintCheckBox:
            self.cfgParser.set('Morse generation','constrainCursorInHotZone',str(newState));
            self.constrainCursorInHotZone = newState; 
        elif checkbox == self.morserOptionsDialog.letterStopSegmentationCheckBox:
            self.cfgParser.set('Morse generation', 'letterDwellSegmentation', str(newState));
            #**************
            pass
            #**************
        elif checkbox == self.morserOptionsDialog.wordStopSegmentationCheckBox:
            self.cfgParser.set('Morse generation', 'wordDwellSegmentation', str(newState));
            #**************
            pass
            #**************
        elif checkbox == self.morserOptionsDialog.typeOutputRadioButton:
            self.cfgParser.set('Morse generation', 'outputDevice', str(newState));
            #**************
            pass
            #**************
        else:
            raise ValueError('Unknown checkbox: %s' % str(checkbox));


    def sliderStateChanged(self, slider, newValue):
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
            self.outputLetters('BackSpace');
        
    def buttonExited(self, buttonObj):
        if buttonObj == self.dotButton:
            self.morseGenerator.stopMorseSeq();
        elif buttonObj == self.dashButton:
            self.morseGenerator.stopMorseSeq();

    def eventFilter(self, target, event):
        eventType = event.type();
        if eventType == QEvent.Enter:
            # Remember X11 window that is active as we
            # enter the application window, but don't remember
            # this morse code window, if that was active:
            morseWinID = self.virtKeyboard.windowUnderMouseCursor(); 
            formerlyActiveWinID = self.virtKeyboard.getRecentWindow(); 
            #***********
            print("Curr win: %s. Prev win: %s" % (morseWinID, formerlyActiveWinID))
            #***********
            if morseWinID != formerlyActiveWinID:
                self.virtKeyboard.saveActiveWindowID();
        elif eventType == QEvent.Leave:
            self.virtKeyboard.activateWindowUnderMouse();
        #if (eventType == QEvent.MouseMove) or (event == QHoverEvent):
        elif eventType == QEvent.MouseMove:
            if self.constrainCursorInHotZone:
                self.mouseUnconstrainTimer.stop();
                self.handleCursorConstraint(event);
        # Pass this event on to its destination (rather than filtering it):
        return False;

    def mousePressEvent(self, mouseEvent):
        # Re-activate the most recently active X11 window
        # to ensure the letters are directed to the 
        # proper window, and not this morse window:
        self.virtKeyboard.activateWindow();
        mouseEvent.accept();

        
    def handleCursorConstraint(self, mouseEvent):
        
        try:
            if self.recentMousePos is None:
                # Very first time: establish a 'previous' mouse cursor position:
                self.recentMousePos = mouseEvent.globalPos();
                return;
                
            globalPosX = mouseEvent.globalX()
            globalPosY = mouseEvent.globalY()
            
            # If cursor moved while we are constraining motion 
            # vertically or horizontally, enforce that constraint now:
            if self.currentMouseDirection is not None:
                if self.currentMouseDirection == Direction.HORIZONTAL:
                    correctedCurPos = QPoint(globalPosX, self.recentMousePos.y());
                    self.recentMousePos.setX(globalPosX);
                else:
                    correctedCurPos = QPoint(self.recentMousePos.x(), globalPosY);
                    self.recentMousePos.setY(globalPosY);
                self.morseCursor.setPos(correctedCurPos);
                return;

            # Not currently constraining mouse move. Check which 
            # movement larger compared to the most recent position: x or y:
            if abs(globalPosX - self.recentMousePos.x()) > abs(globalPosY - self.recentMousePos.y()):
                self.currentMouseDirection = Direction.HORIZONTAL;
            else:
                self.currentMouseDirection = Direction.VERTICAL;
            self.recentMousePos = mouseEvent.globalPos();
        finally:
            # Set timer to unconstrain the mouse if it is
            # not moved for a while (interval is set in __init__()):
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
    def letterCompleteNotification(reason):
        '''
        Called from MorseGenerator when one letter has
        become available, or when a dwell end-of-letter,
        or dwell end-of-word was detected. Sends a signal
        and returns right away.
        @param reason: indicator whether regular letter, or end of word.
        @type reason: TimeoutReason
        '''
        MorseInputSignals.getSignal('MorseInputSignals.letterDone').emit(reason);

    @QtCore.Slot(int)
    def deliverInput(self, reason):
        alpha = self.morseGenerator.getAndRemoveAlphaStr()
        if reason == TimeoutReason.END_OF_WORD:
            alpha += ' '; 
        self.outputLetters(alpha);

    def outputLetters(self, letters):
        if self.outputDevice == OutputType.TYPE:
            #print(letters);
            self.virtKeyboard.typeToActiveWindow(letters);
        elif self.outputDevice == OutputType.SPEAK:
            print("Speech not yet implemented.");

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
    
