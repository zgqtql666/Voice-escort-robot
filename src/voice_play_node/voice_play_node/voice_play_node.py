import rclpy
from rclpy.node import Node
from std_msgs.msg import String#基本消息类型
#导入语音播报的库
import edge_tts
import asyncio
import subprocess
import pygame
import os
import aiofiles
import asyncio
import re
from pypinyin import pinyin, Style
async def replace_files(source_path, target_path):
    async with aiofiles.open(source_path, mode='rb') as source_file:
        async with aiofiles.open(target_path, mode='wb') as target_file:
            content = await source_file.read()
            await target_file.write(content)
def sanitize_filename(text, max_length=255):
    # 使用 pypinyin 库将中文字符转换为拼音
    pinyin_list = pinyin(text, style=Style.NORMAL)
    pinyin_text = ''.join([item[0] for item in pinyin_list])

    # 去除非字母数字的字符，仅保留字母数字和下划线
    sanitized_text = re.sub(r'[^a-zA-Z0-9_]', '_', pinyin_text)

    # 限制文件名长度
    sanitized_text = sanitized_text[:max_length]

    return sanitized_text

def set_system_volume(volume_percent):
    # 将音量转换为0-100的范围
    volume = int(volume_percent)

    # 使用amixer命令设置音量
    subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{volume}%"])
output = '/home/orangepi/result.mp3'
voice_folder = "/home/orangepi/voice_folder"

async def TTS(text):
    voice_path = os.path.join(voice_folder,sanitize_filename(text))
    if os.path.exists(voice_path):
        await replace_files(voice_path,output)
    else:
        voice = 'zh-CN-XiaoxiaoNeural'
        rate = '-10%'
        volume = '+100%'
        tts = edge_tts.Communicate(text=text, voice=voice, rate=rate, volume=volume)
        await tts.save(output)
        await tts.save(voice_path)

class Voice_play_node(Node):
    def __init__(self,name):
        super().__init__(name)
        set_system_volume(100)#！
        pygame.mixer.init()
        self.get_logger().info("voice_play_node ready!")
        #voice_play_node通过voicePlay话题获取要播报的信息
        self.sub_play_text= self.create_subscription(String,"voicePlay",self.recv_play_callback,10)
        
    #voice_play_node通过voicePlay话题接收到要播报的信息
    def recv_play_callback(self,voice_play_msg):
        self.play_Content =voice_play_msg.data
        try:
            if self.play_Content != "":
                self.get_logger().info(f"收到！要播报的内容是:{self.play_Content}")
                asyncio.run(TTS(self.play_Content))
                
                
                track = pygame.mixer.music.load(output)
                pygame.mixer.music.set_volume(1)  # 设置音量大小0~1的浮点数
                pygame.mixer.music.play()
                
                while pygame.mixer.music.get_busy():  # 在音频播放为完成之前不退出程序
                    pass

                try:
                    os.remove(output)
                    self.get_logger().info("播报完毕!") 
                except OSError as e:
                    self.get_logger().warn('Error deleting sound file: %s' % str(e))
        except Exception as e:
            pass

def main(args=None):
    rclpy.init(args=args) # 初始化rclpy
    voice_play_node = Voice_play_node("voice_play_node")  # 新建一个节点
    rclpy.spin(voice_play_node) # 保持节点运行，检测是否收到退出指令（Ctrl+C）
    rclpy.shutdown() # 关闭rclpy
if __name__ == "__main__":
    main()
