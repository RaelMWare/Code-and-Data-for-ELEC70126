// people_counter.ino
// ESP32 Heltec LoRa — Ultrasonic People Counter + Keypad Concentration Rating + Fan Control + ThingSpeak MQTT
// Sensor A (inner / room-side): TRIG=20, ECHO=19
// Sensor B (outer / door-side): TRIG=7,  ECHO=6
// Keypad: Rows=45,42,41,40 | Cols=39,38,1,2
// Fan: GPIO 4

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <Keypad.h>
#include <time.h>
#include "../secrets.h"


const int TRIG_B = 20, ECHO_B = 19;
const int TRIG_A = 7,  ECHO_A = 6;


const int FAN_PIN = 4;


const byte ROWS = 4;
const byte COLS = 4;

char keys[ROWS][COLS] = {
    {'1','2','3','A'},
    {'4','5','6','B'},
    {'7','8','9','C'},
    {'*','0','#','D'}
};

byte rowPins[ROWS] = {45, 42, 41, 40};
byte colPins[COLS] = {39, 38, 1, 2};

Keypad keypad = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);

// --- SENSOR TUNING ---
const int DETECTION_THRESHOLD_CM = 60;
const unsigned long SENSOR_TIMEOUT_US = 30000;
const unsigned long STATE_TIMEOUT_MS = 2000;
const int DEBOUNCE_COUNT = 2;
const unsigned long COOLDOWN_MS = 1500;
const int CONFIRM_HITS = 2;

// --- MQTT ---
const unsigned long MQTT_INTERVAL_MS = 15000;
const char* ca_cert = R"(-----BEGIN CERTIFICATE-----
MIIEyDCCA7CgAwIBAgIQDPW9BitWAvR6uFAsI8zwZjANBgkqhkiG9w0BAQsFADBh
MQswCQYDVQQGEwJVUzEVMBMGA1UEChMMRGlnaUNlcnQgSW5jMRkwFwYDVQQLExB3
d3cuZGlnaWNlcnQuY29tMSAwHgYDVQQDExdEaWdpQ2VydCBHbG9iYWwgUm9vdCBH
MjAeFw0yMTAzMzAwMDAwMDBaFw0zMTAzMjkyMzU5NTlaMFkxCzAJBgNVBAYTAlVT
MRUwEwYDVQQKEwxEaWdpQ2VydCBJbmMxMzAxBgNVBAMTKkRpZ2lDZXJ0IEdsb2Jh
bEcyVExTIFJTQSBTSEEyNTYgMjAyMCBDQTEwggEiMA0GCSqGSIb3DQEBAQUAA4IB
DwAwggEKAoIBAQDM9xBiT6a7Y2/tkFJWxW0nd3oSVorx9PnW5+GPvZWr8mBBFXDT
EgD6Jwq1VzhbfbJRk3GVDmpBlFs1G/p7+rvFviQw/lbvxPN9l+MU9RRNy6cQ8hbq
qyLwMSIRYWmQJrp42Zcf431Wq3VElXPIrP/vXQqKWUPhrLI6D/NI/NdrN8Fj3N5G
1ttF/n0j/ZDoUQceUaNf7UlGVH8siMX0E5yXFTwD6KE53GsMMsFvFldMlEdCfKLI
nH3m1E1Ur0KZqMEEwnec1kjkzhHgKoCZ8ENwzz92a9FMSaskXsINgv1GqKtsk8xi
UkJ1kvie+l5esrBh5R8fuX8JmOg9+oN/R2mhAgMBAAGjggGCMIIBfjASBgNVHRMB
Af8ECDAGAQH/AgEAMB0GA1UdDgQWBBR0hYDAZsffN97PvSk3qgMdvu3NFzAfBgNV
HSMEGDAWgBROIlQgGJXm427mD/r6uRLtBhePOTAOBgNVHQ8BAf8EBAMCAYYwHQYD
VR0lBBYwFAYIKwYBBQUHAwEGCCsGAQUFBwMCMHYGCCsGAQUFBwEBBGowaDAkBggr
BgEFBQcwAYYYaHR0cDovL29jc3AuZGlnaWNlcnQuY29tMEAGCCsGAQUFBzAChjRo
dHRwOi8vY2FjZXJ0cy5kaWdpY2VydC5jb20vRGlnaUNlcnRHbG9iYWxSb290RzIu
Y3J0MEIGBgNVHR8EOzA5MDegNaAzhjFodHRwOi8vY3JsMy5kaWdpY2VydC5jb20v
RGlnaUNlcnRHbG9iYWxSb290RzIuY3JsMD0GA1UdIAQ2MDQwCwYJYIZIAYb9bAIB
MAcGBWeHDAEBMAgGBmeBDAECATAIBgZngQwBAgIwCAYGZ4EMAQIDMAoGCSqGSIb3
DQELBQADggEBAJDxcMsil2XXfHT9wPomeFOu7M1b4bkGqyJrTioh9U1TVpTt3cW1
BSAuWdH/SvWgKtiwla3JLko716f2b4gp/DA/JIS7w7d7kwcsr4drdjPtAFVSslme
5LnQ89/nD/7d+MS5EHKBCQRfz5eeLjJ1js+aWNJXMX43AYGyZm0pGrFmCW3RbpD0
ufovARTFXFZkAdl9h6g4U5+LXUZtXMYnhIHUfoyMo5tS58aI7Dd8KvvwVVo4chDY
ABPPTHPbqjc1qCmBaZx2vN4Ye5DUys/vZwP9BFohFrH/6j/f3IL16/RZkiMNJCqV
JUzKoZHm1Lesh3Sz8W2jmdv51b2EQJ8HmA==
-----END CERTIFICATE-----)";

