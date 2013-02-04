from python_qt_binding import QtCore, QtGui

from QtCore import Signal, QObject
from QtGui import QPushButton

class CommChannel(QObject):
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

    def registerSignals(self, signalsClassInst):
        '''
        Add a new Qt Signal instance under a name. 
        :param sigName: name under which signal object is known, and can be retrieved.
        :type sigName: string
        :param sigObj: the Qt Signal object to register
        :type sigObj: QtCore.Signal
        '''
        if not issubclass(signalsClassInst.__class__, QObject):
            raise ValueError("Class passed to registerSignals must be a subclass of CommChannel.");
        userSignalClassVars = self.getSignalsFromClass(signalsClassInst.__class__)
        for classVarName in userSignalClassVars:
            try:
                sigObj = getattr(signalsClassInst, classVarName);
            except KeyError:
                # Some signals will have been inherited from Object,
                # such as the signal in class var 'destroyed'. Ignore
                # those:
                continue;
            CommChannel.userSigs[signalsClassInst.__class__.__name__ + '.' + classVarName] = sigObj;

    
#    def registerSignals(self, commChannelSubclass):
#        '''
#        Add a new Qt Signal instance under a name. 
#        :param sigName: name under which signal object is known, and can be retrieved.
#        :type sigName: string
#        :param sigObj: the Qt Signal object to register
#        :type sigObj: QtCore.Signal
#        '''
#        if not issubclass(commChannelSubclass, QObject):
#            raise ValueError("Class passed to registerSignals must be a subclass of CommChannel.");
#        userSignalClassVars = self.getSignalsFromClass(commChannelSubclass)
#        userClass = commChannelSubclass();
#        for classVarName in userSignalClassVars:
#            try:
#                sigObj = getattr(userClass, classVarName);
#            except KeyError:
#                # Some signals will have been inherited from Object,
#                # such as the signal in class var 'destroyed'. Ignore
#                # those:
#                continue;
#            CommChannel.userSigs[commChannelSubclass.__name__ + '.' + classVarName] = sigObj;

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
    

    # ----------------------------------------- Private ---------------------------

    def getSignalsFromClass(self, cls):
        #base_attrs = dir(type('dummy', (object,), {}))
        this_cls_attrs = dir(cls)
        res = []
        for attr in this_cls_attrs:
            if type(getattr(cls,attr)) != Signal:
                continue;
            res += [attr]
        return res

if __name__ == '__main__':
    
    ch = CommChannel.getInstance()
    ch.registerSignal('sig1', 'sigObj1');
    print(ch['sig1'])
