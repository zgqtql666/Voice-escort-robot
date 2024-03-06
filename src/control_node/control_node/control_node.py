# 远程控制功能
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from miio import FanP5, Yeelight
from miio.curtain2 import CurtainMiot
import time
"""
1.导入订阅的话题接口类型
2.创建订阅回调函数
3.声明并创建订阅者
4.编写订阅回调处理逻辑
"""


class Control_node(Node):
    def __init__(self, name):
        super().__init__(name)
        self.get_logger().info("control_node ready!")
        # 创建remote_control订阅者
        self.sub_control_text = self.create_subscription(
            String, "remote_control", self.recv_control_callback, 20)

    def recv_control_callback(self, control_text_msg):
        self.control_Content = control_text_msg.data
        self.get_logger().info("收到!收到主节点传来的远程控制请求")
        if self.control_Content == "打开风扇":
            try:
                ip = '192.168.31.50'
                token = 'a6864db3c354a1378626891b85596613'
                a1 = FanP5(ip, token)
                a1.on()
                self.get_logger().info("完成请求!")
            except Exception as e:
                print(f"An error occurred: {e}")
        elif self.control_Content == "关闭风扇":
            try:
                ip = '192.168.31.50'
                token = 'a6864db3c354a1378626891b85596613'
                a1 = FanP5(ip, token)
                a1.off()
                self.get_logger().info("完成请求!")
            except Exception as e:
                print(f"An error occurred: {e}")
        elif self.control_Content == "打开窗帘":
            try:
                ip = '192.168.31.29'
                token = '88131d82e715f5f13d409906d6ea33a2'
                c1 = CurtainMiot(ip, token)
                c1.set_target_position(0)
                self.get_logger().info("完成请求!")
            except Exception as e:
                print(f"An error occurred: {e}")
        elif self.control_Content == "关闭窗帘":
            try:
                ip = '192.168.31.29'
                token = '88131d82e715f5f13d409906d6ea33a2'
                c1 = CurtainMiot(ip, token)
                c1.set_target_position(60)
            except Exception as e:
                print(f"An error occurred: {e}")
        elif self.control_Content == "打开台灯":
            try:
                ip = '192.168.31.132'
                token = '92af32b37065cf70b6f2533c796116fb'
                a1 = Yeelight(ip, token)
                a1.on()
                self.get_logger().info("完成请求!")
            except Exception as e:
                print(f"An error occurred: {e}")
        elif self.control_Content == "关闭台灯":
            try:
                ip = '192.168.31.132'  # 要改
                token = ' 92af32b37065cf70b6f2533c796116fb'  # 要改
                a1 = Yeelight(ip, token)
                a1.off()
                self.get_logger().info("完成请求!")
            except Exception as e:
                print(f"An error occurred: {e}")


def main(args=None):
    rclpy.init(args=args)
    control_node = Control_node("control_node")
    rclpy.spin(control_node)
    rclpy.shutdown()
