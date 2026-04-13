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

// ── IMU Tilt Fault Threshold (degrees) ───────────────────────────────────────
#define IMU_TILT_THRESHOLD_DEG  45.0f

// Camera Config
#define MJPEG_BOUNDARY     "frame"
#define MJPEG_CONTENT_TYPE "multipart/x-mixed-replace;boundary=" MJPEG_BOUNDARY

// Access Point credentials
const char* ssid     = "PROJECT_DUI_ESP32";
const char* password = "12345678";

// Single async server on port 80
AsyncWebServer server(80);

// ── INA219 Current Sensors ───────────────────────────────────────────────────
Adafruit_INA219 ina219_mot1(0x44);   // A1 soldered — motor monitor
Adafruit_INA219 ina219_mot2(0x45);   // A1+A0 soldered — motor monitor

struct PowerData {
  float mot1Volt, mot1Cur;   // INA219 @ 0x44
  float mot2Volt, mot2Cur;   // INA219 @ 0x45
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
  bool imuTilt      = false;
  bool motStall1    = false;
  bool motStall2    = false;
  bool queueOverflow = false;
} faults;

// ── Camera Status ─────────────────────────────────────────────────────────────
bool camOk = false;

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

// ── FIX: Non-blocking wait state (moved to file scope) ───────────────────────
// Previously declared as 'static' inside the switch case, which caused the
// ESTOP handler's cmdBusy=false to be ignored because the blocking while()
// loop in loop() prevented the web server callbacks from ever resolving.
static unsigned long waitUntil = 0;

// Sequence tracking
volatile uint32_t seqTotal     = 0;   // total commands in the last upload
volatile uint32_t seqCurrent   = 0;   // index of command currently executing
volatile bool     seqRunning   = false;

// Status string (last action, error, etc.)
String lastStatus = "idle";

unsigned long loopStart    = 0;   // captured at the very top of loop()
unsigned long lastLoopUs   = 0;   // full cycle duration in ms (previous iteration)

unsigned long lastImuTime  = 0;
uint32_t      pktSeq       = 0;

// ── Log Level Enum ──────────────────────────────────────────────────────
enum LogLevel {
  LOG_DEBUG = 0,
  LOG_INFO,
  LOG_WARN,
  LOG_ERROR,
};

// ── Log Entry ───────────────────────────────────────────────────────────
struct LogEntry {
  uint32_t  timestamp;          // millis() at time of log
  LogLevel  level;
  char      source[16];         // subsystem name, null-terminated
  char      message[96];        // human-readable message, null-terminated
  char      contextJson[64];    // optional extra key/value pairs as JSON object, or ""
};

// ── Log Ring Buffer ─────────────────────────────────────────────────────
static constexpr uint8_t LOG_BUF_SIZE = 64;
LogEntry logBuf[LOG_BUF_SIZE];
volatile uint8_t logHead = 0;   // next slot to write
volatile uint8_t logTail = 0;   // next slot to read (GUI drain cursor)

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

void sendLog(LogLevel level, const char* source, const char* message, const char* contextJson = "");
String buildLogJson();

///////////////////////////////////////////////////////// LOGGING ////////////////////////////////////////////////////////////////

