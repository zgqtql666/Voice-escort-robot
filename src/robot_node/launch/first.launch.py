# 导入库
from launch import LaunchDescription
from launch_ros.actions import Node
#重启节点的依赖
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch.actions import RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch import LaunchDescription

def generate_launch_description():
    # 定义节点
    camera_node = Node(
        package="camera_node",
        executable="camera_node",
        output='screen',
        emulate_tty=True,
        respawn=False,#不重启节点
    )

    voice_play_node = Node(
        package="voice_play_node",
        executable="voice_play_node",
        output='screen',
        emulate_tty=True,
        respawn=False,
    )

    # serious_node = Node(
    #     package="serious_node",
    #     executable="serious_node",
    #     output='screen',
    #     emulate_tty=True,
    #     respawn=True,
    # )

    # control_node = Node(
    #     package="control_node",
    #     executable="control_node",
    #     output='screen',
    #     emulate_tty=True,
    #     respawn=True,
    # )

    # web_node = Node(
    #     package="web_node",
    #     executable="web_node",
    #     output='screen',
    #     emulate_tty=True,
    #     respawn=True,
    # )

    ai_node = Node(
        package="ai_node",
        executable="ai_node",
        output='screen',
        emulate_tty=True,
        respawn=False,
    )

    robot_node = Node(
        package="robot_node",
        executable="robot_node",
        output='screen',
        emulate_tty=True,
        respawn=False,
    )

    serial_node = Node(
        package="serial_node",
        executable="serial_node",
        output='screen',
        emulate_tty=True,
        respawn=False,
    )

    voice_recognition = Node(
        package="voice_recognition",
        executable="voice_recognition",
        output='screen',
        emulate_tty=True,
        respawn=False,
    )

    # nodes = [camera_node, voice_play_node, serious_node, control_node, web_node, ai_node, robot_node, serial_node, voice_recognition]
    nodes = [camera_node, voice_play_node, ai_node, robot_node, serial_node,voice_recognition]

    # # 定义重启处理器
    # def create_restart_handler(node_name):
    #     return RegisterEventHandler(
    #         event_handler=OnProcessExit(
    #             target_action=Node(
    #                 package="voice_recognition",
    #                 executable="voice_recognition",
    #                 output='screen',
    #                 emulate_tty=True,
    #                 respawn=True,
    #             ),
    #             on_exit=[
    #                 LogInfo(
    #                     msg=f'{node_name}节点死亡了！！！正在重启{node_name}节点！！！',
    #                 ),
    #             ],
    #         ),
    #     )

    #restart_handlers = [create_restart_handler(node_name) for node_name in ["camera_node", "voice_play_node", "serious_node", "control_node","ai_node", "robot_node", "serial_node", "voice_recognition"]]
#!restart_handlers = [create_restart_handler(node_name) for node_name in ["camera_node", "voice_play_node", "serious_node", "control_node", "web_node", "ai_node", "robot_node", "serial_node", "voice_recognition"]]

    # 创建 LaunchDescription 对象
    launch_description = LaunchDescription(nodes)
#!launch_description = LaunchDescription(nodes + restart_handlers)

    return launch_description

