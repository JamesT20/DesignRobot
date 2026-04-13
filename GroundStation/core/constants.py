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
    # Power — INA219 @ 0x44 (mot1) and 0x45 (mot2)
    PWR_MOT1_VOLT        = "PWR_MOT1_VOLT"
    PWR_MOT1_CUR         = "PWR_MOT1_CUR"
    PWR_MOT2_VOLT        = "PWR_MOT2_VOLT"
    PWR_MOT2_CUR         = "PWR_MOT2_CUR"

    # Inertial Measurement Unit (MPU6050)
    IMU_ACCEL_X          = "IMU_ACCEL_X"
    IMU_ACCEL_Y          = "IMU_ACCEL_Y"
    IMU_ACCEL_Z          = "IMU_ACCEL_Z"
    IMU_GYRO_X           = "IMU_GYRO_X"
    IMU_GYRO_Y           = "IMU_GYRO_Y"
    IMU_GYRO_Z           = "IMU_GYRO_Z"
    IMU_HEADING          = "IMU_HEADING"
    IMU_ROLL             = "IMU_ROLL"
    IMU_PITCH            = "IMU_PITCH"

    # Temperature probe (payload — reserved)
    TMP_PROBE            = "TMP_PROBE"

    # System
    SYS_UPTIME           = "SYS_UPTIME"
    SYS_HEAP_FREE        = "SYS_HEAP_FREE"
    SYS_LOOP_TIME        = "SYS_LOOP_TIME_MS"
    SYS_PACKET_NUM       = "SYS_PACKET_NUM"
    SYS_MODE             = "SYS_MODE"
    SYS_STATUS           = "SYS_STATUS"
    SYS_TEMP_C           = "SYS_TEMP_C"
    SYS_CAM_OK           = "SYS_CAM_OK"
    SYS_WIFI_RSSI        = "SYS_WIFI_RSSI"

    # Command sequence
    SEQ_RUNNING          = "SEQ_RUNNING"
    SEQ_CURRENT          = "SEQ_CURRENT"
    SEQ_TOTAL            = "SEQ_TOTAL"
    SEQ_QUEUE_DEPTH      = "SEQ_QUEUE_DEPTH"
    SEQ_QUEUE_REMAINING  = "SEQ_QUEUE_REMAINING"

    # Motors (L298N, direction only — no PWM)
    MOT_1_DIR_CMD        = "MOT_1_DIR_CMD"   # last commanded: -1/0/1
    MOT_1_DIR            = "MOT_1_DIR"       # actual hardware state
    MOT_2_DIR_CMD        = "MOT_2_DIR_CMD"
    MOT_2_DIR            = "MOT_2_DIR"
    MOT_BUSY             = "MOT_BUSY"

    # Faults
    FLT_IMU_TILT         = "FLT_IMU_TILT"
    FLT_MOT_STALL_1      = "FLT_MOT_STALL_1"
    FLT_MOT_STALL_2      = "FLT_MOT_STALL_2"
    FLT_QUEUE_OVERFLOW   = "FLT_QUEUE_OVERFLOW"

### Command Names ###
class CMD:
    MOT_SET_DIR          = "CMD_MOT_SET_DIR"      # args: left_dir, right_dir (-1/0/1)
    MOT_STOP             = "CMD_MOT_STOP"          # immediate stop (both motors)
    SYS_WAIT             = "CMD_SYS_WAIT"          # args: ms
    SYS_REBOOT           = "CMD_SYS_REBOOT"
    SYS_CLEAR_FAULTS     = "CMD_SYS_CLEAR_FAULTS"