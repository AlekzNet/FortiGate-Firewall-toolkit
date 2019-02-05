#!/usr/bin/python

import string
import argparse
import re
import sys

try:
	import netaddr
except ImportError:
	print >>sys.stderr, 'ERROR: netaddr module not found, you can install it with \"pip install netaddr\"'
	sys.exit(1)

try:
	import pprint
except ImportError:
	print >>sys.stderr, 'ERROR: pprint module not found. Either install pprint with \"pip install pprint\" \n or replace pprint.pprint with print (the debug function)'
	sys.exit(1)

def debug(string,level=1):
	if args.verbose >= level:
		pprint.pprint(string,sys.stderr,width=70)





class PRule:
	'Class for a rule prototype'

	re_any=re.compile(r'^any$', re.IGNORECASE)
	re_dig=re.compile(r'^\d')		# digital
	re_nondig=re.compile(r'^\D') 	# non-digital
	re_spaces=re.compile(r'\s+') 	# lots of spaces/tabs
	re_comma=re.compile(r'\s*,\s*') # comma, surrounded by spaces/tabs (or not))
	re_remark=re.compile(r'^\s*#')	# the whole line is a comment/remark
	re_comment=re.compile(r'(?P<line>.*)\s*#(?P<comment>.*)') # if there is a comment in the line?


# line (str) - policy line
# deny (boolean) - by default the action is "allow", unless there is an explicit "deny" in the line
# 		 if deny is set to True, the action will be "deny"
	def __init__(self,line,deny=False):
		self.src=[]
		self.dst=[]
		self.srv=[]
		self.action="deny" if deny else "permit"
		self.comment=""
		line=line.strip()
# If the line begins with "#" it's a comment		
		if self.re_remark.search(line):
			self.type="comment"
			self.comment=self.re_remark.sub("",line)
			self.line=None
			return
		else:
			self.type="rule"
		self.line=self.cleanup(line)
		debug(self.line,2)
		self.parse()

	def cleanup(self,line):
		debug("cleanup -- before clean-up: %s" % line,3)
		if self.re_comment.search(line):
			self.comment=self.re_comment.search(line).group('comment')
			line=self.re_comment.search(line).group('line')
		line=self.re_spaces.sub(" ",line)
		line=self.re_comma.sub(",",line)
		debug("After clean-up: %s" % line,3)		
		return line
		
# addr = IP/mask
# return = 1.2.3.4 255.255.255.255
	def cidr2str(self,addr):
		debug("cidr2str -- addr = %s" % addr,4)
		tmp = netaddr.IPNetwork(addr)
		return ' '.join([str(tmp.ip),str(tmp.netmask)])		
		
	def check_arr(self,arr):
		if not len(arr):
			debug(self.line,0)
			debug("Too few fields in the policy.",0)
			sys.exit(1)

# arr -- takes a list, extracts the next address(es), removes the elements from the list
# returns a list of addresses
	def parse_addr(self,arr):
		debug("parse_addr -- arr", 3)
		debug(arr,4)
		if 'any' in  arr[0]:
			addr=['any']
			del arr[0]
		elif not ',' in arr[0]:
			if '/' in arr[0]:
				addr = [self.cidr2str(arr[0])]
				del arr[0]
			elif '0.0.0.0' in arr[0] and '0.0.0.0' in arr[1]:
				addr=['any']
				del arr[0:2]
			else:
				addr = [' '.join(arr[0:2])]
				del arr[0:2]
		else:
			addr = [self.cidr2str(x) for x in arr[0].split(',')]
			addr.sort()
			del arr[0]
		debug("parse_addr - addr = %s" % addr,3)
		return addr

# used when inly the source or destination IP-addresses are used in the line
# returns a list of one IP-address
	def parse_addr_args(self,addr):
		if '/' in addr:
			return [self.cidr2str(addr)]
		elif self.re_any.search(addr):
			return ['any']
		elif self.re_nondig.match(addr):
			return ["object-group "+addr]
		elif ' ' in addr:
			return [addr]
		else: return [addr+' 255.255.255.255']

	def parse(self):
			
		addr1=''
		addr2=''

		arr=self.line.split()

		# Get the first address
		addr1=self.parse_addr(arr)
		debug("addr1 is %s" % addr1,3)
		self.check_arr(arr)

		if self.re_dig.match(arr[0]) or 'any' in arr[0] or 'host' in arr[0]:
			addr2=self.parse_addr(arr)
			debug("addr2 is %s" % addr2,3)
			self.check_arr(arr)

		if not ',' in arr[0]:
			self.srv=[arr[0]]
		else:
			self.proto = ''
			self.srv = [ x for x in arr[0].split(',')]
		del arr[0]

		if len(arr): self.action = arr[0]

		if addr2:
			self.src = addr1
			self.dst = addr2
		elif args.src:
			self.src = self.parse_addr_args(args.src)
			self.dst = addr1
		elif args.dst:
			self.src = addr1
			self.dst = self.parse_addr_args(args.dst)
		else:
			debug(self.line,0)
			debug("Either too few fields or define either --src IP or --dst IP",0)
			sys.exit(1)
		debug("Src = %s" % self.src,2)
		debug("Dst = %s" % self.dst,2)
		debug("Srv = %s" % self.srv,2)
		debug("Action = %s" % self.action,2)
		debug("Comment = %s" % self.comment,2)
		
	

