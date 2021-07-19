#! /usr/bin/env python
# -*- coding: UTF-8 -*-

import sys
import socket
import os
import gzip

'''
====================================================
CLASS FOR WEB SERVER
====================================================
'''
class Server:
    def __init__(self, host, port, staticfiles, cgibin, exec_path):
        self.staticfiles = staticfiles
        self.cgibin = cgibin
        self.exec_path = exec_path

        self.host = host
        self.port = port

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        try:
            self.socket.bind((self.host, self.port))
        except Exception as e:
            print(e)
            self.close()
            sys.exit(1)

        self.socket.listen(128)

    def close(self):
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()

    def server_forever(self):
        while True:
            pid = os.fork()
            if pid:
                os.wait()
                client_socket, client_address = self.socket.accept()
                self.handleRequest(client_socket, client_address)
                client_socket.close()
            else:
                client_socket, client_address = self.socket.accept()
                self.handleRequest(client_socket, client_address)
                client_socket.close()

    def handleRequest(self, client, client_address):
        request_headers = {}
        request_body_lines = []
        client_host, client_port = client_address[0], client_address[1]
        data = client.recv(1024)
        request_messages = data.decode()
        request_messages_list = request_messages.split('\n')

        """ Step 1. parse_request """
        body_start = False

        method, resource, protocol = '', '', ''
        for i in range(len(request_messages_list)):
            message = request_messages_list[i]
            if i == 0:
                start_line_info = message.split()
                method, resource, protocol = start_line_info
                continue

            if message.strip() == '':
                body_start = True
                continue

            if body_start:
                request_body_lines.append(message.strip())
            else:
                header, content = message.strip().split(': ')
                request_headers[header] = content


        """ Step 2. set environment variable """
        header_to_key = {'Accept': 'HTTP_ACCEPT',
                         'Host': 'HTTP_HOST',
                         'User-Agent': 'HTTP_USER_AGENT',
                         'Accept-Encoding': 'HTTP_ACCEPT_ENCODING',
                         }

        # Remote-Address - The IP Address of the client
        # Content-Type - The content type of the request body
        # Content-Length - Size of the request body in bytes
        for h in request_headers.keys():
            if h in header_to_key.keys():
                os.environ[header_to_key[h]] = request_headers[h]

        # Set the next 2 http variable from the connection
        os.environ['REMOTE_ADDRESS'] = str(client_host)
        os.environ['REMOTE_PORT'] = str(client_port)

        # From http request
        os.environ['REQUEST_METHOD'] = method
        os.environ['REQUEST_URI'] = resource

        # From server socket / configuration
        os.environ['SERVER_ADDR'] = str(self.host)
        os.environ['SERVER_PORT'] = str(self.port)

        # Query string
        query_string = resource.split("?")[-1]
        if query_string.strip() != '':
            os.environ['QUERY_STRING'] = query_string

        """ Step 3. construct response """
        response = b''
        # <version> <status> <reason-phrase>
        response_start_line = protocol
        if resource[:7] != '/cgibin':
            path = self.staticfiles + resource
            # If it is just a directory /
            if resource == '/':
                response_start_line += ' ' + '200 OK\n'
                response_header1 = 'Content-Type' + ': ' + 'text/html' + '\n'
                response_header2 = 'Content-Length' + ': ' + str(
                    os.path.getsize(self.staticfiles + '/index.html')) + '\n\n'

                with open(self.staticfiles + '/index.html', 'rb') as f:
                    lines = f.read()

                response = build_response(response_start_line.encode(), response_header1.encode(),
                                          response_header2.encode(), lines)

                if 'Accept-Encoding' in request_headers.keys():
                    if request_headers['Accept-Encoding'] == 'gzip':
                        with open(self.staticfiles + '/index.html', 'rb') as f:
                            pressed_data = compress_data(f.read())

                        response = response_gzip(response, response_start_line, 'text/html', pressed_data)
            else:
                # If it is a file
                is_find = True
                try:
                    with open(path, 'rb') as f:
                        static_file_content = f.read()

                except FileNotFoundError:
                    is_find = False

                if is_find:
                    response_start_line += ' ' + '200 OK\n'

                    ending = resource.split('.')[-1]
                    ending = ending.split("?")[0]
                    response_header1 = 'Content-Type' + ': ' + str(content_type_mapping(ending)) + '\n'
                    response_header2 = 'Content-Length' + ': ' + \
                                       str(os.path.getsize(self.staticfiles + resource.split("?")[0])) + '\n\n'

                    response = build_response(response_start_line.encode(), response_header1.encode(),
                                              response_header2.encode(), static_file_content)

                    if 'Accept-Encoding' in request_headers.keys():
                        if request_headers['Accept-Encoding'] == 'gzip':
                            with open(self.staticfiles + resource.split("?")[0], 'rb') as f:
                                pressed_data = compress_data(f.read())

                            response = response_gzip(response_start_line,
                                                          str(content_type_mapping(ending)), pressed_data)


                else:
                    response_start_line += ' ' + '404 File not found\n'
                    response_header1 = 'Content-Type' + ': ' + 'text/html' + '\n'
                    response_header2 = 'Content-Length' + ': ' + str(sys.getsizeof(contentOf404)) + '\n\n'

                    response = build_response(response_start_line.encode(), response_header1.encode(),
                                              response_header2.encode(), contentOf404.encode())

                    if 'Accept-Encoding' in request_headers.keys():
                        if request_headers['Accept-Encoding'] == 'gzip':
                            response = response_gzip(response_start_line, 'text/html',
                                                          compress_data(contentOf404))


        else:
            path = "." + resource.split("?")[0]
            status_code, status_message, content = self.execute_cgibin(path)
            if 'Status-Code' in content:
                lines = content.split('\n')
                first_line_info = lines[0].split(' ', 2)
                status_code, message = first_line_info[1], first_line_info[2]

                response_start_line += ' ' + str(status_code) + ' ' + message + '\n'
                response_header1 = 'Content-Type' + ': ' + 'text/html' + '\n'
                response_header2 = 'Content-Length' + ': ' + str(sys.getsizeof(content)) + '\n\n'

                response = build_response(response_start_line.encode(), response_header1.encode(),
                                          response_header2.encode(), content.encode())

                if 'Accept-Encoding' in request_headers.keys():
                        if request_headers['Accept-Encoding'] == 'gzip':
                            response = response_gzip(response_start_line, 'text/html',
                                                          compress_data(content))

            elif status_code == 200:
                response_start_line += ' ' + '200 OK\n'
                response_header1 = 'Content-Type' + ': ' + 'text/html' + '\n'
                response_header2 = 'Content-Length' + ': ' + str(sys.getsizeof(content)) + '\n\n'

                response = build_response(response_start_line.encode(), response_header1.encode(),
                                          response_header2.encode(), content.encode())

                if 'content-type' in content.lower() or 'content_length' in content.lower():
                    response = b''
                    response += response_start_line.encode()
                    response += content.encode()

                if 'Accept-Encoding' in request_headers.keys():
                    if request_headers['Accept-Encoding'] == 'gzip':
                        response = response_gzip(response_start_line, 'text/html',
                                                      compress_data(content.encode()))

            else:
                response_start_line += ' ' + '500 Internal Server Error\n'

                response += response_start_line.encode()

                if 'Accept-Encoding' in request_headers.keys():
                    if request_headers['Accept-Encoding'] == 'gzip':
                        response = response_gzip(response_start_line, 'text/html', compress_data(''.encode))

        """ Step 4. Send response """
        client.send(response)
        client.close()


    def execute_cgibin(self, path):
        r, w = os.pipe()

        pid = os.fork()
        if pid:
            # This is the parent process
            # Closes file descriptor w
            child_pid, signal = os.wait()
            os.close(w)
            r = os.fdopen(r)
            content = r.read()

            if signal == 0:
                return 200, "OK", content
            else:
                return 500, "Internal Server Error", ""

        else:
            # This is the child process
            os.close(r)
            os.dup2(w, 1)

            os.execve(self.exec_path, [self.exec_path, path], os.environ)


