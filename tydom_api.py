""" provides all connection to the tydom box """
#!/usr/bin/env python
# from tydom_api import get_device_info
import asyncio
import websockets
import aiohttp
import os
import logging
import json
import base64

# import time
from io import BytesIO
from http.client import HTTPResponse
from http.server import BaseHTTPRequestHandler
import urllib3
import ssl

from requests.auth import HTTPDigestAuth
from .tydomclimate import TydomClimate

ENDPOINT = None

# loop = asyncio.get_event_loop()
loop = asyncio.new_event_loop()

_LOGGER = logging.getLogger(__name__)


class Tydom:
    """ class to manage all calls to the Tydom box """

    _hass = None

    def __init__(self, hass, host, username, password, comfort, saving, away):
        self._mac = username
        self._password = password
        self._host = host
        # self._host = "mediation.tydom.com"
        self.comfort = comfort
        self.saving = saving
        self.away = away
        if self._host == "mediation.tydom.com":
            self._remote = True
            self.cmd_prefix = "\x02"
            self._ssl_context = True
        else:
            self._remote = False
            self.cmd_prefix = ""
            self._ssl_context = ssl._create_unverified_context()

        Tydom._hass = hass
        self._ws = None
        self._climates = {}
        self._task = None
        self._not_ready = True

    def build_digest_headers(self, nonce):
        """ no clue what this is doing """
        digestauth = HTTPDigestAuth(self._mac, self._password)
        chal = dict()
        chal["nonce"] = nonce[2].split("=", 1)[1].split('"')[1]
        chal["realm"] = "ServiceMedia"
        chal["qop"] = "auth"
        digestauth._thread_local.chal = chal
        digestauth._thread_local.last_nonce = nonce
        digestauth._thread_local.nonce_count = 1
        a_temp = digestauth.build_digest_header(
            "GET",
            "https://{}:443/mediation/client?_mac={}&appli=1".format(
                self._host, self._mac
            ),
        )
        return a_temp

    def getinfo(self, device_id, value):
        """ take the value of a specific setting of a specific thermostat and return it """
        # _LOGGER.debug(
        #     "getinfo %s %s =%s",
        #     self._climates[device_id]["name"],
        #     value,
        #     self._climates[device_id][value],
        # )
        return self._climates[device_id][value]

    async def _async_auth(self):
        """ no clue """
        headers_info = {
            "Connection": "Upgrade",
            "Upgrade": "websocket",
            "Host": self._host + ":443",
            "Accept": "*/*",
            "Sec-WebSocket-Key": generate_random_key(),
            "Sec-WebSocket-Version": "13",
            # "Content-Length": "0",
            # "Content-Type": "application/json",
            # "Transac-Id": "0",
        }
        s_url = f"https://{self._host}/mediation/client?mac={self._mac}&appli=1"
        try:
            async with aiohttp.ClientSession(headers=headers_info) as session:
                # async with session.get(s_url, ssl=websocket_ssl_context) as resp:
                async with session.get(s_url, ssl=self._remote) as resp:
                    # async with session.get(s_url) as resp:
                    nonce = resp.headers["WWW-Authenticate"].split(",", 3)
            return {"Authorization": self.build_digest_headers(nonce)}
        except Exception as inst:
            _LOGGER.debug("Error in Auth %s", type(inst))

    async def async_connect(self, msg=""):
        """initiate websocket connection with a tydom box
        msg = message to appear in the debug log"""

        if self._ws is not None:
            if self._ws.open:
                return
        _LOGGER.debug("Opening connection %s", msg)
        auth = await self._async_auth()
        if not self._remote:
            websocket_ssl_context = self._ssl_context
        else:
            websocket_ssl_context = True  # Verify certificate
        uri = "wss://{}:443/mediation/client?mac={}&appli=1".format(
            self._host, self._mac
        )
        self._ws = await websockets.connect(
            uri,
            extra_headers=auth,
            ssl=websocket_ssl_context,
            timeout=5,
            ping_interval=None,
        )
        if self._task is None:
            self._task = self._hass.loop.create_task(self._async_loop_received_data())

    async def _async_get(self, cmd_msg):
        """ send an HTTP GET message to the tydom box """
        mstr = (
            self.cmd_prefix
            + "GET "
            + cmd_msg
            + " HTTP/1.1\r\nContent-Length: 0\r\nContent-Type: application/json; charset=UTF-8\r\nTransac-Id: 0\r\n\r\n"
        )
        if not self._ws.open:
            await self.async_connect()
        _LOGGER.debug("HTTP GET: %s", cmd_msg)
        await self._ws.send(bytes(mstr, "ascii"))

    async def _async_loop_received_data(self):
        """ call to websocket """
        # uri = "ws://localhost:8765"
        _LOGGER.debug("Entering event loop")
        await self.async_connect("Entering loop")
        while True:
            try:
                recv_data = ""
                while recv_data == "":
                    # _LOGGER.debug("Event loop: Waiting data")
                    try:
                        await self.async_connect("Listen loop")
                        recv_data = ""
                        recv_data = await asyncio.wait_for(self._ws.recv(), timeout=35)
                    except websockets.ConnectionClosedError as inst:
                        await self.async_connect("ConnectionClosed Error")
                    except websockets.ConnectionClosed:
                        await self.async_connect("Connection closed")
                    except asyncio.TimeoutError:
                        _LOGGER.debug("Loop event - time out : send refresh")
                        await self._async_post_message("/refresh/all")
                    else:
                        await self._async_process_data(recv_data)
            except Exception as inst:
                _LOGGER.debug("Error in _loop_received_data %s", type(inst))
                _LOGGER.debug("Recv_data: %s", recv_data)
        return

    async def _async_extract_device_data(self, response):
        _vals = ["temperature", "authorization", "hvacMode", "setpoint"]
        # avoid re-entrance issue - skipped data

        elements = json.loads(response)
        try:
            for element in elements:
                data = {}
                for endpoint in element["endpoints"]:
                    for value in endpoint["data"]:
                        if value["name"] in _vals:
                            endpoint_id = endpoint["id"]
                            data["endpoint"] = endpoint_id
                            data[value["name"]] = value["value"]
                            # data["validity"] = value["validity"]
                # if isinstance(self._climates[endpoint_id]["tydom"], str):
                #     _LOGGER.debug(
                #         "Create new instance for %s",
                #         self._climates[endpoint_id]["name"],
                #     )
                #     self._climates[endpoint_id]["tydom"] = TydomClimate(
                #         data["endpoint"],
                #         self._climates[endpoint_id]["name"],
                #         self,
                #     )
                #     for inf in data:
                #         self._climates[endpoint_id][inf] = data[inf]
                # else:
                _LOGGER.debug(
                    "Receive update for %s", self._climates[endpoint_id]["name"]
                )
                _is_updated = False
                for info in data:
                    if info != "endpoint":
                        try:
                            if self._climates[endpoint_id][info] != data[info]:
                                self._climates[endpoint_id][info] = data[info]
                                _is_updated = True
                                # push update
                                _LOGGER.debug(
                                    "%s %s updated",
                                    self._climates[endpoint_id]["name"],
                                    info,
                                )
                        except KeyError:
                            # climate not yet initialized
                            self._climates[endpoint_id][info] = data[info]
                if _is_updated:
                    self._climates[endpoint_id]["tydom"].async_write_ha_state()

        except Exception as inst:
            _LOGGER.debug("Error in extract_device_data %s", type(inst))
            _LOGGER.debug("Data: %s", response)
        return

    async def _async_post_message(self, msg):
        # ensure connection is opened
        # _LOGGER.debug("POST message %s", msg)
        await self.async_connect()
        mstr = (
            self.cmd_prefix
            + "POST "
            + msg
            + " HTTP/1.1\r\nContent-Length: 0\r\nContent-Type: application/json; charset=UTF-8\r\nTransac-Id: 0\r\n\r\n"
        )
        a_bytes = bytes(mstr, "ascii")
        await self._ws.send(a_bytes)

    def _parse_put_response(self, bytes_str):
        resp = bytes_str[len(self.cmd_prefix) :].decode("utf-8")
        fields = resp.split("\r\n")
        fields = fields[6:]  # ignore the PUT / HTTP/1.1
        end_parsing = False
        i = 0
        output = str()
        while not end_parsing:
            field = fields[i]
            if len(field) == 0 or field == "0":
                end_parsing = True
            else:
                output += field
                i = i + 2
        parsed = json.loads(output)
        return json.dumps(parsed)

    def _extract_config(self, response):

        elements = json.loads(response)
        for endpoint in elements["endpoints"]:
            endpoint_id = endpoint["id_endpoint"]
            self._climates[endpoint_id] = {}
            self._climates[endpoint_id]["name"] = endpoint["name"]

            _LOGGER.debug(
                "Create new instance for %s",
                self._climates[endpoint_id]["name"],
            )

            self._climates[endpoint_id]["tydom"] = TydomClimate(
                endpoint_id,
                self._climates[endpoint_id]["name"],
                self,
            )

    async def _async_process_data(self, recv_data):
        """ annalyse data received from the websocket """
        msg_type = str(recv_data)

        if "/devices/data" in msg_type:
            _LOGGER.debug("Received /device/data")
            if "PUT" in msg_type:
                response = self._parse_put_response(recv_data)
            else:
                response = response_from_bytes(recv_data[len(self.cmd_prefix) :])
            await self._async_extract_device_data(response)
            self._not_ready = False
            return
        if "/configs/file" in msg_type:
            _LOGGER.debug("Received /configs/file")
            response = response_from_bytes(recv_data[len(self.cmd_prefix) :])
            self._extract_config(response)
            return
        if "HTTP/1.1 200 OK" in msg_type:
            # _LOGGER.debug("Received HTTP/1.1 200 message - ignored")
            return
        if "refresh" in msg_type:
            _LOGGER.debug("Received REFRESH message - ignored")
            return
        _LOGGER.debug("###############################")
        _LOGGER.debug("Houston? We have a problem: %s", msg_type)

    async def _async_put_data(self, endpoint_id, name, value):
        """ no clue """
        if self._ws is None:
            await self.async_connect()
        body = '[{"name":"' + name + '","value":"' + str(value) + '"}]'

        req = (
            self.cmd_prefix
            + "PUT /devices/{}/endpoints/{}/data HTTP/1.1\r\nContent-Length: ".format(
                str(endpoint_id), str(endpoint_id)
            )
            + str(len(body))
            + "\r\nContent-Type: application/json; charset=UTF-8\r\nTransac-Id: 0\r\n\r\n"
            + body
            + "\r\n\r\n"
        )
        a_bytes = bytes(req, "ascii")
        if not self._ws.open:
            await self.async_connect()
        await self._ws.send(a_bytes)
        # bytes_str = await self._ws.recv()
        # response_from_bytes(bytes_str[len(self.cmd_prefix) :])
        # check response?????

    async def _async_get_all(self):
        # await self.__refresh_all()
        await self._async_get("/configs/file")
        await self._async_get("/devices/data")

    async def async_system_info(self):
        """ Get information from the tydombox """
        _LOGGER.info("system_info")
        if self._ws is None:
            await self.async_connect("System info")
        await self._async_get_all()
        return

    async def async_get_entities(self):
        """ wait until the get config and get data returns """
        tyd = []
        while self._not_ready:
            await asyncio.sleep(5)
        for clim in self._climates:
            tyd.append(self._climates[clim]["tydom"])
        return tyd

    def set_temp(self, endpoint_id, temp):
        """ send the new target temperature to the tydom box """
        self._hass.loop.create_task(self._async_put_data(endpoint_id, "setpoint", temp))

    def set_hvac_mode(self, endpoint_id, state):
        """ send the new hvac mode to the tydom box """
        self._hass.loop.create_task(
            self._async_put_data(endpoint_id, "authorization", state)
        )


class HTTPRequest(BaseHTTPRequestHandler):
    """ no clue """

    def __init__(self, request_text):
        # self.rfile = StringIO(request_text)
        self.raw_requestline = request_text
        self.error_code = self.error_message = self.error_explanation = None
        self.parse_request()

    def send_error(self, code: int, message: str, explain: str):
        self.error_code = code
        self.error_message = message
        self.error_explanation = explain


class BytesIOSocket:
    """ no clue """

    def __init__(self, content):
        self.handle = BytesIO(content)

    def makefile(self, mode):
        """ return the handle """
        return self.handle


def generate_random_key():
    """ return a base64 encoded key """
    return base64.b64encode(os.urandom(16)).decode("utf8")


def response_from_bytes(data):
    """ translate response from bytes to string """
    sock = BytesIOSocket(data)
    response = HTTPResponse(sock)
    response.begin()
    return urllib3.HTTPResponse.from_httplib(response).data.decode("utf-8")


def put_response_from_bytes(data):
    """ no clue """
    request = HTTPRequest(data)
    return request
