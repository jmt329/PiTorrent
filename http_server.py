#!/usr/bin/python
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer

PORT_NUMBER = 8080

response = {
    'interval': str(30),
    'peers': []
    }

#This class will handles any incoming request from
#the browser 
class myHandler(BaseHTTPRequestHandler):
        
  #Handler for the GET requests
  def do_GET(self):
    self.send_response(200)
    self.send_header('Content-type','text/plain')
    self.end_headers()
    print self.path
    # Send the html message
    self.wfile.write("Hello World !")
    return

try:
  #Create a web server and define the handler to manage the
  #incoming request
  server = HTTPServer(('', PORT_NUMBER), myHandler)
  sa = server.socket.getsockname()
  print sa[0]
  print 'Started httpserver on port ',PORT_NUMBER

  #Wait forever for incoming http requests
  server.serve_forever()

except KeyboardInterrupt:
  print '^C received, shutting down the web server'
  server.socket.close()
