import logging
import logging.handlers

import cgi

from wsgiref.simple_server import make_server

#from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import socketserver
#import SocketServer
#import leveldb
#import plyvel
import hashlib
import json
import requests
#from mechanize import Browser
#from bs4 import BeautifulSoup
import argparse
import mechanicalsoup
import os

from boto import dynamodb2
from boto.dynamodb2.table import Table

TABLE_NAME = "books"
REGION = "us-east-1"

conn = dynamodb2.connect_to_region(
    REGION,
    aws_access_key_id="AKIAJM6PK3HASBMTLE3Q",
    aws_secret_access_key="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"
)
table = Table(
    TABLE_NAME,
    connection=conn
)

usertable = Table("Users", connection=conn)



# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Handler
LOG_FILE = '/opt/python/log/sample-app.log'
handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=1048576, backupCount=5)
handler.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add Formatter to Handler
handler.setFormatter(formatter)

# add Handler to Logger
logger.addHandler(handler)

welcome = """
    <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
    <html>
    <head>
    <!--
    Copyright 2012 Amazon.com, Inc. or its affiliates. All Rights Reserved.
    
    Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at
    
    http://aws.Amazon/apache2.0/
    
    or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
    -->
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <title>Welcome</title>
    <style>
    body {
    text-align: center;
    color: #ffffff;
    background-color: #000099;
    font-family: Arial, sans-serif;
    font-size:14px;
    -moz-transition-property: text-shadow;
    -moz-transition-duration: 4s;
    -webkit-transition-property: text-shadow;
    -webkit-transition-duration: 4s;
    text-shadow: none;
    }
    body.blurry {
    -moz-transition-property: text-shadow;
    -moz-transition-duration: 4s;
    -webkit-transition-property: text-shadow;
    -webkit-transition-duration: 4s;
    text-shadow: #fff 0px 0px 25px;
    }
    a {
    color: #0188cc;
    }
    .textColumn, .linksColumn {
    padding: 2em;
    }
    .textColumn {
    position: absolute;
    top: 0px;
    bottom: 0px;
    left: 0px;
    
    text-align: right;
    padding-top: 11em;
    background-color: #1BA86D;
    background-image: -moz-radial-gradient(left top, circle, #6AF9BD 0%, #00B386 60%);
    background-image: -webkit-gradient(radial, 0 0, 1, 0 0, 500, from(#6AF9BD), to(#00B386));
    }
    .textColumn p {
    width: 75%;
    float:right;
    }
    .linksColumn {
    position: absolute;
    top:0px;
    right: 0px;
    bottom: 0px;
    left: 50%;
    
    background-color: #E0E0E0;
    }
    
    h1 {
    font-size: 500%;
    font-weight: normal;
    margin-bottom: 0em;
    }
    h2 {
    font-size: 200%;
    font-weight: normal;
    margin-bottom: 0em;
    }
    ul {
    padding-left: 1em;
    margin: 0px;
    }
    li {
    margin: 1em 0em;
    }
    </style>
    </head>
    <body>

    <h1>Linked Data Scanner Webserver</h1>
    <p>Connects with android app to store isbns in DynamoDB database and return oclc number, title, author and publisher, found at worldcat.com</p>


    </body>
    </html>
    """

def strip_non_ascii(string):
    ''' Returns the string without non ASCII characters'''
    stripped = (c for c in string if 0 < ord(c) < 127)
    return ''.join(stripped)

