#!/usr/bin/env python

import json
import os

import paho.mqtt.publish as publish
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from pyModbusTCP.client import ModbusClient

SMA_HOST = os.getenv("SMA_HOST")
SMA_PORT = os.getenv("SMA_PORT", 502)
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = os.getenv("MQTT_BROKER_PORT", 1883)
MQTT_PUBLISH_TOPIC = os.getenv("MQTT_PUBLISH_TOPIC", "energy/solar/sma")


class SmaModbusProtocol:

    # Modes
    MODBUS_PROTOCOL_MODE = 3  # SMA implementation of modbus

    # Total return
    DATA = 30529

    # DC Power
    DCV = 30771
    DCA = 30769
    DCP = 30773
    
    # AC Power
    ACP = 30775
    ACP1 = 30777
    ACP2 = 30779
    ACP3 = 30781

    # Other
    OUT_TEMP = 34609
    NET_FREQUENCY = 31447


class SmaDataType:
    def get_value(self, data):
        bpd = BinaryPayloadDecoder.fromRegisters(data, byteorder=Endian.Big, wordorder=Endian.Big)
        value = self.get_decoded(bpd)
        if value == self.get_nan_value():
            return None
        return value

    def get_nan_value(self):
        raise NotImplementedError("Use one one of the subclasses\
         that define what the nan value is")

    def get_decoded(self, bpd):
        raise NotImplementedError("Use one one of the subclasses\
         that define how this datatype needs to be decoded")


class U32(SmaDataType):
    def get_decoded(self, bpd):
        return bpd.decode_32bit_uint()

    def get_nan_value(self):
        return 0xffffffff


class S32(SmaDataType):
    def get_decoded(self, bpd):
        return bpd.decode_32bit_int()

    def get_nan_value(self):
        return -0x80000000


class SmaClient:

    READ_VALUES = {
        'total_return': (SmaModbusProtocol.DATA, 0.001, 'kWh', U32),
        'dc_a': (SmaModbusProtocol.DCA, 0.001, 'A', S32),
        'dc_v': (SmaModbusProtocol.DCV, 0.01, 'V', S32),
        'dc_p': (SmaModbusProtocol.DCP, 1.0, 'W', S32),
        'ac_p': (SmaModbusProtocol.ACP, 1.0, 'W', S32),
        'ac_p1': (SmaModbusProtocol.ACP1, 1.0, 'W', S32),
        'ac_p2': (SmaModbusProtocol.ACP2, 1.0, 'W', S32),
        'ac_p3': (SmaModbusProtocol.ACP3, 1.0, 'W', S32),
        # 'net_frequency': (SmaModbusProtocol.NET_FREQUENCY, 1.0, 'Hz', U32)
    }

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.c = ModbusClient(
            host=host,
            port=port,
            unit_id=SmaModbusProtocol.MODBUS_PROTOCOL_MODE,
            auto_open=True, 
            auto_close=True
        )
        self.read_data()
    
    def read_data(self):
        self.values = {}
        self.human_readable_values = {}

        for dimension in SmaClient.READ_VALUES:
            register, multiplier, unit, dt = SmaClient.READ_VALUES[dimension]
            data = self.c.read_holding_registers(register, 2)
            value = dt().get_value(data)
            self.human_readable_values[dimension] = f"{value} {unit}"
            self.values[dimension] = value


def publish_on_mqtt():
    sma = SmaClient(SMA_HOST, SMA_PORT)
    result = {k:v for k,v in sma.values.items() if v is not None}
    print(f"Sending '{MQTT_PUBLISH_TOPIC}': {result}")
    publish.single(MQTT_PUBLISH_TOPIC, json.dumps(result), hostname=MQTT_BROKER_HOST)


if __name__ == '__main__':
    publish_on_mqtt()
