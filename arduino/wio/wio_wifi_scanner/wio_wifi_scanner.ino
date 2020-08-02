#include "AtWiFi.h"
#include "TFT_eSPI.h"
#include "Free_Fonts.h"

TFT_eSPI tft;
int list_display_offset = 0;
int rescan = 1;
int refresh = 1;

#define SCREEN_Y 240
#define SCREEN_X 320

#define Serial_printf(...) do {sprintf(buf, __VA_ARGS__); Serial.print(buf);}while(0)

void doOneScan();
void handleBtnB();
void handleStickDown();
void handleStickUp();
void drawOnScreen();
void drawMessageBox(char *msg);

void setup() {
  char buf[128];
  Serial.begin(115200);
  while (!Serial); // Wait for Serial to be ready

  // Set WiFi to station mode and disconnect from an AP if it was previously connected
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(100);

  // Setup tft
  tft.begin();
  tft.setRotation(3);
  tft.setFreeFont(FM9);
  tft.fillScreen(TFT_BLACK);
  digitalWrite(LCD_BACKLIGHT, HIGH);

  // Attach interrupts
  pinMode(WIO_KEY_A, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(WIO_KEY_B), handleBtnB, FALLING);
  pinMode(WIO_5S_UP, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(WIO_5S_UP), handleStickUp, FALLING);
  pinMode(WIO_5S_DOWN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(WIO_5S_DOWN), handleStickDown, FALLING);

  Serial.println("Setup done");
  Serial_printf("WIFI_AUTH_OPEN: %d\n", WIFI_AUTH_OPEN);
  Serial_printf("WIFI_AUTH_WEP: %d\n", WIFI_AUTH_WEP);
  Serial_printf("WIFI_AUTH_WPA_PSK: %d\n", WIFI_AUTH_WPA_PSK);
  Serial_printf("WIFI_AUTH_WPA2_PSK: %d\n", WIFI_AUTH_WPA2_PSK);
  Serial_printf("WIFI_AUTH_WPA_WPA2_PSK: %d\n", WIFI_AUTH_WPA_WPA2_PSK);
  Serial_printf("WIFI_AUTH_WPA2_ENTERPRISE: %d\n", WIFI_AUTH_WPA2_ENTERPRISE);
}

void loop() {
  if (rescan) {
    doOneScan();
    refresh = 1;
  }
  if (refresh) {
    refresh = 0;
    drawOnScreen();
  }
  delay(10);
}

void handleBtnB() {
  rescan = 1;
}

void handleStickDown() {
  list_display_offset++;
  refresh = 1;
}

void handleStickUp() {
  if (list_display_offset > 0)
    list_display_offset--;
  refresh = 1;
}

void drawMessageBox(char *msg) {
  int16_t width = tft.textWidth(msg) + 20;
  int16_t height = tft.fontHeight() * 2;
  uint8_t old_datum = tft.getTextDatum();
  tft.setTextDatum(MC_DATUM);

  // Draw box outline
  int32_t x = (SCREEN_X-width)/2;
  int32_t y = (SCREEN_Y-height)/2;
  tft.fillRect(x, y, width, height, TFT_BLACK);
  tft.drawRect(x, y, width, height, TFT_RED);
  tft.drawString(msg, SCREEN_X/2, SCREEN_Y/2);

  tft.setTextDatum(old_datum);
}

void doOneScan() {
  char buf[128];
  Serial.println("scan start");

  drawMessageBox("Scanning...");

  // WiFi.scanNetworks will return the number of networks found
  int num_networks = WiFi.scanNetworks();
  if (num_networks < 0) {
    Serial.println("Error scanning!");
    return;
  }
  Serial.println("scan done");
  if (num_networks == 0) {
    Serial.println("no networks found");
  } else {
    Serial.print(num_networks);
    Serial.println(" networks found");
    for (int i = 0; i < num_networks; ++i) {
      sprintf(buf, "%02d: (Ch. %2d) %-16s %s [RSSI: %03d, ENC: %d]\n", i, WiFi.channel(i), WiFi.SSID(i).substring(0, 16).c_str(), WiFi.BSSIDstr(i).c_str(), WiFi.RSSI(i), WiFi.encryptionType(i));
      Serial.print(buf);
    }
  }
  Serial.println("");
  rescan = 0;
}

void drawOnScreen() {
  char buf[128];
  tft.fillScreen(TFT_BLACK);
  int n = WiFi.scanComplete();
  Serial.println("drawOnScreen called");
  if (n < 0) {
    Serial.println("Results not available in drawOnScreen!");
    return;
  } else if (n == 0) {
    Serial.println("No scan results!");
  }
  if (list_display_offset > n)
    list_display_offset = n;
  Serial.print("Starting at offset: ");
  Serial.println(list_display_offset);
  int16_t line_height = tft.fontHeight();
  for (int i = 0; i < n; ++i) {
    sprintf(buf, "%02d: (Ch. %2d) %-16s %s [RSSI: %03d, ENC: %d]", i, WiFi.channel(i), WiFi.SSID(i).substring(0, 16).c_str(), WiFi.BSSIDstr(i).c_str(), WiFi.RSSI(i), WiFi.encryptionType(i));
    if (i < list_display_offset)
      continue;
    int start_y = line_height * (i - list_display_offset);
    if (start_y >= SCREEN_Y)
      break;
    tft.drawString(buf, 0, start_y);
  }
  Serial.println("drawOnScreen done");
}
