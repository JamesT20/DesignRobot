////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//
// Vehicle software for PROJECT DUI robot
//
// Created March 2026 by James Torok
//
////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

///////////////////////////////////////////////////////// INIT ///////////////////////////////////////////////////////////////////

///// Import required Libraries /////
#include <WiFi.h>
#include <ArduinoJson.h>
#include "esp_camera.h"
#include <ESPAsyncWebServer.h>
#include <Wire.h>
#include <MPU6050.h>
#include <Adafruit_INA219.h>

///// Set important constants /////

// ── Camera Pin Definitions ──────────────────────────────────────────────────
#define PWDN_GPIO_NUM   -1
#define RESET_GPIO_NUM  -1
#define XCLK_GPIO_NUM   15
#define SIOD_GPIO_NUM    4
#define SIOC_GPIO_NUM    5
#define Y2_GPIO_NUM     11
#define Y3_GPIO_NUM      9
#define Y4_GPIO_NUM      8
#define Y5_GPIO_NUM     10
#define Y6_GPIO_NUM     12
#define Y7_GPIO_NUM     18
#define Y8_GPIO_NUM     17
#define Y9_GPIO_NUM     16
#define VSYNC_GPIO_NUM   6
#define HREF_GPIO_NUM    7
#define PCLK_GPIO_NUM   13

// ── I2C pins for MPU6050 ─────────────────────────────────────────────────
#define IMU_SDA_PIN     20
#define IMU_SCL_PIN     19

// ── L298N Motor Driver Pins ─────────────────────────────────────────────────

// Motor A (Left)
#define MOT_A_IN1  1    // Direction control A
#define MOT_A_IN2  2    // Direction control B

// Motor B (Right)
#define MOT_B_IN3  3    // Direction control A
#define MOT_B_IN4  14   // Direction control B

// Camera Config
#define MJPEG_BOUNDARY     "frame"
#define MJPEG_CONTENT_TYPE "multipart/x-mixed-replace;boundary=" MJPEG_BOUNDARY

// Access Point credentials
const char* ssid     = "PROJECT_DUI_ESP32";
const char* password = "12345678";

// Single async server on port 80
AsyncWebServer server(80);

// ── INA219 Current Sensors ───────────────────────────────────────────────────
Adafruit_INA219 ina219_mot1(0x44);   // A1 soldered — battery monitor
Adafruit_INA219 ina219_mot2(0x45);   // A1+A0 soldered — motor monitor

struct PowerData {
  float batVolt, batCur;
  float motVolt, motCur;
} pwr = {};

// ── MPU6050 ──────────────────────────────────────────────────────────────────
MPU6050 mpu;

struct ImuData {
  float accelX, accelY, accelZ;
  float gyroX,  gyroY,  gyroZ;
  float roll, pitch, heading;
} imu = {};

static constexpr float ALPHA = 0.96f;

// ── Motor State ───────────────────────────────────────────────────────────────
struct MotorState {
  int8_t dirCmd;   // -1 reverse, 0 stop, 1 forward (last commanded value)
  int8_t dir;      // -1 reverse, 0 stop, 1 forward  (actual hardware state)
} motA = {}, motB = {};

// ── Fault Flags ───────────────────────────────────────────────────────────────
struct Faults {
  bool imuTilt    = false;
  bool motStall1  = false;
  bool motStall2  = false;
} faults;

// ── Command Queue ─────────────────────────────────────────────────────────────

// All supported command types
enum CmdType {
  CMD_NONE = 0,
  CMD_MOT_SET_DIR,      // Set left & right motor direction (-1, 0, or 1)
  CMD_MOT_STOP,         // Immediately stop both motors
  CMD_SYS_WAIT,         // Wait N milliseconds
  CMD_SYS_REBOOT,       // Reboot ESP32
  CMD_SYS_CLEAR_FAULTS, // Clear all fault flags
};

struct Command {
  CmdType  type     = CMD_NONE;
  int32_t  argA     = 0;   // left_dir / ms / generic
  int32_t  argB     = 0;   // right_dir
  uint32_t seqIndex = 0;   // position in the uploaded sequence
};

