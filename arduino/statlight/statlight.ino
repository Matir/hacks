#include <FastLED.h>
#include <string.h>
#include <stdlib.h>


#define NUM_LEDS 8
#define DATA_PIN 11

typedef union {
  void *data;
  CRGB val;
} funcArg;

typedef struct {
  String cmd;
  void (*func)(String args, funcArg arg);
  funcArg arg;
} cmdSet;

String splitFirstWord(String arg);
void setAll(String unused_args, funcArg arg);
void setCustom(String args, funcArg arg);

cmdSet Commands[] = {
  {"off", setAll, {.val = CRGB::Black}},
  {"red", setAll, {.val = CRGB::Red}},
  {"blue", setAll, {.val = CRGB::Blue}},
  {"green", setAll, {.val = CRGB::Green}},
  {"yellow", setAll, {.val = CRGB::Yellow}},
  {"white", setAll, {.val = CRGB::White}},
  {"custom", setCustom, {}},
  {"", NULL, {}},
};

CRGB led_data[NUM_LEDS];

void setup() {
  Serial.begin(115200);
  LEDS.addLeds<WS2812, DATA_PIN, GRB>(led_data, NUM_LEDS);
  LEDS.setBrightness(32);
}

void loop() {
  String argv = Serial.readStringUntil('\n');
  if (argv != "") {
    handleCmd(argv);
  }
}

void handleCmd(String argv) {
  String cmd = splitFirstWord(argv);
  int i=0;
  while (Commands[i].func) {
    if (Commands[i].cmd.equals(cmd)) {
      Commands[i].func(argv, Commands[i].arg);
      FastLED.show();
      break;
    }
    i++;
  };
}

String splitFirstWord(String arg) {
  int pos = arg.indexOf(' ');
  if (pos == -1) {
    return arg;
  }
  String rv = arg.substring(0, pos);
  rv.remove(0, pos+1);
  return rv;
}

void setAll(String unused_args, funcArg arg) {
  for(int i=0;i<NUM_LEDS;i++)
    led_data[i] = arg.val;
}

void setCustom(String args, funcArg arg) {
  for(int i=0;i<NUM_LEDS;i++) {
    String colorWord = splitFirstWord(args);
    int color = strtol(colorWord.c_str(), NULL, 16);
    led_data[i] = color;
  }
}
