import socket
import sys
import time
import errno
import subprocess
import select
import logging
import multiprocessing 


def process_start(s_sock, use_port):
    print("in child")
    logging.info('starting matlab instance to use port %d' % use_port)
    pid = subprocess.Popen(["/opt/matlab/bin/matlab", "-nosplash", "-nodesktop", "-r", 
    "BackgroundSolver("+str(use_port)+");exit"],
     cwd="/home/timos/Work/daapce/matlab")
    time.sleep(5) # give matlab some time to start
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(('localhost', use_port))  # connect to the MATLAB use port
        logging.info('connected to matlab instance on port %d' % use_port)
        s.setblocking(0)                    # use non-blocking IO
        s_sock.setblocking(0)
        while (pid.poll() is None):
            logging.info('waiting for matlab or client to say something on port %d' % use_port)
            readable, writable, exceptional = select.select([s_sock, s], [], [s_sock, s])
            for rs in readable:
                if (rs == s):
                    # matlab said something, forward to client
                    data = s.recv(1024)
                    logging.info('got some data from matlab on port %d' % use_port)
                    if data:
                        while len(data):
                            sent = s_sock.send(data)
                            data = data[sent:]
                    else:
                        # matlab closed the connection, tear down everything
                        logging.info('matlab on port %d closed the connection' % use_port)
                        s.close()
                        s_sock.close()
                        pid.kill()
                        sys.exit(0)
                if (rs == s_sock):
                    # client said something, forward to matlab
                    data = s_sock.recv(1024)
                    if data:
                        print("got ["+str(data)+"] from client")
                        logging.info('got some data from client for matlab on port %d' % use_port)
                        while len(data):
                            sent = s.send(data)
                            data = data[sent:]
                    else:
                        # readable but no data - client closed the conn
                        print("client closed conn, kill matlab..")
                        logging.info('client closed connection, killing matlab on port %d' % use_port)
                        s.close()
                        s_sock.close()
                        pid.kill()
                        sys.exit(0)
            for e in exceptional:
                print("something happened, kill matlab..")
                logging.info('some exception happened, killing matlab on port %d' % use_port)
                s.close()
                s_sock.close()
                pid.kill()
                sys.exit(0)
        print("Matlab is done...")
    print("client socket was closed")
    sys.exit(0) # kill the child process


class MatlabServer:

    def __init__(self):
        self.running_procs = []

    def get_next_free_port(self):
        use_port = 3042
        newlist = []
        for p in self.running_procs:
            (proc, port) = p
            if p.is_alive():
                if port == use_port:
                    use_port += 1
                newlist += [p]
            self.running_procs = newlist
        return use_port

    def run(self): 
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   
        s.bind((sys.argv[1], int(sys.argv[2])))
        print('listen on address %s and port %d' % (sys.argv[1], int(sys.argv[2])))
        logging.info('listen on address %s and port %d' % (sys.argv[1], int(sys.argv[2])))
        s.listen(1)
        try:
            while True:
                try:
                    logging.info('listening for more clients')
                    s_sock, s_addr = s.accept()
                    logging.info('accepted a connection from %s' % str(s_addr))
                    use_port = self.get_next_free_port();
                    logging.info('the used matlab port is %d' % use_port)
                    p = multiprocessing.Process(target=process_start, args=(s_sock, use_port))
                    logging.info('starting subprocess %d' % use_port)
                    print("before start")
                    p.start()
                    print("after start")
                    logging.info('forking of matlab subprocess complete [port %d]' % use_port)

                except socket.error:
                    # stop the client disconnect from killing us
                    print('got a socket error')

        except Exception as e:
            print('an exception occurred!', e)
            sys.exit(1)
        finally:
            s.close()       

if __name__ == '__main__':
    logging.basicConfig(filename="matlab-server.log", level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    logging.info("Server started")
    MatlabServer().run()
    logging.info("Server terminated")