// Circular queue
static constexpr uint8_t CMD_QUEUE_SIZE = 32;
Command cmdQueue[CMD_QUEUE_SIZE];
volatile uint8_t cmdHead = 0;   // next slot to write
volatile uint8_t cmdTail = 0;   // next slot to read
volatile bool    cmdBusy = false;

// Sequence tracking
volatile uint32_t seqTotal     = 0;   // total commands in the last upload
volatile uint32_t seqCurrent   = 0;   // index of command currently executing
volatile bool     seqRunning   = false;

// Status string (last action, error, etc.)
String lastStatus = "idle";

unsigned long lastLoopTime = 0;
unsigned long lastImuTime  = 0;
uint32_t      pktSeq       = 0;

///////////////////////////////////////////////////////// END INIT ///////////////////////////////////////////////////////////////

// Forward declarations
void applyOV3660Corrections();
String buildTelemetryJson();
void updateIMU();
void updatePower();
void setMotorA(int dirCmd);
void setMotorB(int dirCmd);
void stopAllMotors();
bool enqueueCmd(const Command& cmd);
Command dequeueCmd();
bool queueEmpty();
void processCommandQueue();
CmdType parseCmdType(const char* str);

///////////////////////////////////////////////////////// SETUP //////////////////////////////////////////////////////////////////

void setup() {
  Serial.begin(115200);

  // ── Motor GPIO init ──────────────────────────────────────────────────────
  pinMode(MOT_A_IN1, OUTPUT);
  pinMode(MOT_A_IN2, OUTPUT);
  pinMode(MOT_B_IN3, OUTPUT);
  pinMode(MOT_B_IN4, OUTPUT);

  stopAllMotors();

  // ── MPU6050 init ─────────────────────────────────────────────────────────
  Wire.begin(IMU_SDA_PIN, IMU_SCL_PIN);
  mpu.initialize();
  mpu.setXAccelOffset(0);
  mpu.setYAccelOffset(0);
  mpu.setZAccelOffset(0);
  mpu.setXGyroOffset(0);
  mpu.setYGyroOffset(0);
  mpu.setZGyroOffset(0);
  lastImuTime = millis();

  // ── INA219 init ───────────────────────────────────────────────────────────
  if (!ina219_mot1.begin()) Serial.println("INA219 (0x44) not found");
  if (!ina219_mot2.begin()) Serial.println("INA219 (0x45) not found");

  // ── WiFi Access Point ─────────────────────────────────────────────────────
  WiFi.softAP(ssid, password);
  Serial.print("AP Started — IP: ");
  Serial.println(WiFi.softAPIP());

  // ── /tlm — Telemetry ──────────────────────────────────────────────────────
  server.on("/tlm", HTTP_GET, [](AsyncWebServerRequest* request) {
    request->send(200, "application/json", buildTelemetryJson());
  });

  // ── /cmd — Receive command sequence (JSON array) ──────────────────────────
  server.on(
    "/cmd", HTTP_POST,
    [](AsyncWebServerRequest* request) {
      if (!request->_tempObject) {
        request->send(400, "application/json",
                      "{\"error\":\"empty body\"}");
      }
    },
    nullptr,
    [](AsyncWebServerRequest* request,
       uint8_t*               data,
       size_t                 len,
       size_t                 index,
       size_t                 total) {

      if (index == 0) {
        request->_tempObject = new String();
      }
      String* body = reinterpret_cast<String*>(request->_tempObject);
      body->concat(reinterpret_cast<char*>(data), len);

      if (index + len >= total) {
        DynamicJsonDocument doc(4096);
        DeserializationError err = deserializeJson(doc, *body);
        delete body;
        request->_tempObject = nullptr;

        if (err || !doc.is<JsonArray>()) {
          request->send(400, "application/json",
                        "{\"error\":\"invalid JSON array\"}");
          return;
        }

        JsonArray arr = doc.as<JsonArray>();

        cmdHead = cmdTail = 0;
        seqCurrent = 0;
        seqTotal   = arr.size();
        seqRunning = seqTotal > 0;

        uint32_t accepted = 0;
        for (JsonObject obj : arr) {
          if (accepted >= CMD_QUEUE_SIZE) break;
          const char* cmdStr = obj["cmd"] | "";
          CmdType type = parseCmdType(cmdStr);
          if (type == CMD_NONE) continue;

          Command c;
          c.type     = type;
          c.seqIndex = accepted;

          switch (type) {
            case CMD_MOT_SET_DIR:
              c.argA = constrain((int32_t)obj["left_dir"]  | 0, -1, 1);
              c.argB = constrain((int32_t)obj["right_dir"] | 0, -1, 1);
              break;
            case CMD_SYS_WAIT:
              if (obj.containsKey("ms")) {
                c.argA = (int32_t)obj["ms"];
              } else {
                c.argA = (int32_t)(((float)obj["seconds"] | 0.0f) * 1000.0f);
              }
              c.argA = max(c.argA, 0);
              break;
            default:
              break;
          }

          if (enqueueCmd(c)) accepted++;
        }

        lastStatus = "sequence loaded: " + String(accepted) + " cmd(s)";

        String resp = "{\"accepted\":" + String(accepted) +
                      ",\"total\":"    + String(seqTotal) + "}";
        request->send(200, "application/json", resp);
      }
    }
  );

  // ── /cmd/stop — Emergency stop ─────────────────────────────────────────────
  server.on("/cmd/stop", HTTP_POST, [](AsyncWebServerRequest* request) {
    cmdHead = cmdTail = 0;
    seqRunning  = false;
    seqCurrent  = 0;
    cmdBusy     = false;
    stopAllMotors();
    faults.motStall1 = false;
    faults.motStall2 = false;
    lastStatus = "ESTOP";
    request->send(200, "application/json", "{\"status\":\"stopped\"}");
  });

  // ── MJPEG stream ──────────────────────────────────────────────────────────
  server.on("/stream", HTTP_GET, [](AsyncWebServerRequest* request) {
    AsyncResponseStream* response =
        request->beginResponseStream(MJPEG_CONTENT_TYPE);
    response->addHeader("Cache-Control", "no-cache");
    response->addHeader("Connection",    "keep-alive");

    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
      request->send(503, "text/plain", "Camera frame unavailable");
      return;
    }
    response->printf(
        "--" MJPEG_BOUNDARY "\r\n"
        "Content-Type: image/jpeg\r\n"
        "Content-Length: %u\r\n\r\n",
        fb->len);
    response->write(fb->buf, fb->len);
    response->print("\r\n");
    esp_camera_fb_return(fb);
    request->send(response);
  });

  // ── 404 fallback ──────────────────────────────────────────────────────────
  server.onNotFound([](AsyncWebServerRequest* request) {
    request->send(404, "text/plain", "Not found");
  });

  server.begin();

  // ── Camera init ───────────────────────────────────────────────────────────
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size   = FRAMESIZE_QVGA;
  config.jpeg_quality = 12;
  config.fb_count     = 2;
  config.grab_mode    = CAMERA_GRAB_LATEST;

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("Camera init failed");
  }
  applyOV3660Corrections();
}

