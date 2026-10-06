import select
import socket
import sys
import signal
import pickle
import struct

SERVER_HOST = 'localhost'
CHAT_SERVER_NAME = 'Official Server by me'

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

if __name__ == '__main__':
    port = 65525
    server = ChatServer(port)
    server.run()

        






