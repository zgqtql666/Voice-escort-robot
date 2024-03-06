#! /usr/bin/env python
# coding=utf-8

from miio.fan import FanP5
# from miio.device import	Device
import time

ip = '172.20.10.5'
token = 'f77fc2e39671459b53cfd36f2929177f'

a1 = FanP5(ip, token)


a1.off()
  
