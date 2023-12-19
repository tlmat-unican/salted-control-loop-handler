# SALTED - Control Loop Handler

ControlLoopHandler is a Python class intended to ease the development of DET components that use the control loop mechanism envisioned in SALTED. It is aimed at partners working on WP2 and WP4 activities, but may also be of use to external users developing DET components.

This repository comprises 4 files:
- *control_loop.py* is the main script. It is meant to be imported from a DET component and used directly.
- *control_loop.conf* is a configuration file required for the main script to know the locations of the MQTT broker and the token endpoint, as well as the credentials to obtain a valid token from the latter.
- *requirements.txt* is the standard file listing the PyPI packages to be installed.
- *README.md* is this documentation.

## Installation

1. Install the required packages in your Python 3 environment:
```bash
pip install -r requirements.txt
```
2. Move *control_loop.py* and *control_loop.conf* to the working directory of your DET component.

3. Update *control_loop.conf* with your credentials.

## Usage

First, import the ControlLoopHandler class from your DET component and instantiate an object. It has to be initialized with an identifier and a set of parameters to be modified through the control loop.

```python
from control_loop import ControlLoopHandler

det_id = "example_id"
params = {
    "example_param_1": 20,
    "example_param_2": "abc"
}

det_clh = ControlLoopHandler(det_id, params)
```

Calling the *start* method will connect to the MQTT broker and subscribe to the corresponding topic (*[det_id]/#*).

```python
det_clh.start()
```

Afterwards, you can access the updated value of any parameter with the *get_param* method.

```python
new_value = det_clh.get_param("example_param_1")
```

Finally, you can disconnect from the MQTT broker by calling the *stop* method.

```python
det_clh.stop()
```

Methods *update_token*, *set_param* and *add_param* are also available for your needs.

## Application side

Applications can send requests to the DET components using the control loop mechanism. To do so, they can send an MQTT message to the *[det_id]/[app_id]* topic and the DET component will send an acknowledgement message to the *[app_id]* topic. As an example, using Python:

```python
import paho.mqtt.client as mqtt

client = mqtt.Client()
...
client.subscribe(app_id) 
client.publish(det_id+'/'+app_id, msg)
```

The payload must be a valid JSON. The keys are the names of the parameters to be modified, and the values correspond to the new values of those parameters. For instance:

```json
{
    "example_param_1": 10,
    "example_param_2": "cba",
    "example_param_3": 2.3
}
```

The acknowledgement message sent by the DET component after the reconfiguration will also be a JSON. If an error has ocurred:

```json
{
    "error": "Description of the error"
}
```

If no error has ocurred, the JSON payload will contain the parameters that have been successfully reconfigured:

```json
{
    "example_param_1": 10,
    "example_param_2": "cba"
}
```

Additionally, for discoverability purposes, applications can send a message to the *info/[app_id]* topic. The payload will not be checked. All DET components currently connected to the MQTT broker will send a message to the [app_id] topic with basic information about their identifier and customizable parameters. This example is one such possible message:

```json
{
    "det_component_id": "example_id",
    "params": {
        "example_param_1": 10,
        "example_param_2": "cba"
    }
}
```

## Acknowledgement
This work was supported by the European Commission CEF Programme by means of the project SALTED ‘‘Situation-Aware Linked heTerogeneous Enriched Data’’ under the Action Number 2020-EU-IA-0274.

## License
This material is licensed under the GNU Lesser General Public License v3.0 whose full text may be found at the *LICENSE* file.