// ── [LOG] sendLog ─────────────────────────────────────────────────────────────
// Write one structured log entry into the ring buffer.  If the buffer is full
// the oldest unread entry is silently overwritten (newest-wins policy keeps the
// most recent diagnostics alive even under heavy logging).
//
// Parameters:
//   level       — LOG_DEBUG / LOG_INFO / LOG_WARN / LOG_ERROR
//   source      — subsystem name shown in the GUI LogPanel prefix
//   message     — human-readable description of the event
//   contextJson — optional JSON object string with extra metadata, e.g.
//                 "{\"motor_id\":1,\"dir\":1}"  Leave "" if not needed.
void sendLog(LogLevel level,
             const char* source,
             const char* message,
             const char* contextJson) {

  uint8_t slot = logHead;
  logHead = (logHead + 1) % LOG_BUF_SIZE;

  // If we've lapped the tail the oldest entry is silently dropped.
  // (The GUI will see a gap but never a crash.)
  if (logHead == logTail) {
    logTail = (logTail + 1) % LOG_BUF_SIZE;
  }

  LogEntry& e = logBuf[slot];
  e.timestamp = millis();
  e.level     = level;
  strncpy(e.source,      source,      sizeof(e.source)      - 1);  e.source[sizeof(e.source)-1]      = '\0';
  strncpy(e.message,     message,     sizeof(e.message)     - 1);  e.message[sizeof(e.message)-1]     = '\0';
  strncpy(e.contextJson, contextJson, sizeof(e.contextJson) - 1);  e.contextJson[sizeof(e.contextJson)-1] = '\0';

  // Also mirror to Serial for development convenience
  const char* lvlStr[] = { "DEBUG", "INFO", "WARN", "ERROR" };
  Serial.printf("[%s][%s] %s\n", lvlStr[level], source, message);
}

// Build a JSON array string of all pending log entries in the buffer and advance
String buildLogJson() {
  const char* lvlStr[] = { "DEBUG", "INFO", "WARN", "ERROR" };

  String out = "[";
  bool first = true;

  while (logTail != logHead) {
    LogEntry& e = logBuf[logTail];
    logTail = (logTail + 1) % LOG_BUF_SIZE;

    if (!first) out += ",";
    first = false;

    // Build the entry manually to avoid a second StaticJsonDocument on the heap
    out += "{\"type\":\"log\"";
    out += ",\"timestamp\":";  out += e.timestamp;
    out += ",\"level\":\"";    out += lvlStr[e.level]; out += "\"";
    out += ",\"source\":\"";   out += e.source;        out += "\"";
    out += ",\"message\":\"";  out += e.message;       out += "\"";

    if (e.contextJson[0] != '\0') {
      out += ",\"context\":";
      out += e.contextJson;   // already a valid JSON object string
    }

    out += "}";
  }

  out += "]";
  return out;
}

///////////////////////////////////////////////////////// SETUP //////////////////////////////////////////////////////////////////

