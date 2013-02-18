#!/usr/bin/env python

# TODO:
#   - Fast visit interpreted as flick
#   - Widen word list scroll bar
#   - Button to copy output to clipboard
#   - Make cnt-c work
#   - Hook up with text-to-speech
#   - Help panel

import sys;
import os;
sys.path.append(os.path.join(os.path.dirname(__file__), "../../lib"));
from ternarytree import TernarySearchTree;

import re;
from functools import partial;

from utilities import Utilities;

from gesture_button import GestureButton;
from gesture_button import FlickDirection;
from gesture_button import CommChannel;

from word_completion.word_collection import TelPadEncodedWordCollection;

import QtBindingHelper;
from QtCore import QMutex, QMutexLocker, Qt, QTimer, QRect, Slot
from QtGui import QApplication, QColor, QDialog, QMainWindow, QMessageBox, QPixmap, QWidget, QIcon
from QtGui import QButtonGroup

WORD_LIST_SCROLLBAR_WIDTH = 30; # pixels


NUM_LETTER_BUTTONS = 8;

class UseFrequency:
    '''
    Mapping from loose word frequency usage terminology
    to concrete frequency rank. A word's frequency being
    ranked with the number r means that this word is used
    as frequently the the rth most frequently used word
    in out dictionary.
     '''
    RARELY = 4000;
    OCCASIONALLY = 100;
    CONSTANTLY = 0;

class HistoryShiftDir:
    OLDER   = 0;
    YOUNGER = 1;

class StyleID:
    RELEASED = 0;
    PRESSED  = 1;

class ButtonEditMode:
    DIALPAD = 0;
    LETTER_INPUT = 1;

class ButtonID:
    ABC  = 0;
    DEF  = 1;
    GHI  = 2;
    JKL  = 3;
    MNO  = 4;
    PQR  = 5;
    STUV = 6;
    WXYZ = 7;

    legalValues = range(8);
    strRepr = {ABC:'ABC',     
               DEF:'DEF',
               GHI:'GHI',
               JKL:'JKL',
               MNO:'MNO',
               PQR:'PQR',
               STUV:'STUV',
               WXYZ:'WXYZ'}; 
    
    strToID = {'ABC' : ABC,     
               'DEF' : DEF,
               'GHI' : GHI,
               'JKL' : JKL,
               'MNO' : MNO,
               'PQR' : PQR,
               'STUV': STUV,
               'WXYZ': WXYZ}; 
    
    idRepr  = {ABC:'|abc|',     
               DEF:'|def|',
               GHI:'|ghi|',
               JKL:'|jkl|',
               MNO:'|mno|',
               PQR:'|pqr|',
               STUV:'|stuv|',
               WXYZ:'|wxyz|'}; 
    
    @staticmethod
    def toString(buttonID):
        try:
            return ButtonID.strRepr[buttonID];
        except KeyError:
            raise ValueError("Unknown button ID '%s'." % buttonID);

    @staticmethod
    def toButtonID(buttonLabel):
        return ButtonID.strToID[buttonLabel];
    
    @staticmethod
    def idToStringable(buttonID):
        try:
            return ButtonID.idRepr[buttonID];
        except KeyError:
            raise ValueError("Unknown button ID '%s'." % buttonID);