'''
====================================================
FUNCTION FOR PARSING THE CONFIGURATION FILE
====================================================
'''
def parse_configuration_file():
    if len(sys.argv) < 2:
        print("Missing Configuration Argument")
        sys.exit(1)

    config_file = sys.argv[1]

    if not os.path.exists(config_file):
        print("Unable To Load Configuration File")
        sys.exit(1)

    with open(config_file, "r") as f:
        lines = f.readlines()

    properties = {}
    for line in lines:
        #  port - integer, the port the server listens on.
        info = line.strip().split("=")
        properties[info[0]] = info[1]

    for p in ['staticfiles', 'cgibin', 'port', 'exec']:
        if p not in properties.keys() or len(lines) != 4:
            print("Missing Field From Configuration File")
            sys.exit(1)

    return properties


'''
====================================================
FUNCTION FOR BUILDING RESPONSE
====================================================
'''
def content_type_mapping(suffix):
    content_type_map = {"txt": "text/plain", "html": "text/html", "js": "application/javascript",
                            "css": "text/css", "png": "image/png", "jpg": "image/jpeg", "xml": "text/xml"}
    return content_type_map[suffix]

def build_response(start_line, head1, head2, content):
    response = b''
    response += start_line + head1 + head2 + content
    return response


'''
====================================================
FUNCTION FOR EXTENSION (EXTENSION 2:COMPRESS DATA))
====================================================
'''
def response_gzip(start_line, content_type, pressed_content):
    response = b''
    response_header1 = 'Content-Type' + ': ' + content_type + '\n'
    response_header2 = 'Content-Length' + ': ' + str(sys.getsizeof(pressed_content)) + '\n'
    response_header3 = 'Content-Encoding' + ': ' + 'gzip' + '\n\n'

    response += start_line.encode() + response_header1.encode() \
                + response_header2.encode() + response_header3.encode() + pressed_content

    return response


def compress_data(bytes_data):
    return gzip.compress(bytes_data)


'''
====================================================
FUNCTION MAIN
====================================================
'''
def main():
    properties = parse_configuration_file()

    HOST = '127.0.0.1'
    PORT = int(properties['port'])

    server = Server(HOST, PORT, properties['staticfiles'], properties['cgibin'], properties['exec'])

    server.server_forever()

contentOf404 = '<html>\n<head>\n\t<title>404 Not Found</title>\n</head>\n<body bgcolor="white">' \
               '\n<center>\n\t<h1>404 Not Found</h1>\n</center>\n</body>\n</html>\n'

if __name__ == '__main__':
    main()

