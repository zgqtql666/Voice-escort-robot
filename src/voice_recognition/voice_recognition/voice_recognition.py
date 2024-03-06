import rclpy
from rclpy.node import Node
import time
import os#系统找文件的库
import subprocess#让命令行执行命令的库
from mybot_interfaces.srv import SerialService
from std_msgs.msg import String#基本消息类型
from pypinyin import pinyin,lazy_pinyin,Style
import Levenshtein
#语音识别模块的库
import json
import base64
from urllib.request import urlopen
from urllib.request import Request
from urllib.error import URLError
from urllib.parse import urlencode
#转音频文件:16k32bit8通道的pcm音频文件->16ka6bit单通道的pcm文件
from pydub import AudioSegment

#异常情况的类
class DemoError(Exception):
    pass

class Voice_recognition(Node):
    def __init__(self,name):
        super().__init__(name)
        self.get_logger().info("voice_recognition ready!")
        #voice_recognition通过isWake话题获取serial_node发来的唤醒信息
        self.sub_wake_text= self.create_subscription(String,"isWake",self.recv_wake_callback,500)
        #voice_recognition创建voicePlay话题的发布者
        self.pub_play_text=self.create_publisher(String,"voicePlay",10)
        #voice_recognition创建一个serial_Service的客户端
        self.Serial_client=self.create_client(SerialService,"serial_Service")
        #voice_recognition创建microText话题的发布者
        self.pub_micro_text=self.create_publisher(String,"microText",20)
        #voice_recognition创建raycast话题的发布者
        self.raycast_command_pubulish=self.create_publisher(String,"raycast",20)

    #voice_recognition通过isWake话题获取serial_node发来的唤醒信息并保存用户需求语音文件并语音识别然后发给voice_node
    def recv_wake_callback(self,wake_text_msg):
        #树莓派依次发送以下命令给麦克风阵列
        commands=['{"type":"dump_audio","content":{"debug":3}}',
                  '{"type":"dump_audio","content":{"debug":0}}',
                  '{"type":"clean_pcm"}']
        #获取传来的json
        wake=wake_text_msg.data
        # 解析 JSON 数据
        try:
            if type(wake) == str:
                wake_data = json.loads(wake)
                # 获取 "info" 字段中的 JSON 字符串，并再次解析为 Python 对象
                info_data = json.loads(wake_data['content']['info'])
                #！获取"angle"的值,并将结果传给蚌
                angle=info_data['ivw']['angle']
                # 获取 "keyword" 的值
                keyword = info_data['ivw']['keyword']
                if keyword == "xiao3 wei1 xiao3 wei1":
                    self.voicePlay_callback("你好，有什么可以帮您")
                    # 等待播报完毕
                    time.sleep(1)
                #发送serial_Service的服务请求:开始录音->停止录音->下载音频文件
                    self.serial_Service_ask(commands[0])
                    time.sleep(5)#录音5秒
                    self.serial_Service_ask(commands[1])
                    try:
                        subprocess.run("adb pull oem/build/origin.pcm /home/orangepi/", shell=True,
                                    check=True, capture_output=True, universal_newlines=True)
                    # 如果命令执行失败，捕获异常并输出错误信息
                    except subprocess.CalledProcessError as e:
                        print("命令执行失败：", e)
                    self.serial_Service_ask(commands[2])
                #语音识别，并将结果传给主节点
                    micro_content=self.Speech_recognition()
                    self.get_logger().warn('完成语音识别!')
                    if micro_content == "小车过来":#完成声源定位
                        #把声源角度发给底盘
                        raycast_msg = String()
                        raycast_msg.data = str(angle)
                        self.raycast_command_pubulish.publish(raycast_msg)#send the message of microText
                        self.get_logger().info(f'发送成功！声源角度是：{raycast_msg.data}')#print the content of the message
                        self.voicePlay_callback("好的准备开始声源定位功能")
                    if micro_content!=None:
                        if micro_content in ["温度", "湿度", "二氧化碳", "光照"]:
                            micro_text_msg = String()
                            micro_text_msg.data = micro_content
                            self.pub_micro_text.publish(micro_text_msg)  # send the message of microText
                            self.get_logger().info(
                                f'发送成功！发送内容是：{micro_text_msg.data}')  # print the content of the message
                            self.voicePlay_callback(f"好的开始获得{micro_text_msg.data}数据")
                        else:
                            micro_text_msg = String()
                            micro_text_msg.data = micro_content
                            self.pub_micro_text.publish(micro_text_msg)#send the message of microText
                            self.get_logger().info(f'发送成功！发送内容是：{micro_text_msg.data}')#print the content of the message
                            self.voicePlay_callback(f"好的开始{micro_text_msg.data}")
                    else:
                        self.get_logger().info('语音识别后的结果不在服务范围内1')#print the content of the message
                        self.voicePlay_callback("你好，刚刚没听清，请重新说出您的需求")
                else:
                    self.voicePlay_callback("请重新唤醒")
        except Exception as e:
            self.get_logger().info(str(e))#print the content of the message
            self.get_logger().info('语音识别后的结果不在服务范围内')#print the content of the message

    #serial_Service服务
    #1.发布请求
    def serial_Service_ask(self,serial_request):
        if not self.Serial_client.wait_for_service(1.0):#！ while not self.Serial_client.wait_for_service(1.0):
            self.get_logger().warn("服务不在线，我再等等!")
        request=SerialService.Request()
        request.serial_request=serial_request
        #voice_recognition发送异步请求给serial_Service服务端
        self.Serial_client.call_async(request).add_done_callback(self.Serial_Service_response_callback)
    #2.响应服务端传来的结果（没实际意义，保护作用）
    def Serial_Service_response_callback(self,serial_Service_res):
        response=serial_Service_res.result()
        # if response.serial_res:
        #     self.get_logger().info(f'{response.serial_res}')
        if  not response.serial_res:
            self.get_logger().info('没收到结果!')

    #16k32bit8通道的pcm音频文件->16ka6bit单通道的pcm文件
    def convert_audio(self,input_file, output_file):
        # 加载原始音频文件
        audio = AudioSegment.from_file(input_file, format="pcm", frame_rate=16000, channels=8, sample_width=4)
        # 将音频文件转换为16-bit单通道的PCM
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        # 保存转换后的音频文件
        with open(output_file, "wb") as f:
            f.write(audio.raw_data)

    #语音识别时要用到的函数
    def fetch_token_recognition(self):
        params = {'grant_type': 'client_credentials',
                'client_id': 'G7QrG2Wd23jhez7O9AqtEChF',
                'client_secret': 'g0iIpdEY5WVm0k4xaBt6HGoEViwqwhzW'}
        post_data = urlencode(params)
        post_data = post_data.encode( 'utf-8')
        TOKEN_URL = 'http://aip.baidubce.com/oauth/2.0/token'
        req = Request(TOKEN_URL, post_data)
        try:
            f = urlopen(req)
            result_str = f.read()
        except URLError as err:
            print('token http response http code : ' + str(err.code))
            result_str = err.read()
        result_str =  result_str.decode()
        # print(result_str)
        result = json.loads(result_str)
        # print(result)
        SCOPE = 'audio_voice_assistant_get'
        if ('access_token' in result.keys() and 'scope' in result.keys()):
            # print(SCOPE)
            if SCOPE and (not SCOPE in result['scope'].split(' ')):  # SCOPE = False 忽略检查
                raise DemoError('scope is not correct')
            # print('SUCCESS WITH TOKEN: %s  EXPIRES IN SECONDS: %s' % (result['access_token'], result['expires_in']))
            return result['access_token']
        else:
            raise DemoError('MAYBE API_KEY or SECRET_KEY not correct: access_token or scope not found in token response')
        
    #语音识别函数
    def Speech_recognition(self):
        self.get_logger().warn('正在语音识别!')
        timer = time.perf_counter            
        # On most other platforms the best timer is time.time()
        timer = time.time
        ORIGIN_FILE='/home/orangepi/out.pcm'#ORIGIN_FILE='/home/env/out.pcm'
        OUT_FILE='/home/env/out.pcm'# 只支持 pcm/wav/amr 格式，极速版额外支持m4a 格式
        self.convert_audio(ORIGIN_FILE, OUT_FILE)
        AUDIO_FILE='/home/orangepi/out.pcm'#AUDIO_FILE='/home/env/out.pcm'
        # 文件格式
        FORMAT = AUDIO_FILE[-3:]  # 文件后缀只支持 pcm/wav/amr 格式，极速版额外支持m4a 格式
        CUID = '123456PYTHON'
        # 采样率
        RATE = 8000  # 固定值
        # 普通版
        DEV_PID = 1537  # 1537 表示识别普通话，使用输入法模型。根据文档填写PID，选择语言及识别模型
        ASR_URL = 'http://vop.baidu.com/server_api'
        token = self.fetch_token_recognition()
        speech_data = []
        with open(AUDIO_FILE, 'rb') as speech_file:
            speech_data = speech_file.read()
        length = len(speech_data)
        if length == 0:
            raise DemoError('file %s length read 0 bytes' % AUDIO_FILE)
        speech = base64.b64encode(speech_data)
        speech = str(speech, 'utf-8')
        params = {'dev_pid': DEV_PID,
                #"lm_id" : LM_ID,    #测试自训练平台开启此项
                'format': FORMAT,
                'rate': RATE,
                'token': token,
                'cuid': CUID,
                'channel': 1,
                'speech': speech,
                'len': length
                }
        post_data = json.dumps(params, sort_keys=False)
        # print post_data
        req = Request(ASR_URL, post_data.encode('utf-8'))
        req.add_header('Content-Type', 'application/json')
        try:
            begin = timer()
            f = urlopen(req)
            result_str = f.read()
            print ("Request time cost %f" % (timer() - begin))
        except URLError as err:
            print('asr http response http code : ' + str(err.code))
            result_str = err.read()
        result_str = str(result_str, 'utf-8')
        # print(result_str)
       # 使用 json.loads() 方法解析 JSON 数据为 Python 字典对象
        data_dict = json.loads(result_str)
        speech_text = data_dict.get('result', [''])[0].rstrip("。")
        print(f"语音识别后内容:{speech_text}")
        voice_content_result=self.extract_keywords_from_speech(speech_text)
        print(f"提取关键词后结果:{voice_content_result}")
        self.delete_sound_file('/home/orangepi/origin.pcm')
        self.delete_sound_file('/home/orangepi/out.pcm')
        return voice_content_result

    #！提取关键词
    def extract_keywords_from_speech(self, speech_text):
        best_match = None
        best_score = 0
        keywords = {
                    "温度": ["温度", "摄氏度","热","冷","今天温度多少","今天多少度","多少度"],
                    "湿度": ["湿度", "干燥", "潮湿", "湿润", "湿气","干","潮","旱","湿","今天湿度多少"],
                    "二氧化碳": ["二氧化碳", "浓度","今天二氧化碳浓度多少"],
                    "光照": ["光照", "亮度", "明亮", "暗", "勒克斯", "流明","今天光强多少","光照强度"],
                    "小车过来":["小车过来"],
                    "小车启动":["小车启动"],
                    "小车停止":["小车停止"],
                    "小车去厨房":["小车去厨房","去厨房","厨房"],
                    "小车去卧室":["小车去卧室","去卧室","卧室"],
                    "小车去起点":["远点","原点","去原点","回原点"],
                    "小车去客厅":["小车去客厅","小车回客厅","去客厅","客厅"],
                    "打开风扇":["打开风扇","开风扇","开电扇"],
                    "打开台灯":["打开台灯","开台灯","开电灯"],
                    "打开窗帘":["打开窗帘","拉起窗帘"],
                    "关闭风扇":["关闭风扇","关风扇","关电扇"],
                    "关闭台灯":["关闭台灯","关台灯","关电灯"],
                    "关闭窗帘":["关闭窗帘","关窗帘","拉下窗帘"],
                    "录入操作员":["录入操作员","操作员"],
                    "录入客户":["录入客户","客户"],
                    "人脸检测":["人脸检测","开始人脸检测","人脸识别"],
                    "跌倒检测":["跌倒检测","跌倒","开始跌倒检测","老人"],
                   }
        
        for action in keywords:
        
            for keyword in keywords[action]:
                keyword_pinyin = ''.join(lazy_pinyin(keyword))
                speech_text_pinyin = ''.join(lazy_pinyin(speech_text))
                distance = Levenshtein.distance(keyword_pinyin, speech_text_pinyin)
                similarity = 1 - (distance / max(len(keyword_pinyin), len(speech_text_pinyin)))
                if similarity > best_score and similarity >= 0.5:
                    best_match = action
                    best_score = similarity
                if keyword in speech_text:
                    return action
                    
        if best_score != 0 and best_match is not None:
            self.get_logger().info(best_match)#测
            return best_match
        return None

    #删除录音文件
    def delete_sound_file(self, file_path):
        try:
            # 删除音频文件
            os.remove(file_path)
        except OSError as e:
            self.get_logger().warn('Error deleting sound file: %s' % str(e))

    #voice_recognition通过voicePlay话题发布播报信息
    def voicePlay_callback(self,play_content):
        voice_play_msg = String()
        voice_play_msg.data = play_content
        self.pub_play_text.publish(voice_play_msg)
        self.get_logger().info(f'发送成功！发送内容是：{voice_play_msg.data}')#print the content of the message

def main(args=None):
    rclpy.init(args=args) # 初始化rclpy
    voice_recognition = Voice_recognition("voice_recognition")  # 新建一个节点
    rclpy.spin(voice_recognition) # 保持节点运行，检测是否收到退出指令（Ctrl+C）
    rclpy.shutdown() # 关闭rclpy
