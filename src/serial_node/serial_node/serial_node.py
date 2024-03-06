import rclpy
from rclpy.node import Node
from std_msgs.msg import String#基本消息类型
from mybot_interfaces.srv import SerialService
import time
#导入串口依赖
import binascii
import serial
#解析json的依赖
import json

class Serial_node(Node):
    def __init__(self,name):
        super().__init__(name)
        self.get_logger().info("serial_node ready!")
        self.ser = serial.Serial(port="/dev/microphone",
					        baudrate=115200,
                            parity=serial.PARITY_NONE,
                            bytesize=serial.EIGHTBITS,
                            stopbits=serial.STOPBITS_ONE,
                            timeout=1
					       )
        time.sleep(1)
        self.isOpen = False
        #打开串口
        self.Open_serial()
        #serial_node创建serial_Service服务端
        self.Serial_Server=self.create_service(SerialService,"serial_Service", self.serial_Service_callback)
        #serial_node创建isWake话题的发布者
        self.pub_wake_text=self.create_publisher(String,"isWake",30)
        #serial_node创建voicePlay话题的发布者
        self.pub_play_text=self.create_publisher(String,"voicePlay",10)
        #等待用户说唤醒词
        self.create_timer(0.05, self.wake)
        #提醒用户开机成功
        voice_play_msg = String()
        voice_play_msg.data = "开机成功"
        time.sleep(16)
        self.pub_play_text.publish(voice_play_msg)
        self.isOpen = True

    # ……………………………………………………唤醒…………………………………………………… #
    def wake(self):
        read_result_temp = self.handle_read_data()
        if type(read_result_temp) == tuple:
            (msg_type, msgid, temp) = read_result_temp
            if type(temp)==str:
                if self.isOpen:
                  wake_text_msg = String()
                  wake_text_msg.data = temp
                  self.get_logger().info(temp)
                  self.pub_wake_text.publish(wake_text_msg)
    # ……………………………………………………唤醒…………………………………………………… #

    # ……………………………………………………处理Serial_Service服务…………………………………………………… #
    def serial_Service_callback(self,request,response):
        self.get_logger().info("收到服务请求!")
        #录音的指令
        JSON = request.serial_request#接收来自其他节点发来的串口控制的json指令
        if JSON is not None:
            self.handle_send_data(0, JSON)
            read_result_temp = self.handle_read_data()
            if read_result_temp[1] != 0:
                print("msgid error")
            read_result_temp = self.handle_read_data()
            response.serial_res = str(read_result_temp[2])
            JSON = None#执行完json中的指令后清空json，从而保持serial_node等待json指令的状态
        return response
    # ……………………………………………………处理Serial_Service服务…………………………………………………… #

    # ……………………………………………………打开串口…………………………………………………… #
    def Open_serial(self):
        if self.ser.isOpen():
            self.get_logger().info("打开串口成功。")
            self.get_logger().info(self.ser.name)
            self.ser.flushInput()
        else:
            print("打开串口失败。")
    # ……………………………………………………打开串口…………………………………………………… #

    # ……………………………………………………串口数据处理底层…………………………………………………… #
    def joint(self,num_H, num_L):
        num_H = bin(num_H)[2:]
        num_L = bin(num_L)[2:]
        if ((len(num_H) > 8) or (len(num_L) > 8)):
            return None
        str0 = "00000000"
        num_H = str0[0:(8 - len(num_H))] + num_H
        num_L = str0[0:(8 - len(num_L))] + num_L
        num_bin = num_H + num_L
        num_bin = int(num_bin, 2)
        return num_bin

    def split(self,num):
        bin_num = bin(num)[2:]
        if len(bin_num) > 16:
            return None
        str0 = "0000000000000000"
        bin_num = str0[0:(16 - len(bin_num))] + bin_num
        bin_num_Hi = bin_num[0:8]
        bin_num_Lo = bin_num[8:]
        hex_num_Hi = int(bin_num_Hi, 2)
        hex_num_Lo = int(bin_num_Lo, 2)
        return (hex_num_Hi, hex_num_Lo)

    def send_json_formatting(self,send_json):
        send_json_bytes = send_json.encode("utf-8")
        send_json_hex_bytes = send_json_bytes.hex()
        formatting_data = []
        add_time = 1
        while add_time <= (len(send_json_hex_bytes) / 2):
            int_data = int((send_json_hex_bytes[2 * add_time - 2] + send_json_hex_bytes[2 * add_time - 1]),16)
            formatting_data.append(int_data)
            add_time += 1
        return formatting_data

    def reverse(self,num):
        num = bin(num)[2:]
        num = num.replace('0', '2')
        num = num.replace('1', '0')
        num = num.replace('2', '1')
        return int(num, 2)

    def check(self,check_data):
        data_sum = sum(check_data)
        check_sum = self.reverse(data_sum) + 1
        check_sum_byte = int(hex(check_sum)[len(hex(check_sum)) - 2:], 16)
        return check_sum_byte

    def check_full_data(self,data):
        check_sum = self.check(data[:len(data) - 1])
        if check_sum == data[len(data) - 1]:
            return True
        return check_sum

    def read_byte(self):
        data = self.ser.read(1)
        if data:
            byte_hex = str(binascii.b2a_hex(data))[2:-1]
            return int(byte_hex, 16)
        return None

    def data_joint(self,data_H, data_L):
        return self.joint(data_L, data_H)

    def data_split(self,data_num):
        (data_L, data_H) = self.split(data_num)
        return (data_H, data_L)
    # ……………………………………………………串口数据处理底层…………………………………………………… #

    # ……………………………………………………串口数据收发处理…………………………………………………… #
    def read_full_data(self):
        # 尝试读取消息头
        try_time = 0
        data_head = self.read_byte()
        while data_head is None:
            return None
        while data_head != 0xA5:
            data_head = self.read_byte()
            try_time += 1
            print("消息头不正确，正在重试……次数：" + str(try_time))  # 消息头
        try_time = 0
        # 继续读取消息协议部分并组成列表data，包括：消息头、用户ID、消息类型、消息体长度、消息ID、消息体头
        full_data = [data_head, ]
        read_time = 0
        while read_time < 7:
            read_result = self.read_byte()
            if read_result is None:
                self.ser.flushInput()
                print("连接错误(-1)")
                return -1
            full_data.append(read_result)
            read_time += 1
        userid = full_data[1]
        msg_type = full_data[2]
        msg_length = self.data_joint(full_data[3], full_data[4])
        msgid = self.data_joint(full_data[5], full_data[6])
        msg_head = full_data[7]
        # 根据消息体长度读取完整的消息的剩余部分，包括消息体除头外其他部分以及最后的校验位
        read_time = 0
        while read_time < msg_length:
            read_result = self.read_byte()
            if read_result is None:
                print("连接错误(-1)")
                return -1
            full_data.append(read_result)
            read_time += 1
        # 检查消息的校验和
        check_result = self.check_full_data(full_data)
        if check_result is not True:
            print("数据的校验和错误，本次数据无效(-2)")
            return check_result
        # 截取消息体，转换为字节集
        msg_body_int = full_data[7:len(full_data) - 1]
        msg_body_bytes = bytes(msg_body_int)
        # 返回：完整的接收消息、用户ID、消息类型、消息ID、消息体头、完整消息体的字节集
        return (full_data, userid, msg_type, msgid, msg_head, msg_body_bytes)
        
    def send_full_data(self,msg_type, msgid, msg_body_int):  # msg_type是要发送的消息类型，类型是int；msgid是要发送的消息ID，类型是int，若要发送确认消息类型则应保证消息ID一致；msg_body是消息体，类型是list int
        msg_length = len(msg_body_int)
        (msg_length_0, msg_length_1) = self.data_split(msg_length)
        (msgid_0, msgid_1) = self.data_split(msgid)
        full_data = [0xA5, 0x01, msg_type, msg_length_0, msg_length_1, msgid_0, msgid_1]
        add_time = 0
        while add_time < msg_length:
            full_data.append(msg_body_int[add_time])
            add_time += 1
        check_sum = self.check(full_data)
        full_data.append(check_sum)
        self.ser.write(full_data)
    # ……………………………………………………串口数据收发处理…………………………………………………… #

    # ……………………………………………………串口收发用户函数…………………………………………………… #
    def handle_read_data(self):  # 该函数用于处理串口接收的数据，正确情况下函数会返回列表(msg_type, msgid, True)或(msg_type, msgid, read_json);若出现异常则返回(read_result, None, False)或(userid, None, False)或(msg_type, msgid, False)
        # 初步处理读取的消息
        read_result = self.read_full_data()
        if type(read_result) != tuple:
            return (read_result, None, False)
        (full_data, userid, msg_type, msgid, msg_head, msg_body_bytes) = read_result
        if userid != 0x01:
            # 错误处理
            return (userid, None, False)
        # 对待处理的消息按类型进行分类，
        confirm_msg_body = [0xA5, 0x00, 0x00, 0x00]
        if msg_type == 0x01:
            # hand_shaking
            # 发送确认消息（握手消息的ID固定为0x00）
            # 返回握手消息类型和消息ID
            self.send_full_data(0xFF, msgid, confirm_msg_body)
            return (msg_type, msgid, True)
        elif msg_type == 0x04:
            # device_inf
            # 发送确认消息（根据设备消息的消息ID填写确认消息的消息ID）
            # 返回设备消息类型、消息ID和接收到的JSON
            read_json = msg_body_bytes.decode("utf-8")
            self.send_full_data(0xFF, msgid, confirm_msg_body)
            return (msg_type, msgid, read_json)
        elif msg_type == 0xFF:
            # confirm_type
            # 设备发送的确认消息，请确认该消息ID是否与发送给设备的主控消息一致
            # 返回该确认消息的ID用于与发送给设备的主控消息比较
            return (msg_type, msgid, True)
        else:
            # 错误处理
            return (msg_type, msgid, False)

    def handle_send_data(self,msgid, send_json):  # 该函数用于快速发送主控消息。其中，msgid是要发送的主控消息的ID，类型是int；send_json是要发送的主控消息的json，类型是str
        msg_body_int = self.send_json_formatting(send_json)
        self.send_full_data(0x05, msgid, msg_body_int)
    # ……………………………………………………串口收发用户函数…………………………………………………… #

# ……………………………………………………节点运行…………………………………………………… #
def main(args=None):
    rclpy.init(args=args) # 初始化rclpy
    serial_node = Serial_node("serial_node")  # 新建一个节点
    rclpy.spin(serial_node) # 保持节点运行，检测是否收到退出指令（Ctrl+C）
    rclpy.shutdown() # 关闭rclpy

