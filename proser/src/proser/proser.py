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
    import roslib; roslib.load_manifest('proser');
    ROS_AVAILABLE = True;
except ImportError:
    ROS_AVAILABLE = False;


import sys;
import os;
import signal;
from functools import partial

try:
    from word_completion.word_collection import WordCollection;
except ImportError as e:
    print(`e`);
    print("Roslib is unavailable. So your PYTHONPATH will need to include:\n" +
          "word_completion/lib, word_completion/src");
    sys.exit();    


import python_qt_binding;
from python_qt_binding.QtGui import QApplication, QMainWindow, QDialog, QPushButton, QTextEdit, QTextCursor, QShortcut, QErrorMessage;
from python_qt_binding.QtGui import QMessageBox, QWidget;

# ----------------------------------------------- Class DialogService ------------------------------------

class DialogService(QWidget):
    '''
    Provides popup windows for information and error messages 
    '''

    #----------------------------------
    # Initializer
    #--------------

    def __init__(self, parent=None):
        super(DialogService, self).__init__(parent);
        
        # All-purpose error popup message:
        # Used by self.showErrorMsgByErrorCode(<errorCode>), 
        # or self.showErrorMsg(<string>). Returns a
        # QErrorMessage without parent, but with QWindowFlags set
	    # properly to be a dialog popup box:
        self.errorMsgPopup = QErrorMessage.qtHandler();
       	# Re-parent the popup, retaining the window flags set
        # by the qtHandler:
        self.errorMsgPopup.setParent(parent, self.errorMsgPopup.windowFlags());
        #self.errorMsgPopup.setStyleSheet(SpeakEasyGUI.stylesheetAppBG);
        self.infoMsg = QMessageBox(parent=parent);
        #self.infoMsg.setStyleSheet(SpeakEasyGUI.stylesheetAppBG);
    
    #----------------------------------
    # showErrorMsg
    #--------------
    QErrorMessage
    def showErrorMsg(self,errMsg):
        '''
        Given a string, pop up an error dialog on top of the application window.
        @param errMsg: The message
        @type errMsg: string
        '''
        self.errorMsgPopup.showMessage(errMsg);
    
    #----------------------------------
    # showInfoMsg 
    #--------------

    def showInfoMsg(self, text):
        '''
        Display a message window with an OK button on top of the application window.
        @param text: text to display
        @type text: string
        '''
        self.infoMsg.setText(text);
        self.infoMsg.exec_();        

#--------------------------------  Proser Class ---------------------------

