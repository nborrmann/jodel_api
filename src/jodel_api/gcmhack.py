from __future__ import (absolute_import, print_function, unicode_literals)
from future.utils import raise_from

import sys
import random
import requests
import string
import time
import ssl
import socket
import varint
import json
from jodel_api.protos import checkin_pb2
from jodel_api.protos import mcs_pb2
import select
import struct

class GcmException(Exception):
    pass


class AndroidAccount:
    sock = None
    responseTag = 0

    def __init__(self, android_id=None, security_token=None, **kwargs):
        self.session = requests.Session()

        if android_id and security_token:
            self.android_id = android_id
            self.security_token = security_token

        else:
            try:
                self._google_checkin(**kwargs)
            except:
                raise

    def _google_checkin(self, **kwargs):
        # most minimal checkin request possible
        cr = checkin_pb2.CheckinRequest()
        cr.checkin.build.sdkVersion = 18
        cr.version = 3
        cr.fragment = 0

        data = cr.SerializeToString()
        headers = {"Content-type": "application/x-protobuffer",
                   "Accept-Encoding": "gzip",
                   "User-Agent": "Android-Checkin/2.0 (vbox86p JLS36G); gzip"}
        r = self.session.post("https://android.clients.google.com/checkin", headers=headers, data=data, **kwargs)

        if r.status_code == 200:
            cresp = checkin_pb2.CheckinResponse()
            cresp.ParseFromString(r.content)
            self.android_id, self.security_token = cresp.androidId, cresp.securityToken
        else:
            raise GcmException(r.text)

    def get_push_token(self, **kwargs):
        headers = {"Authorization": "AidLogin {}:{}".format(self.android_id, self.security_token)}

        data = {'app': 'com.tellm.android.app',
                'app_ver': '1001800',
                'cert': 'a4a8d4d7b09736a0f65596a868cc6fd620920fb0',
                'device': str(self.android_id),
                'sender': '425112442765',
                'X-appid': "".join(random.choice(string.ascii_letters + string.digits) for _ in range(11)),
                'X-scope': 'GCM' }

        r = self.session.post("https://android.clients.google.com/c2dm/register3", headers=headers, data=data, **kwargs)
        if r.status_code == 200 and "token" in r.text:
            return r.text.split("=")[1]
        else:
            raise GcmException(r.text)

    def receive_verification_from_gcm(self, retry=True):
        # Return the last verification_code that we receive.
        # Note: We cannot return on the first verification_code because the server sometimes sends
        # the same code twice.
        self._establish_connection()
        verification_data = None

        try:
            while True:
                # Sometimes the server sends a response_tag and length but doesn't send the actual content,
                # so we need to remeber them and read just the content on the next call.
                if not self.responseTag:
                    self.responseTag = ord(self._rcv_exact(1))
                    self.length = varint.decode_stream(self.sock)
                
                msg = self._rcv_exact(self.length)
                self.counter += 1

                if self.responseTag == 3:
                    pass # login

                elif self.responseTag == 4:
                    raise Exception("socket closed by server")

                elif self.responseTag == 8:
                    dms = mcs_pb2.DataMessageStanza()
                    dms.ParseFromString(msg)

                    message_type, data = "", None
                    for app_data in dms.app_data:
                        if app_data.key == "message_type_id":
                            message_type = app_data.value
                        elif app_data.key == "payload":
                            data = app_data.value

                    if dms.category == "com.tellm.android.app" and message_type == "16":
                        verification_data = data

                self.responseTag, self.length = 0, 0

        except socket.timeout:
            self._gcm_send_heartbeat()
        except Exception:
            # maybe the socket was closed because we timed out in between calls or 
            # the connection was interrupted. We close the socket and try to reopen.
            try:
                self.sock.close()
            except:
                pass
            self.sock = None

            if retry:
                return self.receive_verification_from_gcm(False)
            else:
                raise

        try:
            d = json.loads(verification_data)
            return d
        except Exception as e:
            raise_from(GcmException("No verification_code received"), None)

    def _establish_connection(self):
        if not self.sock:
            self.sock = ssl.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
            self.sock.connect(("mtalk.google.com", 5228))
            self.sock.setblocking(False)

            self._gcm_send_login(self.android_id, self.security_token)
            version = self._rcv_exact(1)

            self.counter = 0

    def _rcv_exact(self, num_bytes):
        buf = b''
        while len(buf) < num_bytes:
            ready = select.select([self.sock], [], [], 0.2)
            if ready[0]:
                buf += self.sock.recv(num_bytes - len(buf))
            else:
                raise socket.timeout

        return buf

    def _gcm_send_heartbeat(self):
        ping = mcs_pb2.HeartbeatAck()
        ping.last_stream_id_received = self.counter
        ping = ping.SerializeToString()
        self.sock.send(struct.pack('B', 0) + varint.encode(len(ping)) + ping)

    def _gcm_send_login(self, android_id, security_token):
        lr = mcs_pb2.LoginRequest()
        lr.auth_service = 2
        lr.auth_token = str(security_token)
        lr.id = "android-11"
        lr.domain = "mcs.android.com"
        lr.device_id = "android-%0.2X" % android_id
        lr.resource = str(android_id)
        lr.user = str(android_id)
        lr.account_id = android_id

        data = lr.SerializeToString()
        self.sock.sendall(struct.pack('BB', 41, 2) + varint.encode(len(data)) + data)

