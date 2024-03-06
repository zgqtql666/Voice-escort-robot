#!/usr/bin/env python3
import os
import sys
import threading
import time
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from mybot_interfaces.srv import EasyMessage
import json
from collections import deque
import numpy as np
import cv2
import insightface
from insightface.app import FaceAnalysis
import torch
import torch.nn.functional as F
import gc
from ultralytics import YOLO
import subprocess
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup

class HiddenPrints:

    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = open(os.devnull, "w")

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout


def draw(img, face, text):
    dimg = img.copy()
    box = face.bbox.astype(np.int_)
    color = (0, 0, 255)
    cv2.rectangle(dimg, (box[0], box[1]), (box[2], box[3]), color, 2)
    cv2.putText(
        dimg,
        "%s" % (text),
        (box[0] - 1, box[1] - 4),
        cv2.FONT_HERSHEY_COMPLEX,
        0.7,
        (0, 255, 0),
        1,
    )
    return dimg


class FaceRecognition:
    def __init__(self, output=True):
        self.userlist = []

    def add(self, id, gender, age, embedding) -> bool:
        self.userlist.append(
            {"id": id, "gender": gender, "age": age, "embedding": embedding}
        )

    def isexist(self, id) -> bool:
        for user in self.userlist:
            if id == user["id"]:
                return True
        return False

    def embed(self, embedding):
        feature = np.array(embedding).reshape((1, -1))
        embedding_tensor = torch.from_numpy(feature)
        embedding_tensor = F.normalize(embedding_tensor, dim=1)
        embedding = embedding_tensor.numpy()
        return embedding

    def get(self, frame):
        with HiddenPrints():
            model = FaceAnalysis(name="buffalo_s", providers=["CPUExecutionProvider"])
            model.prepare(ctx_id=0, det_size=(640, 640))
            faces = model.get(frame)
        del model
        gc.collect()
        return faces

    def detect(self, image_path):
        img = cv2.imread(image_path)
        faces = self.get(img)
        return faces

    def detect_(self, frame):
        img = frame
        faces = self.get(img)
        return faces

    def check(self, gender, age, embedding, dist):
        best = None
        best_dist = dist
        for user in self.userlist:
            f_dist = self.feature_compare(embedding, user["embedding"])
            # if (
            #     gender == user["gender"]
            #     and abs(int(user["age"]) - age) < 50
            #     and f_dist < dist
            # ):
            if f_dist < dist:
                if best_dist > f_dist:
                    best = user
                    best_dist = f_dist
        if best is not None:
            return best, best_dist
        return None, None

    def feature_compare(self, feature1, feature2):
        diff = np.subtract(feature1, feature2)
        dist = np.sum(np.square(diff), 1)
        return dist

class FallDtect:
    def __init__(self, output=True):
        self.model = YOLO('yolov8n-pose.pt')  # pretrained YOLOv8n model

    def checkFall(self,frame_list,height):
        frames = [frame for frame in frame_list]
        result_list = [self.model(cv2.flip(frames[-1],-1))]
        
        for results in result_list:
            for result in results:
                plot =  result.plot(conf=False,kpt_line=False,masks=False)
                keypoints = result.keypoints

            for keypoint in keypoints:
                points = []
                ym = 0
                for i in range(len(keypoint.xy[0])):
                    point = keypoint[0].xy[0][i]
                    x = int(point[0])
                    y = int(point[1])
                    points.append([x,y])
                try:
                    xm = (points[5][0] + points[6][0]) / 2
                    ym = (points[5][1] + points[6][1]) / 2
                    self.get_logger().info("老人高度:%d"%ym)
                except:
                    pass
                print(ym)
                if ym >= height:
                    return True,plot
                
            return False,None

Image_list = deque(maxlen=10)