def application(environ, start_response):
    path    = environ['PATH_INFO']
    method  = environ['REQUEST_METHOD']
    status = '200 OK'
    headers = [('Content-type', 'text/html')]
    empty_response = ''
    if method == 'POST':
        try:
            if path == '/':
                getting_key = 1
                getting_value = 0
                postvars = {}
                key = ''
                value = ''
                request_body_size = int(environ['CONTENT_LENGTH'])
                request_body = environ['wsgi.input'].read(request_body_size).decode()
                logger.info("Received message: %s" % request_body)
                for c in request_body:
                    if c == '=':
                        getting_key = 0
                        getting_value = 1
                        continue
                    if c == '&':
                        getting_key = 1
                        getting_value = 0
                        postvars[key] = value
                        key = ''
                        value = ''
                        continue
                    if getting_key == 1:
                        key += c
                    if getting_value == 1:
                        value += c
                postvars[key] = value
                if postvars['type'] == 'book':
                    browser = mechanicalsoup.Browser()

                    page = browser.get('https://www.worldcat.org/')
                    form = page.soup.form
                    form.find("input", {"name": "q"})["value"] = postvars['isbn']

                    response = browser.submit(form, page.url).text

                    '''title = ''
                    number = response.find('title=\'')
                    number = number + 7
                    while (response[number] != '\''):
                        title += response[number]
                        number = number + 1
                            
                    response = 'added' + title + '\n'''
                    menu_start = response.find('class="menuElem"')
                    oclc_div_start = response.find('div class="oclc_number">', menu_start)
                    if (oclc_div_start == -1):
                      oclc = 'unknown'
                    else:
                      oclc = ''
                      number = response.find('>', oclc_div_start) + 1
                      while (response[number] != '<'):
                        oclc += response[number]
                        number = number + 1
                    title_div_start = response.find('div class="name"', menu_start)
                    if (title_div_start == -1):
                      title = 'unknwon'
                    else:
                      title_start = response.find('<strong>', title_div_start)
                      title = ''
                      #print("after starts")
                      number = title_start + 8
                      while(response[number] != '<'):
                        title += response[number]
                        number = number + 1
                    author_div_start = response.find('div class="author">', menu_start)
                    if (author_div_start == -1):
                      author = 'unkown'
                    else:
                      number = response.find('>', author_div_start) + 1
                      author = ''
                      while (response[number] != '<'):
                        author += response[number]
                        number = number + 1
                    publisher_div_start = response.find('div class="publisher">', menu_start)
                    if (publisher_div_start == -1):
                      publisher = 'unknown'
                    else:
                      publisher_span_class = response.find('<span class="itemPublisher">', publisher_div_start)
                      publisher = ''
                      number = response.find('>', publisher_span_class) + 1
                      while (response[number] != '<'):
                        publisher += response[number]
                        number += 1
                    try:
                        table.put_item(
                                    {
                                   'isbn' : postvars['isbn'],
                                   'oclc' : oclc,
                                   'title' : title,
                                   'author' : author,
                                   'publisher' : publisher,
                                    'new' : 'new'
                                    }
                        )
                        response = 'isbn added'
                    except:
                        response = 'isbn old'
                                
                        #+ oclc + ', title : ' + title + ', author : ' , author, ', publisher : ' + publisher + '}'
                    #response = postvars['isbn']
                    
                if postvars['type'] == 'createAcct' :
                    try:
                        usertable.put_item(
                            {
                            'username' : postvars['newUser'],
                            'password' : postvars['newPass']
                            }
                        )
                        response = 'account added successfully'
                    except:
                        response = 'username already exists'
                            
                if postvars['type'] == 'login' :
                    try:
                        yuser = usertable.get_item(username=postvars['user'])
                        if (postvars['pass'] == yuser['password']):
                            response = 'authentication successful'
                        else:
                            response = 'incorrect password'
                    except:
                        response = 'user does not exist'
                            
                if postvars['type'] == 'oclc' :
                    browser = mechanicalsoup.Browser()
                            
                    page = browser.get('https://www.worldcat.org/')
                    form = page.soup.form
                    form.find("input", {"name": "q"})["value"] = postvars['isbn']
                                        
                    response = browser.submit(form, page.url).text
                                            
                    i = 0
                    my_response = '['
                    number = 0
                    first_entry = 1;
                    menu_start = response.find('class="menuElem"', number)
                    while (menu_start != -1):
                      if (first_entry == 1):
                        my_response += '{'
                        first_entry = 0
                      else:
                        my_response += ', {'
    
                      oclc_div_start = response.find('div class="oclc_number">', menu_start)
                      if (oclc_div_start == -1):
                        oclc = 'unknown'
                      else:
                        oclc = ''
                        number = response.find('>', oclc_div_start) + 1
                        while (response[number] != '<'):
                          oclc += response[number]
                          number = number + 1
                      title_div_start = response.find('div class="name"', menu_start)
                      if (title_div_start == -1):
                        title = 'unknown'
                      else:
                        title_start = response.find('<strong>', title_div_start)
                        title = ''
                        #print("after starts")
                        number = title_start + 8
                        while(response[number] != '<'):
                          title += response[number]
                          number = number + 1
                      author_div_start = response.find('div class="author">', menu_start)
                      if (author_div_start == -1):
                        author = 'unknown'
                      else:
                        number = response.find('>', author_div_start) + 1
                        author = ''
                    
                    
                        while (response[number] != '<'):
                          author += response[number]
                          number = number + 1
        
                      publisher_div_start = response.find('div class="publisher">', menu_start)
                      if (publisher_div_start == -1):
                        publisher = 'unknown'
                      else:
                        publisher_span_class = response.find('<span class="itemPublisher">', publisher_div_start)
                        publisher = ''
                        number = response.find('>', publisher_span_class) + 1
                        while (response[number] != '<'):
                          publisher += response[number]
                          number += 1
                      menu_start = response.find('class="menuElem"', number)
                      my_response += 'oclc : \"' + oclc + '\", title : \"' + title + '\", author : \"' + author + '\", publisher : \"' + publisher + '\"}'
                      while (i < 20):
                        #print(response[publisher_span_class + 28 + i])
                        i = i+1
                    my_response += ']'
                    #remove_non_ascii
                    
                    response = strip_non_ascii(my_response)
                    logger.info("The response::::: %s" % my_response)
                    
    
    
    

            elif path == '/scheduled':
                logger.info("Received task %s scheduled at %s", environ['HTTP_X_AWS_SQSD_TASKNAME'], environ['HTTP_X_AWS_SQSD_SCHEDULED_AT'])
                response = 'scheduled'
        except (TypeError, ValueError):
            logger.warning('Error retrieving request body for async work.')
            response = 'error'
    else:
        response = welcome


    start_response(status, headers)
    return [response]


if __name__ == '__main__':
    httpd = make_server('', 8000, application)
    print("Serving on port 8000...")
    httpd.serve_forever()
