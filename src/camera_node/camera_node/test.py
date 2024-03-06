import pygame
import pygame.camera
from pygame.locals import *
import time

pygame.init()
pygame.camera.init()

# 获取摄像头列表
camera_list = pygame.camera.list_cameras()

if not camera_list:
    print("未找到摄像头")
else:
    # 选择第一个摄像头
    camera = pygame.camera.Camera(camera_list[0], (640, 480))
    camera.start()

    screen = pygame.display.set_mode((640, 480))

    running = True
    frame_count = 0
    start_time = time.time()

    while running:
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False

        # 从摄像头获取图像
        image = camera.get_image()

        # 在窗口中显示图像
        screen.blit(image, (0, 0))

        # 计算帧率
        frame_count += 1
        if frame_count >= 10:
            end_time = time.time()
            elapsed_time = end_time - start_time
            frame_rate = frame_count / elapsed_time
            frame_count = 0
            start_time = end_time

            # 显示帧率
            font = pygame.font.Font(None, 36)
            text = font.render(f"FPS: {frame_rate:.2f}", True, (255, 255, 255))
            screen.blit(text, (10, 10))

        pygame.display.flip()

    camera.stop()
    pygame.quit()
