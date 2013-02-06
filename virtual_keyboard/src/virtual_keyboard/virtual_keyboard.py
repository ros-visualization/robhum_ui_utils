#!/usr/bin/env python

import subprocess
from subprocess import PIPE
import re

# Requires xdotools (available via apt in Ubuntu)

class VirtualKeyboard(object):
    
    def __init__(self):
        super(VirtualKeyboard,self).__init__();
        # Regex that extracts two named groups from a str
        # like this: "x:1893 y:720 screen:0 window:12595888".
        # The first group will be called 'x', and will contain
        # the number following x (here: 1893). The second group
        # will be called 'y'. See getMouseGlobalPos() for use:
        self.screenPosPattern = re.compile(r'x:(?P<x>[\d]+).*y:(?P<y>[\d]+)');
        # Same for extracting the window ID only:
        self.windowIDPattern  = re.compile(r'.*window:(?P<winID>[\d]+)');
        
        # Pattern to extract x,y,width,height from the xdotool getwindowgeometry command:
        #   Window 46137569
        #     Position: 2765,628 (screen: 0)
        #     Geometry: 1244x848
        # The '.DOTALL' ensures that '.*' matches the newlines:
        self.winGeometryPattern = re.compile('.*Position: (?P<x>[\d]+)[,]+(?P<y>[\d]+).*Geometry: (?P<width>[\d]+)x(?P<height>[\d]+)', re.DOTALL);
        
        # Place for users to have window ids stored:
        self.windowIDs = {};
        
        self.saveActiveWindowID('__startup_win_id__');

    def typeControlCharToActiveWindow(self, theStr):
        '''
		Type a given keystroke. Examples being "alt+r", "Control_L+J",
		"ctrl+alt+n", "BackSpace", "Linefeed".
		Generally, any valid X Keysym string will work. Composited control keys are
		separated by '+'. Aliases exist for "alt", "ctrl", "shift", "super",
		and "meta" which all map to Foo_L, such as Alt_L and Control_L, etc.
        @param theStr: control-char string to send to active window
        @type theStr: string
        '''
        resCode = subprocess.call(['xdotool', 'key', str(theStr)]);
        
    def typeTextToActiveWindow(self, theStr):
        '''
		Type a given string, which must not contain control chars.
		For sending individual control chars, use typeControlCharToActiveWindow().
        @param theStr: control-char string to send to active window
        @type theStr: string
        '''
        resCode = subprocess.call(['xdotool', 'type', str(theStr)]);
        
    def mouseClick(self, buttonNum):
        '''
		Buttons map this way: Left mouse is 1, middle is 2, right is 3,
		wheel up is 4, wheel down is 5.
        @param buttonNum: which mouse button to click
        @type buttonNum: int
        '''
        if buttonNum < 1 or buttonNum > 5:
            raise ValueError("Mouse buttons are 1-3; mouse wheel up is 4; mouse wheel down is 5. Called with %d" % buttonNum)
        resCode = subprocess.call(['xdotool', 'getactivewindow', 'click', str(buttonNum)]);
            
    def mouseDown(self, buttonNum):
        '''
		Buttons map this way: Left mouse is 1, middle is 2, right is 3,
		wheel up is 4, wheel down is 5.
        @param buttonNum: which mouse button to hold down
        @type buttonNum: int
        '''
        if buttonNum < 1 or buttonNum > 5:
            raise ValueError("Mouse buttons are 1-3; mouse wheel up is 4; mouse wheel down is 5. Called with %d" % buttonNum)
        resCode = subprocess.call(['xdotool', 'getactivewindow', 'mousedown', str(buttonNum)]);

    def mouseUp(self, buttonNum):
        '''
		Buttons map this way: Left mouse is 1, middle is 2, right is 3,
		wheel up is 4, wheel down is 5.
        @param buttonNum: which mouse button to hold down
        @type buttonNum: int
        '''
        if buttonNum < 1 or buttonNum > 5:
            raise ValueError("Mouse buttons are 1-3; mouse wheel up is 4; mouse wheel down is 5. Called with %d" % buttonNum)
        proc = subprocess.Popen(['xdotool', 'getactivewindow', 'mouseup', str(buttonNum)]);

    def getMouseGlobalPos(self):
        '''
        Return a dictionary that provides 'x' and 'y' keys,
        whose values are integer x and y coordinates of the
        mouse cursor. The position is relative to the upper left
        corner of the display.
        '''
        proc = subprocess.Popen(['xdotool', 'getmouselocation'], stdout=PIPE, stderr=file("/dev/null", 'w'));
        # Example return in stdoutData: "x:1893 y:720 screen:0 window:12595888"
        (stdoutData, stdinData) = proc.communicate();
        # Turn output into a Python dictionary:
        xdotoolOutputMatch = re.match(self.screenPosPattern, stdoutData);
        if xdotoolOutputMatch is None:
            raise ValueError("Call to xdotool for obtaining mouse cursor position did not return output of expected format. It returned '%s'" % stdoutData)
        # Get at dict from the groups: {x:int1, y:int2}, where int1 and int2 are of string type:
        resDict = xdotoolOutputMatch.groupdict();
        # Turn x and y coords into ints:
        resDict['x'] = int(resDict['x']);
        resDict['y'] = int(resDict['y']);        
        return resDict 
    
    def moveMouseAbsolute(self, x, y):
        '''
        Move mouse cursor to absolute position relative to upper left 
        corner of display.
        @param x: horizontal coordinate
        @type x: int
        @param y: vertical coordinate
        @type y: int
        '''
        resCode = subprocess.call(['xdotool', 'mousemove', '--sync', str(x), str(y)]);

    def moveMouseRelative(self, x, y):
        '''
        Move mouse cursor new position relative to where
        it is currently located. It is legal to use negative 
        offsets for x and/or y.
        @param x: horizontal coordinate
        @type x: int
        @param y: vertical coordinate
        @type y: int
        '''
        resCode = subprocess.call(['xdotool', 'mousemove_relative', '--sync', '--', str(x), str(y)]);

    def saveActiveWindowID(self,retrievalKey):
        '''
        Internally saves the currently active X11 window's ID.
        Use getRecentWindow() to retrieve the ID for use with
        later xdotool commands.
        @param retrievalKey: key under which caller will ask for the ID later on.
        @type retrievalKey: string
        '''
        #*********8
        winid = subprocess.check_output(['xdotool', 'getactivewindow']).strip();
        #*********8
        self.windowIDs[retrievalKey] = subprocess.check_output(['xdotool', 'getactivewindow']).strip();

    def windowsEqual(self, retrievalKey1, retrievalKey2):
        return self._getWinIDSafely_(retrievalKey1) == self._getWinIDSafely_(retrievalKey2);
        
    def activateWindow(self, retrievalKey=None, windowTitle=None):
        '''
        Activates the X11 window with the given window ID.
        If windowID is omitted, the most recently active
        window is activated (see getRecentWindow()).
        @param retrievalKey: key under which caller asked to associate with window in earlier call to saveActiveWindowID
        @type retrievalKey: string
        '''
        if ((retrievalKey is None) and (windowTitle is None)) or\
            ((retrievalKey is not None) and (windowTitle is not None)):
            raise ValueError('Either retrievalKey or windowTitle must be provided (but not both)');
        
        if retrievalKey is not None:  
            resCode = subprocess.call(['xdotool', 'windowactivate', '--sync', str(self._getWinIDSafely_(retrievalKey))]);
        else:
            resCode = subprocess.call(['xdotool', 'search', '--name', '--sync', windowTitle, 'windowactivate']);
            
    def getWindowGeometry(self, retrievalKey=None):
        if retrievalKey is None:
            geo = subprocess.check_output(['xdotool', 'getactivewindow', 'getwindowgeometry']);
        else:
            geo = subprocess.check_output(['xdotool', 'getwindowgeometry', str(self._getWinIDSafely_(retrievalKey))]);
        theMatch = self.winGeometryPattern.match(geo);
        if theMatch is None:
            return None;
        resDict  = theMatch.groupdict();
        return resDict;

    def raiseWindow(self, retrievalKey=None):
        '''
        Flakey; don't rely on it.
        @param retrievalKey:
        @type retrievalKey:
        '''
        if retrievalKey is None:
            rescode = subprocess.call(['xdotool', 'getactivewindow', 'windowraise']);
        else:
            rescode = subprocess.call(['xdotool', 'windowraise', str(self._getWinIDSafely_(retrievalKey))]);

