#!/usr/bin/python2
# vim: set fileencoding=utf-8 :
# Alexander Grothe 2011 - 2012
#
# This script requires python-uinput V 0.6.1. or higher. Additional required packages are libudev0 and libudev-dev.
#
### Fetch the code for python-uinput from git: ###
#
# git clone git://github.com/tuomasjjrasanen/python-uinput.git
# cd python-uinput
# git clone git://github.com/tuomasjjrasanen/libsuinput.git
# sudo python setup.py install
#
###
#
# This script must be run as superuser or with sufficent rights to create an uinput device and exspects a lircd socket using pid from /var/run/lirc/lircd.pid under /var/run/lirc/lircd.<pid of lircd> if none is given by --lircd-socket /PATH/TO/LIRCD_SOCKET
# lircd must not be startet with --uinput, but may be started with --release="_up" to prevent ghosting events if necessary.

import syslog
import string
import socket
import gobject
import sys
import uinput
import datetime
from threading import Timer
from optparse import OptionParser

class Lirc2uinput:
    """Sends keystrokes to a virtual uinput device after applying a repeat-filter"""
    def __init__(self, uinput_name="lircd", options=None, debug=None):
        self.lastkey = None
        self.wait_repeats = options.wait_repeats
        self.max_gap = options.max_gap
        self.min_gap = options.min_gap
        self.acceleration = options.acceleration
        self.lircd_socket = options.lircd_socket
        self.xbmc = options.xbmc
        self.gap_delta = (self.max_gap - self.min_gap)*self.acceleration
        self.current_gap = self.max_gap
        self.repeat_num = 0
        self.debug = debug
        self.timestamp = datetime.datetime.now()
        self.timeout_value = 1
        self.events = []
        self.timeout = Timer(self.timeout_value, uinput.KEY_COFFEE)
        # add all defined KEY_.* to supported key events
        for element in dir(uinput):
          if element.startswith("KEY_"):
            self.events.append(eval("uinput.%s"%element))
            self.debug.log("uinput.%s"%element)
        # create uinput device
        self.specialkeys = [uinput.KEY_VOLUMEUP, uinput.KEY_VOLUMEDOWN]
        self.device = uinput.Device(self.events, uinput_name)
        #self.specialkeys = [(1, 114),(1, 115)] # KEY_VOLUMEDOWN and KEY_VOLUMEUP - a "real" repeat behaviour is used.
        #print "init"

    def get_gap(self,repeat_num):
        if self.current_gap > self.min_gap:
            self.current_gap = self.current_gap - self.gap_delta
        else:
            self.debug.log("minimum gap reached")
            pass
        return self.current_gap

    def getKeyname(self, key):
        try:
          if key[0].islower():
              keycmd = eval('uinput.%s'%(key.upper()))
              k_upper = False
          else:
              keycmd = eval('uinput.%s'%(key.replace('_up','')))
              k_upper = True
              # '_up' ist a suffix added by lircd to keynames optionally to signal key release
        except: 
          keycmd = uinput.KEY_COFFEE
          k_upper = True
          self.debug.log("Key %s is not supported by your input.h, get a coffee ;)"%key)
        #print "%s mapped to %s"%(key,keycmd)
        return keycmd, k_upper
   
    def send_key_r(self,key):
        keycmd, k_upper = self.getKeyname(key)
        self.debug.log(keycmd)
        
        now = datetime.datetime.now()
        # repeated keypress
        if self.lastkey == keycmd and (now - self.timestamp).microseconds < self.current_gap:
                self.debug.log("Passing keypress %s... too early"%(unicode(keycmd)))
                pass     
        elif self.lastkey == keycmd:
                self.debug.log("Repeated keypress %s" %(unicode(keycmd)))
                if self.repeat_num >= self.wait_repeats:
                    self.current_gap = self.get_gap(self.repeat_num)
                else:
                    pass
                if self.repeat_num > 0:
                    self.keypress(keycmd, 2)
                self.timestamp = datetime.datetime.now()
                self.repeat_num += 1
        else:
            self.keypress(keycmd, 1)
            self.repeat_num += 1
        self.lastkey=keycmd
        return keycmd
                
    def send_key(self,key):
        keycmd, k_upper = self.getKeyname(key)
        self.debug.log(keycmd)
        if self.xbmc and keycmd not in self.specialkeys:
                self.keypress(keycmd, 1)
                self.keypress(keycmd, 0)
        else:
            if self.lastkey == keycmd and self.repeat_num > 0:
                self.keypress(keycmd, 2)
            else:
                self.keypress(keycmd, 1)
        self.repeat_num += 1
        self.lastkey=keycmd
        return keycmd
               
    def keypress(self, key, value):
        self.device.emit(key, value)

