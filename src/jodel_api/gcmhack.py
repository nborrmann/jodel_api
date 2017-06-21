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

    def __init__(self, android_id=None, security_token=None, **kwargs):
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
        r = requests.post("https://android.clients.google.com/checkin", headers=headers, data=data, **kwargs)

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

        r = requests.post("https://android.clients.google.com/c2dm/register3", headers=headers, data=data, **kwargs)
        if r.status_code == 200 and "token" in r.text:
            return r.text.split("=")[1]
        else:
            raise GcmException(r.text)

    def receive_verification_from_gcm(self):
        # We read all messages on the server until there are none for a timeout of two seconds.
        # Return the last verification_code that we receive.
        # Note: We cannot return on the first verification_code because the server sometimes sends
        # the same code twice.
        s = ssl.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        s.connect(("mtalk.google.com", 5228))
        s.setblocking(False)

        counter, verification_data = 0, None
        try:
            _gcm_send_login(s, self.android_id, self.security_token)
            version = _rcv_exact(s, 1)

            while True:
                responseTag = ord(_rcv_exact(s, 1))
                length = varint.decode_stream(s)
                msg = _rcv_exact(s, length)
                counter += 1

                if responseTag == 3:
                    pass # login

                elif responseTag == 4:
                    break

                elif responseTag == 8:
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
        except socket.timeout:
            _gcm_send_heartbeat(s, counter)
            pass
        except Exception:
            raise
        finally:
            s.close()

        try:
            return json.loads(verification_data)
        except Exception as e:
            raise_from(GcmException("No verification_code received"), None)


def _rcv_exact(sock, num_bytes):
    buf = b''
    while len(buf) < num_bytes:
        ready = select.select([sock], [], [], 0.2)
        if ready[0]:
            buf += sock.recv(num_bytes - len(buf))
        else:
            raise socket.timeout
    return buf

def _gcm_send_heartbeat(sock, counter):
    ping = mcs_pb2.HeartbeatAck()
    ping.last_stream_id_received = counter
    ping = ping.SerializeToString()
    sock.send(struct.pack('B', 0) + varint.encode(len(ping)) + ping)

def _gcm_send_login(sock, android_id, security_token):
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
    sock.sendall(struct.pack('BB', 41, 2) + varint.encode(len(data)) + data)

