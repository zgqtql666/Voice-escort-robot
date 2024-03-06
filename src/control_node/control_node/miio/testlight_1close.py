#! /usr/bin/env python
# coding=utf-8

from yeelight import Bulb
# from miio.device import	Device
import time

ip = '192.168.10.9'
token = '5b3c53b2e2d88388d29deedc4bbf6d93'

a1 = Bulb(ip, token)


a1.off()
  
