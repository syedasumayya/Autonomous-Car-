# Autonomous Car — WRO Future Engineers 2026

Self-driving car for the World Robot Olympiad *Future Engineers* Self-Driving Cars category. The vehicle drives autonomously around a walled track, avoids coloured pillars on the correct side, turns at each corner, completes three laps, and parks itself between two magenta markers.

This repository contains the source code, wiring notes, and design decisions made during development.

## Table of contents
- [Category rules that shaped the design](#category-rules-that-shaped-the-design)
- [Hardware](#hardware)
- [Wiring](#wiring)
- [Software environment](#software-environment)
- [Repository layout](#repository-layout)
- [Progress](#progress)
- [How to run each script](#how-to-run-each-script)
- [Tuning parameters](#tuning-parameters)
- [Known issues and next steps](#known-issues-and-next-steps)

---

## Category rules that shaped the design

Two rules dominated the mechanical design:

- **Rule 11.3** — the vehicle must be car-like: four wheels, one driving axle, one steering actuator. Differential wheeled bases (tank-style steering) are disqualified.
- **Rule 11.13** — a maximum of two driving motors is allowed, and if two are used they cannot be driven independently.

The design is therefore rear-wheel drive with a single steering servo at the front. Front wheels are free to roll and only serve for steering; the rear wheels are driven together.

Other rules that affected specific choices:

- **11.1** — the vehicle must fit within 300 x 200 x 300 mm.
- **11.2** — maximum weight 1.5 kg.
- **11.10** — no wireless communication during a run (WiFi/Bluetooth is disabled at run time).
- **Obstacle Challenge** — a red pillar must be passed on the right, a green pillar on the left. Magenta blocks mark the parking bay.

## Hardware

| Component | Details |
| --- | --- |
| SBC | Raspberry Pi 4B (4 GB RAM), 64-bit Bookworm |
| Camera | Raspberry Pi Camera v2 (IMX219) |
| Drive motor | TT gear motor, plastic gears (interim; a stronger N20 metal-gear motor is planned) |
| Motor driver | L298N dual H-bridge |
| Steering servo | MG90S (metal gears) |
| Distance sensors | 4 x HC-SR04 ultrasonic (front, left, right, back) |
| IMU | MPU6050 (accelerometer + gyroscope, I2C) |
| Battery | 12 V for the motor; separate USB power bank for the Pi |
| Voltage dividers | 1 k&Omega; + 2 k&Omega; on every ultrasonic Echo pin (required — see below) |

**Why an SG90 was replaced by an MG90S.** The SG90's plastic gears strip once the steering linkage encounters real resistance on the ground. The MG90S has the same footprint and pinout, uses ~500-2500 &micro;s pulse widths (the SG90 is 1000-2000 &micro;s), and its metal gears tolerate the load.

**Why voltage dividers are mandatory on Echo pins.** HC-SR04 modules output 5 V on the Echo pin, but the Pi's GPIO tolerates only 3.3 V. Driving the pin directly can silently damage the Pi. A 1 k&Omega; + 2 k&Omega; divider at every Echo pin brings the input to ~3.3 V.

## Wiring

### GPIO assignments

| Function | Physical pin | GPIO |
| --- | ---: | ---: |
| Servo signal | 12 | 18 |
| Motor ENA | 32 | 12 |
| Motor IN1 | 16 | 23 |
| Motor IN2 | 18 | 24 |
| Front sensor Trig | 37 | 26 |
| Front sensor Echo | 36 | 16 |
| Left sensor Trig | 29 | 5 |
| Left sensor Echo | 31 | 6 |
| Right sensor Trig | 33 | 13 |
| Right sensor Echo | 35 | 19 |
| Back sensor Trig | 15 | 22 |
| Back sensor Echo | 24 | 8 |
| MPU6050 SDA | 3 | 2 |
| MPU6050 SCL | 5 | 3 |

### Power distribution

- 12 V battery -> L298N +12V (drives the motor)
- L298N +5V -> servo red (steering servo power)
- Pi USB-C -> separate 5 V/3 A power bank
- Pi 5V (pin 2) -> ultrasonic sensor VCC rail
- Pi 3.3V (pin 1) -> MPU6050 VCC (**not** 5 V)

### Grounds — the single most important rule

All grounds must be tied together on one node: the 12 V battery negative, the L298N GND, the servo brown wire, the Pi GND, every ultrasonic sensor GND, the MPU6050 GND, and the lower end of every voltage divider. Without a common ground the servo will refuse to move and the sensors will return nonsense. This was the source of the biggest single debugging session during the build.

## Software environment

Bookworm 64-bit was chosen because tutorials and library support for it are much better than for Trixie.

Everything installed with apt where possible:

    sudo apt install -y python3-opencv python3-picamera2 pigpio python3-pigpio i2c-tools
    sudo systemctl enable pigpiod
    sudo systemctl start pigpiod

The MPU6050 library is installed with pip using `--break-system-packages` because Bookworm blocks system-wide pip installs otherwise:

    pip install mpu6050-raspberrypi --break-system-packages

I2C must be enabled in `raspi-config` for the IMU. X11 (not Wayland) must be selected under `raspi-config` -> Advanced Options for OpenCV windows and VNC to work reliably.

The pigpio daemon needs to be running before any script that uses the ultrasonic sensors, the servo, or the IMU:

    sudo systemctl start pigpiod

## Repository layout

    Autonomous-Car-/
    +-- README.md
    +-- schemes/            wiring diagrams
    +-- t-photos/           team photos
    +-- v-photos/           vehicle photos
    +-- src/
        +-- camera_test.py  live camera preview
        +-- motor_test.py   forward / reverse / stop
        +-- servo_test.py   MG90S centre and limits
        +-- hsv_tool.py     interactive HSV tuner (pillars, parking)
        +-- detect.py       red / green pillar detection
        +-- avoid.py        pillar avoidance (camera + servo)
        +-- ultra_test.py   all four ultrasonic sensors
        +-- imu_test.py     MPU6050 accel + gyro
        +-- imu_angle.py    gyro-integrated heading
        +-- lane.py         lane following + smart reverse
        +-- corner_test.py  90 deg IMU-based corner turn
        +-- combined.py     lane + corner + pillar in one loop

## Progress

**Working**

- Raspberry Pi and OpenCV set up.
- Camera streaming at 320x240 / 15 fps.
- Motor forward, reverse, and stop through the L298N.
- Steering servo (MG90S): straight at 10, full left at 90, full right at -23.
- HSV colour tuning done for red and green.
- Red / green pillar detection with the correct pass side reported.
- Pillar avoidance steering (camera + servo).
- All four ultrasonic sensors reading correctly.
- Lane following between two walls with proportional control.
- Smart reverse when the front sensor detects a wall (checks the back sensor too, and steers away from the closer side to un-stick from corners).
- MPU6050 mounted and reading. Yaw axis identified as Gz on this build.
- Gyro bias calibration (100-sample average at start-up).
- Heading tracking (Gz integrated with bias subtracted).
- 90 deg corner turn closed on IMU heading, direction locked to whichever side is more open the first time.
- Combined behaviour: pillar avoidance > corner turn > lane follow, all in one loop.

**In progress / next**

- Lap counting (4 turns = 1 lap; 12 turns = the parking phase).
- Magenta detection and parallel parking between the two markers.
- Chassis and wiring finalised (permanent mounting instead of breadboarded), and the drive motor upgraded to an N20 metal-gear motor for consistent starts and stops.

## How to run each script

Before running anything that talks to the servo, motors, ultrasonics, or IMU, start pigpio:

    sudo systemctl start pigpiod

Then, from `Autonomous-Car-/src`:

| Script | Purpose |
| --- | --- |
| `python3 camera_test.py` | Live camera preview. |
| `python3 motor_test.py` | Rear motor forward / reverse / stop. |
| `python3 servo_test.py` | Enter servo angles interactively. |
| `python3 hsv_tool.py` | Slider-based HSV tuner. Save values shown in the terminal. |
| `python3 detect.py` | Red / green pillar detection, live boxes. |
| `python3 avoid.py` | Pillar avoidance (motor line commented; uncomment for a floor test). |
| `python3 ultra_test.py` | All four distance sensors in a live table. |
| `python3 imu_test.py` | Raw accelerometer and gyroscope. |
| `python3 imu_angle.py` | Heading (yaw) integrated from Gz with bias subtracted. |
| `python3 lane.py` | Lane following with smart reverse. |
| `python3 corner_test.py` | Drive straight, then turn 90 deg on IMU when a wall is close. |
| `python3 combined.py` | The full Obstacle Challenge behaviour loop. |

## Tuning parameters

Most of the tuning lives at the top of `combined.py` and `corner_test.py`:

| Parameter | Meaning | Current value |
| --- | --- | --- |
| `SPEED` | Base forward PWM. | 0.30 - 0.32 |
| `TURN_SPEED` | Forward PWM during a corner turn. | 0.25 |
| `BOOST` / `BOOST_TIME` | Brief high-PWM kick to overcome the TT motor's static friction. | 1.0 for 0.3 s |
| `Kp_LANE` | Proportional gain for lane hold. | 2.5 |
| `Kp_PILLAR` | Steering offset applied when a pillar is in view. | 40 |
| `TARGET_SIDE` | Desired distance from a single wall (cm). | 25 |
| `WALL_MAX` | Beyond this reading (cm) a side is treated as "no wall". | 80 |
| `FRONT_LIMIT` | Turn threshold ahead (cm). | 45 |
| `BACK_LIMIT` | Stop reversing if back distance is below this (cm). | 15 |
| `MIN_AREA` | Minimum coloured blob area (pixels) before the pillar rule fires. | 800 |
| Turn threshold | `abs(angle - start_angle) >= 80` — stops slightly short of 90 deg to account for momentum. | 80 |

## Known issues and next steps

- The TT motor stalls occasionally from a standing start on the floor. The `BOOST` kick reduces this but does not eliminate it. Planned fix: replace with an N20 200 RPM metal-gear motor. Two rear motors run in parallel (same command to both) is the intended configuration, which stays within Rule 11.13.
- The steering travel is asymmetric (80 deg left vs 33 deg right) because of where the servo horn was clocked on the shaft. The code accounts for this, but re-clocking the horn would give symmetric travel and a tighter right turn.
- Gyro-only heading drifts slightly over long periods. A 90 deg corner takes ~2 s so the drift is below 1 deg in practice, but for lap counting the same bias will be re-checked periodically.

## Team

To be filled in by the team.

## Licence

Educational / competition use.
