
// old scale factor for 500g: 3225.35
// old scale factor for 5kg: 453.23
// new scale factor for 5kg: -140.46

  #include <HX711.h>

// HX711 circuit wiring
const int LOADCELL_DOUT_PIN = 11;
const int LOADCELL_SCK_PIN  = 10;

HX711 scale;

// calibration constants (G OUTPUT)
const float OFFSET = 0;
const float SCALE_FACTOR = -453.33;  // g per unit +/- depending on direction

void setup() {
  Serial.begin(9600);

  scale.begin(LOADCELL_DOUT_PIN, LOADCELL_SCK_PIN);
  scale.tare(); // zero the scale
  //scale.set_offset(OFFSET);
  scale.set_scale(SCALE_FACTOR);

  Serial.println("Scale ready (kg output)");
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command == "START") {
      //scale.set_offset(OFFSET);
      scale.set_scale(SCALE_FACTOR);
      Serial.println("Scale reinitialized (g)");
    }

    else if (command == "READ") {
      if (scale.is_ready()) {
        float mass_kg = scale.get_units(5);
        Serial.println(mass_kg, 4);  // 4 decimals = grams resolution
      } else {
        Serial.println("HX711 not ready");
      }
    }
  }

  delay(100);
}
