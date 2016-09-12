import base64
import datetime
import hmac
import json
import random
from hashlib import sha1
from urllib.parse import urlparse
import requests

s = requests.Session()


class JodelAccount:
    post_colors = ['9EC41C', 'FF9908', 'DD5F5F', '8ABDB0', '066A3CB', 'FFBA00']
    client_id = '"client_id":"81e8a76e-1e02-4d17-9ba0-8a7020261b26"'
    api_url = "https://api.go-tellm.com/api%s"
    access_token = None
    device_uid = None

    def __init__(self, lat, lng, city, country=None, name=None, update_location=True,
                 access_token=None, device_uid=None, refresh_token=None, distinct_id=None, expiration_date=None):
        self.lat, self.lng, self.location_str = lat, lng, self._get_location_string(lat, lng, city, country, name)

        if access_token and device_uid and refresh_token and distinct_id and expiration_date:
            self.expiration_date = expiration_date
            self.distinct_id = distinct_id
            self.refresh_token = refresh_token
            self.device_uid = device_uid
            self.access_token = access_token
            if update_location:
                r = self.set_location(lat, lng, city, country, name)
                print(r)

        else:
            print("Creating new account.")
            r = self.refresh_all_tokens()
            if r[0] != 200:
                print("Error creating new account: " + str(r))

    def _send_request(self, method, endpoint, payload=None):
        url = self.api_url % endpoint
        headers = {'User-Agent': 'Jodel/4.4.9 Dalvik/2.1.0 (Linux; U; Android 5.1.1; )',
                   'Accept-Encoding': 'gzip',
                   'Content-Type': 'application/json; charset=UTF-8'}
        if self.access_token:
            headers['Authorization'] = "Bearer " + self.access_token

        self._sign_request(method, url, headers, payload)

        payload = payload.encode('utf-8') if payload is not None else None

        resp = s.request(method=method, url=url, data=payload, headers=headers)
        try:
            resp_text = json.loads(resp.text, encoding="utf-8")
        except:
            resp_text = resp.text

        return resp.status_code, resp_text

    def _sign_request(self, method, url, headers, payload=None):
        timestamp = datetime.datetime.utcnow().isoformat()[:-7] + "Z"

        req = [method,
               urlparse(url).netloc,
               "443",
               urlparse(url).path,
               self.access_token if self.access_token else "",
               timestamp]
        req.extend(sorted(urlparse(url).query.replace("=", "%").split("&")))
        req.append(payload if payload else "")

        secret = bytearray([74, 121, 109, 82, 78, 107, 79, 71, 68, 85, 72, 81, 77, 86, 101, 86, 118, 100, 122, 118, 97,
                            120, 99, 75, 97, 101, 117, 74, 75, 87, 87, 70, 101, 105, 104, 110, 89, 110, 115, 89])
        signature = hmac.new(secret, "%".join(req).encode("utf-8"), sha1).hexdigest().upper()

        headers['X-Authorization'] = 'HMAC ' + signature
        headers['X-Client-Type'] = 'android_4.14.1'
        headers['X-Timestamp'] = timestamp
        headers['X-Api-Version'] = '0.2'

    @staticmethod
    def _get_location_string(lat, lng, city, country=None, name=None):
        return '"location":{"loc_accuracy":0.0,"city":"%s","loc_coordinates":{"lat":%f,"lng":%f},"country":"%s",' \
               '"name":"%s"}' % (city, lat, lng, country if country else 'DE', name if name else city)

    def refresh_all_tokens(self):
        """ Creates a new account with random ID if self.device_uid is not set. Otherwise renews all tokens of the
        account with ID = self.device_uid. """
        if not self.device_uid:
            self.device_uid = ''.join(random.choice('abcdef0123456789') for _ in range(64))

        payload = '{%s,"device_uid":"%s",%s}' % (self.client_id, self.device_uid, self.location_str)
        resp = self._send_request("POST", "/v2/users", payload)
        if resp[0] == 200:
            self.access_token = resp[1]['access_token']
            self.expiration_date = resp[1]['expiration_date']
            self.refresh_token = resp[1]['refresh_token']
            self.distinct_id = resp[1]['distinct_id']
        else:
            raise Exception(resp)
        return resp

    def refresh_access_token(self):
        payload = '{%s,"distinct_id":"%s","refresh_token":"%s"}' % (self.client_id, self.distinct_id, self.refresh_token)
        resp = self._send_request("POST", "/v2/users/refreshToken", payload)
        if resp[0] == 200:
            self.access_token = resp[1]['access_token']
            self.expiration_date = resp[1]['expiration_date']
        return resp

    def get_account_data(self):
        return {'expiration_date': self.expiration_date, 'distinct_id': self.distinct_id,
                'refresh_token': self.refresh_token, 'device_uid': self.device_uid, 'access_token': self.access_token}

    def set_location(self, lat, lng, city, country=None, name=None):
        self.lat, self.lng, self.location_str = lat, lng, self._get_location_string(lat, lng, city, country, name)
        return self._send_request("PUT", "/v2/users/location", "{%s}" % self.location_str)

    def create_post(self, message=None, imgpath=None, color=None):
        if not color:
            color = random.choice(self.post_colors)
        if imgpath:
            with open(imgpath, "rb") as f:
                imgdata = base64.b64encode(f.read()).decode("utf-8")
                payload = '{"color":"%s","image":"%s",%s,"message":"%s"}' % (color, imgdata, self.location_str, message)
        elif message:
            payload = '{"color":"%s",%s,"message":"%s"}' % (color, self.location_str, message)
        else:
            print("One of message or imgpath must not be null.")
            return

        return self._send_request("POST", '/v2/posts/', payload=payload)

    def upvote(self, post_id):
        return self._send_request("PUT", '/v2/posts/%s/upvote' % post_id)

    def downvote(self, post_id):
        return self._send_request("PUT", '/v2/posts/%s/downvote' % post_id)

    def get_post_details(self, message_id):
        return self._send_request("GET", '/v2/posts/%s/' % message_id)

    def _get_posts(self, post_types, skip=None, limit=60, mine=False):
        url = '/v2/posts/%s%s?lat=%f&lng=%f' % ('mine' if mine else 'location', post_types, self.lat, self.lng)
        url += '&skip=%d' % skip if skip else ""
        url += '&limit=%d' % limit if limit else ""
        return self._send_request("GET", url)

    def get_posts_recent(self, skip=None, limit=60, mine=False):
        return self._get_posts('', skip, limit, mine)

    def get_posts_popular(self, skip=None, limit=60, mine=False):
        return self._get_posts('/popular', skip, limit, mine)

    def get_posts_discussed(self, skip=None, limit=60, mine=False):
        return self._get_posts('/discussed', skip, limit, mine)

    def get_user_config(self):
        return self._send_request("GET", "/v3/user/config")

    def get_karma(self):
        return self._send_request("GET", "/v2/users/karma")

    def delete_post(self, post_id):
        return self._send_request("DELETE", "/v2/posts/%s" % post_id)
