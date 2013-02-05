
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
