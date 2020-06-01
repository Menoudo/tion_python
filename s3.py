if __package__ == "":
    from tion import tion
else:
    from . import tion

from bluepy import btle
import time


class s3(tion):
    uuid = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
    uuid_write = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
    uuid_notify = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
    write = None
    notify = None
    statuses = ['off', 'on']
    modes = ['recirculation', 'mixed']
    _btle = None

    command_prefix = 61
    command_suffix = 90

    command_PAIR = 5
    command_REQUEST_PARAMS = 1
    command_SET_PARAMS = 2

    def __init__(self, mac: str):
        self._btle = btle.Peripheral(None)
        self._mac = mac

    @property
    def mac(self):
        return self.mac

    def pair(self):
        self._btle.connect(self.mac, btle.ADDR_TYPE_RANDOM)
        characteristic = self._btle.getServiceByUUID(self.uuid).getCharacteristics()[0]
        characteristic.write(bytes(self._get_pair_command()))
        self._btle.disconnect()

    def create_command(self, command: int) -> bytearray:
        command_special = 1 if command == self.command_PAIR else 0
        return bytearray([self.command_prefix, command, command_special, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                          self.command_suffix])

    def _get_pair_command(self) -> bytearray:
        return self.create_command(self.command_PAIR)

    def _get_status_command(self) -> bytearray:
        return self.create_command(self.command_REQUEST_PARAMS)

    def _process_mode(self, mode_code: int) -> str:
        try:
            result = self.modes[mode_code]
        except IndexError:
            result = 'outside'
        return result

    def _encode_mode(self, mode: str) -> int:
        return self.modes.index(mode) if mode in self.modes else 2

    def _encode_status(self, status: str) -> int:
        return self.statuses.index(status) if status in self.statuses else 0

    def _process_status(self, code: int) -> str:
        try:
            result = self.statuses[code]
        except IndexError:
            result = 'unknown'
        return result

    def _encode_request(self, request: dict) -> bytearray:
        try:
            if request["fan_speed"] == 0:
                del request["fan_speed"]
                reqest["status"] = "off"
        except KeyError:
            pass

        settings = {**self.get(False), **request}
        new_settings = self.create_command(self.command_SET_PARAMS)
        new_settings[2] = settings["fan_speed"]
        new_settings[3] = settings["heater_temp"]
        new_settings[4] = self._encode_mode(settings["mode"])
        new_settings[5] = self._encode_status(settings["heater"]) | (self._encode_status(settings["status"]) << 1) | (
                    self._encode_status(settings["sound"]) << 3)
        return new_settings

    def _decode_response(self, response: bytearray) -> dict:
        try:
            result = {"code": 200, "heater": self._process_status(response[4] & 1),
                "status": self._process_status(response[4] >> 1 & 1),
                "sound": self._process_status(response[4] >> 3 & 1),
                "mode": self._process_mode(int(list("{:02x}".format(response[2]))[0])),
                "fan_speed": int(list("{:02x}".format(response[2]))[1]), "heater_temp": response[3],
                "in_temp": self.decode_temperature(response[8]), "out_temp": self.decode_temperature(response[7]),
                "filter_remain": response[10] * 256 + response[9], "time": "{}:{}".format(response[11], response[12]),
                "request_error_code": response[13], "fw_version": "{:02x}{:02x}".format(response[16], response[17])}
        except IndexError as e:
            result = {"code": 400, "error": "Got bad response from Tion '%s': %s while parsing" % (response, str(e))}
        finally:
            return result

    def _connect(self, new_connection=True):
        if new_connection:
            self._btle.connect(self.mac, btle.ADDR_TYPE_RANDOM)
            for tc in self._btle.getCharacteristics():
                if tc.uuid == self.uuid_notify:
                    self.notify = tc
                if tc.uuid == self.uuid_write:
                    self.write = tc

    def get(self, new_connection=True) -> dict:
        response = ""
        self._connect(new_connection)  # new_connection processed inside

        self.notify.read()
        self.write.write(self._get_status_command())
        response = self._btle.getServiceByUUID(self.uuid).getCharacteristics()[0].read()

        if new_connection:
            self._btle.disconnect()
        return self._decode_response(response)

    def set(self, request: dict):
        self._connect()
        self.notify.read()
        self.write.write(self._encode_request(request))
        self._btle.disconnect()