class FW():
	'General Firewall Class'
	devtype='' #Device type
	rulenum = 0
	netgrp_name='obj_net_' 	# Template for network object-group
	netgrp_cnt=0 			# network object-group counter shift
	srvgrp_name='obj_srv_' 	# Template for service object-group
	srvgrp_cnt=0 			# service object-group counter shift
	log='' 					# logging
	comment=''				# comments

	def fw_netobj_print(self,netobj):
		pass

	def fw_srvobj_print(self,srvobj):
		pass

	def netobj_add(self,netobj,rule):
		pass

	def netgrp_add(self,netgrp,rule):
		pass

	def srvobj_add(self,srvobj,rule):
		pass

	def srvgrp_add(self,srvgrp,rule):
		pass
		
# Create object names:
# h-001.020.003.004  -- for hosts
# n-001.020.003.000_24 -- for networks			
# net - netaddr.IPNetwork(ip)
	def net2name(self,ip):
		net=str(ip.network)
		mask=str(ip.prefixlen)
		if self.ishost(ip): return 'h-' + self.ip2txt(net)
		else: return 'n-' + self.ip2txt(net) + '_'+mask

# ip - string IP-address -- 1.2.3.4
# returns - 001.002.003.004
	def ip2txt(self,ip):
		return ".".join(map(self.octet2txt,ip.split('.')))

# octet - string of 0...255 (e.g. 12, 1, 123)
# returns 012, 001, 123
	def octet2txt(self,octet):
		if len(octet) < 3:
			octet = "0" + octet if len(octet) == 2 else "00" + octet
		return octet

# Returns True if the netmask is 32, and False otherwise
# ip is a netaddr object
	def ishost(self,ip):
		return True if ip.prefixlen == 32 else False		

