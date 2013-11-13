#!/bin/sh -
"exec" "python" "-O" "$0" "$@"

"""
Based on 
        Tiny HTTP Proxy in Python
        by SUZUKI Hisao 
        http://www.oki-osk.jp/esc/python/proxy/
"""

import os,sys,thread,socket
import BaseHTTPServer, select, SocketServer, urlparse

#********* CONSTANT VARIABLES *********
MAX_DATA_RECV = 4096    # max number of bytes we receive at once
DEBUG = True           # set to True to see the debug msgs
DROP = "POST / "
WEBSERVER = "x.x.x.x" #server to redirect requests to
PORT = 8080               #port to redirect requests to

#********* PROXY CLASS ***************

class ProxyHandler (BaseHTTPServer.BaseHTTPRequestHandler):
    __base = BaseHTTPServer.BaseHTTPRequestHandler
    __base_handle = __base.handle

    rbufsize = 0                        # self.rfile Be unbuffered

    def handle(self):
        (ip, port) =  self.client_address
        # self.send_error(403)
        self.__base_handle()

    def _connect_to(self, soc):
        host_port = WEBSERVER, PORT
        try: soc.connect(host_port)
        except socket.error, arg:
            try: msg = arg[1]
            except: msg = arg
            self.send_error(404, msg)
            return 0
        return 1

    def do_CONNECT(self):
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if self._connect_to(soc):
                self._read_write(soc, 300)
        finally:
            soc.close()
            self.connection.close()

    def do_GET(self):        
        (scm, netloc, path, params, query, fragment) = urlparse.urlparse(
            self.path, 'http')
        if (self.command==DROP.split()[0] and path==DROP.split()[1]) or (WEBSERVER in self.headers['Host'] and '/server-status' not in path): #rules to drop comunication before connecting to Apache
            self.send_error(404)
            self.connection.close()
            return
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if self._connect_to(soc):
                (remote_ip, dummy) =  self.client_address
                soc.send("%s %s %s\r\n" % (
                    self.command,
                    urlparse.urlunparse(('', '', path, params, query, '')),
                    self.request_version))
                self.headers['Connection'] = 'close'
                self.headers['x-forwarded-for'] = remote_ip # to track original ip requesting page
                del self.headers['Proxy-Connection']
                for key_val in self.headers.items():
                    soc.send("%s: %s\r\n" % key_val)
                soc.send("\r\n")
                self._read_write(soc)
        finally:
            soc.close()
            self.connection.close()

    def _read_write(self, soc, max_idling=20):
        iw = [self.connection, soc]
        ow = []
        count = 0
        while 1:
            count += 1
            (ins, _, exs) = select.select(iw, ow, iw, 3)
            if exs: break
            if ins:
                for i in ins:
                    if i is soc:
                        out = self.connection
                    else:
                        out = soc
                    data = i.recv(8192)
                    if data:
                        out.send(data)
                        count = 0
            if count == max_idling: break

    do_HEAD = do_GET
    do_POST = do_GET
    do_PUT  = do_GET
    do_DELETE=do_GET

class ThreadingHTTPServer (SocketServer.ThreadingMixIn,
                           BaseHTTPServer.HTTPServer): pass
                           
if __name__ == '__main__':
    BaseHTTPServer.test(ProxyHandler, ThreadingHTTPServer)
