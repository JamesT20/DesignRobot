from enum import Enum

### Connection States ###
class ConnState(Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING   = "CONNECTING"
    CONNECTED    = "CONNECTED"
    RECONNECTING = "RECONNECTING"
    ERROR        = "ERROR"

### Telemetry Mnemonics ###
class TLM:
    # Power
    PWR_BAT_VOLT    = "PWR_BAT_VOLT"
    PWR_BAT_CUR     = "PWR_BAT_CUR"
    PWR_MOT1_VOLT   = "PWR_MOT1_VOLT"
    PWR_MOT1_CUR    = "PWR_MOT1_CUR"
    PWR_MOT2_VOLT   = "PWR_MOT2_VOLT"
    PWR_MOT2_CUR    = "PWR_MOT2_CUR"

    # Inertial measurement unit
    IMU_ACCEL_X     = "IMU_ACCEL_X"
    IMU_ACCEL_Y     = "IMU_ACCEL_Y"
    IMU_ACCEL_Z     = "IMU_ACCEL_Z"
    IMU_GYRO_X      = "IMU_GYRO_X"
    IMU_GYRO_Y      = "IMU_GYRO_Y"
    IMU_GYRO_Z      = "IMU_GYRO_Z"
    IMU_MAG_X       = "IMU_MAG_X"
    IMU_MAG_Y       = "IMU_MAG_Y"
    IMU_MAG_Z       = "IMU_MAG_Z"
    IMU_HEADING     = "IMU_HEADING"

    # Temperature probe
    TMP_PROBE       = "TMP_PROBE"

    # System
    SYS_UPTIME      = "SYS_UPTIME"
    SYS_HEAP_FREE   = "SYS_HEAP_FREE"
    SYS_LOOP_TIME   = "SYS_LOOP_TIME"
    SYS_PACKET_NUM  = "SYS_PACKET_NUM"
    SYS_MODE        = "SYS_MODE"

    # Camera
    IMG_ENDPOINT    = "IMG_ENDPOINT"

    # Motor control
    MOT_1_SPEED     = "MOT_1_SPEED"
    MOT_1_DIR       = "MOT_1_DIR"
    MOT_1_PWM       = "MOT_1_PWM"
    MOT_2_SPEED     = "MOT_2_SPEED"
    MOT_2_DIR       = "MOT_2_DIR"
    MOT_2_PWM       = "MOT_2_PWM"

    # Faults
    FLT_IMU_TILT    = "FLT_IMU_TILT"
    FLT_MOT_STALL_L = "FLT_MOT_STALL_L"
    FLT_MOT_STALL_R = "FLT_MOT_STALL_R"

### Command Names ###
class CMD:
    MOT_SET_SPEED        = "CMD_MOT_SET_SPEED"
    MOT_ESTOP            = "CMD_MOT_ESTOP"
    SYS_REBOOT           = "CMD_SYS_REBOOT"
    CAM_STREAM_START     = "CMD_CAM_STREAM_START"
    CAM_STREAM_STOP      = "CMD_CAM_STREAM_STOP"