class FGT(FW):
	'FortiGate specific class'
	devtype='fgt'
	vdom = ''
	srcintf = ''
	dstintf = ''
	mingrp=0 #minimal amount of objects in the rule to move in a separate group

	re_any = re.compile('any|all|0\.0\.0\.0 0\.0\.0\.0|0\.0\.0\.0/0', re.IGNORECASE)

	predefsvc = {'tcp:540': 'UUCP', 'udp:1-65535': 'ALL_UDP', 'tcp:7000-7009 udp:7000-7009': 'AFS3', 'tcp:70': 'GOPHER', 'IP:89': 'OSPF', 'ip': 'ALL', 'udp:520': 'RIP', 'tcp:1723': 'PPTP', 'udp:67-68': 'DHCP', 'tcp:1720': 'NetMeeting', 'IP:51': 'AH', 'udp:389': 'LDAP_UDP', 'udp:500 udp:4500': 'IKE', 'IP:50': 'ESP', 'udp:517-518': 'TALK', 'tcp:1080 udp:1080': 'SOCKS', 'tcp:465': 'SMTPS', 'IP:47': 'GRE', 'tcp:5631 udp:5632': 'PC-Anywhere', 'tcp:79': 'FINGER', 'tcp:554 tcp:7070 tcp:8554 udp:554': 'RTSP', 'tcp:1433-1434': 'MS-SQL', 'icmp': 'ALL_ICMP', 'tcp:143': 'IMAP', 'tcp:111 tcp:2049 udp:111 udp:2049': 'NFS', 'tcp:995': 'POP3S', 'tcp:993': 'IMAPS', 'udp:2427 udp:2727': 'MGCP', 'tcp:1512 udp:1512': 'WINS', 'tcp:512': 'REXEC', 'udp:546-547': 'DHCP6', 'tcp:5900': 'VNC', 'tcp:3389': 'RDP', 'tcp:6660-6669': 'IRC', 'udp:1645-1646': 'RADIUS-OLD', 'udp:33434-33535': 'TRACEROUTE', 'tcp:80': 'HTTP', 'tcp:2401 udp:2401': 'CVSPSERVER', 'tcp:2000': 'SCCP', 'tcp:1863': 'SIP-MSNmessenger', 'tcp:161-162 udp:161-162': 'SNMP', 'tcp:210': 'WAIS', 'tcp:1720 tcp:1503 udp:1719': 'H323', 'ICMP:8': 'PING', 'tcp:5060 udp:5060': 'SIP', 'tcp:1701 udp:1701': 'L2TP', 'tcp:389': 'LDAP', 'tcp:123 udp:123': 'NTP', 'udp:26000 udp:27000 udp:27910 udp:27960': 'QUAKE', 'tcp:21': 'FTP', 'tcp:5190-5194': 'AOL', 'tcp:23': 'TELNET', 'tcp:53 udp:53': 'DNS', 'tcp:25': 'SMTP', 'tcp:6000-6063': 'X-WINDOWS', 'tcp:7000-7010': 'VDOLIVE', 'tcp:3128': 'SQUID', 'tcp:88 udp:88': 'KERBEROS', 'tcp:0': 'NONE', 'tcp:443': 'HTTPS', 'tcp:445': 'SMB', 'tcp:1-65535': 'ALL_TCP', 'ICMP6:128': 'PING6', 'udp:69': 'TFTP', 'udp:7070': 'RAUDIO', 'tcp:1755 udp:1024-5000': 'MMS', 'udp:1812-1813': 'RADIUS', 'tcp:135 udp:135': 'DCE-RPC', 'tcp:179': 'BGP', 'udp:514': 'SYSLOG', 'tcp:110': 'POP3', 'tcp:119': 'NNTP', 'ICMP:13': 'TIMESTAMP', 'tcp:3306': 'MYSQL', 'tcp:22': 'SSH', 'tcp:111 udp:111': 'ONC-RPC', 'icmp:17': 'INFO_ADDRESS', 'tcp:139': 'SAMBA', 'icmp:15': 'INFO_REQUEST', 'tcp:1494 tcp:2598': 'WINFRAME'}

	def __init__(self,vdom='root',srcintf='any',dstintf='any',rulenum=10000, label='', log=False, comment='', mg=0):
		self.vdom = vdom
		self.srcintf = srcintf
		self.dstintf = dstintf
		self.rulenum=rulenum 	# begin with this rulenumber: edit rulenum
		self.label=label		# section label
		self.mingrp=mg
		self.log = log
		self.comment = comment

	def rprint(self,policy):
		if self.vdom:
			self.fw_header_print()
		self.fw_netobj_print(policy.netobj)
		self.fw_srvobj_print(policy.srvobj)
		self.fw_rules_print(policy)
		self.fw_footer_print()

	def fw_header_print(self):
		if self.vdom:
			print 'config vdom'
			print 'edit ' + self.vdom

	def fw_footer_print(self):
		print 'end'

	def fw_rules_print(self,policy):
		print 'config firewall policy'
		policy.srvobj.update(self.predefsvc)
		for rule in policy.policy:
			if "comment" in rule.type: 
				self.label = rule.comment
				next
			print ' edit ' + str(self.rulenum)
			print '  set srcintf ' + self.srcintf
			print '  set dstintf ' + self.dstintf
			print '  set srcaddr ' + ' '.join(map(lambda x: policy.netobj[x], rule.src))
			print '  set dstaddr ' + ' '.join(map(lambda x: policy.netobj[x], rule.dst))
			print '  set service ' + ' '.join(map(lambda x: policy.srvobj[x], rule.srv))
			print '  set schedule always'
			print '  set status enable'
			if 'permit' in rule.action:
				print '  set action accept'
			else:
				print '  set action deny'
			if self.label:
				print '  set global-label "' + self.label + '"'
			if self.log:
				if type(self.log) is string and "disable" in self.log:
					print '  set logtraffic disable'
				else:
					print '  set logtraffic all'
			if self.comment or rule.comment:
				print '  set comments "'+ self.comment + ' ' + rule.comment + '"'
			self.rulenum += 1
			print ' next'
		print 'end'

	def fw_netobj_print(self,netobj):
		print 'config firewall address'
		for obj in netobj:
			print ' edit '+ netobj[obj]
			print '  set subnet ' + obj
			print ' next'
		print 'end'

	def fw_srvobj_print(self,srvobj):
		print 'config firewall service custom'
		for obj in srvobj:
			if not '*' in obj:
				# For some reason the following construction does not work
				# proto,ports = obj.split(':') if ':' in obj else obj,''
				if ':' in obj:	proto,ports = obj.split(':')
				else: proto,ports = obj,''
				print ' edit ' + srvobj[obj]
				if 'udp' in proto or 'tcp' in proto:
					print '  set protocol TCP/UDP/SCTP'
					print '  set ' + proto + '-portrange ' + ports
				elif 'icmp' in proto:
					print '  set protocol ICMP'
					if ports:
						print '  set icmptype ' + ports
				elif 'ip' in proto:
					if ports:
						print '  set protocol IP'
						print '  set protocol-number ' + ports
				else:
					print '  set protocol IP'
					print '  set protocol-number ' + proto
				print ' next'
		print 'end'

	def netobj_add(self,netobj,rule):
		for addrs in rule.src,rule.dst:
			# Convert a single IP-address to a list
