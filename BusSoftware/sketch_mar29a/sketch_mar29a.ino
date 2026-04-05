/*
  ESP32-S3 WROOM + OV3660 — MJPEG Stream Server
  Streams to: http://192.168.4.1/stream
  Board settings (Arduino IDE):
    Board:            ESP32S3 Dev Module
    PSRAM:            OPI PSRAM
    Partition Scheme: Huge APP (3MB No OTA / 1MB SPIFFS)
    USB CDC On Boot:  Enabled
*/

#include "esp_camera.h"
#include <WiFi.h>
#include <WiFiClient.h>

const char* AP_SSID     = "ESP32-CAM";
const char* AP_PASSWORD = "12345678";

// Target frame interval in milliseconds — raise to slow down, lower to speed up
#define FRAME_INTERVAL_MS 150   // ~6 fps

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

#define MJPEG_BOUNDARY     "frame"
#define MJPEG_CONTENT_TYPE "multipart/x-mixed-replace;boundary=" MJPEG_BOUNDARY

WiFiServer server(80);

// ── OV3660 image-quality tuning ─────────────────────────────────────────────
// Called once after esp_camera_init().  The OV3660 ships with conservative
// defaults; these register writes bring colours, contrast and sharpness up to
// a usable level.
void applyOV3660Corrections() {
  sensor_t* s = esp_camera_sensor_get();
  if (!s) return;

  // Orientation — OV3660 on most ESP32-S3 carrier boards is mounted upside-down
  s->set_vflip(s, 1);        // flip vertically
  s->set_hmirror(s, 0);      // set to 1 if image is also horizontally mirrored

}
// ────────────────────────────────────────────────────────────────────────────

void handleStream(WiFiClient& client) {
  client.print(
    "HTTP/1.1 200 OK\r\n"
    "Content-Type: " MJPEG_CONTENT_TYPE "\r\n"
    "Cache-Control: no-cache\r\n"
    "Connection: keep-alive\r\n"
    "\r\n"
  );

  unsigned long lastFrame = 0;

  while (client.connected()) {

    // ── rate limiting ───────────────────────────────────────────────────────
    unsigned long now = millis();
    long toWait = (long)FRAME_INTERVAL_MS - (long)(now - lastFrame);
    if (toWait > 0) {
      delay(toWait);
    }
    lastFrame = millis();
    // ───────────────────────────────────────────────────────────────────────

    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) { delay(10); continue; }

    String frameHeader =
      "--" MJPEG_BOUNDARY "\r\n"
      "Content-Type: image/jpeg\r\n"
      "Content-Length: " + String(fb->len) + "\r\n"
      "\r\n";
    client.print(frameHeader);

    const uint8_t* ptr = fb->buf;
    size_t remaining   = fb->len;
    while (remaining > 0 && client.connected()) {
      size_t sent = client.write(ptr, min(remaining, (size_t)1024));
      if (sent == 0) break;
      ptr       += sent;
      remaining -= sent;
    }
    client.print("\r\n");
    esp_camera_fb_return(fb);
  }
}

void handleClient(WiFiClient& client) {
  String requestLine = client.readStringUntil('\n');
  requestLine.trim();

  while (client.available()) {
    String line = client.readStringUntil('\n');
    if (line == "\r" || line.isEmpty()) break;
  }

  if (requestLine.startsWith("GET /stream")) {
    handleStream(client);
  } else {
    client.print(
      "HTTP/1.1 404 Not Found\r\n"
      "Content-Length: 0\r\n"
      "Connection: close\r\n"
      "\r\n"
    );
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("Starting...");

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

  if (psramFound()) {
    config.frame_size   = FRAMESIZE_VGA;
    config.jpeg_quality = 10;  // slightly higher quality (lower number = better)
    config.fb_count     = 2;
    config.grab_mode    = CAMERA_GRAB_LATEST;
  } else {
    config.frame_size   = FRAMESIZE_QQVGA;
    config.jpeg_quality = 20;
    config.fb_count     = 1;
    config.grab_mode    = CAMERA_GRAB_WHEN_EMPTY;
  }

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("Camera init failed");
    while (true) delay(1000);
  }

  // Apply OV3660-specific image corrections after init
  applyOV3660Corrections();

  WiFi.softAP(AP_SSID, AP_PASSWORD);
  delay(500);
  Serial.printf("Stream: http://%s/stream\n", WiFi.softAPIP().toString().c_str());

  server.begin();
}

void loop() {
  if (server.hasClient()) {
    WiFiClient client = server.available();
    if (client) {
      handleClient(client);
    }
  }
}