# -*- coding:utf-8 -*-#导入socket依赖(实现两个树莓派通信)
import rclpy
from rclpy.node import Node
from std_msgs.msg import String,Bool#基本消息类型
from mybot_interfaces.srv import CloudService#自定义服务接口
from mybot_interfaces.srv import EasyMessage#自定义服务接口
import time
#导入语音播报的库
from urllib.request import urlopen
from urllib.parse import urlencode
from urllib.parse import quote_plus
#导入系统执行的库
import subprocess
import os
#小车启动的依赖
from geometry_msgs.msg import Twist
from geometry_msgs.msg import Pose2D

#异常情况的类
class DemoError(Exception):
    pass

class Robot_node(Node):
    def __init__(self,name):
        super().__init__(name)
        self.get_logger().info("robot_node ready!")

        #主节点创建nav2where话题的发布者
        self.pub_nav_text=self.create_publisher(String,"nav2where",20)
        #主节点通过microText话题获取voice_recognition发来的语音识别后的关键词
        self.sub_micro_text= self.create_subscription(String,"microText",self.recv_microText_callback,20)
        #主节点创建一个cloud_service的客户端
        self.cloudclient=self.create_client(CloudService,"cloud_service")
        #主节点创建remote_control话题的发布者
        self.pub_control_text=self.create_publisher(String,"remote_control",20)
        # 主节点创建一个cameraChange话题的发布者
        self.pub_camera_text = self.create_publisher(String, "cameraChange", 10)
        #主节点创建一个ai_service的客户端
        self.aiclient=self.create_client(EasyMessage,"get_result")
        # 主节点通过AI_result话题获取跌倒检测的结果
        self.sub_ai_result = self.create_subscription(String, "AI_result", self.recv_AI_result_callback, 20)
        #主节点创建voicePlay话题的发布者
        self.pub_play_text=self.create_publisher(String,"voicePlay",10)
        #主节点创建一个sendMessage话题的发布者
        self.pub_send_message=self.create_publisher(Bool,"sendMessage",2)
        #主节点创建一个用于小车启动与停止
        self.cmd_vel_pub = self.create_publisher(Twist, 'cmd_vel', 10)  # 创建一个Twist类型的发布者，用于发布控制机器人运动的消息
        self.twist_msg = Twist()  # 创建一个Twist类型的消息对象

    #主节点通过nav2where话题发布信息给底盘
    def nav2where_callback(self,nav_content):
        nav_text_msg = String()
        nav_text_msg.data = nav_content
        self.pub_nav_text.publish(nav_text_msg)
        self.get_logger().info(f'发送成功！发送内容是：{nav_text_msg.data}')#print the content of the message

    #主节点通过microText话题获取voice_recognition传来的语音交互的需求信息
    def recv_microText_callback(self,micro_text_msg):
        self.voice_Content=micro_text_msg.data
        self.get_logger().info(f"收到!收到voice_recognition传来的内容:%s"% self.voice_Content)
        #=============选择语音交互、室内导航、远程控制、人脸识别、跌倒检测
        #语音交互
        web_strings=["温度","湿度","二氧化碳","光照",]
        #室内导航
        go_strings=["小车去厨房","小车去卧室","小车去客厅","小车去起点"] 
        #语音控制
        control_strings=["小车启动","小车停止"]
        #远程控制
        remote_strings=["打开风扇","打开台灯","打开窗帘","关闭风扇","关闭台灯","关闭窗帘"]
        #人脸识别
        face_strings=["录入操作员","录入客户","人脸检测"]
        #跌倒检测
        fall_strings=["跌倒检测"]
        #=============处理语音交互、语音定位、室内导航、远程控制、人脸识别功能、跌倒检测功能
        #语音交互
        if self.voice_Content in web_strings:
            self.get_logger().info("开启语音交互功能!") 
            #发送cloud_service的服务请求
            self.cloudService_ask(self.voice_Content)
        #室内导航
        if self.voice_Content in go_strings:
            self.get_logger().info("开启室内导航功能!")
            if self.voice_Content == "小车去厨房":
                #发信息给底盘
                self.nav2where_callback("厨房")

            if self.voice_Content == "小车去卧室":
                #发信息给主底盘
                self.nav2where_callback("卧室")

            if self.voice_Content == "小车去客厅":
                #发信息给底盘
                self.nav2where_callback("客厅")

            if self.voice_Content == "小车去起点":
                #发信息给底盘
                self.nav2where_callback("起点")

        #语音控制
        if self.voice_Content in control_strings:
            self.get_logger().info("开启语音控制功能!")
            if self.voice_Content == "小车启动":
                #发信息给底盘
                self.nav2where_callback("客厅")
            
            if self.voice_Content == "小车停止":
                #发信息给底盘
                self.publish_twist_stop()

        #远程控制
        if self.voice_Content in remote_strings:
            self.get_logger().info("开启远程控制功能!")
            control_text_msg = String()
            control_text_msg.data = self.voice_Content
            self.pub_control_text.publish(control_text_msg)#send the message of voiceText 
            self.get_logger().info(f'发送成功!发送给control_node的内容是:{control_text_msg.data}')#print the content of the message
        #人脸识别功能
        if self.voice_Content in face_strings:
            self.get_logger().info("开启人脸识别功能!")
            #发送ai_service的服务请求
            self.AI_Service_ask(self.voice_Content)
        #跌倒检测功能
        if self.voice_Content in fall_strings:
            self.get_logger().info("开启跌倒检测功能!")
            #发送ai_service的服务请求
            self.AI_Service_ask(self.voice_Content)

    #云端服务
    #1.发布请求
    def cloudService_ask(self,web_request):
        self.get_logger().info(f'要获得{web_request}的数据')
        if not self.cloudclient.wait_for_service(3.0):#! while not self.cloudclient.wait_for_service(1.0):
            self.get_logger().warn("服务不在线，我再等等!")
        request=CloudService.Request()
        request.web_request=web_request
        #主节点发送异步请求给cloud_service服务端
        self.cloudclient.call_async(request).add_done_callback(self.cloudService_response_callback)
    #2.响应服务端传来的结果
    def cloudService_response_callback(self,cloud_service_res):
        response=cloud_service_res.result()
        if response.request_value:
            self.get_logger().info(f'收到结果!结果是:{response.request_value}')
            #voicePlay_callback函数播报的信息
            if self.voice_Content == "温度":
                self.get_logger().info(f"{self.voice_Content}:{response.request_value}摄氏度")
                self.voicePlay_callback(f"{self.voice_Content}:{response.request_value}摄氏度" )
            elif self.voice_Content == "湿度":
                self.get_logger().info(f"{self.voice_Content}:百分之{response.request_value}")
                self.voicePlay_callback(f"{self.voice_Content}:百分之{response.request_value}")
            elif self.voice_Content == "二氧化碳":
                self.get_logger().info(f"{self.voice_Content}:百万分之{response.request_value}")
                self.voicePlay_callback(f"{self.voice_Content}:百万分之{response.request_value}")
            elif self.voice_Content == "光照":
                self.get_logger().info(f"{self.voice_Content}:{response.request_value}勒克斯")
                self.voicePlay_callback(f"{self.voice_Content}:{response.request_value}勒克斯")
        else:
            self.get_logger().info('没收到结果!')

    #AI_Service
    #我自己代码为了一眼丁真才命名为AI_Service,实际服务名叫:get_result
    #1.发布请求
    def AI_Service_ask(self,ai_request):
        self.get_logger().info(f'要完成{ai_request}的服务!')
        if not self.aiclient.wait_for_service(3.0):#! while not self.aiclient.wait_for_service(1.0):
            self.get_logger().warn("服务不在线，我再等等!")
        request=EasyMessage.Request()
        if ai_request == "录入操作员":
            camera_text_msg = String()
            camera_text_msg.data = "人脸"
            self.pub_camera_text.publish(camera_text_msg)  # send the message
            self.get_logger().info(
                f'发送成功!换成上面的摄像头')  # print the content of the message
            time.sleep(2)#改1
            request.type="add"
            request.data="操作员"
        if ai_request == "录入客户":
            camera_text_msg = String()
            camera_text_msg.data = "人脸"
            self.pub_camera_text.publish(camera_text_msg)  # send the message
            self.get_logger().info(
                f'发送成功!换成上面的摄像头')  # print the content of the message
            time.sleep(2)#改1
            request.type="add"
            request.data="客户"
        if ai_request == "人脸检测":
            request.type="check"
            request.data="操作员"
        if ai_request == "跌倒检测":
            camera_text_msg = String()
            camera_text_msg.data = "老人"
            self.pub_camera_text.publish(camera_text_msg)  # send the message
            self.get_logger().info(
                f'发送成功!换成下面的摄像头')  # print the content of the message
            request.type="fall"
            request.data="老人"
        #主节点发送异步请求给ai_service服务端
        self.aiclient.call_async(request).add_done_callback(self.aiService_response_callback)
    #2.响应服务端传来的结果
    def aiService_response_callback(self,ai_service_res):#！如果出问题可能是这里有问题！
        response=ai_service_res.result()
        if response.status == "录入成功":
            #在voicePlay话题主节点发布信息给voice_play_node要播报的信息
            self.voicePlay_callback("录入成功")
        if response.status == "检测到人脸":
            name = response.data
            #在voicePlay话题主节点发布信息给voice_play_node要播报的信息
            self.voicePlay_callback("你是%s"%name)
        if response.status == "没有检测到人脸":
            #在voicePlay话题主节点发布信息给voice_play_node要播报的信息
            self.voicePlay_callback("没有检测到人脸")

    #主节点通过AI_result获得跌倒检测的结果
    def recv_AI_result_callback(self,AI_result_msg):
        if AI_result_msg:
            self.get_logger().info("老人跌倒了")
            self.voicePlay_callback("老人跌倒了")
            self.sendMessage_callback()

    #主节点通过voicePlay话题发布播报信息给voice_play_node
    def voicePlay_callback(self,play_content):
        voice_play_msg = String()
        voice_play_msg.data = play_content
        self.pub_play_text.publish(voice_play_msg)
        self.get_logger().info(f'发送成功！发送内容是：{voice_play_msg.data}')#print the content of the message

    #紧急信息发送
    def sendMessage_callback(self):
        #发送老人跌倒的信息
        serious_msg = Bool()
        serious_msg.data = True
        self.pub_send_message.publish(serious_msg)

    #小车启动
    def publish_twist_start(self):
        self.twist_msg.linear.x = 0.1  # 设置线速度，使机器人沿x轴正方向以0.2的线速度移动
        self.cmd_vel_pub.publish(self.twist_msg)  # 发布Twist消息，控制机器人运动
        self.get_logger().info(f'发送成功！')#print the content of the message

    #小车停止
    def publish_twist_stop(self):
        self.twist_msg.linear.x = 0.0  # 设置线速度，使机器人沿x轴正方向以0.2的线速度移动
        self.cmd_vel_pub.publish(self.twist_msg)  # 发布Twist消息，控制机器人运动
        self.get_logger().info(f'发送成功！')#print the content of the message


