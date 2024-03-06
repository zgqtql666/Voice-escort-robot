#远程控制功能
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from miio import FanP5,Yeelight

ip = '192.168.31.157'
token = 'e82d7d50f2e5dd234c6d929332f8c4c2'
a1 = FanP5(ip, token)
a1.on()
print("success")