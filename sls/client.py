import socket
import logging
import functools

from . import protocol
from .protocol import (DEFAULT_CTRL_PORT, DEFAULT_STOP_PORT, SLSError,
                       TimerType, ResultType)

class Connection:

    def __init__(self, addr):
        self.addr = addr
        self.sock = None
        self.log = logging.getLogger('Connection({0[0]}:{0[1]})'.format(addr))

    def connect(self):
        sock = socket.socket()
        sock.connect(self.addr)
        self.reader = sock.makefile('rb')
        self.sock = sock

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None

    def __repr__(self):
        return '{0}({1[0]}:{1[1]})'.format(type(self).__name__, self.addr)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, etype, evalue, etb):
        self.close()

    def write(self, buff):
        self.log.debug('send: %r', buff)
        self.sock.sendall(buff)

    def recv(self, size):
        data = self.sock.recv(size)
        if not data:
            self.close()
            raise ConnectionError('connection closed')
        self.log.debug('recv: %r', data)
        return data

    def read(self, size):
        data = self.reader.read(size)
        if not data:
            self.close()
            raise ConnectionError('connection closed')
        self.log.debug('read: %r', data)
        return data


class Detector:

    def auto_ctrl_connect(f):
        name = f.__name__
        is_update = name != 'update_client'
        @functools.wraps(f)
        def wrapper(self, *args, **kwargs):
            with self.conn_ctrl:
                result, reply = f(self, *args, **kwargs)
                if result == ResultType.FORCE_UPDATE and not is_update:
                    self.update_client()
                return reply
        return wrapper

    def auto_stop_connect(f):
        @functools.wraps(f)
        def wrapper(self, *args, **kwargs):
            with self.conn_stop:
                result, reply = f(self, *args, **kwargs)
                return reply
        return wrapper

    def __init__(self, host,
                 ctrl_port=DEFAULT_CTRL_PORT,
                 stop_port=DEFAULT_STOP_PORT):
        self.conn_ctrl = Connection((host, ctrl_port))
        self.conn_stop = Connection((host, stop_port))

    @auto_ctrl_connect
    def update_client(self):
        return protocol.update_client(self.conn_ctrl)

    @auto_ctrl_connect
    def get_id(self, mode, mod_nb=-1):
        return protocol.get_id(self.conn_ctrl, mode, mod_nb=mod_nb)

    @auto_ctrl_connect
    def get_energy_threshold(self, mod_nb=0):
        return protocol.get_energy_threshold(self.conn_ctrl, mod_nb)

    @auto_ctrl_connect
    def get_synchronization(self):
        return protocol.get_synchronization(self.conn_ctrl)

    @auto_ctrl_connect
    def set_synchronization(self, value):
        return set_synchronization(self.conn_ctrl, value)

    synchronization = property(get_synchronization, set_synchronization)

    @auto_ctrl_connect
    def get_type(self):
        return protocol.get_detector_type(self.conn_ctrl)

    @auto_ctrl_connect
    def get_module(self, mod_nb=0):
        return protocol.get_module(self.conn_ctrl, mod_nb)

    @auto_ctrl_connect
    def get_time_left(self, timer):
        return protocol.get_time_left(self.conn_ctrl, timer)

    @property
    def exposure_time_left(self):
        return self.get_time_left(TimerType.ACQUISITION_TIME)

    @auto_ctrl_connect
    def set_timer(self, timer, value):
        return protocol.set_timer(self.conn_ctrl, timer, value)

    @auto_ctrl_connect
    def get_timer(self, timer):
        return protocol.get_timer(self.conn_ctrl, timer)

    @property
    def exposure_time(self):
        return self.get_timer(TimerType.ACQUISITION_TIME)

    @exposure_time.setter
    def exposure_time(self, exposure_time):
        self.set_timer(TimerType.ACQUISITION_TIME, exposure_time)

    @property
    def nb_frames(self):
        return self.get_timer(TimerType.NB_FRAMES)

    @nb_frames.setter
    def nb_frames(self, nb_frames):
        self.set_timer(TimerType.NB_FRAMES, nb_frames)

    @property
    def nb_cycles(self):
        return self.get_timer(TimerType.NB_CYCLES)

    @nb_cycles.setter
    def nb_cycles(self, nb_cycles):
        self.set_timer(TimerType.NB_CYCLES, nb_cycles)

    @auto_ctrl_connect
    def get_master(self):
        return protocol.get_master(self.conn_ctrl)

    @auto_ctrl_connect
    def set_master(self, master):
        return protocol.set_master(self.conn_ctrl, master)

    master = property(get_master, set_master)

    @auto_ctrl_connect
    def get_settings(self, mod_nb):
        return protocol.get_settings(self.conn_ctrl, mod_nb)

    @auto_stop_connect
    def get_run_status(self):
        return protocol.get_run_status(self.conn_stop)

    run_status = property(get_run_status)

    @auto_ctrl_connect
    def start_acquisition(self):
        protocol.start_acquisition(self.conn_ctrl)

    @auto_stop_connect
    def stop_acquisition(self):
        protocol.stop_acquisition(self.conn_stop)

    @auto_ctrl_connect
    def get_readout(self):
        return protocol.get_readout(self.conn_ctrl)

    @auto_ctrl_connect
    def set_readout(self, value):
        return protocol.set_readout(self.conn_ctrl, value)

    readout = property(get_readout, set_readout)

    @auto_ctrl_connect
    def get_rois(self):
        return protocol.get_rois(self.conn_ctrl)

    rois = property(get_rois)


if __name__ == '__main__':
    conn = Connection(('localhost', DEFAULT_CTRL_PORT))