const char* mqttServer = "mqtt3.thingspeak.com";
const int mqttPort = 8883;


char subscribeTopic[64];

WiFiClientSecure wifiClient;
PubSubClient mqtt(wifiClient);

// --- DOOR STATE ---
enum DoorState { DOOR_IDLE, A_TRIGGERED, B_TRIGGERED };
DoorState currentState = DOOR_IDLE;
unsigned long stateEnteredAt = 0;
unsigned long lastEventAt = 0;
unsigned long lastMqttPublish = 0;
int peopleCount = 0;
bool countChanged = true;

int debounceA = 0;
int debounceB = 0;
int confirmHits = 0;

// KEYPAD STATE 
int concentrationRating = -1;
bool resetDoneToday = false;


//  handles incoming fan commands

void callback(char* topic, byte* payload, unsigned int length) {
    Serial.print("Message received on topic: ");
    Serial.println(topic);

    String message = "";
    for (int i = 0; i < length; i++) {
        message += (char)payload[i];
    }
    Serial.print("Payload: ");
    Serial.println(message);

    int fanCommand = message.toInt();
    if (fanCommand == 1) {
        digitalWrite(FAN_PIN, HIGH);
        Serial.println("Fan turned ON");
    } else if (fanCommand == 0) {
        digitalWrite(FAN_PIN, LOW);
        Serial.println("Fan turned OFF");
    }
}


// KEYPAD HANDLER
// Press 1-9 for rating, A for 10

void handleKeypad() {
    char key = keypad.getKey();
    if (!key) return;

    if (key >= '1' && key <= '9') {
        concentrationRating = key - '0';
        countChanged = true;
        Serial.printf(">>> Concentration rating set to: %d\n", concentrationRating);
    } else if (key == 'A') {
        concentrationRating = 10;
        countChanged = true;
        Serial.printf(">>> Concentration rating set to: 10\n");
    }

}


// DISTANCE SENSORR

long readDistanceCm(int trigPin, int echoPin) {
    digitalWrite(trigPin, LOW);
    delayMicroseconds(2);
    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);

    long duration = pulseIn(echoPin, HIGH, SENSOR_TIMEOUT_US);
    if (duration == 0) return 999;
    return duration * 0.034 / 2;
}

// WIFI + MQTT

void connectWiFi() {
    Serial.print("Connecting to WiFi");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 40) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    if (WiFi.status() == WL_CONNECTED) {
        Serial.print("\nWiFi connected! IP: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\nWiFi FAILED — continuing offline");
    }
}

void connectMQTT() {
    if (WiFi.status() != WL_CONNECTED) return;
    wifiClient.setCACert(ca_cert);
    mqtt.setServer(mqttServer, mqttPort);
    mqtt.setCallback(callback);

    Serial.print("Connecting to ThingSpeak MQTT...");
    if (mqtt.connect(TS_MQTT_CLIENT, TS_MQTT_USER, TS_MQTT_PASS)) {
        Serial.println(" connected!");
        // Subscribe to fan command channel
        mqtt.subscribe(subscribeTopic);
        Serial.print("Subscribed to: ");
        Serial.println(subscribeTopic);
    } else {
        Serial.print(" failed, rc=");
        Serial.println(mqtt.state());
    }
}


// MQTT PUBLISH
// field1 = people count
// field2 = concentration rating (if set)
// Publishes to TS_CHANNEL_ID (3278561)

void publishData() {
    if (!mqtt.connected()) connectMQTT();
    if (!mqtt.connected()) return;

    char topic[64];
    snprintf(topic, sizeof(topic), "channels/%d/publish", TS_CHANNEL_ID_NODE2);

    char payload[128];
    if (concentrationRating >= 0) {
        snprintf(payload, sizeof(payload), "field1=%d&field2=%d", peopleCount, concentrationRating);
        concentrationRating = -1;
    } else {
        snprintf(payload, sizeof(payload), "field1=%d", peopleCount);
    }

    if (mqtt.publish(topic, payload)) {
        Serial.print("MQTT published: ");
        Serial.println(payload);
    } else {
        Serial.println("MQTT publish failed");
    }
}


// SETUP

