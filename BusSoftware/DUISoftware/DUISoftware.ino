////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//
// Vehicle software for PROJECT DUI robot
//
// Created March 2026 by James Torok
// Rewritten to use ESPAsyncWebServer
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

///// Set important constants /////

// Pin Definitions
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

// I2C pins for MPU6050
#define IMU_SDA_PIN     20
#define IMU_SCL_PIN     19

// Camera Config
#define MJPEG_BOUNDARY     "frame"
#define MJPEG_CONTENT_TYPE "multipart/x-mixed-replace;boundary=" MJPEG_BOUNDARY

// Access Point credentials
const char* ssid     = "PROJECT_DUI_ESP32";
const char* password = "12345678";

// Single async server on port 80
AsyncWebServer server(80);

// MPU6050
MPU6050 mpu;

// IMU state — updated every loop iteration
struct ImuData {
  float accelX, accelY, accelZ;   // m/s²
  float gyroX,  gyroY,  gyroZ;    // °/s
  float roll, pitch, heading;      // degrees
} imu = {};

// Complementary filter coefficient (0 = trust gyro only, 1 = trust accel only)
static constexpr float ALPHA = 0.96f;

unsigned long lastLoopTime  = 0;
unsigned long lastImuTime   = 0;
uint32_t seq = 0;

///////////////////////////////////////////////////////// END INIT ///////////////////////////////////////////////////////////////

void applyOV3660Corrections();
String buildTelemetryJson();
void updateIMU();

///////////////////////////////////////////////////////// SETUP //////////////////////////////////////////////////////////////////

void setup() {
  Serial.begin(115200);

  // ── MPU6050 init ────────────────────────────────────────────────────────────
  Wire.begin(IMU_SDA_PIN, IMU_SCL_PIN);
  mpu.initialize();

  // Remove built-in offsets; calibrate on a level surface if needed
  mpu.setXAccelOffset(0);
  mpu.setYAccelOffset(0);
  mpu.setZAccelOffset(0);
  mpu.setXGyroOffset(0);
  mpu.setYGyroOffset(0);
  mpu.setZGyroOffset(0);

  lastImuTime = millis();

  // ── WiFi Access Point ───────────────────────────────────────────────────────
  WiFi.softAP(ssid, password);
  Serial.println("AP Started!");
  Serial.println(WiFi.softAPIP());

  // ── Telemetry endpoint ──────────────────────────────────────────────────────
  server.on("/tlm", HTTP_GET, [](AsyncWebServerRequest* request) {
    String json = buildTelemetryJson();
    request->send(200, "application/json", json);
  });

  // ── MJPEG stream endpoint ───────────────────────────────────────────────────
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
        "Content-Length: %u\r\n"
        "\r\n",
        fb->len
    );
    response->write(fb->buf, fb->len);
    response->print("\r\n");

    esp_camera_fb_return(fb);
    request->send(response);
  });

  // ── 404 fallback ────────────────────────────────────────────────────────────
  server.onNotFound([](AsyncWebServerRequest* request) {
    request->send(404, "text/plain", "Not found");
  });

  server.begin();

  // ── Camera init ─────────────────────────────────────────────────────────────
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
  delay(10);
}

///////////////////////////////////////////////////////// HELPERS ////////////////////////////////////////////////////////////////

void updateIMU() {
  int16_t ax, ay, az, gx, gy, gz;
  mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);

  // ── Scale raw values ────────────────────────────────────────────────────────
  // Default full-scale: ±2g accel, ±250°/s gyro
  constexpr float ACCEL_SCALE = 9.80665f / 16384.0f;  // LSB → m/s²
  constexpr float GYRO_SCALE  = 1.0f    / 131.0f;     // LSB → °/s

  imu.accelX = ax * ACCEL_SCALE;
  imu.accelY = ay * ACCEL_SCALE;
  imu.accelZ = az * ACCEL_SCALE;
  imu.gyroX  = gx * GYRO_SCALE;
  imu.gyroY  = gy * GYRO_SCALE;
  imu.gyroZ  = gz * GYRO_SCALE;

  // ── Complementary filter for roll & pitch ───────────────────────────────────
  unsigned long now = millis();
  float dt = (now - lastImuTime) / 1000.0f;   // seconds
  lastImuTime = now;

  // Accel-derived angles (reliable when stationary, noisy when moving)
  float accelRoll  = atan2f(imu.accelY, imu.accelZ) * 180.0f / M_PI;
  float accelPitch = atan2f(-imu.accelX,
                             sqrtf(imu.accelY * imu.accelY +
                                   imu.accelZ * imu.accelZ)) * 180.0f / M_PI;

  // Fuse with gyro integration
  imu.roll    = ALPHA * (imu.roll  + imu.gyroX * dt) + (1.0f - ALPHA) * accelRoll;
  imu.pitch   = ALPHA * (imu.pitch + imu.gyroY * dt) + (1.0f - ALPHA) * accelPitch;

  // Heading: gyro-integrated yaw only — drifts over time.
  // Replace with a magnetometer (e.g. HMC5883L / QMC5883L) for true heading.
  imu.heading += imu.gyroZ * dt;

  // Keep heading in [0, 360)
  if (imu.heading <   0.0f) imu.heading += 360.0f;
  if (imu.heading >= 360.0f) imu.heading -= 360.0f;
}

String buildTelemetryJson() {
  StaticJsonDocument<1536> doc;

  doc["type"] = "tlm";

  // System
  doc["SYS_UPTIME"]     = millis() / 1000;
  doc["SYS_HEAP_FREE"]  = ESP.getFreeHeap();
  doc["SYS_LOOP_TIME"]  = millis() - lastLoopTime;
  doc["SYS_PACKET_NUM"] = seq++;
  doc["SYS_MODE"]       = "TEST";

  // Power
  doc["PWR_BAT_VOLT"]  = 0;
  doc["PWR_BAT_CUR"]   = 0;
  doc["PWR_MOT1_VOLT"] = 0;
  doc["PWR_MOT1_CUR"]  = 0;
  doc["PWR_MOT2_VOLT"] = 0;
  doc["PWR_MOT2_CUR"]  = 0;

  // IMU — real values
  doc["IMU_ACCEL_X"] = serialized(String(imu.accelX, 3));
  doc["IMU_ACCEL_Y"] = serialized(String(imu.accelY, 3));
  doc["IMU_ACCEL_Z"] = serialized(String(imu.accelZ, 3));
  doc["IMU_GYRO_X"]  = serialized(String(imu.gyroX,  3));
  doc["IMU_GYRO_Y"]  = serialized(String(imu.gyroY,  3));
  doc["IMU_GYRO_Z"]  = serialized(String(imu.gyroZ,  3));
  doc["IMU_HEADING"] = serialized(String(imu.heading, 1));
  doc["IMU_ROLL"]    = serialized(String(imu.roll,    1));
  doc["IMU_PITCH"]   = serialized(String(imu.pitch,   1));

  // Temp
  doc["TMP_PROBE"] = 0;

  // Motors
  doc["MOT_1_SPEED"] = 0;
  doc["MOT_1_DIR"]   = 0;
  doc["MOT_1_PWM"]   = 0;
  doc["MOT_2_SPEED"] = 0;
  doc["MOT_2_DIR"]   = 0;
  doc["MOT_2_PWM"]   = 0;

  // Faults
  doc["FLT_IMU_TILT"]    = false;
  doc["FLT_MOT_STALL_1"] = false;
  doc["FLT_MOT_STALL_2"] = false;

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