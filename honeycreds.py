#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author: Ben Ten (Ben0xA)
# HoneyCreds - Detecting LLMNR/NBNS/HTTP Listeners
# Updated: 10/29/2020
# Version: 0.1

# Requires:
# python 3
# smbprotocol
# cffi

import smbclient
import os
import subprocess
import logging
import time
import sys
import requests
import threading
from signal import signal, SIGINT

# You can set these once or specify them on the command line.
# Please... change these... really. If I see this on a pentest, I will cry.
def_username = 'honeycreds'
def_domain   = 'XQQX'
def_password = 'This is a honey cred account.'
def_fqdn     = 'xqqx.local'
def_hostname = 'HNECRD01'
def_logfile  = 'honeycreds.log'

SMB = 'ON'
HTTP = 'ON'
SMB_SLEEP = 5
HTTP_SLEEP = 12
smb_Thread = None
http_Thread = None
smb_exit = threading.Event()
http_exit = threading.Event()

def signal_handler(sig, frame):	
	global smb_Thread, http_Thread, exit
	print('')
	print('[*] Exiting...')	
	if smb_Thread and smb_Thread.is_alive():
		print('[*] Terminating SMB Client, please wait...')		
		smb_exit.set()
		smb_Thread.join()
		print('[*] SMB Client terminated.')
	if http_Thread and http_Thread.is_alive():
		print('[*] Terminating HTTP Client, please wait...')		
		http_exit.set()
		http_Thread.join()
		print('[*] HTTP Client terminated.')

def init():
	global SMB, HTTP
	log_format = ('[%(asctime)s] %(levelname)-8s %(name)-12s %(message)s')	
	logging.basicConfig(
		level=logging.CRITICAL,
		format=log_format,
		filename=(def_logfile)
	)
	SMB = str.upper(SMB)
	HTTP = str.upper(HTTP)

def banner():
	oncolor = termcolor.GREEN
	print(termcolor.YELLOW + termcolor.BOLD + '       .-=-=-=-.        ' + termcolor.END)
	print(termcolor.YELLOW + termcolor.BOLD + '     (`-=-=-=-=-`)      ' + termcolor.END)
	print(termcolor.YELLOW + termcolor.BOLD + '   (`-=-=-=-=-=-=-`)    ' + termcolor.WHITE + '  _   _                              ___                     _       ' + termcolor.END)
	print(termcolor.YELLOW + termcolor.BOLD + '  (`-=-=-=-=-=-=-=-`)   ' + termcolor.WHITE + ' ( ) ( )                            (  _ \\                  ( )      ' + termcolor.END)
	print(termcolor.YELLOW + termcolor.BOLD + ' ( `-=-=-=-(@)-=-=-` )  ' + termcolor.WHITE + ' | |_| |   _     ___     __   _   _ | ( (_) _ __    __     _| |  ___ ' + termcolor.END)
	print(termcolor.YELLOW + termcolor.BOLD + ' (`-=-=-=-=-=-=-=-=-`)  ' + termcolor.WHITE + ' |  _  | / _ \\ /  _  \\ / __ \\( ) ( )| |  _ (  __) / __ \\ / _  |/  __)' + termcolor.END)
	print(termcolor.YELLOW + termcolor.BOLD + ' (`-=-=-=-=-=-=-=-=-`)  ' + termcolor.WHITE + ' | | | |( (_) )| ( ) |(  ___/| (_) || (_( )| |   (  ___/( (_| |\\__  \\' + termcolor.END)
	print(termcolor.YELLOW + termcolor.BOLD + ' (`-=-=-=-=-=-=-=-=-`)  ' + termcolor.WHITE + ' (_) (_) \\ __/ (() (_) )\\___) \\__  |(____/ (()    )\\___) ) _ _)(__(_/' + termcolor.END)
	print(termcolor.YELLOW + termcolor.BOLD + ' (`-=-=-=-=-=-=-=-=-`)  ' + termcolor.WHITE + '         /(    (_)    (__)   ( )_| |       (_)   (__)   (__)     /(  ' + termcolor.END)
	print(termcolor.YELLOW + termcolor.BOLD + '  (`-=-=-=-=-=-=-=-`)   ' + termcolor.WHITE + '        (__)                  \\___/                             (__) ' + termcolor.END)
	print(termcolor.YELLOW + termcolor.BOLD + '   (`-=-=-=-=-=-=-`)' + termcolor.END)
	print(termcolor.YELLOW + termcolor.BOLD + '     (`-=-=-=-=-`)' + termcolor.END)
	print(termcolor.YELLOW + termcolor.BOLD + '      `-=-=-=-=-`' + termcolor.END)
	print(termcolor.YELLOW + '                                   Author: ' + termcolor.WHITE + termcolor.BOLD + 'Ben Ten (@ben0xa)' + termcolor.END + termcolor.WHITE + ' - ' + termcolor.YELLOW + 'Version: ' + termcolor.WHITE + termcolor.BOLD + '0.1' + termcolor.END)
	print('')
	print(termcolor.GREEN + termcolor.BOLD + '[+]' + termcolor.END + ' Clients:')	
	if str.upper(SMB) == 'OFF':
		oncolor = termcolor.RED
	else:
		oncolor = termcolor.GREEN
	print('    SMB Client\t\t' + oncolor + termcolor.BOLD + '[' + SMB + ']' + termcolor.END)
	if str.upper(HTTP) == 'OFF':
		oncolor = termcolor.RED
	else:
		oncolor = termcolor.GREEN
	print('    HTTP Client\t\t' + oncolor + termcolor.BOLD + '[' + HTTP + ']' + termcolor.END)
	print('')
	print(termcolor.GREEN + termcolor.BOLD + '[+]' + termcolor.END + ' Generic Options:')
	print('    Domain\t\t' + termcolor.YELLOW + termcolor.BOLD + '[' + def_domain + ']' + termcolor.END)
	print('    Username\t\t' + termcolor.YELLOW + termcolor.BOLD + '[' + def_username + ']' + termcolor.END)
	print('    Password\t\t' + termcolor.YELLOW + termcolor.BOLD + '[' + def_password + ']' + termcolor.END)
	print('    Hostname\t\t' + termcolor.YELLOW + termcolor.BOLD + '[' + def_hostname + ']' + termcolor.END)
	print('    FQDN\t\t' + termcolor.YELLOW + termcolor.BOLD + '[' + def_fqdn + ']' + termcolor.END)
	print('    SMB Sleep\t\t' + termcolor.YELLOW + termcolor.BOLD + '[' + str(SMB_SLEEP) + ' seconds]' + termcolor.END)
	print('    HTTP Sleep\t\t' + termcolor.YELLOW + termcolor.BOLD + '[' + str(HTTP_SLEEP) + ' seconds]' + termcolor.END)
	print('')

