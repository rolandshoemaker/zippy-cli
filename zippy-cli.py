#!/usr/bin/python3
import http.cookiejar, urllib.request
import urllib
import re
import time
import argparse
from progressbar import ProgressBar, Percentage, Bar, ETA, FileTransferSpeed
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from urllib.error import URLError, HTTPError

parser = argparse.ArgumentParser()
parser.add_argument("URL", nargs=1, help="Target ZippyShare URL to download from")
parser.add_argument("-v", action="store_true", help="Enable verbose output")
args = parser.parse_args()

class colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

class AppURLopener(urllib.request.FancyURLopener):
	version = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36"

urllib._urlopener = AppURLopener()
urllib._urlretrieve =  AppURLopener()

def retries(max_tries, delay=1, backoff=2, exceptions=(Exception,), hook=None):
	def dec(func):
		def f2(*args, **kwargs):
			mydelay = delay
			tries = range(max_tries)
			#tries.reverse()
			for tries_remaining in tries:
				try:
					return func(*args, **kwargs)
				except exceptions as e:
					if tries_remaining > 0:
						if hook is not None:
							hook(tries_remaining, e, mydelay)
							sleep(mydelay)
							mydelay = mydelay * backoff
						else:
							raise
				else:
					break
		return f2
	return dec

@retries(max_tries=15, delay=3, backoff=2, exceptions=(URLError, HTTPError))
def retry_urlopen(url):
	return urllib.request.urlopen(url)

def zippy_attack(url):
	global zippy_secret_attempts
	global zippy_conn_attempts
	zippy_req = urllib.request.Request(url)
	try:
		zippy_data = retry_urlopen(zippy_req)
		if zippy_data.status == 200:
			zippy_html = str(zippy_data.read())
			zippy_soup = BeautifulSoup(zippy_html)
			if not zippy_soup.title.text == "Zippyshare.com - ":
				zippy_dl = zippy_soup.find('a', id="dlbutton")
				if not zippy_dl is None:
					zippy_js = zippy_soup.find_all('script')
					for js in zippy_js:
						if re.match('\\\\n   var somffunction', js.text) or re.match('\\\\n   var otfunction', js.text):
							a = re.search('var a = (\d*)\;', js.text)
							if a.group(1):
								if args.v:
									print(colors.OKGREEN+"Attemping to break secret"+colors.ENDC)
								secret = int(a.group(1))
								download_secret = str(int((secret%78956)*(secret%3)+18))
								url_info = url.split('/')
								download_server = str(url_info[2].split('.')[0])
								download_file = str(url_info[4])
								zippy_title = zippy_soup.title.text.split(' - ')
								zippy_title.pop(0)
								download_name = " ".join(zippy_title)
								download_name = urllib.parse.quote(download_name)
								url = "http://"+download_server+".zippyshare.com/d/"+download_file+"/"+download_secret+"/"+download_name
								test_req = urllib.request.Request(url=url, method='HEAD')
								test_data = urllib.request.urlopen(test_req)
								content_type = test_data.headers['content-type'].split(';')
								if content_type[0] == "application/x-download":
									if args.v:
										print(colors.OKBLUE+"\tSuccess"+colors.ENDC)
									widgets = [" "+" ".join(zippy_title)+" ", Percentage(), ' ', Bar(), ' ', ETA(), ' ', FileTransferSpeed()]
									pbar = ProgressBar(widgets=widgets)
									def dlProgress(count, blockSize, totalSize):
										if pbar.maxval is None:
											pbar.maxval = totalSize
											pbar.start()

										pbar.update(min(count*blockSize, totalSize))

									dl, headers = urllib.request.urlretrieve(url, " ".join(zippy_title), reporthook=dlProgress)
									pbar.finish()
								elif zippy_secret_attempts <= zippy_secret_attempts_max:
									if args.v:
										print(colors.WARNING+"\tFailed"+colors.ENDC)
									zippy_secret_attempts += 1
									zippy_attack(url)
								else:
									print(colors.FAIL+"Reached max secret attempts, exiting"+colors.ENDC)
									exit(0)
									
				else:
					print(colors.WARNING+"Can't find download button..."+colors.ENDC)
			else:
				print(colors.WARNING+"Dead link"+colors.ENDC)
		else:
			print(colors.WARNING+"Bad status code: "+str(zippy_data.status)+colors.ENDC)

	except URLError:
		if zippy_conn_attempts <= zippy_conn_attempts_max:
			if args.v:
				print(colors.WARNING+"Connection refused, let's wait 5 seconds and retry"+colors.ENDC)
			zippy_conn_attempts += 1
			time.sleep(5)
			zippy_attack(url)
		else:
			print(colors.FAIL+"Reached connection retry limit, exiting"+colors.ENDC)
			exit(0)
			
					
def get_cookie(jar, name):
	return [cookie for cookie in jar if cookie.name == name][0]

VERSION = '0.05'
if args.v:
	print(colors.HEADER+"zippy-cli v"+VERSION+colors.ENDC)

# Settings
zippy_secret_attempts_max = 14
zippy_conn_attempts_max = 4
zippy_conn_attempts = 0
zippy_secret_attempts = 0 

# Cookies & opener
if args.v:
	print(colors.OKBLUE+"Making a cookie jar..."+colors.ENDC)
cookies = http.cookiejar.LWPCookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
urllib.request.install_opener(opener)

# Main body
zippy_attack(args.URL[0])

# Clean up
cookies.clear()

