#!/bin/bash
echo "dolphin-memory-lib requires sudo permission to read and write to the emulator process memory."
sudo python memtest_lin.py
read -n1 -r
