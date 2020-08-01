#include "AtWiFi.h"
 
void setup() {
    Serial.begin(115200);
    while(!Serial); // Wait for Serial to be ready
    delay(1000);
 
    // Set WiFi to station mode and disconnect from an AP if it was previously connected
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();
    delay(100);
 
    Serial.println("Setup done");
}

#define Serial_printf(...) do {sprintf(buf, __VA_ARGS__); Serial.print(buf);}while(0)
 
void loop() {
    char buf[128];
    Serial_printf("WIFI_AUTH_OPEN: %d\n", WIFI_AUTH_OPEN);
    Serial_printf("WIFI_AUTH_WEP: %d\n", WIFI_AUTH_WEP);
    Serial_printf("WIFI_AUTH_WPA_PSK: %d\n", WIFI_AUTH_WPA_PSK);
    Serial_printf("WIFI_AUTH_WPA2_PSK: %d\n", WIFI_AUTH_WPA2_PSK);
    Serial_printf("WIFI_AUTH_WPA_WPA2_PSK: %d\n", WIFI_AUTH_WPA_WPA2_PSK);
    Serial_printf("WIFI_AUTH_WPA2_ENTERPRISE: %d\n", WIFI_AUTH_WPA2_ENTERPRISE);
    Serial.println("scan start");
 
    // WiFi.scanNetworks will return the number of networks found
    int n = WiFi.scanNetworks();
    Serial.println("scan done");
    if (n == 0) {
        Serial.println("no networks found");
    } else {
        Serial.print(n);
        Serial.println(" networks found");
        for (int i = 0; i < n; ++i) {
            Serial_printf("%02d: (Ch. %2d) %32s %s [RSSI: %03d, ENC: %d]\n", i, WiFi.channel(i), WiFi.SSID(i).c_str(), WiFi.BSSIDstr(i).c_str(), WiFi.RSSI(i), WiFi.encryptionType(i));
            delay(10);
        }
    }
    Serial.println("");
 
    // Wait a bit before scanning again
    delay(30000);
}
