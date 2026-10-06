import select
import socket
import sys
import pickle
import struct

SERVER_HOST = 'localhost'

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
    client = ChatClient(name=name, port=port)
    client.run()
        






