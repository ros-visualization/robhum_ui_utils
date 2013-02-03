#from python_qt_binding import QtCore
#from python_qt_binding import QtGui
#
#from QtGui import QObject
#from QtCore import Signal

class CommChannel(object):
    '''
    Combines Qt signals into one place. Avoids error "... has no method 'emit'". 
    This is a singleton class, which is enforced.
    
    Use addSignal() and commChannelInstance[sigName] to retrieve a signal.
    '''
    singletonInstance = None;

    userSigs = {}

    def __init__(self):
        super(CommChannel,self).__init__();
        if CommChannel.singletonInstance is not None:
            raise RuntimeError("Use getInstance() to obtain CommChannel instances.");
        CommChannel.singletonInstance = self;
        self.userSignals = {};
        
    @staticmethod
    def getInstance():
        '''
        Obtain the (only) instance of CommChannel. If none exists
        yet, it is created. Else the existing instance is returned. 
        '''
        if CommChannel.singletonInstance:
            return CommChannel.singletonInstance;
        else:
            return CommChannel();
    
    def addSignal(self, sigName, sigObj):
        '''
        Add a new Qt Signal instance under a name. 
        :param sigName: name under which signal object is known, and can be retrieved.
        :type sigName: string
        :param sigObj: the Qt Signal object to register
        :type sigObj: QtCore.Signal
        '''
        CommChannel.userSigs[sigName] = sigObj;

    def getSignal(self, sigName):
        '''
        Retrieve a previously added signal. Alternatively,
        use dict style syntaxs: commInstance[sigName].
        :param sigName: name under which signal was registered.
        :type sigName: string
        '''
        return CommChannel.userSigs[sigName];
        
    def __getitem__(self, sigName):
        return CommChannel.userSigs[sigName];
    
    def registeredSignals(self):
        '''
        Return list of all registered signal objects.
        '''
        return CommChannel.userSigs.values();
    
    def registeredSignalNames(self):
        '''
        Return list of all registered signal registration names.
        '''
        return CommChannel.userSigs.keys();
    
if __name__ == '__main__':
    
    ch = CommChannel.getInstance()
    ch.addSignal('sig1', 'sigObj1');
    print(ch['sig1'])
        

        