void setup() {
    Serial.begin(115200);
    delay(500);

    // Build subscribe topic from secrets
    snprintf(subscribeTopic, sizeof(subscribeTopic), 
             "channels/%d/subscribe/fields/field1", TS_FAN_CHANNEL_ID);

    pinMode(TRIG_A, OUTPUT);
    pinMode(ECHO_A, INPUT);
    pinMode(TRIG_B, OUTPUT);
    pinMode(ECHO_B, INPUT);

    pinMode(FAN_PIN, OUTPUT);
    digitalWrite(FAN_PIN, LOW);  // Fan off by default

    Serial.println("=== People Counter + Concentration Rating + Fan Control ===");
    Serial.println("Keypad: press 1-9 for rating, A for 10");
    Serial.println("Sensor A (inner): TRIG=20, ECHO=19");
    Serial.println("Sensor B (outer): TRIG=7,  ECHO=6");
    Serial.println("Fan pin: GPIO 4");

    connectWiFi();
    configTime(0, 0, "pool.ntp.org");
    connectMQTT();
}

unsigned long lastDebugPrint = 0;


// LOOP

void loop() {
    // Keep MQTT alive + process incoming fan commands
    if (!mqtt.connected()) {
        connectMQTT();
    }
    mqtt.loop();

    // 4 AM daily reset (non-blocking, 0ms timeout)
    struct tm timeinfo;
    if (getLocalTime(&timeinfo, 0)) {
        if (timeinfo.tm_hour == 4 && !resetDoneToday) {
            peopleCount = 0;
            countChanged = true;
            resetDoneToday = true;
            Serial.println("4 AM reset — count set to 0");
        }
        if (timeinfo.tm_hour != 4) resetDoneToday = false;
    }

    // Always check keypad
    handleKeypad();

    long distA = readDistanceCm(TRIG_A, ECHO_A);
    long distB = readDistanceCm(TRIG_B, ECHO_B);

    bool rawA = distA < DETECTION_THRESHOLD_CM;
    bool rawB = distB < DETECTION_THRESHOLD_CM;

    if (rawA) debounceA++; else debounceA = 0;
    if (rawB) debounceB++; else debounceB = 0;

    bool sensorA = debounceA >= DEBOUNCE_COUNT;
    bool sensorB = debounceB >= DEBOUNCE_COUNT;

    unsigned long now = millis();

    // Debug output
    if (now - lastDebugPrint > 500) {
        Serial.printf("A: %ld cm | B: %ld cm | People: %d | Rating: %s\n",
            distA, distB, peopleCount,
            concentrationRating != -1 ? String(concentrationRating).c_str() : "not set");
        lastDebugPrint = now;
    }

    // Publish when count or rating changed (rate-limited to 15s)
    if (countChanged && (now - lastMqttPublish) > MQTT_INTERVAL_MS) {
        publishData();
        lastMqttPublish = now;
        countChanged = false;
    }

    // Reconnect WiFi if dropped
    if (WiFi.status() != WL_CONNECTED && (now % 30000) < 20) {
        connectWiFi();
    }

    // Cooldown after a people-counting event
    if ((now - lastEventAt) < COOLDOWN_MS && lastEventAt != 0) {
        delay(20);
        return;
    }

    // People counting state machine
    switch (currentState) {
        case DOOR_IDLE:
            if (sensorA && !sensorB) {
                currentState = A_TRIGGERED;
                stateEnteredAt = now;
                confirmHits = 0;
            } else if (sensorB && !sensorA) {
                currentState = B_TRIGGERED;
                stateEnteredAt = now;
                confirmHits = 0;
            }
            break;

        case A_TRIGGERED:
            if (rawB) confirmHits++;
            if (confirmHits >= CONFIRM_HITS) {
                peopleCount--;
                if (peopleCount < 0) peopleCount = 0;
                Serial.printf("EXIT  -> Count: %d\n", peopleCount);
                currentState = DOOR_IDLE;
                lastEventAt = now;
                debounceA = 0; debounceB = 0; confirmHits = 0;
                countChanged = true;
            } else if ((now - stateEnteredAt) > STATE_TIMEOUT_MS) {
                Serial.println("Timeout (A only) - resetting");
                currentState = DOOR_IDLE;
                confirmHits = 0;
            }
            break;

        case B_TRIGGERED:
            if (rawA) confirmHits++;
            if (confirmHits >= CONFIRM_HITS) {
                peopleCount++;
                if (peopleCount > 3) peopleCount = 3;
                Serial.printf("ENTER -> Count: %d\n", peopleCount);
                currentState = DOOR_IDLE;
                lastEventAt = now;
                debounceA = 0; debounceB = 0; confirmHits = 0;
                countChanged = true;
            } else if ((now - stateEnteredAt) > STATE_TIMEOUT_MS) {
                Serial.println("Timeout (B only) - resetting");
                currentState = DOOR_IDLE;
                confirmHits = 0;
            }
            break;
    }

    delay(20);
}