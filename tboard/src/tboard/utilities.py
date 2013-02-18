import sys;
import os;



class Utilities(object):    
    
    @staticmethod
    def findFile(path, matchFunc=os.path.isfile):
        if path is None:
            return None
        for dirname in sys.path:
            candidate = os.path.join(dirname, path)
            if matchFunc(candidate):
                return candidate
        return None;
