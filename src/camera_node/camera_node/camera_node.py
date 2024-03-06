import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import cv2
import numpy as np
from std_msgs.msg import String
import pygame
import pygame.camera
from pygame.locals import *
pygame.init()
pygame.camera.init()

class CameraSwitcher:
    def __init__(self, cameras=None,size=(640,480)):
        cameras_list = []
        if cameras is not None:
            for id in cameras:
                camera = pygame.camera.Camera(id, size)
                cameras_list.append(camera)

        self.cameras = cameras_list
        self.current_camera = 0

        self.cameras[self.current_camera].start()

    def change_camera(self, id):
        self.cameras[self.current_camera].stop()
        self.current_camera = id
        self.cameras[self.current_camera].start()

    def read(self):
        image = self.cameras[self.current_camera].get_image()
        frame = pygame.surfarray.array3d(image)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        return frame

class CameraPublisher(Node):
    def __init__(self, name):
        super().__init__(name)
        self.get_logger().info("[%s]Node has started" % name)
        self.camera_publisher = self.create_publisher(Image, "Image", 1)

        self.sub_camera_text = self.create_subscription(String, "cameraChange", self.recv_cameraChange_callback, 20)

        self.size = (640, 480)
        my_camera_list =  ["/dev/video0","/dev/video2"]  # 修改为您的摄像头设备路径
        self.fall_camera = 1
        self.face_camera = 0
        self.use_camera = self.face_camera
        self.switcher = CameraSwitcher(my_camera_list,self.size)

        self.get_logger().info("Using camera: [%s]" % self.use_camera)
        self.declare_parameter('open_camera', True)
        self.declare_parameter('switch_camera', self.use_camera)
        self.is_open = self.get_parameter("open_camera").value
        self.switcher.change_camera(self.use_camera)
        
        self.timer = self.create_timer(0.1, self.timer_callback)
        self.count = 0

    def recv_cameraChange_callback(self, camera_text_msg):
        self.camera_content = camera_text_msg.data
        self.is_open = False
        if self.camera_content == "老人":
            self.get_logger().info("Received command to switch to fall detection camera")   
            self.switcher.change_camera(self.fall_camera)
        elif self.camera_content == "人脸":
            self.get_logger().info("Received command to switch to face detection camera")
            self.switcher.change_camera(self.face_camera)
        self.is_open = True

    def timer_callback(self):   
        if self.is_open:
            frame = self.switcher.read()

            self.count += 1
            if frame is not None:
                img = Image()
                img.header.stamp = self.get_clock().now().to_msg()
                img.header.frame_id = "camera_frame"
                img.height = frame.shape[0]
                img.width = frame.shape[1]
                img.encoding = "bgr8"
                img.step = frame.shape[1] * 3
                img.data = np.array(frame).tobytes()
                self.camera_publisher.publish(img)
                if self.count == 5:
                    self.count = 0

def main(args=None):
    rclpy.init(args=args)
    node = CameraPublisher("camera")
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == "__main__":
    main()