#			if not type(addrs) is list: addrs=[addrs]
			for addr in addrs:
				if addr not in netobj:
					if self.re_any.search(addr):
						netobj[addr]  = 'all'
					else: netobj[addr] = self.net2name(netaddr.IPNetwork(re.sub(' ','/',addr)))

	def srvobj_add(self,srvobj,rule):
		services = rule.srv
#		if not type(services) is list: services=[services]
		for srv in services:
			if srv not in srvobj and srv not in self.predefsvc:
				if '*' in srv:
					srvobj[srv] = 'ALL'
				else:
					srvobj[srv]=re.sub(':','-',srv)


class ASA(FW):
	'ASA specific class'
	devtype='asa'
	aclname='' #ACL name


	def __init__(self,aclname='Test_ACL',rulenum=0, log=False, comment=''):
		self.aclname=aclname
		self.rulenum=rulenum
		if log: self.log = "log"
		self.comment = comment

	def fw_rules_print(self,policy):
		if self.comment:
			print ' '.join(["access-list", self.aclname, self.rule_line(), "remark", self.comment])
		for rule in policy.policy:
			if "comment" in rule.type:
				print ' '.join(["access-list", self.aclname, self.rule_line(), "remark", rule.comment])
			else:
				if  rule.comment:
					print ' '.join(["access-list", self.aclname, self.rule_line(), "remark", rule.comment])
				print  ' '.join(["access-list", self.aclname, self.rule_line(), "extended", rule.action, self.rule_proto(rule), \
					self.rule_addr(rule.src), self.rule_addr(rule.dst), self.rule_port(rule), self.log])

	def rule_proto(self,rule):
		if len(rule.srv) > 1:
			return 'object-group ' + policy.srvgrp[tuple(rule.srv)]
		else:
			return self.protocol(rule.srv[0])

	def rule_line(self):
		if self.rulenum > 0:
			line = 'line ' + str(self.rulenum)
			self.rulenum += 1
		else:
			line=''
		return line

	def rule_port(self,rule):
		if len(rule.srv) > 1:
			return ''
		else:
			return self.port(rule.srv[0])

	def rule_addr(self,addr):
		if len(addr) > 1:
			return 'object-group ' + policy.netgrp[tuple(addr)]
		else:
			return addr[0]

	def rprint(self,policy):
		self.fw_header_print()
		self.fw_netgrp_print(policy.netgrp)
		self.fw_srvgrp_print(policy.srvgrp)
		self.fw_rules_print(policy)
		self.fw_footer_print()

	def fw_header_print(self):
		print 'config terminal'

	def fw_footer_print(self):
		print 'wri'
		print 'exit'

	def fw_netgrp_print(self,netgrp):
		for addrs in netgrp:
			print 'object-group network',netgrp[tuple(addrs)]
			for addr in addrs:
				print ' network-object',addr

	def fw_srvgrp_print(self,srvgrp):
		for svcs in srvgrp:
			print 'object-group service',srvgrp[tuple(svcs)]
			for svc in svcs:
				if 'icmp' in self.protocol(svc):
					print ' service-object',self.protocol(svc),'icmp_type',self.port(svc)
				else:
					print ' service-object',self.protocol(svc),'destination',self.port(svc)

	def protocol(self,service):
		if "*" in service:
			return "ip"
		elif ":" in service:
			tmp = service.split(":")
			return tmp[0]
		else:
			return service

	def port(self,service):
		if ":" in service:
			tmp = service.split(":")
			if "-" in tmp[1]:
				low,high = tmp[1].split("-")
				if int(low) == 1:
					return "lt " +high
				elif int(high) == 65535:
					return "gt " +low
				else:
					return "range "+low+" "+high
			elif "icmp" not in tmp[0]:
				return "eq "+tmp[1]
			else:
				return tmp[1]
		else:
			return ''

	def netgrp_add(self,netgrp,rule):
		for addrs in rule.src,rule.dst:
			if len(addrs) > 1:
				if tuple(addrs) not in netgrp:
					objname=self.netgrp_name+str(len(netgrp)+1+self.netgrp_cnt)
					netgrp[tuple(addrs)]=objname


	def srvgrp_add(self,srvgrp,rule):
		if len(rule.srv) > 1:
			if tuple(rule.srv) not in srvgrp:
				objname=self.srvgrp_name+str(len(srvgrp)+1+self.srvgrp_cnt)
				srvgrp[tuple(rule.srv)]=objname


