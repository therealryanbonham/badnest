import requests

API_URL = "https://home.nest.com"
CAMERA_WEBAPI_BASE = "https://webapi.camera.home.nest.com"
CAMERA_URL = "https://nexusapi-us1.camera.home.nest.com"


class NestAPI:
    def __init__(self, email, password):
        self._user_id = None
        self._access_token = None
        self._session = requests.Session()
        self._session.headers.update({"Referer": "https://home.nest.com/"})
        self._device_id = None
        self._login(email, password)
        self.update()

    def _login(self, email, password):
        r = self._session.post(
            f"{API_URL}/session", json={"email": email, "password": password}
        )
        self.user_id = r.json()["userid"]
        self._access_token = r.json()["access_token"]

    def update(self):
        raise NotImplementedError()


class NestThermostatAPI(NestAPI):
    def __init__(self, email, password):
        super(NestThermostatAPI, self).__init__(email, password)
        self._shared_id = None
        self._czfe_url = None
        self._compressor_lockout_enabled = None
        self._compressor_lockout_time = None
        self._hvac_ac_state = None
        self._hvac_heater_state = None
        self.mode = None
        self._time_to_target = None
        self._fan_timer_timeout = None
        self.can_heat = None
        self.can_cool = None
        self.has_fan = None
        self.fan = None
        self.away = None
        self.current_temperature = None
        self.target_temperature = None
        self.target_temperature_high = None
        self.target_temperature_low = None
        self.current_humidity = None

    def get_action(self):
        if self._hvac_ac_state:
            return "cooling"
        elif self._hvac_heater_state:
            return "heating"
        else:
            return "off"

    def update(self):
        r = self._session.post(
            f"{API_URL}/api/0.1/user/{self._user_id}/app_launch",
            json={
                "known_bucket_types": ["shared", "device"],
                "known_bucket_versions": [],
            },
            headers={"Authorization": f"Basic {self._access_token}"},
        )

        self._czfe_url = r.json()["service_urls"]["urls"]["czfe_url"]

        for bucket in r.json()["updated_buckets"]:
            if bucket["object_key"].startswith("shared."):
                self._shared_id = bucket["object_key"]
                thermostat_data = bucket["value"]
                self.current_temperature = \
                    thermostat_data["current_temperature"]
                self.target_temperature = thermostat_data["target_temperature"]
                self._compressor_lockout_enabled = thermostat_data[
                    "compressor_lockout_enabled"
                ]
                self._compressor_lockout_time = thermostat_data[
                    "compressor_lockout_timeout"
                ]
                self._hvac_ac_state = thermostat_data["hvac_ac_state"]
                self._hvac_heater_state = thermostat_data["hvac_heater_state"]
                self.mode = thermostat_data["target_temperature_type"]
                self.target_temperature_high = thermostat_data[
                    "target_temperature_high"
                ]
                self.target_temperature_low = \
                    thermostat_data["target_temperature_low"]
                self.can_heat = thermostat_data["can_heat"]
                self.can_cool = thermostat_data["can_cool"]
            elif bucket["object_key"].startswith("device."):
                self._device_id = bucket["object_key"]
                thermostat_data = bucket["value"]
                self._time_to_target = thermostat_data["time_to_target"]
                self._fan_timer_timeout = thermostat_data["fan_timer_timeout"]
                self.has_fan = thermostat_data["has_fan"]
                self.fan = thermostat_data["fan_timer_timeout"] > 0
                self.current_humidity = thermostat_data["current_humidity"]
                self.away = thermostat_data["home_away_input"]

    def set_temp(self, temp, temp_high=None):
        if temp_high is None:
            self._session.post(
                f"{self._czfe_url}/v5/put",
                json={
                    "objects": [
                        {
                            "object_key": self._shared_id,
                            "op": "MERGE",
                            "value": {"target_temperature": temp},
                        }
                    ]
                },
                headers={"Authorization": f"Basic {self._access_token}"},
            )
        else:
            self._session.post(
                f"{self._czfe_url}/v5/put",
                json={
                    "objects": [
                        {
                            "object_key": self._shared_id,
                            "op": "MERGE",
                            "value": {
                                "target_temperature_low": temp,
                                "target_temperature_high": temp_high,
                            },
                        }
                    ]
                },
                headers={"Authorization": f"Basic {self._access_token}"},
            )

    def set_mode(self, mode):
        self._session.post(
            f"{self._czfe_url}/v5/put",
            json={
                "objects": [
                    {
                        "object_key": self._shared_id,
                        "op": "MERGE",
                        "value": {"target_temperature_type": mode},
                    }
                ]
            },
            headers={"Authorization": f"Basic {self._access_token}"},
        )

    def set_fan(self, date):
        self._session.post(
            f"{self._czfe_url}/v5/put",
            json={
                "objects": [
                    {
                        "object_key": self._device_id,
                        "op": "MERGE",
                        "value": {"fan_timer_timeout": date},
                    }
                ]
            },
            headers={"Authorization": f"Basic {self._access_token}"},
        )

    def set_eco_mode(self):
        self._session.post(
            f"{self._czfe_url}/v5/put",
            json={
                "objects": [
                    {
                        "object_key": self._device_id,
                        "op": "MERGE",
                        "value": {"eco": {"mode": "manual-eco"}},
                    }
                ]
            },
            headers={"Authorization": f"Basic {self._access_token}"},
        )


class NestCameraAPI(NestAPI):
    def __init__(self, email, password):
        super(NestCameraAPI, self).__init__(email, password)
        # log into dropcam
        self._session.post(
            f"{API_URL}/dropcam/api/login",
            data={"access_token": self._access_token}
        )
        self.location = None
        self.name = "Nest Camera"
        self.online = None
        self.is_streaming = None
        self.battery_voltage = None
        self.ac_voltge = None
        self.data_tier = None

    def set_device(self, uuid):
        self._device_id = uuid
        self.update()

    def update(self):
        if self._device_id:
            props = self.get_properties()
            self._location = None
            self.name = props["name"]
            self.online = props["is_online"]
            self.is_streaming = props["is_streaming"]
            self.battery_voltage = props["rq_battery_battery_volt"]
            self.ac_voltge = props["rq_battery_vbridge_volt"]
            self.location = props["location"]
            self.data_tier = props["properties"]["streaming.data-usage-tier"]

    def _set_properties(self, property, value):
        r = self._session.post(
            f"{CAMERA_WEBAPI_BASE}/api/dropcams.set_properties",
            data={property: value, "uuid": self._device_id},
        )

        return r.json()["items"]

    def get_properties(self):
        r = self._session.get(
            f"{API_URL}/dropcam/api/cameras/{self._device_id}"
        )
        return r.json()[0]

    def get_cameras(self):
        r = self._session.get(
            f"{CAMERA_WEBAPI_BASE}/api/cameras."
            + "get_owned_and_member_of_with_properties"
        )
        return r.json()["items"]

    # def set_upload_quality(self, quality):
    #     quality = str(quality)
    #     return self._set_properties("streaming.data-usage-tier", quality)

    def turn_off(self):
        return self._set_properties("streaming.enabled", "false")

    def turn_on(self):
        return self._set_properties("streaming.enabled", "true")

    def get_image(self, now):
        r = self._session.get(
            f"{CAMERA_URL}/get_image?uuid={self._device_id}&cachebuster={now}"
        )

        return r.content
