import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
#紧急信息api依赖
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.sms.v20210111 import sms_client, models
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile

class Serious_node(Node):
    def __init__(self,name):
        super().__init__(name)
        self.get_logger().info("serious_node ready!")

        self.sub_send_message= self.create_subscription(Bool,"sendMessage",self.recv_warn_callback,2)

    def recv_warn_callback(self,msg):
        self.Serious=msg.data
        self.get_logger().info("收到！")
        if self.Serious:
            try:
                cred = credential.Credential('AKIDAMjFbkgu5GMJArriQ8pYCf4XqxpdL5mN', 'mXs0AKXxHgDg6Uiz6HVkrqlRuCRYmUBs')
                httpProfile = HttpProfile()
                httpProfile.reqMethod = "POST"
                httpProfile.reqTimeout = 30
                httpProfile.endpoint = "sms.tencentcloudapi.com"
                clientProfile = ClientProfile()
                clientProfile.signMethod = "TC3-HMAC-SHA256"
                clientProfile.language = "en-US"
                clientProfile.httpProfile = httpProfile
                client = sms_client.SmsClient(cred, "ap-guangzhou", clientProfile)
                req = models.SendSmsRequest()
                req.SmsSdkAppId = "1400840029"
                req.SignName = "嵌瓷入心公众号"
                req.TemplateId = "1872055"
                req.TemplateParamSet = []
                req.PhoneNumberSet = ["+8615388296926"]#!
                req.SessionContext = ""
                req.ExtendCode = ""
                req.SenderId = ""
                resp = client.SendSms(req)
                # print(resp.to_json_string(indent=2))
            except TencentCloudSDKException as err:
                print(err)
        self.get_logger().info("要换手机号码")
        self.Serious=False

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
    serious_node = Serious_node("serious_node")  # 新建一个节点
    rclpy.spin(serious_node) # 保持节点运行，检测是否收到退出指令（Ctrl+C）
    rclpy.shutdown() # 关闭rclpy