void setup() {
  Serial.begin(115200);

// Log Boot started
  sendLog(LOG_INFO, "system", "Firmware boot started",
          "{\"version\":\"1.0\",\"build\":\"" __DATE__ " " __TIME__ "\"}");

  // ── Motor GPIO init ──────────────────────────────────────────────────────
  pinMode(MOT_A_IN1, OUTPUT);
  pinMode(MOT_A_IN2, OUTPUT);
  pinMode(MOT_B_IN3, OUTPUT);
  pinMode(MOT_B_IN4, OUTPUT);

  stopAllMotors();
  // Motor GPIO ready
  sendLog(LOG_INFO, "motors", "Motor GPIO initialised and stopped",
          "{\"pins_a\":[1,2],\"pins_b\":[3,14]}");

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
  // IMU ready
  sendLog(LOG_INFO, "imu", "MPU6050 initialised with zero offsets",
          "{\"sda\":20,\"scl\":19,\"tilt_threshold_deg\":45}");

  // ── INA219 init ───────────────────────────────────────────────────────────
  if (!ina219_mot1.begin()) {
    Serial.println("INA219 (0x44) not found");
    // Power sensor fault
    sendLog(LOG_ERROR, "power", "INA219 @ 0x44 not found — battery monitor offline",
            "{\"addr\":\"0x44\"}");
  } else {
    // Power sensor OK
    sendLog(LOG_INFO, "power", "INA219 @ 0x44 (battery monitor) online",
            "{\"addr\":\"0x44\"}");
  }

  if (!ina219_mot2.begin()) {
    Serial.println("INA219 (0x45) not found");
    // Power sensor fault
    sendLog(LOG_ERROR, "power", "INA219 @ 0x45 not found — motor monitor offline",
            "{\"addr\":\"0x45\"}");
  } else {
    // Power sensor OK
    sendLog(LOG_INFO, "power", "INA219 @ 0x45 (motor monitor) online",
            "{\"addr\":\"0x45\"}");
  }

  // ── WiFi Access Point ─────────────────────────────────────────────────────
  WiFi.softAP(ssid, password);
  Serial.print("AP Started — IP: ");
  Serial.println(WiFi.softAPIP());
  // WiFi AP up
  {
    char ctx[64];
    snprintf(ctx, sizeof(ctx), "{\"ssid\":\"%s\",\"ip\":\"%s\"}", ssid,
             WiFi.softAPIP().toString().c_str());
    sendLog(LOG_INFO, "wifi", "Access point started", ctx);
  }

  // ── /tlm — Telemetry ──────────────────────────────────────────────────────
  server.on("/tlm", HTTP_GET, [](AsyncWebServerRequest* request) {
    request->send(200, "application/json", buildTelemetryJson());
  });

  // ── /log — Log drain endpoint ─────────────────────────────────────────────
  // [LOG] Register the /log endpoint that the GUI polls to drain log entries.
  // Returns a JSON array of all pending log entries and clears them from the
  // ring buffer.  If there are no pending entries the response is "[]".
  server.on("/log", HTTP_GET, [](AsyncWebServerRequest* request) {
    request->send(200, "application/json", buildLogJson());
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
          // [LOG] Bad command payload
          sendLog(LOG_WARN, "commands", "Received invalid /cmd payload — JSON parse failed",
                  "{\"error\":\"invalid JSON array\"}");
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
                c.argA = (int32_t)(obj["seconds"].as<float>() * 1000.0f);
              }
              c.argA = max(c.argA, (int32_t)0);
              break;
            default:
              break;
          }

          if (enqueueCmd(c)) accepted++;
        }

        // [LOG] Sequence loaded
        {
          char ctx[64];
          snprintf(ctx, sizeof(ctx), "{\"accepted\":%u,\"total\":%u}", accepted, (uint32_t)seqTotal);
          sendLog(LOG_INFO, "commands", "Command sequence loaded", ctx);
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
    // ── FIX: Also clear waitUntil so the non-blocking wait check in
    // processCommandQueue() resolves immediately on the next loop() tick.
    waitUntil = 0;

    cmdHead = cmdTail = 0;
    seqRunning  = false;
    seqCurrent  = 0;
    cmdBusy     = false;
    stopAllMotors();
    faults.motStall1    = false;
    faults.motStall2    = false;
    faults.queueOverflow = false;
    lastStatus = "ESTOP";
    // [LOG] Emergency stop
    sendLog(LOG_WARN, "commands", "Emergency stop received — queue cleared, motors stopped", "");
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
      // [LOG] Frame grab failure
      sendLog(LOG_ERROR, "camera", "Frame grab failed on /stream request", "");
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
    // [LOG] Unknown route
    char ctx[80];
    snprintf(ctx, sizeof(ctx), "{\"url\":\"%s\",\"method\":%d}",
             request->url().c_str(), (int)request->method());
    sendLog(LOG_WARN, "server", "404 — unknown route", ctx);
    request->send(404, "text/plain", "Not found");
  });

  server.begin();
  // [LOG] HTTP server up
  sendLog(LOG_INFO, "server", "HTTP server started on port 80",
          "{\"endpoints\":[\"/tlm\",\"/log\",\"/cmd\",\"/cmd/stop\",\"/stream\"]}");

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
    camOk = false;
    // [LOG] Camera init failure
    sendLog(LOG_ERROR, "camera", "esp_camera_init failed — camera offline",
            "{\"pixel_format\":\"JPEG\",\"frame_size\":\"QVGA\"}");
  } else {
    camOk = true;
    applyOV3660Corrections();
    // [LOG] Camera ready
    sendLog(LOG_INFO, "camera", "Camera initialised OK — OV3660 corrections applied",
            "{\"pixel_format\":\"JPEG\",\"frame_size\":\"QVGA\",\"quality\":12,\"fb_count\":2}");
  }

  // [LOG] Boot complete
  sendLog(LOG_INFO, "system", "Setup complete — entering main loop", "");
}

