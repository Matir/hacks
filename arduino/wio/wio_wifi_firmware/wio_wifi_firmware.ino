uint32_t baud;
uint32_t old_baud;
 
void setup() {
  // initialize both serial ports:
  pinMode(PIN_SERIAL2_RX, OUTPUT);
  pinMode(RTL8720D_CHIP_PU, OUTPUT);
  digitalWrite(PIN_SERIAL2_RX, LOW);
  digitalWrite(RTL8720D_CHIP_PU, LOW);
  delay(500);
  digitalWrite(RTL8720D_CHIP_PU, HIGH);
  delay(500);
  pinMode(PIN_SERIAL2_RX, INPUT);
  Serial.beginWithoutDTR(115200);
  //  Serial.baud
  old_baud = Serial.baud();
  RTL8720D.begin(old_baud);
 
  delay(500);
}
 
void loop() {
 
  baud = Serial.baud();
  if(baud != old_baud)
  {
    RTL8720D.begin(baud);
    old_baud = baud;
  }
  // read from port 1, send to port 0:
  if (Serial.available())
  {
    int inbyte = Serial.read();
    RTL8720D.write(inbyte);
    //Serial1.write(inbyte);
  }
  //   read from port 1, send to port 0:
  if (RTL8720D.available())
  {
    int inbyte = RTL8720D.read();
    Serial.write(inbyte);
    //Serial1.write(inbyte);
  }
}