///////////////////////////////////////////////////////// LOOP ///////////////////////////////////////////////////////////////////

void loop() {
  lastLoopTime = millis();
  updateIMU();
  updatePower();
  processCommandQueue();
  delay(10);
}

///////////////////////////////////////////////////////// MOTOR CONTROL //////////////////////////////////////////////////////////

// Set Motor A direction. dirCmd: 1 = forward, -1 = reverse, 0 = stop/brake.
void setMotorA(int dirCmd) {
  dirCmd = constrain(dirCmd, -1, 1);
  motA.dirCmd = dirCmd;
  motA.dir    = dirCmd;

  if (dirCmd > 0) {
    digitalWrite(MOT_A_IN1, HIGH);
    digitalWrite(MOT_A_IN2, LOW);
  } else if (dirCmd < 0) {
    digitalWrite(MOT_A_IN1, LOW);
    digitalWrite(MOT_A_IN2, HIGH);
  } else {
    // Brake: both HIGH (L298N short-brake)
    digitalWrite(MOT_A_IN1, HIGH);
    digitalWrite(MOT_A_IN2, HIGH);
  }
}

// Set Motor B direction. Same convention as setMotorA.
void setMotorB(int dirCmd) {
  dirCmd = constrain(dirCmd, -1, 1);
  motB.dirCmd = dirCmd;
  motB.dir    = dirCmd;

  if (dirCmd > 0) {
    digitalWrite(MOT_B_IN3, HIGH);
    digitalWrite(MOT_B_IN4, LOW);
  } else if (dirCmd < 0) {
    digitalWrite(MOT_B_IN3, LOW);
    digitalWrite(MOT_B_IN4, HIGH);
  } else {
    digitalWrite(MOT_B_IN3, HIGH);
    digitalWrite(MOT_B_IN4, HIGH);
  }
}