class Policy(PRule):
	'Class for the whole policy'
	netobj = {} # { '10.0.1.0 255.255.255.0': 'n-010.000.001.000_24' }
	srvobj = {} # { 'tcp:20-23': 'TCP-20-23' }
	netgrp = {}	# { 'net-group1: }network-groups
	srvgrp = {}	# service-groups
	policy = [] # global policy
	device = '' # 'ASA' or 'FGT' class object

	def __init__(self,dev):
		self.device = dev

	def getdev(self):
		return self.device

	def addrule(self,rule):
		self.policy.append(rule)

	def getpol(self):
		return self.policy

	def get_objects(self):
		for rule in self.policy:
			self.device.netobj_add(self.netobj,rule)
			self.device.netgrp_add(self.netgrp,rule)
			self.device.srvobj_add(self.srvobj,rule)
			self.device.srvgrp_add(self.srvgrp,rule)

	def rprint(self):
		self.get_objects()
		self.device.rprint(self)


parser = argparse.ArgumentParser(description='Creates Cisco ASA or Fortigate policy')
parser.add_argument('pol', default="-", nargs='?', help="Firewall policy or \"-\" to read from the console (default)")
parser.add_argument('-v','--verbose', default=0, help='Verbose mode. Messages are sent to STDERR.\n To increase the level add "v", e.g. -vvv', action='count')
sd = parser.add_mutually_exclusive_group()
sd.add_argument('-s','--src', default=False, help="Source IP-address/netmask or object name")
sd.add_argument('-d','--dst', default=False, help="Destination IP-address/netmasks or object name")
parser.add_argument('--deny', help="Use deny by default instead of permit", action="store_true")
log = parser.add_mutually_exclusive_group()
log.add_argument('--log', default=False, help="Logging. Default: none for ASA, utm for FGT. ", action="store_true")
log.add_argument('--nolog', default=False, help="Logging. Default: none for ASA, utm for FGT. ", action="store_true")
parser.add_argument('--comment', default='', help="Comment, Default - none")
parser.add_argument('--dev', default="asa", choices=['asa','fgt'], help="Type of device: asa (default) or fgt")
asa = parser.add_argument_group('Cisco ASA')
asa.add_argument('--acl', default="Test_ACL", nargs='?', help="ACL name for ASA. Default=Test_ACL")
asa.add_argument('--ln', default=0, help="Starting line number for ASA. Default - 0 (no line numbers)", type=int)
fgt = parser.add_argument_group('Fortigate')
fgt.add_argument('--vdom', default='', help="VDOM name for FortiGate. Default - none")
fgt.add_argument('--si', default="any", help="Source interface for FortiGate. Default - any")
fgt.add_argument('--di', default="any", help="Destination interface for FortiGate. Default - any")
fgt.add_argument('--rn', default=10000, help="Starting rule number for Fortigate. Default - 10000")
fgt.add_argument('--label', default='', help="Section label, Default - none")


args = parser.parse_args()


f=sys.stdin if "-" == args.pol else open (args.pol,"r")

if 'asa' in args.dev:
	dev=ASA(args.acl,args.ln, args.log, args.comment)
elif 'fgt' in args.dev:
	if args.nolog: args.log = "disable"
	dev=FGT(args.vdom, args.si, args.di, int(args.rn), args.label, args.log, args.comment)
else:
	print >>sys.stderr, dev, "- not supported device. It should be asa (Cisco ASA) or fgt (FortiGate)"
	sys.exit(1)

policy = Policy(dev)

for line in f:
	r=PRule(line,args.deny)
	policy.addrule(r)

policy.rprint()