///////////////////////////////////////////////////////// LOOP ///////////////////////////////////////////////////////////////////

void loop() {
  unsigned long now = millis();
  lastLoopUs  = now - loopStart;   // duration of the previous iteration
  loopStart   = now;

  updateIMU();
  updatePower();
  processCommandQueue();
  delay(10);
}

///////////////////////////////////////////////////////// MOTOR CONTROL //////////////////////////////////////////////////////////

// Set Motor A direction. dirCmd: 1 = forward, -1 = reverse, 0 = stop/brake.
void setMotorA(int dirCmd) {
  dirCmd = constrain(dirCmd, -1, 1);

  // [LOG] Log only on direction change to avoid flooding the buffer
  if (dirCmd != motA.dir) {
    char ctx[48];
    snprintf(ctx, sizeof(ctx), "{\"motor_id\":1,\"prev_dir\":%d,\"new_dir\":%d}",
             (int)motA.dir, dirCmd);
    sendLog(LOG_DEBUG, "motors", "Motor A direction changed", ctx);
  }

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

  // [LOG] Log only on direction change
  if (dirCmd != motB.dir) {
    char ctx[48];
    snprintf(ctx, sizeof(ctx), "{\"motor_id\":2,\"prev_dir\":%d,\"new_dir\":%d}",
             (int)motB.dir, dirCmd);
    sendLog(LOG_DEBUG, "motors", "Motor B direction changed", ctx);
  }

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
  // [LOG] Both motors stopped (only useful at INFO when called outside normal dir-change flow)
  sendLog(LOG_INFO, "motors", "All motors stopped (brake applied)", "");
}

///////////////////////////////////////////////////////// COMMAND QUEUE //////////////////////////////////////////////////////////