void stopAllMotors() {
  setMotorA(0);
  setMotorB(0);
}

///////////////////////////////////////////////////////// COMMAND QUEUE //////////////////////////////////////////////////////////

bool enqueueCmd(const Command& cmd) {
  uint8_t next = (cmdHead + 1) % CMD_QUEUE_SIZE;
  if (next == cmdTail) return false;
  cmdQueue[cmdHead] = cmd;
  cmdHead = next;
  return true;
}

Command dequeueCmd() {
  Command c;
  if (cmdHead == cmdTail) return c;
  c = cmdQueue[cmdTail];
  cmdTail = (cmdTail + 1) % CMD_QUEUE_SIZE;
  return c;
}

bool queueEmpty() {
  return cmdHead == cmdTail;
}

CmdType parseCmdType(const char* str) {
  if (strcmp(str, "CMD_MOT_SET_DIR")      == 0) return CMD_MOT_SET_DIR;
  if (strcmp(str, "CMD_MOT_STOP")         == 0) return CMD_MOT_STOP;
  if (strcmp(str, "CMD_SYS_WAIT")         == 0) return CMD_SYS_WAIT;
  if (strcmp(str, "CMD_SYS_REBOOT")       == 0) return CMD_SYS_REBOOT;
  if (strcmp(str, "CMD_SYS_CLEAR_FAULTS") == 0 ||
      strcmp(str, "SYS_CLEAR_FAULTS")     == 0) return CMD_SYS_CLEAR_FAULTS;
  return CMD_NONE;
}

void processCommandQueue() {
  if (cmdBusy) return;
  if (queueEmpty()) {
    if (seqRunning) {
      seqRunning = false;
      lastStatus = "sequence complete";
      Serial.println("[CMD] Sequence complete");
    }
    return;
  }

  Command c = dequeueCmd();
  seqCurrent = c.seqIndex;
  Serial.printf("[CMD] Executing #%u type=%d\n", c.seqIndex, (int)c.type);

  switch (c.type) {

    case CMD_MOT_SET_DIR:
      setMotorA((int)c.argA);
      setMotorB((int)c.argB);
      lastStatus = "MOT_SET_DIR L=" + String(c.argA) + " R=" + String(c.argB);
      break;

    case CMD_MOT_STOP:
      stopAllMotors();
      lastStatus = "MOT_STOP";
      break;

    case CMD_SYS_WAIT: {
      static unsigned long waitUntil = 0;
      waitUntil = millis() + (unsigned long)c.argA;
      cmdBusy   = true;
      lastStatus = "WAIT " + String(c.argA) + "ms";

      while (millis() < waitUntil) {
        delay(1);
      }
      cmdBusy = false;
      break;
    }

    case CMD_SYS_REBOOT:
      stopAllMotors();
      lastStatus = "REBOOTING";
      Serial.println("[CMD] REBOOT");
      delay(500);
      ESP.restart();
      break;

    case CMD_SYS_CLEAR_FAULTS:
      faults.imuTilt   = false;
      faults.motStall1 = false;
      faults.motStall2 = false;
      lastStatus = "FAULTS CLEARED";
      break;

}

///////////////////////////////////////////////////////// HELPERS ////////////////////////////////////////////////////////////////

void updatePower() {
  pwr.mot1Volt = ina219_mot1.getBusVoltage_V();
  pwr.mot1Cur  = ina219_mot1.getCurrent_mA();
  pwr.mot2Volt = ina219_mot2.getBusVoltage_V();
  pwr.mot2Cur  = ina219_mot2.getCurrent_mA();
}

void updateIMU() {
  int16_t ax, ay, az, gx, gy, gz;
  mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);

  constexpr float ACCEL_SCALE = 9.80665f / 16384.0f;
  constexpr float GYRO_SCALE  = 1.0f    / 131.0f;

  imu.accelX = ax * ACCEL_SCALE;
  imu.accelY = ay * ACCEL_SCALE;
  imu.accelZ = az * ACCEL_SCALE;
  imu.gyroX  = gx * GYRO_SCALE;
  imu.gyroY  = gy * GYRO_SCALE;
  imu.gyroZ  = gz * GYRO_SCALE;

  unsigned long now = millis();
  float dt = (now - lastImuTime) / 1000.0f;
  lastImuTime = now;

  float accelRoll  = atan2f(imu.accelY, imu.accelZ) * 180.0f / M_PI;
  float accelPitch = atan2f(-imu.accelX,
                             sqrtf(imu.accelY * imu.accelY +
                                   imu.accelZ * imu.accelZ)) * 180.0f / M_PI;

  imu.roll    = ALPHA * (imu.roll  + imu.gyroX * dt) + (1.0f - ALPHA) * accelRoll;
  imu.pitch   = ALPHA * (imu.pitch + imu.gyroY * dt) + (1.0f - ALPHA) * accelPitch;
  imu.heading += imu.gyroZ * dt;
  if (imu.heading <    0.0f) imu.heading += 360.0f;
  if (imu.heading >= 360.0f) imu.heading -= 360.0f;
}

