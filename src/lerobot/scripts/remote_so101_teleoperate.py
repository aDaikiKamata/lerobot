# !/usr/bin/env python

# Copyright 2025 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time

from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig
from lerobot.robots.remote_so101 import RemoteSO101Client, RemoteSO101ClientConfig
from lerobot.teleoperators.keyboard.teleop_keyboard import KeyboardTeleop, KeyboardTeleopConfig
from lerobot.teleoperators.so101_leader import SO101Leader, SO101LeaderConfig
from lerobot.utils.robot_utils import busy_wait
from lerobot.utils.visualization_utils import init_rerun, log_rerun_data

FPS = 30

# Create the robot and teleoperator configurations
robot_config = RemoteSO101ClientConfig(
    remote_ip="192.168.0.5",
    id="follower",
    cameras={
        "front": OpenCVCameraConfig(
            index_or_path=0, fps=30, width=640, height=480
        ),
    }
)
teleop_arm_config = SO101LeaderConfig(
    port="/dev/tty.usbmodem5A7A0180951", id="leader")
keyboard_config = KeyboardTeleopConfig(id="my_laptop_keyboard")

# Initialize the robot and teleoperator
robot = RemoteSO101Client(robot_config)
leader_arm = SO101Leader(teleop_arm_config)
keyboard = KeyboardTeleop(keyboard_config)

# Connect to the robot and teleoperator
# To connect you already should have this script running on LeKiwi: `python -m lerobot.robots.lekiwi.lekiwi_host --robot.id=my_awesome_kiwi`
robot.connect()
leader_arm.connect()
keyboard.connect()

# Init rerun viewer
init_rerun(session_name="remote_so101")

if not robot.is_connected or not leader_arm.is_connected or not keyboard.is_connected:
    raise ValueError("Robot or teleop is not connected!")

print("Starting teleop loop...")
while True:
    t0 = time.perf_counter()

    observation = robot.get_observation()
    print(observation.keys())
    action = leader_arm.get_action()
    _ = robot.send_action(action)

    # Visualize
    log_rerun_data(observation=observation, action=action)

    busy_wait(max(1.0 / FPS - (time.perf_counter() - t0), 0.0))