def main(args=None):
    rclpy.init(args=args)  # 初始化ROS 2节点
    twist_controller = TwistController()  # 创建TwistController类的实例
    rclpy.spin(twist_controller)  # 运行节点，直到节点关闭
    twist_controller.destroy_node()  # 销毁节点
    rclpy.shutdown()  # 关闭ROS 2节点

if __name__ == '__main__':
    main()  # 调用main函数，启动节点

def main(args=None):
    """
    ros2运行该节点的入口函数
    编写ROS2节点的一般步骤
    1. 导入库文件
    2. 初始化客户端库
    3. 新建节点对象
    4. spin循环节点
    5. 关闭客户端库
    """
    rclpy.init(args=args) # 初始化rclpy
    robot_node = Robot_node("robot_node")  # 新建一个节点
    rclpy.spin(robot_node) # 保持节点运行，检测是否收到退出指令（Ctrl+C）
    rclpy.shutdown() # 关闭rclpy

 # #创建两个主节点的socket通信的发送端
    # def create_socket(self,send_msg):
    #     s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #     s.bind(('192.168.1.165', 1200))  #！绑定ip和端口号（IP为发送数据的树莓派ip，端口号自己指定）(可能会变)
    #     s.listen(5)
    #     c, address = s.accept()#等待别的树莓派接入
    #     socket_msg = send_msg
    #     c.send(socket_msg.encode('utf-8'))   #编码

