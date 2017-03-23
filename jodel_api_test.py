import jodel_api
from random import uniform
import time
import base64

lat, lng, city = 48.144378, 11.573044, "Munich"

class TestUnverifiedAccount:

    @classmethod
    def setup_class(self):
        self.j = jodel_api.JodelAccount(lat + uniform(-0.01, 0.01), lng + uniform(-0.01, 0.01), city)
        assert isinstance(self.j, jodel_api.JodelAccount)

        r = self.j.get_posts_discussed()
        assert r[0] == 200
        assert "posts" in r[1] and "post_id" in r[1]["posts"][0]
        self.pid = r[1]['posts'][0]['post_id']

    def test_refresh_access_token(self):
        r = self.j.refresh_access_token()
        assert r[0] == 200
        assert set(r[1].keys()) == set(["expiration_date", "token_type", "expires_in", "access_token"])

    def test_set_location(self):
        r = self.j.set_location(lat + uniform(-0.01, 0.01), lng + uniform(-0.01, 0.01), city)
        assert r[0] == 204

    def test_read_posts_recent(self):
        r = self.j.get_posts_recent()
        assert r[0] == 200

    def test_get_posts_popular(self):
        r = self.j.get_posts_popular()
        assert r[0] == 200

    def test_get_posts_pinned(self):
        assert self.j.get_my_pinned_posts()[0] == 200

    def test_get_posts_channel(self):
        r = self.j.get_posts_recent(channel="selfies")
        assert r[0] == 200
        assert "posts" in r[1]

    def test_get_channels(self):
        r = self.j.get_recommended_channels()
        assert "local" in r[1]
        assert r[0] == 200

        channel = r[1]["local"][0]["channel"]
        assert self.j.get_channel_meta(channel)[0] == 200

    def test_follow_channel(self):
        assert self.j.follow_channel("selfies")[0] == 204
        assert self.j.follow_channel("selfies")[0] == 204

    def test_get_config(self):
        r = self.j.get_user_config()
        assert r[0] == 200
        assert "verified" in r[1]

        assert self.j.get_karma()[0] == 200

    def test_captcha(self):
        r = self.j.get_captcha()
        assert r[0] == 200
        assert "image_url" in r[1]
        assert "key" in r[1]

        assert self.j.submit_captcha(r[1]["key"], [3])[0] == 200

    def test_notifications(self):
        assert self.j.get_notifications()[0] == 200
        assert self.j.get_notifications_new()[0] == 200

    def test_post_details(self):
        r = self.j.get_post_details(self.pid)
        assert r[0] == 200
        assert len(r[1]["children"]) == r[1]["child_count"]

    def test_pin(self):
        assert self.j.pin(self.pid)[0] == 200
        assert self.j.unpin(self.pid)[0] == 200

    def test_vote(self):
        assert self.j.upvote(self.pid)[0] == 478
        assert self.j.downvote(self.pid)[0] == 478

    def test_switch_notifications(self):
        r = self.j.enable_notifications(self.pid)
        assert r[0] == 200
        assert r[1]["notifications_enabled"] == True

        r = self.j.disable_notifications(self.pid)
        assert r[0] == 200
        assert r[1]["notifications_enabled"] == False



class TestVerifiedAccount:
    acc = {'device_uid': 'cbbbdfb235d92b360a96e20b5de710ea14cc1f56fd7f7d70d9fd8b08600ecf2a',
           'expiration_date': 1490881346,
           'refresh_token': '1d026f42-c0b5-461e-901f-8367c12aea20',
           'distinct_id': '58d3d0c217c50b1a006139e7',
           'access_token': '76546754-dba5a820-fbe5dfc2-24ae-445c-a21c-33c9414ae429'}

    @classmethod
    def setup_class(self):
        self.j = jodel_api.JodelAccount(lat, lng, city, update_location=False, **self.acc)
        r = self.j.refresh_all_tokens()
        assert r[0] == 200

        r = self.j.get_posts_popular()
        assert r[0] == 200
        assert "posts" in r[1] and "post_id" in r[1]["posts"][0]
        self.pid1 = r[1]['posts'][0]['post_id']
        self.pid2 = r[1]['posts'][1]['post_id']
        assert self.j.follow_channel("repost")[0] == 204

    def test_post_message(self):
        color = "FF9908"
        msg = "This is an automated test message. Color is #%s. Location is %f:%f. Time is %s" % (color, lat, lng, time.ctime())
        r = self.j.create_post(msg, color=color)
        assert r[0] == 200
        assert "post_id" in r[1]

        p = self.j.get_post_details(r[1]["post_id"])
        assert p[0] == 200
        assert p[1]["color"] == color
        assert p[1]["message"] == msg

        assert self.j.delete_post(r[1]["post_id"])[0] == 204

    def test_post_channel_img(self):
        color = "9EC41C"
        msg = "This is an automated test message. Color is #%s. Location is %f:%f. Time is %s" % (color, lat, lng, time.ctime())
        with open("testimg.png", "rb") as f:
            imgdata = base64.b64encode(f.read()).decode("utf-8")
        
        r = self.j.create_post(msg, b64img=imgdata, color=color, channel="repost")
        assert r[0] == 200
        assert "post_id" in r[1]

        assert self.j.delete_post(r[1]["post_id"])[0] == 204

    def test_post_reply(self):
        color = "FFBA00"
        msg = "This is an automated test message. Color is #%s. Location is %f:%f. Time is %s" % (color, lat, lng, time.ctime())
        r = self.j.create_post(msg, color=color, ancestor=self.pid1)
        assert r[0] == 200
        assert "post_id" in r[1]

        p = self.j.get_post_details(self.pid1)
        assert p[0] == 200
        assert "children" in p[1]

        my_post = next(post for post in p[1]["children"] if post["post_id"] == r[1]["post_id"])
        assert my_post["color"] == color
        assert my_post["message"] == msg

        assert self.j.delete_post(r[1]["post_id"])[0] == 204

    def test_vote(self):
        assert self.j.upvote(self.pid1)[0] == 200
        assert self.j.downvote(self.pid2)[0] == 200



