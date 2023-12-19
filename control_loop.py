import os
import json
import requests
import configparser
import paho.mqtt.client as mqtt
from datetime import datetime

# Config variables
PROGRAM_PATH = os.path.dirname(os.path.realpath(__file__))
config = configparser.ConfigParser()
config.read(PROGRAM_PATH + '/control_loop.conf')
token_endpoint = config.get('mqtt', 'AUTH_ENDPOINT')
mqtt_endpoint = config.get('mqtt', 'BROKER_ENDPOINT')
mqtt_port = config.getint('mqtt', 'BROKER_PORT')
auth_client_id = config.get('mqtt', 'AUTH_CLIENT_ID')
auth_client_secret = config.get('mqtt', 'AUTH_CLIENT_SECRET')


class ControlLoopHandler():
    """Handles parameter changes through MQTT messages."""
    
    def __init__(self, det_component_id: str, starting_params: dict):
        """Initializes ControlLoopHandler.
        
        det_component_id (str): An identifier of the DET component to be used as the MQTT topic.
        starting_params: A dictionary of all parameters to be handled and their initial values.
        """
        # 'info' is a reserved word and cannot be used as a det name
        if det_component_id == 'info':
            raise ValueError('\'info\' name is reserved. Choose any other.')

        # Basic parameters
        self.__client = mqtt.Client()
        self.__token = ''
        self.__token_expiry_time = 0
        self.__params = starting_params
        self.__mqtt_topic = det_component_id + '/#'
        # Request parameters
        self.__headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        self.__data = {
            'grant_type': 'client_credentials',
            'client_id': auth_client_id,
            'client_secret': auth_client_secret,
            'scope': 'salted'
        }

    def __on_message(self, client, userdata, message):
        """Reconfigure one or more parameters on request."""
        topic = message.topic
        app_id = "/".join(topic.split("/")[1:])

        # Give info on request
        if topic.startswith("info/"):
            response = {
                'det_component_id': "/".join(self.__mqtt_topic.split("/")[:-1]),
                'params': self.__params
            }
            self.__client.publish(app_id, json.dumps(response))
            return

        # Check JSON validity
        try:
            params = json.loads(message.payload)
        except Exception:
            response = {'error': 'Reconfiguration not applied. Reason: message received is not a valid JSON.'}
            self.__client.publish(app_id, json.dumps(response))
            return
        if not isinstance(params, dict):
            response = {'error': 'Reconfiguration not applied. Reason: message received is not a valid JSON.'}
            self.__client.publish(app_id, json.dumps(response))
            return

        # Check at least one param is valid
        if self.__params.keys().isdisjoint(params.keys()):
            response = {'error': 'Reconfiguration not applied. Reason: No valid parameters found.'}
            self.__client.publish(app_id, json.dumps(response))
            return

        # Apply reconfiguration
        response = dict()
        for name, value in params.items():
            if name not in self.__params.keys(): continue
            self.__params[name] = value
            response[name] = value
        self.__client.publish(app_id, json.dumps(response))

    def __on_disconnect(self, client, userdata, rc):
        """Update token after a disconnection to avoid trouble with automatic reconnections."""
        self.update_token()
        self.__client.username_pw_set(self.__token)
        
    def update_token(self) -> None:
        """Update token if the current one has expired."""
        if (self.__token_expiry_time > datetime.timestamp(datetime.now())): return
        res = requests.post(token_endpoint, headers=self.__headers, data=self.__data)
        res_dict = json.loads(res.text)
        res.close()
        if "access_token" not in res_dict:
            raise RuntimeError("Access token could not be obtained. Credentials might be invalid.")
        self.__token = res_dict["access_token"]
        self.__token_expiry_time = datetime.timestamp(datetime.now()) + res_dict["expires_in"] - 10

    def start(self) -> None:
        """Start listening for parameter change requests."""
        self.update_token()
        self.__client.username_pw_set(self.__token)
        self.__client.on_message = self.__on_message
        self.__client.on_disconnect = self.__on_disconnect
        self.__client.tls_set()
        self.__client.connect(mqtt_endpoint, mqtt_port, 60)
        self.__client.subscribe(self.__mqtt_topic)
        self.__client.subscribe('info/#')
        self.__client.loop_start()

    def stop(self) -> None:
        """Stop listening for parameter change requests."""
        self.__client.loop_stop()
        self.__client.disconnect()

    def get_param(self, param_name: str):
        """Get current value of a parameter.
        
        param_name (str): The name of said parameter.
        """
        if param_name not in self.__params:
            return None
        else:
            return self.__params[param_name]

    def set_param(self, param_name: str, param_value) -> bool:
        """Manually change the current value of a parameter.
        
        param_name (str): The name of the parameter.
        param_value: The new value of the parameter.
        """
        if param_name not in self.__params:
            return False
        else:
            self.__params[param_name] = param_value
            return True

    def add_param(self, param_name: str, param_value) -> None:
        """Add a new parameter.
        
        param_name (str): The name of the new parameter.
        param_value: The starting value of the new parameter.
        """
        self.__params[param_name] = param_value
