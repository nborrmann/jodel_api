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
    client_id = '81e8a76e-1e02-4d17-9ba0-8a7020261b26'
    api_url = "https://api.go-tellm.com/api%s"
    access_token = None
    device_uid = None

    def __init__(self, lat, lng, city, country=None, name=None, update_location=True,
                 access_token=None, device_uid=None, refresh_token=None, distinct_id=None, expiration_date=None, 
                 **kwargs):
        self.lat, self.lng, self.location_dict = lat, lng, self._get_location_dict(lat, lng, city, country, name)

        if access_token and device_uid and refresh_token and distinct_id and expiration_date:
            self.expiration_date = expiration_date
            self.distinct_id = distinct_id
            self.refresh_token = refresh_token
            self.device_uid = device_uid
            self.access_token = access_token
            if update_location:
                r = self.set_location(lat, lng, city, country, name, **kwargs)
                if r[0] != 204:
                    raise Exception("Error updating location: " + str(r))

        else:
            print("Creating new account.")
            r = self.refresh_all_tokens(**kwargs)
            if r[0] != 200:
                raise Exception("Error creating new account: " + str(r))

    def _send_request(self, method, endpoint, payload=None, **kwargs):
        url = self.api_url % endpoint
                
        headers = {'User-Agent': 'Jodel/4.4.9 Dalvik/2.1.0 (Linux; U; Android 5.1.1; )',
                   'Accept-Encoding': 'gzip',
                   'Content-Type': 'application/json; charset=UTF-8'}
        if self.access_token:
            headers['Authorization'] = "Bearer " + self.access_token

        self._sign_request(method, url, headers, payload)

        if payload:
            payload = json.dumps(payload, separators=(',',':'))

        resp = s.request(method=method, url=url, data=payload, headers=headers, **kwargs)
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
               timestamp,
               *sorted(urlparse(url).query.replace("=", "%").split("&")),
               json.dumps(payload, separators=(',',':'))]

        secret = bytearray([97, 120, 77, 71, 97, 104, 69, 104, 104, 66, 72, 115, 83, 105, 85, 111, 103, 107, 113, 122, 
                            112, 76, 69, 69, 86, 65, 101, 80, 115, 76, 98, 68, 84, 89, 111, 86, 74, 105, 109, 72])
        signature = hmac.new(secret, "%".join(req).encode("utf-8"), sha1).hexdigest().upper()

        headers['X-Authorization'] = 'HMAC ' + signature
        headers['X-Client-Type'] = 'android_4.18.2'
        headers['X-Timestamp'] = timestamp
        headers['X-Api-Version'] = '0.2'

    @staticmethod
    def _get_location_dict(lat, lng, city, country=None, name=None):
        return {"loc_accuracy": 0.0, 
                "city": city, 
                "loc_coordinates": {"lat": lat, "lng": lng}, 
                "country": country if country else "DE", 
                "name": name if name else city}

    def refresh_all_tokens(self, **kwargs):
        """ Creates a new account with random ID if self.device_uid is not set. Otherwise renews all tokens of the
        account with ID = self.device_uid. """
        if not self.device_uid:
            self.device_uid = ''.join(random.choice('abcdef0123456789') for _ in range(64))

        payload = {"client_id": self.client_id, 
                   "device_uid": self.device_uid,
                   "location": self.location_dict}

        resp = self._send_request("POST", "/v2/users", payload, **kwargs)
        if resp[0] == 200:
            self.access_token = resp[1]['access_token']
            self.expiration_date = resp[1]['expiration_date']
            self.refresh_token = resp[1]['refresh_token']
            self.distinct_id = resp[1]['distinct_id']
        else:
            raise Exception(resp)
        return resp

    def refresh_access_token(self, **kwargs):
        payload = {"client_id": self.client_id, 
                   "distinct_id": self.distinct_id, 
                   "refresh_token": self.refresh_token}

        resp = self._send_request("POST", "/v2/users/refreshToken", payload, **kwargs)
        if resp[0] == 200:
            self.access_token = resp[1]['access_token']
            self.expiration_date = resp[1]['expiration_date']
        return resp

    def get_account_data(self):
        return {'expiration_date': self.expiration_date, 'distinct_id': self.distinct_id,
                'refresh_token': self.refresh_token, 'device_uid': self.device_uid, 'access_token': self.access_token}

    def set_location(self, lat, lng, city, country=None, name=None, **kwargs):
        self.lat, self.lng, self.location_dict = lat, lng, self._get_location_dict(lat, lng, city, country, name)
        return self._send_request("PUT", "/v2/users/location", {"location": self.location_dict}, **kwargs)

    def create_post(self, message=None, imgpath=None, color=None, ancestor=None, **kwargs):
        payload = {"color": color if color else random.choice(self.post_colors),
                   "location": self.location_dict}
        if ancestor:
            payload["ancestor"] = ancestor
        if imgpath:
            with open(imgpath, "rb") as f:
                imgdata = base64.b64encode(f.read()).decode("utf-8")
                payload["image"] = imgdata
        if message:
            payload["message"] = message
        if not imgpath and not message:
            raise Exception("One of message or imgpath must not be null.")

        return self._send_request("POST", '/v2/posts/', payload=payload, **kwargs)

    def upvote(self, post_id, **kwargs):
        return self._send_request("PUT", '/v2/posts/%s/upvote' % post_id, **kwargs)

    def downvote(self, post_id, **kwargs):
        return self._send_request("PUT", '/v2/posts/%s/downvote' % post_id, **kwargs)

    def get_post_details(self, message_id, **kwargs):
        return self._send_request("GET", '/v2/posts/%s/' % message_id, **kwargs)

    def _get_posts(self, post_types, skip=None, limit=60, mine=False, **kwargs):
        url = '/v2/posts/%s%s?lat=%f&lng=%f' % ('mine' if mine else 'location', post_types, self.lat, self.lng)
        url += '&skip=%d' % skip if skip else ""
        url += '&limit=%d' % limit if limit else ""
        return self._send_request("GET", url, **kwargs)

    def get_posts_recent(self, skip=None, limit=60, mine=False, **kwargs):
        return self._get_posts('', skip, limit, mine, **kwargs)

    def get_posts_popular(self, skip=None, limit=60, mine=False, **kwargs):
        return self._get_posts('/popular', skip, limit, mine, **kwargs)

    def get_posts_discussed(self, skip=None, limit=60, mine=False, **kwargs):
        return self._get_posts('/discussed', skip, limit, mine, **kwargs)

    def get_user_config(self, **kwargs):
        return self._send_request("GET", "/v3/user/config", **kwargs)

    def get_karma(self, **kwargs):
        return self._send_request("GET", "/v2/users/karma", **kwargs)

    def delete_post(self, post_id, **kwargs):
        return self._send_request("DELETE", "/v2/posts/%s" % post_id, **kwargs)