#    def activateWindowUnderMouse(self):
#        winID = self.windowUnderMouseCursor();
#        self.activateWindow(windowID=winID);
        
#    def windowUnderMouseCursor(self):
#        '''
#        Returns the ID of the X11 window under the mouse cursor.
#        '''
#        stdoutData = subprocess.check_output(['xdotool', 'getmouselocation'], stderr=file("/dev/null", 'w'));
#        xdotoolOutputMatch = re.match(self.windowIDPattern, stdoutData);
#        if xdotoolOutputMatch is None:
#            raise ValueError("Call to xdotool for obtaining mouse cursor position did not return output of expected format. It returned '%s'" % stdoutData)
#        # Get at dict from the group: {winID:winID}, where winID is of string type:
#        resDict = xdotoolOutputMatch.groupdict();
#        return resDict['winID'];


    #----------------------------------------   Private Methods  ----------------------------
    
    def _getWinIDSafely_(self, retrievalKey):
        try:
            return self.windowIDs[retrievalKey];
        except KeyError as e:
            raise ValueError("No retrieval key %s is known to virtual keyboard." % `e`);
        

if __name__ == '__main__':
    
    import time
    vBoard = VirtualKeyboard()
    # Time for human user to switch to another window for this test:
#    time.sleep(4)
#    vBoard.typeToActiveWindow("This is my test.")
    
