import select
import socket
import sys
import signal
import pickle
import struct

SERVER_HOST = 'localhost'
CHAT_SERVER_NAME = 'server'

def send(channel, *args):
    buffer = pickle.dumps(args)
    value = socket.htonl(len(buffer))
    size = struct.pack("L", value)
    channel.send(size)
    channel.send(buffer)

def receive(channel):
    size = struct.calcsize("L")
    size = channel.recv(size)
    try:
        size = socket.ntohl(struct.unpack("L", size)[0])
    except struct.error as e:
        return ""
    buf = ""
    while len(buf) < size:
        buf = channel.recv(size - len(buf))
    return pickle.loads(buf)[0]

class ChatServer(object):
    def __init__(self, port, backlog = 5):
        self.clients = 0
        self.clientmap = {}
        self.outputs = []
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((SERVER_HOST, port))
        print("listening on port:\t", port)
        self.server.listen(backlog)
        signal.signal(signal.SIGINT, self.signal_handler)
    def signal_handler(self, signum, frame):
        """clean up client outputs"""
        print("shutting down server 😭")
        # close existing client sockets
        for output in self.outputs:
            output.close()
        self.server.close()

    def get_client_name(self, client):
        """get client name"""
        info = self.clientmap[client]
        host, name = info[0][0], info[1]
        return '🆔'.join((host, name))

    def run(self):
        inputs = [self.server, sys.stdin]
        self.outputs = []
        running = True
        while running:
            try:
                readable, writable, exceptional = select.select(inputs, self.outputs, [])
            except select.error as e:
                break

            for sock in readable:
                if sock == self.server:
                    # handle the server socket
                    client, address = self.server.accept()
                    print("accepted connection from ", str(address[0]))
                    #read login name
                    cname = receive(client).split('NAME: ')[1]
                    # compute client name and send back
                    self.clients += 1
                    send(client, 'CLIENT: ' + str(address[0]))
                    inputs.append(client)
                    self.clientmap[client] = (address, cname)
                    #sending join info to others
                    msg = "\n(connected new client so now theres %d people. the client's id is '%s' 👋" %(self.clients, self.get_client_name(client))# damn that line is long
                    for output in self.outputs:
                        send(output, msg)
                    self.outputs.append(client)
                elif sock == sys.stdin:
                    #handle standard input
                    junk = sys.stdin.readline()
                    running = False
                else:
                    try:
                        data = receive(sock)
                        if data:
                            # send join info
                            msg = '\n[' +self.get_client_name(sock) + ']🗣️\t' + data
                            # send data to all but yourself
                            for output in self.outputs:
                                if output != sock:
                                    send(output, msg)
                            print(msg)
                        else:
                            print("SERVER>> %d left the chat" % sock.fileno())
                            self.clients -= 1
                            sock.close()
                            inputs.remove(sock)
                            self.outputs.remove(sock)

                            # sending that client hung up
                            msg = "\n(Person left the chat: client with id \"%s\" " % self.get_client_name(sock)

                            for output in self.outputs:
                                send(output, msg)
                    except socket.error as e:
                        # smth is wrong so remove
                        inputs.remove(sock)
                        self.outputs.remove(sock)
        self.server.close()

class ChatClient(object):
    """cli client"""
    def __init__(self, name, port, host=SERVER_HOST):
        self.name = name
        self.connected = False
        self.host = host
        self.port = port
        # Initial prompt
        self.prompt = '['+'🆔'.join((name, socket.gethostname().split('.')[0]))+']> '
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, self.port))
            print("---------now connected to chat server@ port %d--------------" % self.port)
            self.connected = True
            # send name :)
            send(self.sock,'NAME: ' + self.name) #
            data = receive(self.sock)
            # contains client addr; set it
            addr = data.split('CLIENT: ')[1]
            self.prompt = '['+'🆔'.join((self.name, addr))+']> '
        except socket.error as e:
            print("failed to connect @ port %d" % self.port)
            print(str(e))
            sys.exit(1)
    def run(self):
        """client main loop"""
        while self.connected:
            try:
                sys.stdout.write(self.prompt)
                sys.stdout.flush()

                readable, writable, exceptional = select.select([0, self.sock], [], [])

                for sock in readable:
                    if sock == 0:
                        data = sys.stdin.readline().strip()
                        if data:
                            send(self.sock, data)
                    elif sock == self.sock:
                        data = receive(self.sock)
                        if not data:
                            print("client shutting down")
                            self.connected = False
                            break
                        else:
                            sys.stdout.write(data+'\n')
                            sys.stdout.flush()
            except KeyboardInterrupt:
                print("client interupted")
                self.sock.close()

if __name__ == '__main__':
    name  = input("watss ur name:\t")
    port = int(input("which port (port must be 0-65535.):\t"))
    if name == CHAT_SERVER_NAME:
        server = ChatServer(port)
        server.run()
    else:
        client = ChatClient(name=name, port=port)
        client.run()
        






