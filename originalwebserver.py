import cgi

# !/usr/bin/env python
"""
Very simple HTTP server in python.
Usage::
    ./dummy-web-server.py [<port>]
Send a GET request::
    curl http://localhost
Send a HEAD request::
    curl -I http://localhost
Send a POST request::
    curl -d "foo=bar&bin=baz" http://localhost
"""
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import SocketServer
import leveldb
import plyvel
import hashlib
import json
import requests
from mechanize import Browser
from bs4 import BeautifulSoup


# Use one salt for the whole server
# Obviates the need to store an individual salt for each user entry (but is less secure)
SALT = "RANDSALT"
ADMINPASS = "default"

class S(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        self._set_headers()
        self.wfile.write("<html><body><h1>Webserver</h1></body></html>")
        db = plyvel.DB('./books')
        for key, value in db:
            if (value == 'new'):
                db.delete(key)
                db.put(key, 'old');
                self.wfile.write("isbn: %s<br>" % key)

        del db

    def do_HEAD(self):
        self._set_headers()

    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        ctype, pdict = cgi.parse_header(self.headers['content-type'])

        if ctype == 'multipart/form-data':
            postvars = cgi.parse_multipart(self.rfile, pdict)
        elif ctype == 'application/x-www-form-urlencoded':
            length = int(self.headers['content-length'])
            postvars = cgi.parse_qs(self.rfile.read(length), keep_blank_values=1)
        else:
            postvars = {}

        back = self.path if self.path.find('?') < 0 else self.path[:self.path.find('?')]


        # Handle POST request based on type
        if postvars['type'][0] == 'book':
            #self.wfile.write('isbn: %s\n' % postvars['isbn'][0])        #DEBUG
            db = leveldb.LevelDB('./books')
            try:
                db.Get(postvars['isbn'][0])
                self.wfile.write('isbn already added')
            except:
                db.Put(postvars['isbn'][0], 'new')
                self.wfile.write('isbn added, %s\n' % db.Get(postvars['isbn'][0]))
            del db
	    # Get mechanize browser instance
	    br = Browser()
	    br.set_handle_robots(False) # Ignoring this may be violating Worldcat T&A. Oops?

	    # Get the search form and submit form with ISBN from phone. 
	    br.open('https://www.worldcat.org/')
	    br.select_form(name="worldcatsearch") # searchbar name="worldcatsearch"
	    br['q'] = postvars['isbn'][0] # searchbar input field name='q'
	    br.submit()

	    # Get response into BeautifulSoup
	    soup = BeautifulSoup(br.response().read(), "html.parser")

	    entries = soup.find_all('tr', class_="menuElem") # All entries for specific ISBN
	    entriesResults = [] # Initialize empty list to store dictionaries
	    for entry in entries:
	    	oclcU = entry.find('div', class_="oclc_number").get_text() # type unicode
	    	titleU = entry.find('div', class_="name").find('strong').get_text() # type unicode
	    	authorU = entry.find('div', class_="author").get_text() # type unicode
	    	publisherU = entry.find('span', class_="itemPublisher").get_text() # type unicode
	    	oclc = oclcU.encode('ascii','replace') # convert to ascii string
	    	title = titleU.encode('ascii','replace') # convert to ascii string
	    	author = authorU.encode('ascii','replace') # convert to ascii string
	    	publisher =publisherU.encode('ascii','replace') # convert to ascii string
	    	entriesResults.append({'oclc':oclc,'title':title,'author':author,'publisher':publisher}) # append dictionary to list
	    	
	    json_string = json.dumps(entriesResults, separators=(',',':')) # convert to JSON
	    
		self.wfile.write('%s' % json_string)
		#self.wfile.write('%s^' % author)
		#self.wfile.write('%s\n' % publisher)


        elif postvars['type'][0] == 'login':
            #self.wfile.write('user: %s\n' % postvars['user'][0])        #DEBUG
            #self.wfile.write('pass: %s\n' % postvars['pass'][0])        #DEBUG
            db = leveldb.LevelDB('./users')
            try:
                storedPassHash = db.Get(postvars['user'][0])
                # Check hashed passwords
                if storedPassHash == hashlib.sha512(postvars['pass'][0] + SALT).hexdigest():
                    self.wfile.write('authentication successful')
                else:
                    self.wfile.write('incorrect password')
            except:
                # User key was not found in the database, send unregistered response
                self.wfile.write('unregistered user')
            del db

        elif postvars['type'][0] == 'createAcct':
            #self.wfile.write('user: %s\n' % postvars['newUser'][0])        #DEBUG
            #self.wfile.write('pass: %s\n' % postvars['newPass'][0])        #DEBUG
            db = leveldb.LevelDB('./users')
            newUser = postvars['newUser'][0]
            newPass = postvars['newPass'][0]
            #If the user already exists, send "already exists" response
            try:
                db.Get(newUser)
                self.wfile.write("username already exists")
            #If user isn't already in database, add account
            except:
                db.Put(newUser, hashlib.sha512(newPass + SALT).hexdigest())
                self.wfile.write("account added successfully")
        else:
            self.wfile.write('unrecognized request')


# '''	db = leveldb.LevelDB('./books')
#
#
# 	self.wfile.write('isbn: %s\n' % postvars['isbn'][0])
# 	try:
# 	    db.Get(postvars['isbn'][0])
# 	    self.wfile.write('isbn already added')
# 	except:
# 	    db.Put(postvars['isbn'][0], 'new')
# 	    self.wfile.write('isbn added, %s\n' % db.Get(postvars['isbn'][0]))
#
# 	del db
# '''


#    for key in postvars:
#	self.wfile.write('%s : ' % key)
#       self.wfile.write('%s\n' % postvars[key])



# self.wfile.write('  </body>')
# self.wfile.write('</html>')


def run(server_class=HTTPServer, handler_class=S, port=8888):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    
    # Add admin credentials
    db = leveldb.LevelDB('./users')
    db.Put(b'admin', hashlib.sha512(ADMINPASS + SALT).hexdigest())
    del db
    
    # Start server
    print 'Starting httpd...'
    httpd.serve_forever()


if __name__ == "__main__":
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
