import json
import logging
from threading import Lock
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

class Device:
    """Представление одного устройства"""
    def __init__(self, friendly_name, ieee_addr=None, model=None):
        self.friendly_name = friendly_name
        self.ieee_addr = ieee_addr
        self.model = model
        self.state = {}
        self._lock = Lock()

    def update_state(self, payload):
        with self._lock:
            self.state = payload

    def get_state(self):
        with self._lock:
            return dict(self.state)

class MqttManager:
    def __init__(self, broker_host="localhost", broker_port=1883, base_topic="zigbee2mqtt"):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.base_topic = base_topic
        self.devices = {}          # friendly_name -> Device
        self.devices_lock = Lock()
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self._message_callback = None  # будет установлен извне для WebSocket

    def set_message_callback(self, callback):
        """Функция, вызываемая при обновлении любого устройства (для SocketIO)"""
        self._message_callback = callback

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            logger.info("MQTT: подключено")
            # Подписываемся на все устройства и на список устройств
            client.subscribe(f"{self.base_topic}/#")
            logger.info(f"Подписка на {self.base_topic}/#")
            # Запрашиваем список устройств (Zigbee2MQTT сам пришлёт)
            client.publish(f"{self.base_topic}/bridge/request/devices", json.dumps({}))
        else:
            logger.error(f"MQTT: ошибка подключения {reason_code}")

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        payload_str = msg.payload.decode()
        try:
            payload = json.loads(payload_str)
        except:
            return

        # Обработка списка устройств
        if topic == f"{self.base_topic}/bridge/devices":
            for dev in payload:
                friendly = dev.get("friendly_name")
                if friendly:
                    with self.devices_lock:
                        if friendly not in self.devices:
                            self.devices[friendly] = Device(
                                friendly_name=friendly,
                                ieee_addr=dev.get("ieee_address"),
                                model=dev.get("model_id")
                            )
                            logger.info(f"Обнаружено устройство: {friendly}")
            if self._message_callback:
                self._message_callback("devices_updated", None)
            return

        # Обработка состояния конкретного устройства
        if topic.startswith(f"{self.base_topic}/") and not topic.endswith("/set") and not "bridge" in topic:
            parts = topic.split("/")
            if len(parts) >= 2:
                friendly = parts[1]
                with self.devices_lock:
                    if friendly in self.devices:
                        self.devices[friendly].update_state(payload)
                        if self._message_callback:
                            self._message_callback("state_updated", friendly)
                    else:
                        # Новое устройство? Добавим на лету
                        self.devices[friendly] = Device(friendly_name=friendly)
                        self.devices[friendly].update_state(payload)
                        logger.info(f"Новое устройство из топика: {friendly}")
                        if self._message_callback:
                            self._message_callback("state_updated", friendly)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        logger.warning(f"MQTT: отключено, код {reason_code}")

    def start(self):
        self.client.connect(self.broker_host, self.broker_port, keepalive=60)
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

    def get_all_devices(self):
        with self.devices_lock:
            return {name: dev.get_state() for name, dev in self.devices.items()}

    def get_device_state(self, friendly_name):
        with self.devices_lock:
            dev = self.devices.get(friendly_name)
            return dev.get_state() if dev else {}

    def send_command(self, friendly_name, command):
        """Отправить JSON-команду устройству"""
        topic = f"{self.base_topic}/{friendly_name}/set"
        self.client.publish(topic, json.dumps(command))
        logger.info(f"Команда {command} -> {friendly_name}")

    def send_group_command(self, group_devices, command):
        """Отправить команду списку устройств (группа)"""
        for dev in group_devices:
            self.send_command(dev, command)