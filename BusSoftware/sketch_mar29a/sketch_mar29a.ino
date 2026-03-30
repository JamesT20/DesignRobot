/*
  ESP32-S3 WROOM + OV3660 — Access Point Web Server
  Broadcasts a JPEG snapshot every 5 seconds on http://192.168.4.1

  Board settings (Arduino IDE):
    Board:            ESP32S3 Dev Module
    PSRAM:            OPI PSRAM  (if your board has it, otherwise disabled)
    Partition Scheme: Huge APP (3MB No OTA / 1MB SPIFFS)
    USB CDC On Boot:  Enabled   (for Serial output via USB)
*/

#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>

// ── WiFi AP credentials ──────────────────────────────────────────────────────
const char* AP_SSID     = "ESP32-CAM";
const char* AP_PASSWORD = "12345678";   // min 8 chars; use "" for open network

// ── Pin map for ESP32-S3 WROOM + OV3660 ─────────────────────────────────────
// These match the common ESP32-S3-WROOM camera reference design.
// If your board has a different wiring, adjust accordingly.
#define PWDN_GPIO_NUM   -1
#define RESET_GPIO_NUM  -1
#define XCLK_GPIO_NUM   15
#define SIOD_GPIO_NUM    4   // SDA
#define SIOC_GPIO_NUM    5   // SCL

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

WebServer server(80);

// ── HTML page ────────────────────────────────────────────────────────────────
const char INDEX_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ESP32-S3 Camera</title>
  <style>
    body { margin: 0; background: #111; display: flex; flex-direction: column;
           align-items: center; justify-content: center; min-height: 100vh;
           font-family: sans-serif; color: #eee; }
    img  { max-width: 100%; border: 2px solid #333; border-radius: 6px; }
    p    { font-size: 0.85rem; color: #888; margin-top: 8px; }
  </style>
</head>
<body>
  <h2 style="margin-bottom:12px;">ESP32-S3 Live View</h2>
  <img id="cam" src="/cam" alt="camera frame">
  <p id="ts">Refreshing every 5 seconds...</p>
  <script>
    function refresh() {
      document.getElementById('cam').src = '/cam?t=' + Date.now();
      document.getElementById('ts').textContent =
        'Last update: ' + new Date().toLocaleTimeString();
    }
    setInterval(refresh, 5000);
  </script>
</body>
</html>
)rawliteral";

// ── Route handlers ───────────────────────────────────────────────────────────
void handleRoot() {
  server.send_P(200, "text/html", INDEX_HTML);
}

void handleCam() {
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    server.send(500, "text/plain", "Camera capture failed");
    return;
  }
  server.sendHeader("Cache-Control", "no-cache, no-store, must-revalidate");
  server.sendHeader("Pragma",        "no-cache");
  server.sendHeader("Expires",       "0");
  server.send_P(200, "image/jpeg",
                (const char*)fb->buf,
                fb->len);
  esp_camera_fb_return(fb);
}

void handleNotFound() {
  server.send(404, "text/plain", "Not found");
}

// ── Setup ────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  Serial.println("\n=== ESP32-S3 WROOM + OV3660 AP Server ===");

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

  // OV3660 works best at 20 MHz XCLK
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  if (psramFound()) {
    Serial.println("PSRAM found — using VGA quality");
    config.frame_size   = FRAMESIZE_VGA;   // 640x480; try FRAMESIZE_SVGA for 800x600
    config.jpeg_quality = 12;              // 0=best, 63=worst
    config.fb_count     = 2;
    config.grab_mode    = CAMERA_GRAB_LATEST;  // always get the freshest frame
  } else {
    Serial.println("No PSRAM — using QQVGA");
    config.frame_size   = FRAMESIZE_QQVGA;  // 320x240
    config.jpeg_quality = 20;
    config.fb_count     = 1;
    config.grab_mode    = CAMERA_GRAB_WHEN_EMPTY;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x\n", err);
    Serial.println("Check your pin definitions and power supply.");
    return;
  }
  Serial.println("Camera initialised OK");

  // OV3660-specific tuning
  sensor_t* s = esp_camera_sensor_get();
  if (s) {
    // OV3660 outputs images upside-down on most breakout boards — flip if needed
    s->set_vflip(s,     1);
    s->set_hmirror(s,   0);
    s->set_brightness(s,  1);  // slight brightness boost
    s->set_saturation(s, -1);  // tame saturation a touch
    s->set_whitebal(s,    1);  // auto white balance on
    s->set_exposure_ctrl(s, 1);// auto exposure on
    s->set_gain_ctrl(s,   1);  // auto gain on
  }

  // Start Access Point
  WiFi.softAP(AP_SSID, AP_PASSWORD[0] == '\0' ? nullptr : AP_PASSWORD);
  delay(500);
  IPAddress ip = WiFi.softAPIP();
  Serial.printf("AP started — SSID: %s\n", AP_SSID);
  Serial.printf("Connect to WiFi then open http://%s\n", ip.toString().c_str());

  // Register routes
  server.on("/",    HTTP_GET, handleRoot);
  server.on("/cam", HTTP_GET, handleCam);
  server.onNotFound(handleNotFound);
  server.begin();
  Serial.println("HTTP server started");
}

// ── Loop ─────────────────────────────────────────────────────────────────────
void loop() {
  server.handleClient();
}
