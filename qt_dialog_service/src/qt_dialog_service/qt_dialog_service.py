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

import sys

from python_qt_binding import QtGui
from QtGui import QWidget, QErrorMessage, QMessageBox, QApplication

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

if __name__ == '__main__':
    

    app = QApplication(sys.argv);
    dservice = DialogService()
    dservice.showErrorMsg("This is an error")
    dservice.showInfoMsg("This is info")
    app.exec_();
    sys.exit();
