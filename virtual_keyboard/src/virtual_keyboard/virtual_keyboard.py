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

    def typeToActiveWindow(self, theStr):
        '''
		Type a given keystroke. Examples being "alt+r", "Control_L+J",
		"ctrl+alt+n", "BackSpace".
		Generally, any valid X Keysym string will work. Multiple keys are
		separated by '+'. Aliases exist for "alt", "ctrl", "shift", "super",
		and "meta" which all map to Foo_L, such as Alt_L and Control_L, etc.        
        :param theStr: string to send to active window
        :type theStr: string
        '''
        resCode = subprocess.call(['xdotool', 'getactivewindow', 'type', str(theStr)]);
        
    def mouseClick(self, buttonNum):
        '''
		Buttons map this way: Left mouse is 1, middle is 2, right is 3,
		wheel up is 4, wheel down is 5.
        :param buttonNum: which mouse button to click
        :type buttonNum: int
        '''
        if buttonNum < 1 or buttonNum > 5:
            raise ValueError("Mouse buttons are 1-3; mouse wheel up is 4; mouse wheel down is 5. Called with %d" % buttonNum)
        resCode = subprocess.call(['xdotool', 'getactivewindow', 'click', str(buttonNum)]);
            
    def mouseDown(self, buttonNum):
        '''
		Buttons map this way: Left mouse is 1, middle is 2, right is 3,
		wheel up is 4, wheel down is 5.
        :param buttonNum: which mouse button to hold down
        :type buttonNum: int
        '''
        if buttonNum < 1 or buttonNum > 5:
            raise ValueError("Mouse buttons are 1-3; mouse wheel up is 4; mouse wheel down is 5. Called with %d" % buttonNum)
        resCode = subprocess.call(['xdotool', 'getactivewindow', 'mousedown', str(buttonNum)]);

    def mouseUp(self, buttonNum):
        '''
		Buttons map this way: Left mouse is 1, middle is 2, right is 3,
		wheel up is 4, wheel down is 5.
        :param buttonNum: which mouse button to hold down
        :type buttonNum: int
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
        :param x: horizontal coordinate
        :type x: int
        :param y: vertical coordinate
        :type y: int
        '''
        resCode = subprocess.call(['xdotool', 'mousemove', '--sync', str(x), str(y)]);

    def moveMouseRelative(self, x, y):
        '''
        Move mouse cursor new position relative to where
        it is currently located. It is legal to use negative 
        offsets for x and/or y.
        :param x: horizontal coordinate
        :type x: int
        :param y: vertical coordinate
        :type y: int
        '''
        resCode = subprocess.call(['xdotool', 'mousemove_relative', '--sync', '--', str(x), str(y)]);

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
        
    vBoard.moveMouseRelative(-100, 100);
    
    

        