#    time.sleep(4)
#    vBoard.mouseClick(1)
    
#    locDict = vBoard.getMouseGlobalPos();
#    print("X: %d; Y: %d" % (locDict['x'], locDict['y']))
    
#    vBoard.moveMouseAbsolute(100, 100);
        
#    vBoard.moveMouseRelative(-100, 100);

#    currentWinID = vBoard.windowUnderMouseCursor();
#    print("Move cursor to a different window; it will be activated.");
#    while True:
#        winIDNow = vBoard.windowUnderMouseCursor() 
#        if winIDNow != currentWinID:
#            break;
#        time.sleep(1);
#    vBoard.activateWindow(winIDNow);
#    print("Done.")

#    geometryDict = vBoard.getWindowGeometry();
#    print(str(geometryDict));
#    
#    vBoard.saveActiveWindowID('testWindow');
#    geometryDict = vBoard.getWindowGeometry(retrievalKey='testWindow');
#    print(str(geometryDict));

    vBoard.windowIDs['test'] = str(46137569);
    vBoard.raiseWindow(retrievalKey='test')


    # The following test doesn't work, because
    # 'xdotool selectwindow' doesn't select the clicked-on window
    # in the X11 sense. It only indicates to xdotools which window
    # will be talked about in the remainder of a command chain:
#    print("Select a window to save.");
#    winID = subprocess.check_output(['xdotool', 'selectwindow'])
#    print("winid was: %s" % winID);
#    vBoard.saveActiveWindowID();
#    print("Click another window and then wait 3 seconds for original window to regain focus.");
#    newWinID = subprocess.check_output(['xdotool', 'selectwindow'])
#    time.sleep(3);
#    vBoard.activateWindow();

        