class main:
    """Listens to LIRC's domain socket and calls a method each time an
    IR command is received."""
    def __init__(self):
        parser = Options()
        self.options = parser.get_opts()
        self.Dbg = Debug(self.options.debug)
        self.timeout = self.options.timeout
        if (self.timeout * 1000) < self.options.min_gap:
            self.timeout = self.options.min_gap + 10000
            self.Dbg.log("Warning: timeout < --min-gap: setting timeout 10ms greater than --min-gap")
        self.repeatfilter = self.options.repeatfilter
        self.xbmc = self.options.xbmc
        self.syslog_init()
        self.timer = None
        if not self.options.lircd_socket:
            # use /var/run/lirc/lircd.<pidof lircd> as socket
            try:
                with open("/var/run/lirc/lircd.pid", 'r') as pidfile:
                    pid = int(pidfile.read().strip("\n"))
                self.socket_path =  "/var/run/lirc/lircd.%s"%(pid)
            except IOError:
                self.Dbg.log(syslog.LOG_ERR, 'Error reading PID for lircd, I will sleep 1 second and exit this script')
                time.sleep(1)
                sys.exit("socket not found")
            finally:
                self.Dbg.log('lircd_socket = %s'%(self.socket_path))
        else:
            self.socket_path = self.options.lircd_socket
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.socket_path)
        self.uinputdev = Lirc2uinput(options=self.options, debug=self.Dbg)
        if self.repeatfilter:
            self.command = "send_key_r"
            gobject.io_add_watch(self.sock, gobject.IO_IN, self.handler)
        else:
            self.command = "send_key"
            gobject.io_add_watch(self.sock, gobject.IO_IN, self.handler)
            
    def handler(self, sock, *args):
        try:
             gobject.source_remove(self.timer)
             #print "removed timer"
        except: pass
        buf = self.sock.recv(1024)
        lines = string.split(buf, "\n")
        for line in lines[:-1]:
            code,count,cmd,device = string.split(line, " ")
            keycmd = eval("self.uinputdev.%s(cmd)"%(self.command))
            self.timer = gobject.timeout_add(self.timeout, self.release_key,keycmd)
        return True
        
    def release_key(self, keycmd):
        self.uinputdev.keypress(keycmd, 0)
        self.uinputdev.repeat_num = 0
        self.uinputdev.lastkey = None
        self.uinputdev.current_gap = self.uinputdev.max_gap
        #print 'released key', keycmd
        return 0
            
    def syslog_init(self):
        self.Dbg.log('Started lircd2uinput with these options:')
        self.Dbg.log('wait_repeats = %s'%(self.options.wait_repeats))
        self.Dbg.log('max_gap = %s'%(self.options.max_gap))
        self.Dbg.log('min_gap = %s'%(self.options.min_gap))
        self.Dbg.log('acceleration = %s'%(self.options.acceleration))


class Options:
    def __init__(self):
        self.parser = OptionParser()
        self.parser.add_option("-f", "--repeat-filter", dest="repeatfilter", action="store_true",
                  help=u'enable repeat-filter')
        self.parser.add_option("-s", "--lircd-socket", dest="lircd_socket", default=None,
                  help=u"choose lircd socket to listen on", metavar="LIRCD_SOCKET")
        self.parser.add_option("-d", "--debug", dest="debug", action="store_true",
                  help=u'enable debug mode')
        self.parser.add_option("-x", "--xbmc", dest="xbmc", action="store_true",
                  help=u'enable xbmc single keypress mode')
        self.parser.add_option("-l", "--min-gap", dest="min_gap", default=150000, type="int",
                  help=u"set minimum gap between repeated keystrokes (default 150000 µs) - needs active repeat-filter", metavar="MIN_GAP")
        self.parser.add_option("-u", "--max-gap", dest="max_gap", default=300000, type="int",
                  help=u"set maximum gap between repeated keystrokes (default 300000 µs) - needs active repeat-filter", metavar="MAX_GAP")
        self.parser.add_option("-r", "--min-repeats", dest="wait_repeats", default=2, type="int",
                  help=u"number of repeats before using accelerated keypresses (default = 2) - needs active repeat-filter", metavar="WAIT_REPEATS")
        self.parser.add_option("-t", "--timeout", dest="timeout", default=200, type="int",
                  help=u"release key after x ms no following key is received (default = 200 ms)", metavar="TIMEOUT")
        self.parser.add_option("-a", "--acceleration", dest="acceleration", default=0.25, type="float",
                  help=u"acceleration to get from MAX_GAP to MIN_GAP. default value of 0.25 equals 4 repeated keystrokes to reach maximum speed - needs active repeat-filter",
                    metavar="ACCELERATION")

        
                  
    def get_opts(self):
        (options, args) = self.parser.parse_args()
        return options
        
class Debug():
    def __init__(self,isactive=False):
        self.active = isactive
        
    def log(self, message):
        if self.active:
              syslog.syslog(unicode(message))



if __name__ == "__main__":
    vlirc = main()
    gobject.MainLoop().run()
