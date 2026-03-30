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

///// Set important constants /////

// Access Point credentials
const char* ssid = "PROJECT_DUI_ESP32";
const char* password = "12345678";

// Create server on port 8080
WiFiServer server(8080);

// Setup wifi client for recieving data
WiFiClient client;

unsigned long lastSend = 0;
unsigned long lastLoopTime = 0;
uint32_t seq = 0;

///////////////////////////////////////////////////////// END INIT ///////////////////////////////////////////////////////////////

void setup() {
  Serial.begin(115200);

  // Start as Access Point, not a client
  WiFi.softAP(ssid, password);

  Serial.println("AP Started!");
  Serial.println(WiFi.softAPIP());  // Usually 192.168.4.1

  server.begin();  // <-- Don't forget this!
}

void loop() {
  lastLoopTime = millis();

  if (!client || !client.connected()){
    client = server.available();
    return;
  }

  if (millis() - lastSend > 100){
    sendTelemetry();
    lastSend = millis();
  }
}

void sendTelemetry()
{
  StaticJsonDocument<1536> doc;

  float t = millis() / 1000.0;

  doc["type"] = "tlm";

  // System
  doc["SYS_UPTIME"] = millis() / 1000;
  doc["SYS_HEAP_FREE"] = ESP.getFreeHeap();
  doc["SYS_LOOP_TIME"] = millis() - lastLoopTime;
  doc["SYS_PACKET_NUM"] = seq;
  doc["SYS_MODE"] = "TEST";

  // Power
  doc["PWR_BAT_VOLT"] = 0;
  doc["PWR_BAT_CUR"] = 0;
  doc["PWR_MOT1_VOLT"] = 0;
  doc["PWR_MOT1_CUR"] = 0;
  doc["PWR_MOT2_VOLT"] = 0;
  doc["PWR_MOT2_CUR"] = 0;

  // IMU
  doc["IMU_ACCEL_X"] = 0;
  doc["IMU_ACCEL_Y"] = 0;
  doc["IMU_ACCEL_Z"] = 0;

  doc["IMU_GYRO_X"] = 0;
  doc["IMU_GYRO_Y"] = 0;
  doc["IMU_GYRO_Z"] = 0;

  doc["IMU_HEADING"] = 0;
  doc["IMU_ROLL"] = 0;
  doc["IMU_PITCH"] = 0;

  // Temp
  doc["TMP_PROBE"] = 0;

  // Camera
  doc["IMG_ENDPOINT"] = "TBD";

  // Motors
  doc["MOT_1_SPEED"] = 0;
  doc["MOT_1_DIR"] = 0;
  doc["MOT_1_PWM"] = 0;

  doc["MOT_2_SPEED"] = 0;
  doc["MOT_2_DIR"] = 0;
  doc["MOT_2_PWM"] = 0;

  // Faults
  doc["FLT_IMU_TILT"] = false;
  doc["FLT_MOT_STALL_1"] = false;
  doc["FLT_MOT_STALL_2"] = false;

  String out;
  serializeJson(doc,out);
  client.println(out);

  seq++;
}