class AI_Node(Node):
    def __init__(self, name):
        super().__init__(name)
        self.FR = FaceRecognition()
        self.timer_cb_group = MutuallyExclusiveCallbackGroup()

        self.AI_Serivice = self.create_service(
            EasyMessage, "get_result", self.handle_AI_Serivice
        )
        self.ImageScubscribe = self.create_subscription(
            Image, "Image", self.ImageSubscribe, 1,callback_group=self.timer_cb_group
        )
        
        self.Fall_publisher = self.create_publisher(String, "AI_result", 10)
        self.result_publisher = self.create_publisher(Image, "AI_Image", 10)
        self.FallDtect = FallDtect()
        self.Fall_mode = False
        self.timer = self.create_timer(1, self.timer_callback)
        self.get_logger().warn("AI_Node Ready!")
        # ros2 service call /get_result mybot_interfaces/srv/SimpleMessage "{a: 5,b: 10}"


    # ======================================================
    def timer_callback(self):
        if(self.Fall_mode):
            ret,plot = self.FallDtect.checkFall(Image_list,200)
            if ret:
                self.get_logger().info("检测到有人摔倒了")
                msg = String()
                msg.data = '有人摔倒了'
                self.Fall_publisher.publish(msg)
                self.publish_Image(plot)
                self.Fall_mode = False
            self.get_logger().info("正在检测")

    def ImageSubscribe(self, msg):
        frame = np.frombuffer(msg.data, dtype=np.uint8).reshape(
            msg.height, msg.width, -1
        )
        # frame = cv2.flip(frame, 0)
        
        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        Image_list.append(frame)
        
        # self.get_logger().info(f"image had received")

    def publish_Image(self, frame):
        img = Image()
        img.header.stamp = self.get_clock().now().to_msg()
        img.header.frame_id = "camera_frame"
        img.height = frame.shape[0]
        img.width = frame.shape[1]
        img.encoding = "bgr8"
        img.step = 640 * 3
        img.data = np.array(frame).tobytes()
        self.result_publisher.publish(img)
        self.get_logger().info("Image published.")

    def handle_AI_Serivice(self, request, response):
        self.get_logger().info(f"接收Service请求")


        response.status = "请重试"
        response.data = ""

        if len(Image_list) <= 0:
            self.get_logger().info(f"没有图片")
            response.status = "failed"
            response.data = "camera_node not open"
            return response
        
        if request.type == "check":
            frame = Image_list[-1]
            faces = self.FR.detect_(frame)
            rimg = frame.copy()
            for face in faces:
                gender = face["gender"]
                age = face["age"]
                embedding = self.FR.embed(face["embedding"])
                best, best_dist = self.FR.check(gender, age, embedding, 1.0)
                if best == None:
                    response.status = "没有检测到人脸"
                else:
                    id = best["id"]
                    self.FR.add(best["id"], gender, age, embedding)
                    self.get_logger().warn(
                        "detect users %s,%s" % (best["id"], best_dist)
                    )
                    response.status = "检测到人脸"
                    response.data = best["id"]
                    rimg = draw(rimg, face,best["id"])
                    self.publish_Image(rimg)

        if request.type == "add":
            frame = Image_list[-1]
            faces = self.FR.detect_(frame)
            rimg = frame.copy()
            #print("shit")测1前面faces有问题
            for face in faces:
                #print("shit")#测1前面有问题
                gender = face["gender"]
                age = face["age"]
                embedding = self.FR.embed(face["embedding"])
                id = request.data
                self.FR.add(id, gender, age, embedding)
                self.get_logger().warn(
                    "add users %s" % (id)
                )
                response.status = "录入成功"
                rimg = draw(frame, face, id)
                self.publish_Image(rimg)

        if request.type == "fall": 
            self.Fall_mode = True
        return response


def main(args=None):
    rclpy.init(args=args)  # 初始化rclpy
    node = AI_Node("ai_node")  # 新建一个节点
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        node.destroy_node()
    # rclpy.spin(node)  # 保持节点运行，检测是否收到退出指令（Ctrl+C）
    rclpy.shutdown()  # 关闭rclpy
if __name__ == "__main__":
    main()
