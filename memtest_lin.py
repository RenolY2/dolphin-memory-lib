import ctypes
import struct
import os
import sys
from subprocess import check_output
from ctypes import sizeof, addressof, POINTER, pointer

# Various Linux structs needed for operation

class iovec(ctypes.Structure):
    _fields_ = [("iov_base",ctypes.c_void_p),("iov_len",ctypes.c_size_t)]

libc = ctypes.cdll.LoadLibrary("libc.so.6")
vm = libc.process_vm_readv
vm.argtypes = [ctypes.c_int, POINTER(iovec), ctypes.c_ulong, POINTER(iovec), ctypes.c_ulong, ctypes.c_ulong]
vmwrite = libc.process_vm_writev
vmwrite.argtypes = [ctypes.c_int, POINTER(iovec), ctypes.c_ulong, POINTER(iovec), ctypes.c_ulong, ctypes.c_ulong]


# The following code is a port of aldelaro5's Dolphin memory access methods 
# for Linux into Python+ctypes.
# https://github.com/aldelaro5/Dolphin-memory-engine

"""
MIT License

Copyright (c) 2017 aldelaro5

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

class Dolphin(object):
    def __init__(self):
        self.pid = -1
        self.handle = -1
        
        self.address_start = 0
        self.mem1_start = 0
        self.mem2_start = 0
        self.mem2_exists = False
        
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
        
    def get_emu_info(self):
        MEM1_found = False
        try:
            maps_file = open("/proc/{}/maps".format(self.pid), 'r')
        except IOError:
            print("Cant open maps for process {}".format(self.pid))
        heap_info = None
        for line in maps_file:
            foundDevShmDolphin = False
            if '/dev/shm/dolphinmem' in line:
                heap_info = line.split()
            if '/dev/shm/dolphin-emu' in line:
                heap_info = line.split()
            if heap_info is None:
                continue
            else:
                offset = 0
                offset_str = "0x" + str(heap_info[2])
                offset = int(offset_str, 16)
                if offset != 0 and offset != 0x2000000:
                       continue
                first_address = 0
                second_address = 0
                index_dash = heap_info[0].find('-')
                
                first_address_str = "0x" + str(heap_info[0][: index_dash])
                second_address_str = "0x" + str(heap_info[0][(index_dash + 1):])
                
                first_address = int(first_address_str, 16)
                second_address = int(second_address_str, 16)
                
                if (second_address - first_address) == 0x4000000 and offset == 0x2000000:
                        self.mem2_start = first_address
                        self.mem2_exists = True
                if (second_address - first_address) == 0x2000000 and offset == 0x0:
                        self.address_start = first_address
        
        if self.address_start == 0:
            return False
        return True

    def read_ram(self, offset, size):
        buffer_ = (ctypes.c_char*size)()
        nread = ctypes.c_size_t
        local = (iovec*1)()
        remote = (iovec*1)()
        local[0].iov_base = ctypes.addressof(buffer_)
        local[0].iov_len = size
        remote[0].iov_base = ctypes.c_void_p(self.address_start + offset)
        remote[0].iov_len = size
        nread = vm(self.pid, local, 1, remote, 1, 0)
        if nread != size:
            return False, buffer_
        return True, buffer_
        
    def write_ram(self, offset, data):
        buffer_ = (ctypes.c_char*len(data))(*data)
        nwrote = ctypes.c_size_t
        local = (iovec*1)()
        remote = (iovec*1)()
        local[0].iov_base = ctypes.addressof(buffer_)
        local[0].iov_len = len(data)
        remote[0].iov_base = ctypes.c_void_p(self.address_start + offset)
        remote[0].iov_len = len(data)
        nwrote = vmwrite(self.pid, local, 1, remote, 1, 0)
        if nwrote != len(data):
            return False
        return True

    def read_uint32(self, addr):
        assert addr >= 0x80000000
        success, value = self.read_ram(addr-0x80000000, 4)

        if success:
            return struct.unpack(">I", value)[0]
        else:
            return None

    def read_float(self, addr):
        assert addr >= 0x80000000
        success, value = self.read_ram(addr - 0x80000000, 4)

        if success:
            return struct.unpack(">f", value)[0]
        else:
            return None

    def write_float(self, addr, val):
        assert addr >= 0x80000000
        return self.write_ram(addr - 0x80000000, struct.pack(">f", val))
        

if __name__ == "__main__":
    dolphin = Dolphin()

    if dolphin.find_dolphin():

        print("Found Dolphin! ")
    else:
        print("Didn't find Dolphin")
        
    print(dolphin.pid)
        
    if dolphin.get_emu_info():
        print("We found MEM1 and/or MEM2!", dolphin.address_start, dolphin.mem2_start)
    else:
        print("We didn't find it...")
    print(dolphin.write_ram(0, b"GMS"))
    success, result = dolphin.read_ram(0, 8)
    print(result[0:8])
    
    print(dolphin.write_ram(0, b"AWA"))
    success, result = dolphin.read_ram(0, 8)
    print(result[0:8])
