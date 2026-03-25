#include <Arduino.h>
#include <SensirionI2cScd30.h>
#include <Wire.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include "../secrets.h"

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

String publishTopic = "channels/" + String(TS_CHANNEL_ID_NODE1) + "/publish";

#define SDA_PIN 41
#define SCL_PIN 42

SensirionI2cScd30 sensor;
static int16_t error;

WiFiClientSecure wifiClient;
PubSubClient mqttClient(wifiClient);

// --- MQTT Reconnect ---
void reconnectMQTT() {
    while (!mqttClient.connected()) {
        Serial.print("Connecting to ThingSpeak MQTT...");
        if (mqttClient.connect(TS_MQTT_CLIENT, TS_MQTT_USER, TS_MQTT_PASS)) {
            Serial.println(" connected!");
        } else {
            Serial.printf(" failed, rc=%d. Retrying in 5s...\n", mqttClient.state());
            delay(5000);
        }
    }
}

void setup() {
    Serial.begin(115200);
    while (!Serial) delay(100);

    // 1. Connect to Wi-Fi
    Serial.print("Connecting to Wi-Fi");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWi-Fi connected!");

    // 2. Configure MQTT client
    wifiClient.setCACert(ca_cert);
    mqttClient.setServer(mqttServer, mqttPort);

    // 3. Initialize the SCD30 Sensor
    Wire.begin(SDA_PIN, SCL_PIN);
    sensor.begin(Wire, SCD30_I2C_ADDR_61);
    sensor.stopPeriodicMeasurement();
    sensor.softReset();
    delay(2000);
    sensor.startPeriodicMeasurement(0);
}

void loop() {
    // Maintain MQTT connection
    if (!mqttClient.connected()) {
        reconnectMQTT();
    }
    mqttClient.loop();

    float co2 = 0.0;
    float temp = 0.0;
    float hum = 0.0;

    // Read data from the sensor
    error = sensor.blockingReadMeasurementData(co2, temp, hum);

    if (error == 0) {
        Serial.printf("CO2: %.2f ppm | Temp: %.2f C | Hum: %.2f %%\n", co2, temp, hum);

        // Build ThingSpeak MQTT payload
        // field1=CO2, field2=Humidity, field3=Temperature
        String payload = "field1=" + String(co2, 2) +
                         "&field2=" + String(hum, 2) +
                         "&field3=" + String(temp, 2);

        // Publish to ThingSpeak
        if (mqttClient.publish(publishTopic.c_str(), payload.c_str())) {
            Serial.println("MQTT publish successful: " + payload);
        } else {
            Serial.println("MQTT publish failed.");
        }

    } else {
        Serial.println("Failed to read from SCD30 sensor.");
    }

    // ThingSpeak requires a minimum of 15 seconds between updates
    delay(15000);
}