class Proser(QMainWindow):
    '''
    Creates a top level X window in which user can type. Proser provides 
    statistical word completion suggestions. The suggestions are displayed
    on five buttons at the top of the window. Two methods are available to
    select one of the suggestions: Click the respective onscreen button, or
    type one of F5-F9. Completion is based on the word_completion package,
    which uses a frequency-ranked 6000 word dictionary. 
    
    A Copy button copies the entire typed text into the X cut buffer (a.k.a. clipboard), 
    from where it may be pasted into any other window.
    
    A special link exists between Proser and SpeakEasy. Proser provides two
    SpeakEasy related buttons:
        1. Erase the SpeakEasy text display
        2. Send the entire Proser window text to SpeakEasy and have it
           spoken by the currently selected voice. The SpeakEasy window
           may be minimized during this operation.
    
    Users may type their text from a physical, or any onscreen keyboard.
    '''
    
    VERSION = "1.0";
    SPEAKEASY_PID_PUBLICATION_FILE = "/tmp/speakeasyPID"; 
    NO_COMPLETION_TEXT = '';
    FIRST_SHORTCUT_FUNC_KEY = 5;
    
    # Unix signals for use with clearing text remotely, and with
    # pasting and speech-triggering from remote:
    REMOTE_CLEAR_TEXT_SIG = signal.SIGUSR1;
    REMOTE_PASTE_AND_SPEAK_SIG = signal.SIGUSR2;
    
    
    def __init__(self, dictDir=None, userDictFilePath=None):
        
        super(Proser,self).__init__();
        
        # Get the word completion machinery:
        self.completer = WordCollection(dictDir=dictDir, userDictFilePath=userDictFilePath);
        
        # Fill our space with the UI:
        guiPath = os.path.join(os.path.dirname(__file__), 'qt_files/Proser/proser.ui');
        self.ui = python_qt_binding.loadUi(guiPath, self);
        self.setWindowTitle("Proser (V" + Proser.VERSION + ")");
        self.completionButtons = [self.wordOption1Button,
                                  self.wordOption2Button,
                                  self.wordOption3Button,
                                  self.wordOption4Button,
                                  self.wordOption5Button];
        self.clearCompletionButtons();
        self.dialogService = DialogService(parent=self);
        self.connectWidgets();
        
        self.show();
        self.focusOnTextArea();
        
    def connectWidgets(self):
        '''
        Attach slots and widgets to actions.
        '''
        self.clearButton.clicked.connect(self.actionClear);
        self.copyButton.clicked.connect(self.actionCopy);
        self.textArea.textChanged.connect(self.actionTextChanged);
        for buttonObj in self.completionButtons:
            buttonObj.clicked.connect(partial(self.actionCompletionButton,buttonObj));
            
        # Make F5-F9 work as shortcuts for pressing the word suggestion buttons:
                
        for i in range(len(self.completionButtons) + 1):
            shortcut = QShortcut(self.tr('F' + str(i + Proser.FIRST_SHORTCUT_FUNC_KEY)), self);
            # Pass the completion button index (0 through 4) to the handler:
            shortcut.activated.connect(partial(self.actionKeyShortcut, i));
            
        self.addToDictButton.clicked.connect(self.actionAddToDictButton);
        self.clearSpeakEasyButton.clicked.connect(self.actionClearSpeakEasyText);
        self.sayButton.clicked.connect(self.actionSendTextToSpeakEasy);
    
    def actionClear(self):
        '''
        Clear the text display.
        '''
        self.textArea.clear();
        self.clearCompletionButtons();
        self.focusOnTextArea();
        
    def actionCopy(self):
        '''
        Copy all Proser text to the X cut buffer (i.e. clipboard).
        '''
        currCursor = self.textArea.textCursor(); 
        currCursor.select(QTextCursor.Document);
        self.textArea.setTextCursor(currCursor);
        self.textArea.copy();
        currCursor = self.textArea.textCursor(); 
        currCursor.clearSelection();
        self.textArea.setTextCursor(currCursor);
        self.focusOnTextArea();

    def actionTextChanged(self):
        '''
        Act on notification that text in the text panel changed.
        This notification occurs with every one of the user's keystroke.
        In response this method updates the text completion buttons.
        '''
        wordSoFar = self.getWordSoFar();
        if len(wordSoFar) == 0:
            self.clearCompletionButtons();
            return;
        completions = self.completer.prefix_search(wordSoFar, cutoffRank=len(self.completionButtons));
        if len(completions) == 0:
            self.clearCompletionButtons();
        #print str(completions)
        self.clearCompletionButtons();
        for index,button in enumerate(self.completionButtons):
            if index >= len(completions):
                return;
            button.setText(completions[index]);
            
    def actionCompletionButton(self, buttonObj):
        '''
        One of the text completion buttons was pushed. Insert the 
        respective text at the current cursor position.
        @param buttonObj: the QPushButton object that was pushed.
        @type buttonObj: QPushButton
        '''
        text = buttonObj.text().encode('UTF-8');
        alreadyTypedTxt = self.getWordSoFar();
        if len(alreadyTypedTxt) >= len(text):
            return;
        textToAppend =  text[len(alreadyTypedTxt):] + " ";
        self.textArea.textCursor().insertText(textToAppend);
        # Ensure that text area gets focus again:
        self.focusOnTextArea();

    def actionKeyShortcut(self, buttonIndex):
        '''
        User pressed a function key F5-F9. Invoke the actionCompletionButton() method.
        @param buttonIndex: Index 0-4 into the array self.completionButtons.
        @type buttonIndex: int
        '''
        
        #print 'Function key F' + str(buttonIndex + Proser.FIRST_SHORTCUT_FUNC_KEY) + ' pressed.'
        try:
            self.actionCompletionButton(self.completionButtons[buttonIndex]);
        except IndexError:
            # don't recognize this function key:
            pass;
        
    def actionAddToDictButton(self):
        '''
        Add selected text to the dictionary that is used for word completion.
        Words added by this method are appended to the dict_files/dictUserRankAndWord.txt
        file in the word_completion package. A default rank of 100 is attached.
        
        The method attempts to warn the user if the text selection seems to span
        multiple words. In that case, a warning is displayed. A confirmation
        dialog is raised in case of success.
        @raise ValueError: if provided rank < 0. 
        '''
        # The following used to be a keyword arg, but keyword args don't
        # seem to work when method is called from PyQt as a button handler.
        # So the default rank of the new word is set up here now:
        rank = 100;
        if rank < 0:
            raise ValueError("Rank must be greater than or equal to zero");
        try:
            currCursor = self.textArea.textCursor();
            selText = currCursor.selectedText().encode('UTF-8');
            if len(selText) == 0:
                self.dialogService.showErrorMsg("Please select a word to be added to the dictionary.");
                return;
            if len(selText.split(' ')) != 1 or\
               len(selText.split(',')) != 1 or\
               len(selText.split('.')) != 1 or\
               len(selText.split(';')) != 1 or\
               len(selText.split(':')) != 1:
                self.dialogService.showErrorMsg("Please select only one word to be added to the dictionary.");
                return;
            self.completer.addToUserDict(selText, rankInt=rank);
            self.dialogService.showInfoMsg("Added %s to dictionary." % selText);
        finally:
            self.focusOnTextArea();
        

    def getWordSoFar(self):
        '''
        Service method to retrieve the most recent partially typed word.  
        '''
        currCursor = self.textArea.textCursor();
        currCursor.select(QTextCursor.WordUnderCursor);
        wordFragment = currCursor.selectedText().encode('UTF-8');
        #print "Frag (cur at: " + str(currCursor.position()) + "): " + str(wordFragment);
        return wordFragment;      
        
    def clearCompletionButtons(self):
        '''
        Service method to clear labels on all word completion buttons.
        '''
        for completionButton in self.completionButtons:
            completionButton.setText(completionButton.setText(Proser.NO_COMPLETION_TEXT));
    
    def focusOnTextArea(self):
        '''
        Service method to force the cursor focus into the text area.
        '''
        self.textArea.setFocus();

    def actionSendTextToSpeakEasy(self):
        '''
        Copy current content of the text field into the X clipboard.
        Cause a running SpeakEasy process to paste that newly loaded X clipboard into
        its SpeakEasy text area, and to speak the content using the current voice.
        The method getSpeakEasyPID() is called from here, and that method will
        raise a warning dialog if no SpeakEasy process is currently running.
        That method will also raise the ValueError documented below.
        
        Implementation: Send a Unix signal REMOTE_PASTE_AND_SPEAK_SIG to the
        SpeakEasy application, if one is running.  
        
        @raise ValueError: if the file /tmp/speakeasyPID does not contain an integer. That
                           file is initialized by SpeakEasy with that process' PID. While that
                           pid might be stale, it would still be an integer, unless the file
                           is changed manually. 
        '''
        pid = self.getSpeakEasyPID();
        if pid is None:
            # Error message was already provided by getSpeakEasyPID
            return;
        self.actionCopy();
        try:
            os.kill(pid, Proser.REMOTE_PASTE_AND_SPEAK_SIG);
        except OSError:
            # PID was invalid:
            self.dialogService.showErrorMsg("SpeakEasy application seems not to be running. Please start it.");

    def actionClearSpeakEasyText(self):
        '''
        Cause a running SpeakEasy process to clear its text area.
        
        Implementation: Send a Unix signal REMOTE_CLEAR_TEXT_SIG to 
        the SpeakEasy process if one is running. Else a warning dialog is raised.
        
        @raise ValueError: if the file /tmp/speakeasyPID does not contain an integer. That
                           file is initialized by SpeakEasy with that process' PID. While that
                           pid might be stale, it would still be an integer, unless the file
                           is changed manually. 
        '''
        pid = self.getSpeakEasyPID();
        if pid is None:
            # Error message was already provided by getSpeakEasyPID
            return;
        try:
            os.kill(pid, Proser.REMOTE_CLEAR_TEXT_SIG);
        except OSError:
            # PID was invalid:
            self.dialogService.showErrorMsg("SpeakEasy application seems not to be running. Please start it.");

    def getSpeakEasyPID(self):
        '''
        Return the PID of the SpeakEasy application, if it is running.
        Else return None. The PID is communicated via a file. Note that
        this file's content might be stale. So callers must protect against
        the target process not running any more.
        
        @raise ValueError: if the file /tmp/speakeasyPID does not contain an integer. That
                           file is initialized by SpeakEasy with that process' PID. While that
                           pid might be stale, it would still be an integer, unless the file
                           is changed manually. 
        '''
        try:
            pidFile = os.fdopen(os.open(Proser.SPEAKEASY_PID_PUBLICATION_FILE, os.O_RDONLY));
        except OSError:
            self.dialogService.showErrorMsg("SpeakEasy application seems not to be running. Please start it.");
            return None;
        try:
            pid = int(pidFile.readline());
        except ValueError:
            # PID file did not contain an integer:
            self.dialogService.showErrorMsg("SpeakEasy PID file did not contain an integer. Please notify the developer.");
            return None;
        
        return pid;
            
    
if __name__ == '__main__':
    
    app = QApplication(sys.argv);
    #QApplication.setStyle(QCleanlooksStyle())
    proser = Proser();
    app.exec_();
    sys.exit();
    
        