String buildTelemetryJson() {
  StaticJsonDocument<2048> doc;

  doc["type"] = "tlm";

  // System
  doc["SYS_UPTIME"]     = millis() / 1000;
  doc["SYS_HEAP_FREE"]  = ESP.getFreeHeap();
  doc["SYS_LOOP_TIME"]  = millis() - lastLoopTime;
  doc["SYS_PACKET_NUM"] = pktSeq++;
  doc["SYS_MODE"]       = seqRunning ? "RUN" : "IDLE";
  doc["SYS_STATUS"]     = lastStatus;

  // Sequence
  doc["SEQ_RUNNING"]  = seqRunning;
  doc["SEQ_CURRENT"]  = seqCurrent;
  doc["SEQ_TOTAL"]    = seqTotal;
  doc["SEQ_QUEUE"]    = (cmdHead - cmdTail + CMD_QUEUE_SIZE) % CMD_QUEUE_SIZE;

  // Power
  doc["PWR_MOT1_VOLT"] = serialized(String(pwr.mot1Volt, 2));
  doc["PWR_MOT1_CUR"]  = serialized(String(pwr.mot1Cur,  1));
  doc["PWR_MOT2_VOLT"] = serialized(String(pwr.mot2Volt, 2));
  doc["PWR_MOT2_CUR"]  = serialized(String(pwr.mot2Cur,  1));

  // IMU
  doc["IMU_ACCEL_X"] = serialized(String(imu.accelX, 3));
  doc["IMU_ACCEL_Y"] = serialized(String(imu.accelY, 3));
  doc["IMU_ACCEL_Z"] = serialized(String(imu.accelZ, 3));
  doc["IMU_GYRO_X"]  = serialized(String(imu.gyroX,  3));
  doc["IMU_GYRO_Y"]  = serialized(String(imu.gyroY,  3));
  doc["IMU_GYRO_Z"]  = serialized(String(imu.gyroZ,  3));
  doc["IMU_HEADING"] = serialized(String(imu.heading, 1));
  doc["IMU_ROLL"]    = serialized(String(imu.roll,    1));
  doc["IMU_PITCH"]   = serialized(String(imu.pitch,   1));

  // Motors
  doc["MOT_1_DIR_CMD"] = motA.dirCmd;
  doc["MOT_1_DIR"]     = motA.dir;
  doc["MOT_2_DIR_CMD"] = motB.dirCmd;
  doc["MOT_2_DIR"]     = motB.dir;

  // Faults
  doc["FLT_IMU_TILT"]    = faults.imuTilt;
  doc["FLT_MOT_STALL_1"] = faults.motStall1;
  doc["FLT_MOT_STALL_2"] = faults.motStall2;

  String out;
  serializeJson(doc, out);
  return out;
}

void applyOV3660Corrections() {
  sensor_t* s = esp_camera_sensor_get();
  if (!s) return;
  s->set_vflip(s, 1);
  s->set_hmirror(s, 0);
}