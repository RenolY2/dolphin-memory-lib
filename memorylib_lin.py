import ctypes
import struct
import os
import sys
from struct import pack, unpack
from subprocess import check_output
from multiprocessing import shared_memory

class Dolphin(object):
    def __init__(self):
        self.pid = -1
        self.memory = None
        
    def reset(self):
        self.pid = -1
        self.memory = None
        
    def find_dolphin(self):
        try:
            if check_output(["pidof", "dolphin-emu"]) != '\n':
                self.pid = int(check_output(["pidof", "dolphin-emu"]))
            if check_output(["pidof", "dolphin-emu-qt2"]) != '\n':
                self.pid = int(check_output(["pidof", "dolphin-emu-qt2"]))
            if check_output(["pidof", "dolphin-emu-wx"]) != '\n':
                self.pid = int(check_output(["pidof", "dolphin-emu-wx"]))
        except Exception: #subprocess.CalledProcessError
            # Do nothing because self.pid cant be modified until a successful run of pidof
            pass
        
        if self.pid == -1:
            return False
        
        return True
        
    def init_shared_memory(self):
        print("Waiting for shared memory...")
        while True:
            try:
                self.memory = shared_memory.SharedMemory('dolphin-emu.'+str(self.pid))
                return True
            except FileNotFoundError:
                pass
            
    def read_ram(self, offset, size):
        return self.memory.buf[offset:offset+size]
        
    def write_ram(self, offset, data):
        self.memory.buf[offset:offset+len(data)] = data

    def read_uint32(self, addr):
        assert addr >= 0x80000000
        value = self.read_ram(addr-0x80000000, 4)

        return struct.unpack(">I", value)[0]
        
    def write_uint32(self, addr, val):
        assert addr >= 0x80000000
        return self.write_ram(addr - 0x80000000, pack(">I", val))

    def read_float(self, addr):
        assert addr >= 0x80000000
        value = self.read_ram(addr - 0x80000000, 4)

        return struct.unpack(">f", value)[0]

    def write_float(self, addr, val):
        assert addr >= 0x80000000
        return self.write_ram(addr - 0x80000000, struct.pack(">f", val))
        

if __name__ == "__main__":
    dolphin = Dolphin()
    import multiprocessing 

    if dolphin.find_dolphin():
        
        print("Found Dolphin! ")
    else:
        print("Didn't find Dolphin")
        
    print(dolphin.pid)
    
    if dolphin.init_shared_memory():
        print("We found MEM1 and/or MEM2!")
    else:
        print("We didn't find it...")
    
    import random 
    randint = random.randint
    from timeit import default_timer
    
    start = default_timer()
    
    print("Testing Shared Memory Method")
    start = default_timer()
    count = 500000
    for i in range(count):
        value = randint(0, 2**32-1)
        dolphin.write_uint32(0x80000000, value)
        
        result = dolphin.read_uint32(0x80000000)
        assert result == value
    diff = default_timer()-start 
    print(count/diff, "per sec")
    print("time: ", diff)