class termcolor:
    WHITE = '\033[37m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    RED = '\033[31m'
    END = '\033[0m'
    BOLD = '\033[1m'

class messages:
	RSP_RECVD = '%(color)s%(bold)s[%(proto)s]%(end)s Poisoned response received from %(ip)s for name %(hostname)s.'
			
class SMBClient(threading.Thread):
	def __init__(self, username, hostname):
		threading.Thread.__init__(self)
		self.username = username
		self.hostname = hostname

	def run(self):
		global def_password, smb_exit
		username = self.username
		hostname = self.hostname
		while smb_exit.is_set() == False:
			smbclient.ClientConfig(username=username, password=def_password, connection_timeout=1)
			connected = False
			try:
				with smbclient.open_file(r'\\\\' + hostname + '\\share\\file.txt', mode='r') as f:
					connected = True
			except Exception as exception:
				if type(exception).__name__ == 'AccessDenied':
					drslt = subprocess.check_output('dig +short ' + hostname, shell=True, text=True)
					drslt_parts = drslt.split('\n')
					rmt_ip = 'Unknown'
					if len(drslt_parts) > 1:
						if hostname in drslt_parts[0]:
							rmt_ip = drslt_parts[1]
						else:
							rmt_ip = drslt_parts[0]

					logging.critical(messages.RSP_RECVD % {'color':'', 'bold':'', 'proto':'SMB', 'end':'', 'ip':rmt_ip, 'hostname':hostname})
					print(messages.RSP_RECVD % {'color':termcolor.BLUE, 'bold':termcolor.BOLD, 'proto':'SMB', 'end':termcolor.END, 'ip':rmt_ip, 'hostname':hostname})
			except:
				pass
			smbclient.reset_connection_cache()
			if smb_exit.is_set() == False:
				smb_exit.wait(SMB_SLEEP)

class HTTPClient(threading.Thread):
	def __init__(self, username, hostname):
		threading.Thread.__init__(self)
		self.username = username
		self.hostname = hostname

	def run(self):
		global def_password, http_exit
		username = self.username
		hostname = self.hostname
		url = 'http://' + hostname
		while http_exit.is_set() == False:			
			try:
				hrsp = requests.get(url, auth=(username, def_password), timeout=(1,5))
				drslt = subprocess.check_output('dig +short ' + hostname, shell=True, text=True)
				drslt_parts = drslt.split('\n')
				rmt_ip = 'Unknown'
				if len(drslt_parts) > 1:
					if len(drslt_parts) > 1:
						if hostname in drslt_parts[0]:
							rmt_ip = drslt_parts[1]
						else:
							rmt_ip = drslt_parts[0]

				logging.critical(messages.RSP_RECVD % {'color':'', 'bold':'', 'proto':'HTTP', 'end':'', 'ip':rmt_ip, 'hostname':hostname})
				print(messages.RSP_RECVD % {'color':termcolor.BLUE, 'bold':termcolor.BOLD, 'proto':'HTTP', 'end':termcolor.END, 'ip':rmt_ip, 'hostname':hostname})
			except:
				pass
			if http_exit.is_set() == False:
				http_exit.wait(HTTP_SLEEP)

def main():
	global smb_Thread, http_Thread
	os.system('clear')
	banner()
	print(termcolor.GREEN + termcolor.BOLD + '[+]' + termcolor.END + ' Sending events...')
	username = def_domain + '\\' + def_username
	hostname = def_hostname + '.' + def_fqdn
	if str.upper(SMB) == 'ON':
		smb_Thread = SMBClient(username, hostname)
		smb_Thread.start()
	if str.upper(HTTP) == 'ON':
		http_Thread = HTTPClient(username, hostname)
		http_Thread.start()

if __name__ == '__main__':
	signal(SIGINT, signal_handler)
	init()
	main()