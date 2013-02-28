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


from python_qt_binding import QtCore, QtGui

from QtCore import Signal, QObject
from QtGui import QPushButton

class CommChannel(QObject):
    '''
    Combines Qt signals into one place. Avoids error "... has no method 'emit'". 
    This is a static class. Usage:
       - Subclass this class; without creating any methods, including __init__().
       - The only active part in the subclass is to define Qt signals. Example::
       
             class MySignals(CommChannel):
                quitSig      = QtCore.Signal(QPushButton)
                taskDoneSig  = QtCore.Signal()
                
       - Before using the signals in your application, call registerSignals on CommChannel,
         passing your subclass::
         
             CommChannel.registerSignals(MySignals)
             
       - After that call, access your signals like this::
        
            CommChannel.getSignal('MySignals.quitSig')
            
         Note that the signal ID is a string consisting of the name
         of your subclass, followed by a dot, followed by the 
         signal class attribute's name.
         
       - Other modules in the same application can access the signals the same way.
    
    '''
    # Hold on to the CommChannel subclass instances that
    # are created in registerSignals(), so that they are not
    # GC'ed:
    commInstances = [];
    userSigs = {}

    @staticmethod
    def registerSignals(signalsClass):
        '''
        Add a new Qt Signal instance under a name. 
        @param signalsClass: name under which signal object is known, and can be retrieved.
        @type signalsClass: string
        '''
        if not issubclass(signalsClass, QObject):
            raise ValueError("Class passed to registerSignals must be a subclass of CommChannel.");
        userSignalClassVars = CommChannel.getSignalsFromClass(signalsClass)
        signalsClassInst = signalsClass();
        CommChannel.commInstances.append(signalsClassInst);
        for classVarName in userSignalClassVars:
            try:
                sigObj = getattr(signalsClassInst, classVarName);
            except KeyError:
                # Some signals will have been inherited from Object,
                # such as the signal in class var 'destroyed'. Ignore
                # those:
                continue;
            CommChannel.userSigs[signalsClass.__name__ + '.' + classVarName] = sigObj;


    @staticmethod
    def getSignal(sigName):
        '''
        Retrieve a previously added signal. Alternatively,
        use dict style syntaxs: commInstance[sigName].
        @param sigName: name under which signal was registered.
        @type sigName: string
        @return: signal object, or None, if signal of given name was not registered.
        @rtype: {QtCore.Signal | None}
        '''
        return CommChannel.userSigs[sigName];
    
    @staticmethod    
    def __getitem__(sigName):
        return CommChannel.userSigs[sigName];
    
    @staticmethod
    def registeredSignals():
        '''
        Return list of all registered signal objects.
        '''
        return CommChannel.userSigs.values();
    
    @staticmethod
    def registeredSignalNames():
        '''
        Return list of all registered signal registration names.
        '''
        return CommChannel.userSigs.keys();
    

    # ----------------------------------------- Private ---------------------------

    @staticmethod
    def getSignalsFromClass(cls):
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
