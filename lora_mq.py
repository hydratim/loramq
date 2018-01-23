from network import LoRa
import time
import socket
import binascii
import struct
import _thread

class LoRaMQ:
    def __init__(self, config):
        self.lora = LoRa(mode=LoRa.LORAWAN)
        # set the 3 default channels to the same frequency (must be before sending the OTAA join request)
        self.lora.add_channel(0, frequency=config.LORA_FREQUENCY, dr_min=0, dr_max=5)
        self.lora.add_channel(1, frequency=config.LORA_FREQUENCY, dr_min=0, dr_max=5)
        self.lora.add_channel(2, frequency=config.LORA_FREQUENCY, dr_min=0, dr_max=5)
        # join a network using OTAA
        self.lora.join(activation=LoRa.OTAA, auth=(binascii.unhexlify(config.DEV_EUI), binascii.unhexlify(config.APP_EUI), binascii.unhexlify(config.APP_KEY)), timeout=0, dr=config.LORA_NODE_DR)
        # wait until the module has joined the network
        while not self.lora.has_joined():
            time.sleep(2.5)
            print('Not joined yet...')
        # remove all the non-default channels
        for i in range(3, 16):
            self.lora.remove_channel(i)
        # create a LoRa socket
        self.s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
        # set the LoRaWAN data rate
        self.s.setsockopt(socket.SOL_LORA, socket.SO_DR, config.LORA_NODE_DR)
        # make the socket non-blocking
        self.s.setblocking(False)
        time.sleep(5.0)
        self.send_mutex = _thread.allocate_lock()
        self.send_queue = []
        self.recv_mutex = _thread.allocate_lock()
        self.recv_queue = []
        self.callback = None
        self.lora.callback(LoRa.RX_PACKET_EVENT, self._recv)

    def _recv(self, data):
        rx, port = s.recvfrom(256)
        self.recv_mutex.acquire()
        self.recv_queue.append((port,rx))
        self.recv_mutex.release()
        if self.callback:
            _thread.start_new_thread(self.callback, tuple())

    def send(self, data):
        self.send_mutex.acquire()
        self.send_queue.append(data)
        self.send_mutex.release()

    def receive(self):
        self.recv_mutex.acquire()
        if not len(self.recv_queue):
            return False
        data = self.recv_queue.pop(0)
        self.recv_mutex.release()
        return data

    def rq_length(self):
        self.recv_mutex.acquire()
        size = len(self.recv_queue)
        self.recv_mutex.release()
        return size

    def attach_callback(self, callback):
        self.callback = callback

    def _loop(self):
        while True:
            #acquire a lock on the send message queue
            self.send_mutex.acquire()
            #get the message from the front of the queue
            if len(self.send_queue):
                data = self.send_queue.pop(0)
            else:
                data=None
            self.send_mutex.release()
            if data:
                #acquire a lock on the channel
                self.recv_mutex.acquire()
                #send the data
                self.s.send(data)
                #release the channel lock
                self.recv_mutex.release()
                #LoRa protocol only allows sending and recieving every 5 seconds
                #so to avoid protocol errors from the transciever sleep the thread
                #for 5 seconds
            time.sleep(5)

    def start(self):
        _thread.start_new_thread(self._loop, tuple())