#***class JBoard(QMainWindow):
class JBoard(QWidget):

    # Ids for checkboxes in the 'add-new-word' dialog:
    RARELY_BUTTON_ID = 0;
    OCCCASIONALLY_BUTTON_ID = 1;
    CONSTANTLY_BUTTON_ID = 2;
    
    def __init__(self):
        super(JBoard, self).__init__();
        
        self.setWindowTitle("JBoard");        
        
        # Find QtCreator's XML file in the PYTHONPATH:
        currDir = os.path.realpath(__file__);
        relPathQtCreatorFile = "jboard_ui/jboard_ui.ui";
        qtCreatorXMLFilePath = Utilities.findFile(relPathQtCreatorFile);
        if qtCreatorXMLFilePath is None:
            raise ValueError("Can't find QtCreator user interface file %s" % relPathQtCreatorFile);
        # Make QtCreator generated UI a child if this instance:
        QtBindingHelper.loadUi(qtCreatorXMLFilePath, self);
        self.letterWidgets = [self.ABCWidget, self.DEFWidget, self.GHIWidget, self.JKLWidget,
                              self.MNOWidget, self.PQRWidget, self.STUVWidget, self.WXYZWidget];
                              
        self.createColors();
                              
        # Populate all empty letter board button widgets with
        # GestureButton instances:
        self.populateGestureButtons();
        
        self.preparePixmaps();

	# Increase the width of the word area scrollbar:
	self.wordList.verticalScrollBar().setFixedWidth(WORD_LIST_SCROLLBAR_WIDTH) # pixels

        # Where we accumulate evolving words in encoded form
        # (see symbolToEnc dict in word_collection.py):
        self.encEvolvingWord = ""; 
        self.currButtonUsedForFlick = False;
        self.wordCollection = TelPadEncodedWordCollection();
          
        self.commChannel = CommChannel.getInstance();
        # Timer to ensure that a crossed-out button doesn't 
        # stay crossed out forever:
        self.crossOutTimer =  QTimer();
        self.crossOutTimer.setSingleShot(True);
        self.crossedOutButtons = [];
        
        # Popup dialog for adding new words to dictionary:
        self.initNewDictWordDialog();
        
        # Gesture buttons all in Dialpad (speed-write mode):
        self.buttonEditMode = ButtonEditMode.DIALPAD;

        # Disable selecting for the remaining-words panel:
	self.wordList.setFocusPolicy(Qt.NoFocus);

        # Mutex for keeping very fast flicking gestures
        # out of each others' hair:
        self.mutex = QMutex();
        
        # The system clipboard for copy:
        self.clipboard = QApplication.clipboard();
        
        # Speak-button not working yet:
        self.speakButton.setDisabled(True);
        
        self.connectWidgets();
        #self.setGeometry(500, 500, 300, 100);
        self.show();


    # -------------------------------------- UI Setup Methods -------------------------
    
    def initNewDictWordDialog(self):
        
        # Find QtCreator's XML file in the PYTHONPATH:
        currDir = os.path.realpath(__file__);
        relPathQtCreatorFile = "jboard_ui/addWord_dialog/addWordDialog.ui";
        qtCreatorXMLFilePath = Utilities.findFile(relPathQtCreatorFile);
        if qtCreatorXMLFilePath is None:
            raise ValueError("Can't find QtCreator user interface file for 'new dictionary word' dialog file %s" % relPathQtCreatorFile);
        #****self.addWordDialog = QWidget();
	self.addWordDialog = QDialog();
        QtBindingHelper.loadUi(qtCreatorXMLFilePath, self.addWordDialog);
        # Assign int IDs to the frequency checkboxes:
        rareButton = self.addWordDialog.useRarelyButton;
        occasionButton = self.addWordDialog.useOccasionallyButton;  
        constantButton = self.addWordDialog.useConstantlyButton; 
        self.addWordButtonGroup = QButtonGroup();
	self.addWordButtonGroup.addButton(rareButton, JBoard.RARELY_BUTTON_ID);
	self.addWordButtonGroup.addButton(occasionButton, JBoard.OCCCASIONALLY_BUTTON_ID);
	self.addWordButtonGroup.addButton(constantButton, JBoard.CONSTANTLY_BUTTON_ID);	
        self.addWordDialog.hide();
            
    def populateGestureButtons(self):
        '''
        Creates GestureButton instances for each telephone pad button.
        Creates convenience data structures:
        <ul>
          <li><code>letterButtons</code> is an array of all GestureButton instances</li>
          <li><code>letterButtonToID</code> maps GestureButton instances to the buttons'
              IDs, which happen to be their label strings ('ABC', 'DEF', etc.).</li>
          <li><code>idToLetterButton</code> is the reverse: a dictionary mapping button labels,
              like "ABC" to the corresponding button instance.</li>
        </ul>
        This function also sets style sheets for the all GestureButton instances.
        '''
        # Sorted array of all letter button objs:
        self.letterButtons = [];
        # Letter button object to button label: "ABC", "DEF", etc:
        self.letterButtonToID = {};
        self.idToLetterButton = {};
        for buttonID in ButtonID.legalValues:
            self.letterButtons.append(GestureButton(ButtonID.toString(buttonID), 
                                                    parent=self.letterWidgets[buttonID]));
            self.letterButtonToID[self.letterButtons[-1]] = self.letterButtons[-1].text(); 
            self.letterButtons[-1].setGeometry(0,0,200,100);
            self.idToLetterButton[self.letterButtons[-1].text()] = self.letterButtons[-1]; 
        for buttonObj in self.letterButtons:
            self.setGestureButtonStyle(buttonObj, StyleID.RELEASED);
            #****buttonObj.setFocusPolicy(Qt.FocusPolicy.NoFocus);
	    buttonObj.setFocusPolicy(Qt.NoFocus);
            
                        
    def connectWidgets(self):
        self.commChannel.flickSig.connect(self.handleButtonFlicks);
        self.commChannel.buttonEnteredSig.connect(self.handleButtonEntered);
        self.commChannel.buttonExitedSig.connect(self.handleButtonExited);
        self.eraseWordButton.clicked.connect(self.handleEraseWordButton);
        self.addWordButton.clicked.connect(self.handleSaveWordButton);
        self.crossOutTimer.timeout.connect(self.handleCrossoutTimeout);
        # Number pad:
        for button in set([self.numPad1, self.numPad2, self.numPad3, self.numPad4, self.numPad5, 
                          self.numPad6, self.numPad7, self.numPad8, self.numPad9, self.numPad0]):
            button.clicked.connect(partial(self.handleNumPad, button));
        
        # Special characters:
        for button in set([self.commaButton, self.colonButton, self.questionButton, self.atButton, self.leftParenButton, 
                          self.periodButton, self.backspaceButton, self.slashButton, self.spaceButton, self.rightParenButton]):
            button.clicked.connect(partial(self.handleSpecialChars, button));
            
        # Gesture button clicks (switching between dialpad and letter mode:
        for buttonObj in self.letterButtons:
            buttonObj.clicked.connect(partial(self.handleGestureButtonClick, buttonObj));
        
        # Add word dialog box capitalization checkbox state changed:    
        self.addWordDialog.capitalizeCheckbox.stateChanged.connect(self.handleAddDictWordCapitalizeStateChanged);
        # Add word dialog box OK or Cancel botton clicked:
        self.addWordDialog.cancelButton.clicked.connect(partial(self.handleAddDictWordOK_Cancel, self.addWordDialog.cancelButton));
        self.addWordDialog.addWordButton.clicked.connect(partial(self.handleAddDictWordOK_Cancel, self.addWordDialog.addWordButton));
        
        # CopyAll button:
        self.copyButton.clicked.connect(self.handleCopyAll);
        
    def preparePixmaps(self):
        
        imgDirPath = os.path.join(os.path.dirname(__file__), "img/");
        self.buttonBackGroundPixmaps = [];
        buttonWidth = self.letterButtons[0].width();
        buttonHeight = self.letterButtons[0].height();
        for backgroundImgNum in range(NUM_LETTER_BUTTONS):
            buttonPixmap = QPixmap();
            #****imgPath = os.path.join(imgDirPath, "jboardButtonBackgroundTrail" + str(backgroundImgNum + 1) + ".png");
            imgPath = os.path.join(imgDirPath, "jboardButtonBackgroundsSmall" + str(backgroundImgNum + 1) + ".png");
            if not buttonPixmap.load(imgPath):
                raise IOError("Could not find button background icon at " + imgPath);
            #scaledPixmap = buttonPixmap.scaled(buttonWidth, buttonHeight);
            #*****scaledPixmap = buttonPixmap.scaled(buttonWidth + 50, buttonHeight);
            scaledPixmap = buttonPixmap;
            #*****
            self.buttonBackGroundPixmaps.append(scaledPixmap);
        
        self.crossedOutButtonBackground = QPixmap();
        imgPath = os.path.join(imgDirPath, "jboardButtonBackgroundCrossedOut.png");
        if not self.crossedOutButtonBackground.load(imgPath):
            raise IOError("Could not find crossed-out button background icon at " + imgPath);
        self.crossedOutButtonBackground = self.crossedOutButtonBackground.scaled(buttonWidth + 50, buttonHeight);
        
        # Initialize all buttons to a background with
        # trail spot 8 (darkest):
        for button in self.letterButtons:
            self.setButtonImage(button, self.buttonBackGroundPixmaps[NUM_LETTER_BUTTONS - 1]);
            
        # Initialize dictionary that tracks button background icons.
        # Keys are button objs, values are ints that index into the 
        # self.buttonBackgroundPixmaps array. None means the button
        # is so old that it has a plain background, or that it was never
        # used so far:
        self.currentButtonBackgrounds = {};
        for buttonObj in self.letterButtons:
            self.currentButtonBackgrounds[buttonObj] = None;
            
        self.setStyleSheet("QWidget{background-color: %s}" % self.offWhiteColor.name());

    def createColors(self):
        self.grayBlueColor = QColor(89,120,137);  # Letter buttons
        self.offWhiteColor = QColor(206,230,243); # Background
        self.darkGray      = QColor(65,88,101);   # Central buttons
        self.wordListFontColor = QColor(62,143,185); # Darkish blue.
        self.purple        = QColor(147,124,195); # Gesture button pressed

    def setGestureButtonStyle(self, buttonObj, styleID):
        if styleID == StyleID.RELEASED:
            buttonObj.setStyleSheet("background-color: %s; color: %s; border: 2px outset %s; border-radius: 15; font-size: 18px" %
                                    (self.grayBlueColor.name(),
                                     self.offWhiteColor.name(),
                                     self.offWhiteColor.name()));
                                     
        elif styleID == StyleID.PRESSED:
            buttonObj.setStyleSheet("background-color: %s; color: %s; border-radius: 15; font-size: 22px" %
                                    (self.purple.name(),
                                     self.offWhiteColor.name()));
        self.setFocus();
        
    # -------------------------------------- Signal Handlers -------------------------            
    
    @Slot(GestureButton, int)
    def handleButtonFlicks(self, gestureButton, flickDirection):
        #print "Flick direction: " + FlickDirection.toString(flickDirection);
        
        # Protect against re-entry. Not that 
        # QtCore.QMutexLocker locks when created, and
        # unlocks when destroyed (i.e. when function
        # is left; no explicit unlocking needed);
        
        myMutexLocker = QMutexLocker(self.mutex);
        
        # West flick: Undo last letter (in Dialpad mode) or
        # highlight next letter (in Letter_Edit mod):
        if flickDirection == FlickDirection.WEST:
            if self.buttonEditMode == ButtonEditMode.DIALPAD:
                self.erasePreviousLetter();
                self.showRemainingWords();
                self.updateTickerTape();
            else: # individual-letter-input mode:
                self.highlightNextLetter(gestureButton, FlickDirection.WEST);
                
        # North flick: Scroll word list up:
        elif flickDirection == FlickDirection.NORTH:
            currRemainingWordsRow = self.wordList.currentRow();
            if currRemainingWordsRow == 0 or self.buttonEditMode == ButtonEditMode.LETTER_INPUT:
                pass;
            else:
                self.wordList.setCurrentRow(currRemainingWordsRow - 1);
        # South flick: Scroll word list down:
        elif flickDirection == FlickDirection.SOUTH:
            currRemainingWordsRow = self.wordList.currentRow();
            if currRemainingWordsRow >= self.wordList.count() or self.buttonEditMode == ButtonEditMode.LETTER_INPUT:
                pass;
            else:
                self.wordList.setCurrentRow(currRemainingWordsRow + 1);
        # East flick: Accept word that is selected in remaining words list:
        else:
            if self.buttonEditMode == ButtonEditMode.LETTER_INPUT:
                self.highlightNextLetter(gestureButton, FlickDirection.EAST);
            else:
                # No word in word list?
                count = self.wordList.count()
                currItem = self.wordList.currentItem();
                if count <= 0 or currItem is None:
                    pass;
                else:
                    self.outputPanel.insertPlainText(" " + currItem.text());
                    # Word entry done for this word:
                    self.eraseCurrentWord();
            
        # Remember that we just used this button 
        # for a flick action. 
        self.currButtonUsedForFlick = True;

    @Slot(GestureButton)
    def handleButtonEntered(self, gestureButtonObj):
        #print "Button %s entered" % str(gestureButtonObj);
        pass;

    @Slot(GestureButton)
    def handleButtonExited(self, gestureButtonObj):
        
        # Protect against re-entry. Not that 
        # QtCore.QMutexLocker locks when created, and
        # unlocks when destroyed (i.e. when function
        # is left; no explicit unlocking needed);
        
        myMutexLocker = QMutexLocker(self.mutex);
        
        # If we are in letter entry mode, return this button 
        # to Dialpad mode:
        if self.buttonEditMode == ButtonEditMode.LETTER_INPUT:
            self.switchButtonMode(gestureButtonObj, ButtonEditMode.DIALPAD);
            return;

        # If button being left was just used for a flick,
        # don't count the exit:            
        if self.currButtonUsedForFlick:
            self.currButtonUsedForFlick = False;
            return;
        
        # Get 'ABC', or 'DEF', etc representation from the button:
        buttonLabelAsStr = str(gestureButtonObj);
        newEncLetter = self.wordCollection.encodeTelPadLabel(buttonLabelAsStr);
        self.encEvolvingWord += newEncLetter;
        self.shiftButtonTrails(HistoryShiftDir.OLDER, newHead=gestureButtonObj);
        #print self.encEvolvingWord;
        self.showRemainingWords();
        self.updateTickerTape();

    def handleEraseWordButton(self):
        self.eraseCurrentWord();
        self.showRemainingWords();
        self.updateTickerTape();
        
    def handleCrossoutTimeout(self):
        for buttonObj in self.crossedOutButtons:
            self.setButtonImage(buttonObj, self.buttonBackGroundPixmaps[self.currentButtonBackgrounds[buttonObj]]);
        self.crossedOutButtons = [];
            
    def handleNumPad(self, numButton):
        buttonLabel = numButton.text();
        self.outputPanel.insertPlainText(buttonLabel);
        
    def handleSpecialChars(self, specCharButton):
        if specCharButton == self.backspaceButton:
            self.outputPanel.textCursor().deletePreviousChar();
            return;
        elif specCharButton == self.spaceButton:
            char = " ";
        else:
            char = specCharButton.text();
        self.outputPanel.insertPlainText(char);            
    
    def handleGestureButtonClick(self, buttonObj):
        
        # If button is in default dialpad mode, switch to letter-input mode:
        if self.buttonEditMode == ButtonEditMode.DIALPAD:
            self.switchButtonMode(buttonObj, ButtonEditMode.LETTER_INPUT);
        
        # If button is in letter edit mode, add the currently
        # capitalized letter to the output panel, and switch the
        # button back into default dialpad mode:          
        elif self.buttonEditMode == ButtonEditMode.LETTER_INPUT:
            labelBeingEdited = buttonObj.text();
            capLetter = labelBeingEdited[self.findCapitalLetter(labelBeingEdited)];
            self.outputPanel.insertPlainText(capLetter.lower());
            self.switchButtonMode(buttonObj, ButtonEditMode.DIALPAD);
    
    def handleSaveWordButton(self):
        # Get content of output panel:
        currOutput = self.outputPanel.toPlainText();
        # If noth'n there, done:
        if len(currOutput) == 0:
            QMessageBox.information(self, "Dictionary addition", "Output panel has no content; so there is no word to save.", QMessageBox.Ok, QMessageBox.NoButton);
            return;
        # Get the last word in the output panel:
        newWord = re.split("[.;:?! @()]", currOutput)[-1];
        # Ask user about capitalization, and expected word frequency.
        # This call will raise a modal dialog box. Signal handlers
        # handleAddDictWordCapitalizeStateChanged(), and handleAddDictWordOK_Cancel()
        # take it from there:
        self.getAddWordUserInfo(newWord);
        
    def handleAddDictWordCapitalizeStateChanged(self, newCapsState):
        dialog = self.addWordDialog;
        newWord = dialog.newWord.text();
        if newCapsState == 0:
            dialog.newWord.setText(newWord.lower());
        else:
            dialog.newWord.setText(newWord.capitalize());

    def handleAddDictWordOK_Cancel(self, button):
        if button == self.addWordDialog.cancelButton:
            self.addWordDialog.hide();
            return;
                    
        frequencyCheckboxID = self.addWordButtonGroup.checkedId();
        if frequencyCheckboxID == JBoard.RARELY_BUTTON_ID:
            freqRank = UseFrequency.RARELY;
        elif frequencyCheckboxID == JBoard.OCCCASIONALLY_BUTTON_ID:
            freqRank = UseFrequency.OCCASIONALLY;
        elif frequencyCheckboxID == JBoard.CONSTANTLY_BUTTON_ID:
            freqRank = UseFrequency.CONSTANTLY;
        else:
            raise ValueError("Unknown use frequency checkbox ID in add word to dictionary dialog handling: " + str(frequencyCheckboxID));
        
        self.doAddWordButton(self.addWordDialog.newWord.text(), freqRank);
        self.addWordDialog.hide();
        
    def handleCopyAll(self):
        self.clipboard.setText(self.outputPanel.toPlainText());
    
    # -------------------------------------- UI Manipulation -------------------------

    def doAddWordButton(self, newWord, rank):
        additionResult = self.wordCollection.addToUserDict(newWord, rankInt=rank);
        if additionResult:
            QMessageBox.information(self,  # dialog parent 
                                    "Dictionary addition", "Word '%s' has been saved in user dictionary." % newWord, 
                                    QMessageBox.Ok, 
                                    QMessageBox.NoButton);
        else:
            QMessageBox.information(self,  # dialog parent 
                                    "Dictionary addition", "Word '%s' was already in the dictionary. No action taken" % newWord, 
                                    QMessageBox.Ok, 
                                    QMessageBox.NoButton);
        

    def switchButtonMode(self, buttonObj, newEditMode):
        if newEditMode == ButtonEditMode.DIALPAD:
            self.setGestureButtonStyle(buttonObj, StyleID.RELEASED);
            self.buttonEditMode = ButtonEditMode.DIALPAD;
            buttonObj.setText(buttonObj.text().upper());
        elif newEditMode == ButtonEditMode.LETTER_INPUT:
            self.setGestureButtonStyle(buttonObj, StyleID.PRESSED);
            self.buttonEditMode = ButtonEditMode.LETTER_INPUT;
            buttonObj.setText(buttonObj.text().capitalize());

    def highlightNextLetter(self, buttonObj, flickDirection):
        label = buttonObj.text();
        capitalLetterPos = self.findCapitalLetter(label);
        label = label.lower();
        if flickDirection == FlickDirection.EAST:
            newCapPos = (capitalLetterPos + 1) % len(label);
        else:
            newCapPos = (capitalLetterPos - 1) % len(label);
        #label = label[:newCapPos] + label[newCapPos].upper() + label[min(newCapPos + 1, len(label) - 1):]; 
        label = label[:newCapPos] + label[newCapPos].upper() + label[newCapPos + 1:] if newCapPos < len(label) else "";
            
        buttonObj.setText(label);
    
    def findCapitalLetter(self, word):
        for (pos, char) in enumerate(word):
            if char.isupper():
                return pos;
        raise ValueError("No capital letter found.");
            
    
    def updateTickerTape(self):
        if len(self.encEvolvingWord) == 0:
            self.tickerTape.setText("");
            return;
        visibleEncoding = "";
        for encChar in self.encEvolvingWord:
            dialpadButtonLabel = self.wordCollection.decodeTelPadLabel(encChar);
            buttonID = ButtonID.toButtonID(dialpadButtonLabel);
            visibleEncoding += ButtonID.idToStringable(buttonID);
        self.tickerTape.setText(visibleEncoding); 
    
    def showRemainingWords(self):
        remainingWords = self.wordCollection.prefix_search(self.encEvolvingWord);
        rankSortedWords = sorted(remainingWords, key=self.wordCollection.rank);
        self.wordList.clear();
        
        self.wordList.addItems(rankSortedWords);
        self.wordList.setCurrentRow(0);
        
        #print self.wordCollection.prefix_search(self.encEvolvingWord);
        
    def eraseCurrentWord(self):
        self.encEvolvingWord = "";
        self.updateTickerTape();
        self.eraseTrail();
        self.wordList.clear();
        
    def erasePreviousLetter(self):
        if len(self.encEvolvingWord) == 0:
            # Just to make sure, erase all history trail:
            self.eraseTrail();
            return;
        oldNewestButton = self.getButtonFromEncodedLetter(self.encEvolvingWord[-1]);
        self.encEvolvingWord = self.encEvolvingWord[0:-1];
        if len(self.encEvolvingWord) > 0:
            newNewestButton = self.getButtonFromEncodedLetter(self.encEvolvingWord[-1]);
        else:
            newNewestButton = None;
        self.shiftButtonTrails(HistoryShiftDir.YOUNGER, newHead=newNewestButton);
        self.crossOutButton(oldNewestButton);
        if len(self.encEvolvingWord) == 0:
            self.eraseTrail();
        
    def crossOutButton(self, buttonObj):
        '''
        Show the given button crossed out. Update the
        currentButtonBackgrounds dict to show that this
        button now has a different background (not one of the
        trails.
        @param buttonObj: GestureButton object to cross out.
        @type buttonObj: QPushButton
        '''
        self.setButtonImage(buttonObj, self.crossedOutButtonBackground);
        self.crossedOutButtons.append(buttonObj);
        # Take the crossout away in 2 seconds:
        self.crossOutTimer.start(2000);
        
    def eraseTrail(self):
        '''
        Erase the history trail. 
        '''
        for buttonObj in self.letterButtons:
            self.setButtonImage(buttonObj, self.buttonBackGroundPixmaps[-1]);
            self.currentButtonBackgrounds[buttonObj] = NUM_LETTER_BUTTONS - 1;
        
    def shiftButtonTrails(self, direction, newHead=None):
        if direction == HistoryShiftDir.OLDER:
            # Every button gets one older:
            for buttonObj in self.letterButtons:
                currPixmapIndex = self.currentButtonBackgrounds[buttonObj];
                if currPixmapIndex is None:
                    continue;
                if currPixmapIndex >= NUM_LETTER_BUTTONS - 1:
                    # Button already as old as it gets:
                    continue;
                buttonObj.setIcon(QIcon(self.buttonBackGroundPixmaps[currPixmapIndex + 1]));
                self.currentButtonBackgrounds[buttonObj] = currPixmapIndex + 1;
            if newHead is not None:
                self.setButtonImage(newHead, self.buttonBackGroundPixmaps[0]);
                self.currentButtonBackgrounds[newHead] = 0;
            
        else:
            # Make everyone younger:
            for buttonObj in self.letterButtons:
                currPixmapIndex = self.currentButtonBackgrounds[buttonObj];
                if currPixmapIndex is None:
                    # Button has a special, temporary background, like being crossed out:
                    continue;
                if currPixmapIndex <= 0:
                    # Button already as young as it gets. Make it the oldest:
                    self.setButtonImage(buttonObj,self.buttonBackGroundPixmaps[NUM_LETTER_BUTTONS - 1]);
                self.setButtonImage(buttonObj, self.buttonBackGroundPixmaps[currPixmapIndex - 1]);
                self.currentButtonBackgrounds[buttonObj] = currPixmapIndex - 1;
            
      
    def setButtonImage(self, gestureButtonObj, pixmap):
        # PySide: gestureButtonObj.setIcon(pixmap);
	gestureButtonObj.setIcon(QIcon(pixmap));
        gestureButtonObj.setIconSize(pixmap.rect().size());
        
        
    def getAddWordUserInfo(self, newWord):
        '''
        Prepare the Add New Word dialog, and show it:
        @param newWord:
        @type newWord:
        '''
        # New word capitalized? Pre-set the Capitalize checkbox accordingly:
        if newWord.istitle():
            self.addWordDialog.capitalizeCheckbox.setChecked(True);
        else:
            self.addWordDialog.capitalizeCheckbox.setChecked(False);
        # Init the label in the dialog box that shows the word to be added:
        self.addWordDialog.newWord.setText(newWord);
        
        # Place the dialog somewhere over the application window:
        jBoardGeoRect = self.geometry();
        dialogGeoRect = self.addWordDialog.geometry();
        newDialogGeo  = QRect(jBoardGeoRect.x() + 50, 
                              jBoardGeoRect.y() + 50,
                              dialogGeoRect.width(),
                              dialogGeoRect.height());
        self.addWordDialog.setGeometry(newDialogGeo);
        
        self.addWordDialog.show();
        
    # -------------------------------------- Handy Methods -------------------------
                
    def getButtonFromEncodedLetter(self, encLetter):
        # From the encoded letter, get the corresponding
        # "ABC", "PQR", etc label:
        buttonLabel = self.wordCollection.decodeTelPadLabel(encLetter);
        buttonID    = ButtonID.toButtonID(buttonLabel);
        return self.letterButtons[buttonID];
        
if __name__ == "__main__":
    
    app = QApplication(sys.argv);
    b = JBoard();
    app.exec_();
    sys.exit();