bool enqueueCmd(const Command& cmd) {
  uint8_t next = (cmdHead + 1) % CMD_QUEUE_SIZE;
  if (next == cmdTail) {
    faults.queueOverflow = true;
    Serial.println("[CMD] Queue overflow — command dropped");
    char ctx[48];
    snprintf(ctx, sizeof(ctx), "{\"cmd_type\":%d}", (int)cmd.type);
    sendLog(LOG_ERROR, "commands", "Command queue overflow — command dropped", ctx);
    return false;
  }
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
  // ── FIX: Non-blocking wait check ─────────────────────────────────────────
  // Previously, CMD_SYS_WAIT used a blocking while(millis() < waitUntil) loop
  // inside loop(), which prevented the async web server from ever dispatching
  // the /cmd/stop callback while a wait was in progress — making ESTOP a no-op
  // during any wait command.
  //
  // Now cmdBusy=true simply means "we are mid-wait; come back next tick".
  // The ESTOP handler sets cmdBusy=false AND waitUntil=0, which causes the
  // check below to fall through immediately on the next loop() iteration.
  if (cmdBusy) {
    if (millis() < waitUntil) {
      return;   // still waiting — yield to loop() so the web server can run
    }
    // Wait elapsed (or cancelled by ESTOP setting waitUntil=0)
    cmdBusy = false;
    sendLog(LOG_DEBUG, "commands", "CMD_SYS_WAIT complete", "");
    // Fall through to process the next command in the queue
  }

  if (queueEmpty()) {
    if (seqRunning) {
      seqRunning = false;
      lastStatus = "sequence complete";
      Serial.println("[CMD] Sequence complete");
      // [LOG] Sequence finished
      sendLog(LOG_INFO, "commands", "Command sequence complete", "");
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
      // [LOG] Motor direction command executed
      {
        char ctx[64];
        snprintf(ctx, sizeof(ctx),
                 "{\"seq\":%u,\"left_dir\":%d,\"right_dir\":%d}",
                 c.seqIndex, (int)c.argA, (int)c.argB);
        sendLog(LOG_DEBUG, "commands", "CMD_MOT_SET_DIR executed", ctx);
      }
      break;

    case CMD_MOT_STOP:
      stopAllMotors();
      lastStatus = "MOT_STOP";
      // [LOG] Explicit stop command
      {
        char ctx[32];
        snprintf(ctx, sizeof(ctx), "{\"seq\":%u}", c.seqIndex);
        sendLog(LOG_INFO, "commands", "CMD_MOT_STOP executed", ctx);
      }
      break;

    case CMD_SYS_WAIT:
      // ── FIX: No longer blocks. Set waitUntil and cmdBusy=true, then return.
      // processCommandQueue() will be called again next loop() tick and the
      // non-blocking check at the top will handle expiry / ESTOP cancellation.
      waitUntil = millis() + (unsigned long)c.argA;
      cmdBusy   = true;
      lastStatus = "WAIT " + String(c.argA) + "ms";
      {
        char ctx[48];
        snprintf(ctx, sizeof(ctx), "{\"seq\":%u,\"wait_ms\":%d}", c.seqIndex, (int)c.argA);
        sendLog(LOG_DEBUG, "commands", "CMD_SYS_WAIT started", ctx);
      }
      // Return immediately — do NOT block here.
      break;

    case CMD_SYS_REBOOT:
      stopAllMotors();
      lastStatus = "REBOOTING";
      Serial.println("[CMD] REBOOT");
      // [LOG] Reboot commanded — this will be the last log entry before restart
      sendLog(LOG_WARN, "system", "CMD_SYS_REBOOT — rebooting in 500 ms", "");
      delay(500);
      ESP.restart();
      break;

    case CMD_SYS_CLEAR_FAULTS:
      faults.imuTilt      = false;
      faults.motStall1    = false;
      faults.motStall2    = false;
      faults.queueOverflow = false;
      lastStatus = "FAULTS CLEARED";
      // [LOG] Faults cleared
      {
        char ctx[32];
        snprintf(ctx, sizeof(ctx), "{\"seq\":%u}", c.seqIndex);
        sendLog(LOG_INFO, "commands", "All fault flags cleared by CMD_SYS_CLEAR_FAULTS", ctx);
      }
      break;

    default:
      break;

  }
}

///////////////////////////////////////////////////////// HELPERS ////////////////////////////////////////////////////////////////

void updatePower() {
  pwr.mot1Volt = ina219_mot1.getBusVoltage_V();
  pwr.mot1Cur  = ina219_mot1.getCurrent_mA();
  pwr.mot2Volt = ina219_mot2.getBusVoltage_V();
  pwr.mot2Cur  = ina219_mot2.getCurrent_mA();

  // [LOG] Warn on very high motor current (possible stall / short)
  static float prevMot2Cur = 0.0f;
  constexpr float MOTOR_OVERCURRENT_MA = 200.0f;
  if (pwr.mot2Cur > MOTOR_OVERCURRENT_MA && prevMot2Cur <= MOTOR_OVERCURRENT_MA) {
    char ctx[64];
    snprintf(ctx, sizeof(ctx), "{\"current_ma\":%.1f,\"threshold\":2000}", pwr.mot2Cur);
    sendLog(LOG_WARN, "power", "Motor overcurrent detected", ctx);
  }
  prevMot2Cur = pwr.mot2Cur;
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

  // ── Tilt fault detection with edge-triggered logging ──────────────────────
  bool tiltNow = (fabsf(imu.roll)  > IMU_TILT_THRESHOLD_DEG ||
                  fabsf(imu.pitch) > IMU_TILT_THRESHOLD_DEG);

  if (tiltNow && !faults.imuTilt) {
    // [LOG] Tilt fault rising edge
    char ctx[80];
    snprintf(ctx, sizeof(ctx),
             "{\"roll\":%.1f,\"pitch\":%.1f,\"threshold\":%.0f}",
             imu.roll, imu.pitch, IMU_TILT_THRESHOLD_DEG);
    sendLog(LOG_ERROR, "imu", "Tilt fault triggered — vehicle may be overturned", ctx);
  } else if (!tiltNow && faults.imuTilt) {
    // [LOG] Tilt fault cleared
    char ctx[80];
    snprintf(ctx, sizeof(ctx),
             "{\"roll\":%.1f,\"pitch\":%.1f}", imu.roll, imu.pitch);
    sendLog(LOG_INFO, "imu", "Tilt fault cleared — orientation restored", ctx);
  }

  faults.imuTilt = tiltNow;
}

String buildTelemetryJson() {
  StaticJsonDocument<2048> doc;

  doc["type"] = "tlm";

  // System
  doc["SYS_UPTIME"]          = millis() / 1000;
  doc["SYS_HEAP_FREE"]       = ESP.getFreeHeap();
  doc["SYS_LOOP_TIME_MS"]    = lastLoopUs;              
  doc["SYS_PACKET_NUM"]      = pktSeq++;
  doc["SYS_MODE"]            = seqRunning ? "RUN" : "IDLE";
  doc["SYS_STATUS"]          = lastStatus;
  doc["SYS_WIFI_RSSI"]       = WiFi.softAPgetStationNum() > 0 ? (int)WiFi.RSSI() : 0; 
  doc["SYS_TEMP_C"]          = serialized(String(temperatureRead(), 1));  
  doc["SYS_CAM_OK"]          = camOk;                   

  // Sequence
  doc["SEQ_RUNNING"]         = seqRunning;
  doc["SEQ_CURRENT"]         = seqCurrent;
  doc["SEQ_TOTAL"]           = seqTotal;
  doc["SEQ_QUEUE_DEPTH"]     = (cmdHead - cmdTail + CMD_QUEUE_SIZE) % CMD_QUEUE_SIZE;
  doc["SEQ_QUEUE_REMAINING"] = CMD_QUEUE_SIZE - 1 - (cmdHead - cmdTail + CMD_QUEUE_SIZE) % CMD_QUEUE_SIZE;

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
  doc["MOT_BUSY"]      = cmdBusy;

  // Faults
  doc["FLT_IMU_TILT"]      = faults.imuTilt;
  doc["FLT_MOT_STALL_1"]   = faults.motStall1;
  doc["FLT_MOT_STALL_2"]   = faults.motStall2;
  doc["FLT_QUEUE_OVERFLOW"] = faults.queueOverflow;

  // [LOG] Log a warning if heap is getting tight (under 20 kB free)
  if (ESP.getFreeHeap() < 20000) {
    char ctx[48];
    snprintf(ctx, sizeof(ctx), "{\"free_heap\":%u}", ESP.getFreeHeap());
    sendLog(LOG_WARN, "system", "Low heap memory", ctx);
  }

  String out;
  serializeJson(doc, out);
  return out;
}

void applyOV3660Corrections() {
  sensor_t* s = esp_camera_sensor_get();
  if (!s) {
    // [LOG] Sensor handle unavailable after init
    sendLog(LOG_WARN, "camera", "applyOV3660Corrections: sensor handle is null", "");
    return;
  }
  s->set_vflip(s, 1);
  s->set_hmirror(s, 0);
  // [LOG] OV3660 corrections applied
  sendLog(LOG_DEBUG, "camera", "OV3660 vflip=1 hmirror=0 applied", "");
}
