import binascii
import serial
from time import sleep

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, Int32
from mybot_interfaces.srv import CloudService

ser = serial.Serial(port="/dev/web",
                                baudrate=4800,
                                parity=serial.PARITY_NONE,
                                bytesize=serial.EIGHTBITS,
                                stopbits=serial.STOPBITS_ONE,
                                timeout=1
                                )

# ……………………………………………………串口数据处理底层…………………………………………………… .#

def joint(num_H, num_L):
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


def joint_16(num_H, num_L):
    num_H = bin(num_H)[2:]
    num_L = bin(num_L)[2:]
    if ((len(num_H) > 16) or (len(num_L) > 16)):
        return None
    str0 = "0000000000000000"
    num_H = str0[0:(16 - len(num_H))] + num_H
    num_L = str0[0:(16 - len(num_L))] + num_L
    num_bin = num_H + num_L
    num_bin = int(num_bin, 2)
    return num_bin


def split(num):
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


def CRC_check(datas):
    crc16 = 0xffff
    poly = 0xa001
    for data in datas:
        # 表示将datas列表中的每一个变量赋值给data
        # 在此你可以自由输入数值，校验的次数时有你输入的数值的多少决定的。
        crc16 = data ^ crc16
        # ^异或运算，如果两个位为异，则该位结果时1，否则是0.
        for i in range(8):
            # 对于每一个data,都需要右移8次，可以简单理解为对每一位都完成校验
            if 1 & (crc16) == 1:
                # crc16与上1的结果（16位二进制）只有第0位是1或0，其他都是0
                # & 与运算：都是1才是1，否则为0
                crc16 = crc16 >> 1
                # >> 右移，即从高位向低位移动，高位补充0
                crc16 = crc16 ^ poly
            else:
                crc16 = crc16 >> 1
    # 将10进制转化成16进制
    crc16 = hex(int(crc16))
    # 大写
    crc16 = crc16[2:].upper()
    length = len(crc16)
    # 一些结果以0开头，会自动把0给吞掉，.zfill(2)可以让结果以二进制的形式输出
    high = crc16[0:length-2].zfill(2)
    high = str(high)
    low = crc16[length-2:length].zfill(2)
    low = str(low)
    return (int(high, 16), int(low, 16))


def CRC16_check_modbus(data):
    crc = 0xFFFF
    for i in range(len(data)):
        crc ^= data[i]
        for j in range(8):
            if crc | 0xFFFE == 0xFFFF:
                crc = crc >> 1
                crc ^= 0xA001
            else:
                crc = crc >> 1
    return (split(crc))


def read_byte():
    data = ser.read(1)
    if data:
        byte_hex = str(binascii.b2a_hex(data))[2:-1]
        return int(byte_hex, 16)
    print("ser overtime, waiting...")
    read_byte()
# ……………………………………………………串口数据处理底层…………………………………………………… #


# ……………………………………………………串口数据收发处理…………………………………………………… #
def send_ask_data(register_loc):
    msg = [0x01, 0x03, 0x00, register_loc, 0x00, 0x01]
    (CRC_H, CRC_L) = CRC16_check_modbus(msg)
    msg.append(CRC_L)
    msg.append(CRC_H)
    ser.write(msg)


def read_response_data():
    response_data = []
    for i in range(3):
        temp_data = read_byte()
        if (temp_data != None):
            response_data.append(temp_data)
        else:
            return -1
    i = 0
    if (response_data[0] == 0x01 and response_data[1] == 0x03):
        data_length = response_data[2]
    acquire_data = []
    for i in range(data_length):
        temp_data = read_byte()
        if (temp_data != None):
            response_data.append(temp_data)
            acquire_data.append(temp_data)
        else:
            return -1
    (CRC_H, CRC_L) = CRC16_check_modbus(response_data)
    if (CRC_L == read_byte() and CRC_H == read_byte()):
        data_len = len(acquire_data)
        if (data_len == 1):
            data = acquire_data[0]
        elif (data_len == 2):
            data = joint(acquire_data[0], acquire_data[1])
        else:
            data = -2
        return (data)
    else:
        return -2
# ……………………………………………………串口数据收发处理…………………………………………………… #


# ……………………………………………………串口数据收发处理…………………………………………………… #

# ……………………………………………………串口数据收发处理…………………………………………………… #


class AirDataPublisher(Node):
    def __init__(self,name):
        super().__init__(name)
        self.Inital()#初始化串口
        self.get_logger().info("web_node ready!")
        # air_data_node创建cloud_service服务
        self.cloudserver = self.create_service(
            CloudService, "cloud_service", self.cloudService_callback)

    def Inital(self):#初始化串口
        if ser.isOpen():
            self.get_logger().info("打开串口成功！")
            self.get_logger().info(ser.name)
        else:
            self.get_logger().info("打开串口失败！")

    def cloudService_callback(self, request, response):
        self.get_logger().info("收到来自主节点的请求!")
        response.request_res = request.web_request
        response.request_value = str(self.get_air_data(request.web_request))
        if response.request_value == None:
            self.get_logger().info("不属于cloud_service的范畴!")
        self.get_logger().info("cloud_service完毕!")
        return response

    def get_air_data(self,item):
        self.get_logger().info("%s"% item)
        if (item ==  "湿度"):
            send_ask_data(0x02)
            get_data = read_response_data()
            if (get_data >= 0):
                get_data /= 10
            return get_data
        elif (item == "温度"):
            send_ask_data(0x03)
            get_data = read_response_data()
            if (get_data >= 0):
                get_data /= 10
            return get_data
        elif (item == "二氧化碳"):
            send_ask_data(0x08)
            get_data = read_response_data()
            return get_data
        elif (item == "光照"):
            send_ask_data(0x05)
            Lux_H = read_response_data()
            send_ask_data(0x06)
            Lux_L = read_response_data()
            if (Lux_H >= 0 and Lux_L >= 0):
                Lux = joint_16(Lux_H, Lux_L)
                return Lux
            return min(Lux_H, Lux_L)
        else:
            return None

def main(args=None):
    rclpy.init(args=args)
    air_data_publisher = AirDataPublisher("air_data_publisher")
    rclpy.spin(air_data_publisher)
    air_data_publisher.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
