#! /usr/bin/env python
# coding=utf-8

from miio.chuangmi_plug import PlugV3
# from miio.device import	Device
import time

ip = '192.168.10.8'
token = 'dd22a2db0a689a2ed9d1fdd43752395b'

a1 = PlugV3(ip, token)


a1.off()
  
