import logging
import sys
import requests
import simplejson

from time import sleep

API_URL = "https://home.nest.com"
CAMERA_WEBAPI_BASE = "https://webapi.camera.home.nest.com"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/75.0.3770.100 Safari/537.36"
)
URL_JWT = "https://nestauthproxyservice-pa.googleapis.com/v1/issue_jwt"

# Nest website's (public) API key
NEST_API_KEY = "AIzaSyAdkSIMNc51XGNEAYWasX9UOWkS5P6sZE4"

KNOWN_BUCKET_TYPES = [
    # Thermostats
    "device",
    "shared",
    # Protect
    "topaz",
    # Temperature sensors
    "kryptonite",
]

REQUEST_TIMEOUT = 30

_LOGGER = logging.getLogger(__name__)
# _LOGGER.setLevel(logging.DEBUG)


class NestAPI:
    def __init__(self, user_id, access_token, issue_token, cookie, region):
        self.device_data = {}
        self._wheres = {}
        self._user_id = user_id
        self._access_token = access_token
        self._session = requests.Session()
        self._session.headers.update(
            {"Referer": "https://home.nest.com/", "User-Agent": USER_AGENT,}
        )
        self._issue_token = issue_token
        self._cookie = cookie
        self._czfe_url = None
        self._camera_url = f"https://nexusapi-{region}1.camera.home.nest.com"
        self.cameras = []
        self.thermostats = []
        self.temperature_sensors = []
        self.protects = []
        if self.login():
            self._get_devices()
            self.update()
            for camera in self.cameras:
                self.update_camera(camera)

    def __getitem__(self, name):
        return getattr(self, name)

    def __setitem__(self, name, value):
        return setattr(self, name, value)

    def __delitem__(self, name):
        return delattr(self, name)

    def __contains__(self, name):
        return hasattr(self, name)

    def _call_nest_api(
        self,
        method,
        url,
        headers,
        json=None,
        params=None,
        data=None,
        is_retry=False,
        is_json=True,
    ):
        try:
            if method == "get":
                r = self._session.get(
                    url=url,
                    headers=headers,
                    params=params,
                    json=json,
                    data=data,
                    timeout=REQUEST_TIMEOUT,
                )
            elif method == "post":
                r = self._session.post(
                    url=url,
                    headers=headers,
                    params=params,
                    json=json,
                    data=data,
                    timeout=REQUEST_TIMEOUT,
                )
            else:
                _LOGGER.error("Unsupported Method: {}".format(method))
        except requests.exceptions.RequestException as e:
            _LOGGER.error(e)
            _LOGGER.error("Failed Calling: {}\nMethod: {}".format(url, method))
        except KeyError:
            if is_retry:
                _LOGGER.error(
                    "KeyError Retry Failed Calling: {}\nMethod: {}".format(url, method)
                )
            else:
                _LOGGER.error(
                    "KeyError Failed Calling: {}\nMethod: {}".format(url, method)
                )
                if self.login():
                    if "Authorization" in headers:
                        headers["Authorization"] = f"Basic {self._access_token}"
                    return self._call_nest_api(
                        method,
                        url,
                        headers,
                        json=json,
                        params=params,
                        data=data,
                        is_retry=True,
                        is_json=is_json,
                    )
        else:
            # Parse Json
            if r.status_code == 200:
                try:
                    if is_json:
                        api_response = r.json()
                    else:
                        api_response = r.content
                except simplejson.errors.JSONDecodeError as e:
                    _LOGGER.error(
                        "API Response: JsonDecodeError: return code {} and returned text {}  for url {}".format(
                            r.text, r.status_code, url
                        )
                    )
                else:
                    return api_response
            elif r.status_code != 200 and r.status_code not in (502, 401):
                _LOGGER.error(
                    "Bad API Response: Information for further debugging: return code {} and returned text {} for url {}".format(
                        r.status_code, r.text, url
                    )
                )
            elif r.status_code == 401:
                if is_retry:
                    _LOGGER.error(
                        "401 Retry Failed Calling: {}\nMethod: {}".format(url, method)
                    )
                else:
                    _LOGGER.error(
                        "401 Failed Calling: {}\nMethod: {}".format(url, method)
                    )
                    if self.login():
                        if "Authorization" in headers:
                            headers["Authorization"] = f"Basic {self._access_token}"
                        return self._call_nest_api(
                            method,
                            url,
                            headers,
                            json=json,
                            params=params,
                            data=data,
                            is_retry=True,
                            is_json=is_json,
                        )
            else:
                _LOGGER.error("502 API Response for url {}".format(url))
        return False

    def login(self):
        status = False
        if self._issue_token and self._cookie:
            status = self._login_google(self._issue_token, self._cookie)
            if not status:
                _LOGGER.error("Login To Google Failes")
        else:
            _LOGGER.error("Issue Token and Cookie Not Set. Unable To Auth To Google")
        return status

    def _login_google(self, issue_token, cookie):
        headers = {
            "User-Agent": USER_AGENT,
            "Sec-Fetch-Mode": "cors",
            "X-Requested-With": "XmlHttpRequest",
            "Referer": "https://accounts.google.com/o/oauth2/iframe",
            "cookie": cookie,
        }
        r = self._call_nest_api(method="get", url=issue_token, headers=headers)
        if not r:
            _LOGGER.error("Failed Getting Access Token")
            return False
        else:
            access_token = r["access_token"]

            headers = {
                "User-Agent": USER_AGENT,
                "Authorization": "Bearer " + access_token,
                "x-goog-api-key": NEST_API_KEY,
                "Referer": "https://home.nest.com",
            }
            params = {
                "embed_google_oauth_access_token": True,
                "expire_after": "3600s",
                "google_oauth_access_token": access_token,
                "policy_id": "authproxy-oauth-policy",
            }
            r = self._call_nest_api(
                method="post", url=URL_JWT, headers=headers, params=params
            )
            if not r:
                _LOGGER.error("Failed Getting JWT")
                return False
            else:
                self._user_id = r["claims"]["subject"]["nestId"]["id"]
                self._access_token = r["jwt"]
        return True

    def _get_cameras(self):
        cameras = []
        headers = {
            "User-Agent": USER_AGENT,
            "X-Requested-With": "XmlHttpRequest",
            "Referer": "https://home.nest.com/",
            "cookie": f"user_token={self._access_token}",
        }

        r = self._call_nest_api(
            method="get",
            url=f"{CAMERA_WEBAPI_BASE}/api/cameras."
            + "get_owned_and_member_of_with_properties",
            headers=headers,
        )
        if not r:
            _LOGGER.error("Failed Getting Owned Cameras")
            return False
        else:
            for camera in r["items"]:
                cameras.append(camera["uuid"])
                self.device_data[camera["uuid"]] = {}
        return cameras

    def _get_devices(self):
        url = f"{API_URL}/api/0.1/user/{self._user_id}/app_launch"
        json = {
            "known_bucket_types": ["buckets"],
            "known_bucket_versions": [],
        }
        headers = {"Authorization": f"Basic {self._access_token}"}
        r = self._call_nest_api(method="post", url=url, json=json, headers=headers)
        if not r:
            _LOGGER.error("Failed Getting czfe url and buckets")
            return False

        self._czfe_url = r["service_urls"]["urls"]["czfe_url"]

        buckets = r["updated_buckets"][0]["value"]["buckets"]
        for bucket in buckets:
            if bucket.startswith("topaz."):
                sn = bucket.replace("topaz.", "")
                self.protects.append(sn)
                self.device_data[sn] = {}
            elif bucket.startswith("kryptonite."):
                sn = bucket.replace("kryptonite.", "")
                self.temperature_sensors.append(sn)
                self.device_data[sn] = {}
            elif bucket.startswith("device."):
                sn = bucket.replace("device.", "")
                self.thermostats.append(sn)
                self.temperature_sensors.append(sn)
                self.device_data[sn] = {}
        cameras = self._get_cameras()
        if cameras is not False:
            self.cameras = cameras
        return True

    def _map_nest_protect_state(self, value):
        if value == 0:
            return "Ok"
        elif value == 1 or value == 2:
            return "Warning"
        elif value == 3:
            return "Emergency"
        else:
            return "Unkown"

    def update_camera(self, camera):
        headers = {
            "User-Agent": USER_AGENT,
            "X-Requested-With": "XmlHttpRequest",
            "Referer": "https://home.nest.com/",
            "cookie": f"cztoken={self._access_token}",
        }
        url = f"{API_URL}/dropcam/api/cameras/{camera}"
        r = self._call_nest_api(method="get", url=url, headers=headers)
        if not r:
            _LOGGER.error("Failed Getting camers")
            return
        else:
            sensor_data = r[0]
            self.device_data[camera]["name"] = sensor_data["name"]
            self.device_data[camera]["is_online"] = sensor_data["is_online"]
            self.device_data[camera]["is_streaming"] = sensor_data["is_streaming"]
            self.device_data[camera]["battery_voltage"] = sensor_data[
                "rq_battery_battery_volt"
            ]
            self.device_data[camera]["ac_voltage"] = sensor_data[
                "rq_battery_vbridge_volt"
            ]
            self.device_data[camera]["location"] = sensor_data["location"]
            self.device_data[camera]["data_tier"] = sensor_data["properties"][
                "streaming.data-usage-tier"
            ]

    def update(self):
        # To get friendly names
        APP_LAUNCH_URL = f"{API_URL}/api/0.1/user/{self._user_id}/app_launch"
        APP_LAUNCH_HEADERS = {"Authorization": f"Basic {self._access_token}"}
        APP_LAUNCH_JSON = {
            "known_bucket_types": ["where"],
            "known_bucket_versions": [],
        }
        r = self._call_nest_api(
            method="post",
            url=APP_LAUNCH_URL,
            json=APP_LAUNCH_JSON,
            headers=APP_LAUNCH_HEADERS,
        )
        if not r:
            _LOGGER.error("Failed Calling App Launch")
            return False
        buckets = r["updated_buckets"]
        for bucket in buckets:
            sensor_data = bucket["value"]
            sn = bucket["object_key"].split(".")[1]
            if bucket["object_key"].startswith(f"where.{sn}"):
                wheres = sensor_data["wheres"]
                for where in wheres:
                    self._wheres[where["where_id"]] = where["name"]

        APP_LAUNCH_JSON = {
            "known_bucket_types": KNOWN_BUCKET_TYPES,
            "known_bucket_versions": [],
        }
        r = self._call_nest_api(
            method="post",
            url=APP_LAUNCH_URL,
            json=APP_LAUNCH_JSON,
            headers=APP_LAUNCH_HEADERS,
        )
        if not r:
            _LOGGER.error("Failed Calling App Launch")
            return False

        buckets = r["updated_buckets"]
        for bucket in buckets:
            sensor_data = bucket["value"]
            sn = bucket["object_key"].split(".")[1]
            # Thermostats (thermostat and sensors system)
            if bucket["object_key"].startswith(f"shared.{sn}"):
                self.device_data[sn]["current_temperature"] = sensor_data[
                    "current_temperature"
                ]
                self.device_data[sn]["target_temperature"] = sensor_data[
                    "target_temperature"
                ]
                self.device_data[sn]["hvac_ac_state"] = sensor_data["hvac_ac_state"]
                self.device_data[sn]["hvac_heater_state"] = sensor_data[
                    "hvac_heater_state"
                ]
                self.device_data[sn]["target_temperature_high"] = sensor_data[
                    "target_temperature_high"
                ]
                self.device_data[sn]["target_temperature_low"] = sensor_data[
                    "target_temperature_low"
                ]
                self.device_data[sn]["can_heat"] = sensor_data["can_heat"]
                self.device_data[sn]["can_cool"] = sensor_data["can_cool"]
                self.device_data[sn]["mode"] = sensor_data["target_temperature_type"]
                if self.device_data[sn]["hvac_ac_state"]:
                    self.device_data[sn]["action"] = "cooling"
                elif self.device_data[sn]["hvac_heater_state"]:
                    self.device_data[sn]["action"] = "heating"
                else:
                    self.device_data[sn]["action"] = "off"
            # Thermostats, pt 2
            elif bucket["object_key"].startswith(f"device.{sn}"):
                self.device_data[sn]["name"] = self._wheres[sensor_data["where_id"]]
                # When acts as a sensor
                if "backplate_temperature" in sensor_data:
                    self.device_data[sn]["temperature"] = sensor_data[
                        "backplate_temperature"
                    ]
                if "battery_level" in sensor_data:
                    self.device_data[sn]["battery_level"] = sensor_data["battery_level"]

                if sensor_data.get("description", None):
                    self.device_data[sn]["name"] += f' ({sensor_data["description"]})'
                self.device_data[sn]["name"] += " Thermostat"
                self.device_data[sn]["has_fan"] = sensor_data["has_fan"]
                self.device_data[sn]["fan"] = sensor_data["fan_timer_timeout"]
                self.device_data[sn]["current_humidity"] = sensor_data[
                    "current_humidity"
                ]
                self.device_data[sn]["target_humidity"] = sensor_data["target_humidity"]
                self.device_data[sn]["target_humidity_enabled"] = sensor_data[
                    "target_humidity_enabled"
                ]
                if (
                    sensor_data["eco"]["mode"] == "manual-eco"
                    or sensor_data["eco"]["mode"] == "auto-eco"
                ):
                    self.device_data[sn]["eco"] = True
                else:
                    self.device_data[sn]["eco"] = False
            # Protect
            elif bucket["object_key"].startswith(f"topaz.{sn}"):
                self.device_data[sn]["name"] = self._wheres[sensor_data["where_id"]]
                if sensor_data.get("description", None):
                    self.device_data[sn]["name"] += f' ({sensor_data["description"]})'
                self.device_data[sn]["name"] += " Protect"
                self.device_data[sn]["co_status"] = self._map_nest_protect_state(
                    sensor_data["co_status"]
                )
                self.device_data[sn]["smoke_status"] = self._map_nest_protect_state(
                    sensor_data["smoke_status"]
                )
                self.device_data[sn][
                    "battery_health_state"
                ] = self._map_nest_protect_state(sensor_data["battery_health_state"])
            # Temperature sensors
            elif bucket["object_key"].startswith(f"kryptonite.{sn}"):
                self.device_data[sn]["name"] = self._wheres[sensor_data["where_id"]]
                if sensor_data.get("description", None):
                    self.device_data[sn]["name"] += f' ({sensor_data["description"]})'
                self.device_data[sn]["name"] += " Temperature"
                self.device_data[sn]["temperature"] = sensor_data["current_temperature"]
                if sensor_data.get("description", None):
                    self.device_data[sn]["name"] += f' ({sensor_data["description"]})'
                self.device_data[sn]["name"] += " Temperature"
                self.device_data[sn]["temperature"] = sensor_data["current_temperature"]
                self.device_data[sn]["battery_level"] = sensor_data["battery_level"]
        return self.device_data

    def thermostat_set_temperature(self, device_id, temp, temp_high=None):
        if device_id not in self.thermostats:
            _LOGGER.error(
                f"Failed Setting Thermostat Temperature, Invalid Device ID: {device_id}"
            )
            return False
        url = f"{self._czfe_url}/v5/put"
        headers = {"Authorization": f"Basic {self._access_token}"}
        if temp_high is None:
            json = {
                "objects": [
                    {
                        "object_key": f"shared.{device_id}",
                        "op": "MERGE",
                        "value": {"target_temperature": temp},
                    }
                ]
            }
        else:
            json = {
                "objects": [
                    {
                        "object_key": f"shared.{device_id}",
                        "op": "MERGE",
                        "value": {
                            "target_temperature_low": temp,
                            "target_temperature_high": temp_high,
                        },
                    }
                ]
            }
        r = self._call_nest_api(method="post", url=url, json=json, headers=headers)
        if not r:
            _LOGGER.error("Failed Setting Thermostat Temperature")
            return False
        return True

    def thermostat_set_target_humidity(self, device_id, humidity):
        _LOGGER.error(
            f"Failed Setting Thermostat Humidity, Invalid Device ID: {device_id}"
        )
        if device_id not in self.thermostats:
            return False
        url = f"{self._czfe_url}/v5/put"
        json = {
            "objects": [
                {
                    "object_key": f"device.{device_id}",
                    "op": "MERGE",
                    "value": {"target_humidity": humidity},
                }
            ]
        }
        headers = {"Authorization": f"Basic {self._access_token}"}
        r = self._call_nest_api(method="post", url=url, json=json, headers=headers)
        if not r:
            _LOGGER.error("Failed Setting Thermostat Humidity")
            return False
        return True

    def thermostat_set_mode(self, device_id, mode):
        if device_id not in self.thermostats:
            _LOGGER.error(
                f"Failed Setting Thermostat Mode, Invalid Device ID: {device_id}"
            )
            return False
        url = f"{self._czfe_url}/v5/put"
        json = {
            "objects": [
                {
                    "object_key": f"shared.{device_id}",
                    "op": "MERGE",
                    "value": {"target_temperature_type": mode},
                }
            ]
        }
        headers = {"Authorization": f"Basic {self._access_token}"}
        r = self._call_nest_api(method="post", url=url, json=json, headers=headers)
        if not r:
            _LOGGER.error("Failed Setting Thermostat Mode")
            return False
        return True

    def thermostat_set_fan(self, device_id, date):
        if device_id not in self.thermostats:
            _LOGGER.error(
                f"Failed Setting Thermostat Fan, Invalid Device ID: {device_id}"
            )
            return False
        url = f"{self._czfe_url}/v5/put"
        json = {
            "objects": [
                {
                    "object_key": f"device.{device_id}",
                    "op": "MERGE",
                    "value": {"fan_timer_timeout": date},
                }
            ]
        }
        headers = {"Authorization": f"Basic {self._access_token}"}
        r = self._call_nest_api(method="post", url=url, json=json, headers=headers)
        if not r:
            _LOGGER.error("Failed Setting Thermostat Mode")
            return False
        return True

    def thermostat_set_eco_mode(self, device_id, state):
        if device_id not in self.thermostats:
            _LOGGER.error(
                f"Failed Setting Thermostat Eco Mode, Invalid Device ID: {device_id}"
            )
            return False
        mode = "manual-eco" if state else "schedule"
        url = f"{self._czfe_url}/v5/put"
        json = {
            "objects": [
                {
                    "object_key": f"device.{device_id}",
                    "op": "MERGE",
                    "value": {"eco": {"mode": mode}},
                }
            ]
        }
        headers = {"Authorization": f"Basic {self._access_token}"}
        r = self._call_nest_api(method="post", url=url, json=json, headers=headers)
        if not r:
            _LOGGER.error("Failed Setting Thermostat Eco Mode")
            return False
        return True

    def _camera_set_properties(self, device_id, property, value):
        if device_id not in self.cameras:
            _LOGGER.error(
                f"Failed Setting Camera Properties, Invalid Device ID: {device_id}"
            )
            return False

        headers = {
            "User-Agent": USER_AGENT,
            "X-Requested-With": "XmlHttpRequest",
            "Referer": "https://home.nest.com/",
            "cookie": f"user_token={self._access_token}",
        }
        url = f"{CAMERA_WEBAPI_BASE}/api/dropcams.set_properties"
        data = {property: value, "uuid": device_id}
        r = self._call_nest_api(method="get", url=url, data=data, headers=headers)
        if not r:
            _LOGGER.error("Failed Setting Thermostat Eco Mode")
            return False
        return r["items"]

    def camera_turn_off(self, device_id):

        return self._camera_set_properties(device_id, "streaming.enabled", "false")

    def camera_turn_on(self, device_id):

        return self._camera_set_properties(device_id, "streaming.enabled", "true")

    def camera_get_image(self, device_id, now):
        if device_id not in self.cameras:
            _LOGGER.error(f"Failed to get camera Image, Invalid Device ID: {device_id}")
            return False
        headers = {
            "User-Agent": USER_AGENT,
            "X-Requested-With": "XmlHttpRequest",
            "Referer": "https://home.nest.com/",
            "cookie": f"user_token={self._access_token}",
        }
        url = f"{self._camera_url}/get_image?uuid={device_id}&cachebuster={now}"
        r = self._call_nest_api(method="get", url=url, headers=headers, is_json=False)
        if not r:
            _LOGGER.error("Failed Getting Camera Image")
            return False
        return r
