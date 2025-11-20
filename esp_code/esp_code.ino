#include <WiFi.h>
#include <WebServer.h>

// ================= CONFIGURATION =================
const char* ssid = "tirtharaj50_fpkhr_2.4G";     // UPDATE IF NEEDED
const char* password = "Nepal@9806555163";    // UPDATE IF NEEDED

IPAddress local_IP(192, 168, 1, 214);     // STATIC IP
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 255, 0);

const int IN1 = 26; const int IN2 = 25;
const int IN3 = 33; const int IN4 = 32;
const int TRIG = 5; const int ECHO = 18;

WebServer server(80);
String currentAction = "STOP";

// ================= MOTOR FUNCTIONS =================
void stopMotors() {
  digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW); digitalWrite(IN4, LOW);
  currentAction = "STOP";
}
void moveForward() {
  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
  digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);
  currentAction = "FORWARD";
}
void moveBackward() {
  digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH);
  digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH);
  currentAction = "BACKWARD";
}
void turnLeft() {
  digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
  digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);
  currentAction = "LEFT";
}
void turnRight() {
  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW); digitalWrite(IN4, LOW);
  currentAction = "RIGHT";
}

// ================= SERVER =================
void handleCommand() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  if (!server.hasArg("action")) return server.send(400, "text/plain", "Missing action");
  String action = server.arg("action");
  
  if (action == "forward") moveForward();
  else if (action == "backward") moveBackward();
  else if (action == "left") turnLeft();
  else if (action == "right") turnRight();
  else stopMotors();
  
  server.send(200, "text/plain", "OK");
}

void setup() {
  Serial.begin(115200);
  pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT);
  
  if (!WiFi.config(local_IP, gateway, subnet)) Serial.println("STA Failed");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) delay(500);
  
  server.on("/cmd", handleCommand);
  server.begin();
}

void loop() {
  server.handleClient();
}