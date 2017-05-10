Jodel API
=========

|Build Status| |Coverage Status| |Health| |Python Versions| |PyPI Version| |License|

Inofficial interface to the private API of the Jodel App. Not affiliated
with *The Jodel Venture GmbH*.

Installation
------------

Using pip:

.. code::

    pip install jodel_api

or using setup.py:

.. code::

    git clone https://github.com/nborrmann/jodel_api.git
    cd jodel_api
    python setup.py install


Usage
-----

Account Creation
~~~~~~~~~~~~~~~~

Calling the bare constructor creates a new account:

.. code:: python

    >>> import jodel_api
    >>> lat, lng, city = 48.148434, 11.567867, "Munich"
    >>> j = jodel_api.JodelAccount(lat=lat, lng=lng, city=city)
    Creating new account.

``get_account_data()`` returns all data associated with this account
(censored by me):

.. code:: python

    >>> j.get_account_data()
    {'access_token': 'xxx', 'expiration_date': 1472660000, 'refresh_token': 'xxx', 'distinct_id': 'xxx', 'device_uid': 'xxx'}

Save this data to reuse the account later on, feed it to the
JodelAccount() constructor to reinitiate the account. This constructor
issues one request to update the location of the account.

.. code:: python

    >>> j = jodel_api.JodelAccount(lat=lat, lng=lng, city=city, access_token='xxx', expiration_date='xxx', 
                                   refresh_token='xxx', distinct_id='xxx', device_uid='xxx')
    (204, '')

Add ``update_location=False`` to suppress this behaviour. The
constructor will only instantiate an object, without making any remote
calls:

.. code:: python

    >>> j = jodel_api.JodelAccount(lat=lat, lng=lng, city=city, update_location=False, **account_data)

For some functionality (look out for error 478) accounts need to be
verified by entering a captcha:

.. code:: python

    >>> j.verify_account()
    https://s3-eu-west-1.amazonaws.com/jodel-image-captcha/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.png
    Open the url above in a browser and enter the images containing a racoon (left to right, starting with 0) separated by spaces: 3 5
    Verification failed. Retrying ...
    https://s3-eu-west-1.amazonaws.com/jodel-image-captcha/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.png
    Open the url above in a browser and enter the images containing a racoon (left to right, starting with 0) separated by spaces: 0 3 7
    Account successfully verified.
    >>> j.verify_acccount()
    Account is already verified.
    
(It's a fun challenge to solve these captchas using machine learning.
`Here's <https://u.nya.is/tbqweg.mp4/>`_ what that looks like when you're done.)

After ``expiration_date`` has passed, call ``refresh_access_tokens()``
to re-authenticate. If ``refresh_access_token`` fails, use
``refresh_all_tokens`` instead (this is akin to creating a new account,
but preserves the account's data (karma, etc)):

.. code:: python

    >>> j.refresh_access_token()
    (200, {'token_type': 'bearer', 'access_token': 'xxx', 'expires_in': 604800, 'expiration_date': xxx})
    >>> j.refresh_all_tokens()
    (200, {'expires_in': 604800, 'access_token': 'xxx', 'token_type': 'bearer', 'returning': True,
           'refresh_token': 'xxx', 'expiration_date': 1472600000, 'distinct_id': 'xxx'})

API calls
~~~~~~~~~

All remote API calls return a tuple of HTTP status\_code and the
response (if possible a dict, parsed from the API response), but might
also be a string (error message).

The following API calls are supported (presented without their 
respective responses):


.. code:: python

    # API methods for reading posts:
    >>> j.get_posts_recent(skip=0, limit=60, after=None, mine=False, hashtag=None, channel=None)
    >>> j.get_posts_popular(skip=0, limit=60, after=None, mine=False, hashtag=None, channel=None)
    >>> j.get_posts_discussed(skip=0, limit=60, after=None, mine=False, hashtag=None, channel=None)
    >>> j.get_pictures_recent(skip=0, limit=60, after=None)
    >>> j.get_pictures_popular(skip=0, limit=60, after=None)
    >>> j.get_pictures_discussed(skip=0, limit=60, after=None)
    >>> j.get_my_pinned_posts(skip=0, limit=60, after=None)
    >>> j.get_my_replied_posts(skip=0, limit=60, after=None)
    >>> j.get_my_voted_posts(skip=0, limit=60, after=None)
    >>> j.get_newsfeed(after=None)

    # API methods for interacting with single posts:
    >>> j.create_post(message=None, imgpath=None, b64img=None, color=None, ancestor=None, channel="")
    >>> j.get_post_details(post_id)
    >>> # This api endpoint implements paging and returns at most 50 replies,
    >>> # use the skip parameter to page through the thread:
    >>> j.get_post_details_v3(post_id, skip=0) 
    >>> j.upvote(post_id)
    >>> j.downvote(post_id)
    >>> j.give_thanks(post_id)
    >>> j.get_share_url(post_id)
    >>> j.pin(post_id)
    >>> j.unpin(post_id)
    >>> j.enable_notifications(post_id)
    >>> j.disable_notifications(post_id)
    >>> j.delete_post(post_id) # Only works on your own posts ಠ_ಠ

    # API methods for interacting with sticky posts:
    >>> j.upvote_sticky_post(post_id)
    >>> j.downvote_sticky_post(post_id)
    >>> j.dismiss_sticky_post(post_id)

    # API methods for interacting with notifications:
    >>> j.get_notifications()
    >>> j.get_notifications_new()
    >>> j.notification_read(post_id=None, notification_id=None)

    # API methods for interacting with channels:
    >>> j.get_recommended_channels()
    >>> j.get_channel_meta(channel)
    >>> j.follow_channel(channel)
    >>> j.unfollow_channel(channel)

    # API methods for interacting with your user profile:
    >>> j.set_location(lat, lng, city, country=None, name=None) # country and name appear to have no effect
    >>> j.set_user_profile(user_type=None, gender=None, age=None)
    >>> j.get_user_config()
    >>> j.get_karma()
    >>> j.get_captcha()
    >>> j.submit_captcha(key, answer)


The parameters ``skip``,
``limit`` and ``after`` implement paging. While ``skip`` and ``limit``
are integers, ``after`` is a ``post_id`` parameter and will return all
jodels that follow that one. The former two paramters seem to be 
deprecated in favor of the latter, however ``after`` doesn't work
on all ``/mine/`` endpoints (ie. ``mine=True`` or ``get_my_x_posts``).

The arguments ``mine`` (boolean), ``hashtag``, ``channel`` (both strings)
are exclusive. If ``mine`` evaluates to ``true``, the other two arguments
are discarded, if ``hashtag`` evaluates ``true`` , ``channel`` is 
discarded.

``get_newsfeed()`` is a new endpoint (as of March 17) that isn't yet
available through the app. It returns all popular (upvotes/comments) 
Jodels from a larger timeframe than the usual ``get_posts()`` methods
can access. 

You can pass additional arguments (such as proxies and timeouts) to all
API calls through the ``**xargs`` argument that will be passed to the
``requests.request()`` function:

.. code:: python

    >>> j.upvote(post_id, timeout=5, proxies={'https': '127.0.0.1:5000'})
    
For unimplemented endpoints, check `issue #22 
<https://github.com/nborrmann/jodel_api/issues/22/>`_.


Error Codes
~~~~~~~~~~~

-  **403 "Access Denied"**: Your IP is banned accross endpoints,
   just read-only endpoints still work. Effective for 24 hours.
-  **429 "Too Many Requests"**: Your IP is rate-limited. Applies only
   to one specific endpoint.
-  **477 "Signed Request Expected"**: This library should handle request
   signing. Make sure to upgrade to the latest version of ``jodel_api``,
   as the signing key changes every few weeks.
-  **478 "Account not verified"**: Solve the captcha challenge (eg.
   through ``verify_account()``).
-  **502 "Bad Gateway"**: Something went wrong server-side. This happens
   pretty randomly. ``jodel_api`` automatically retries two times when
   it sees this error. If you encounter this status, the jodel servers
   are probably having issues. Try again later.

Rate-Limits
~~~~~~~~~~~

The Jodel API appears to have the following (IP-based) rate-limits

-  max of 200 new account registrations from one IP per half hour
-  max of 200 votes per minute
-  max of 100 captcha requests per minute

They also hand out 403 bans if you overdo it.

Tests
-----

Nearly all tests in ``jodel_api_test.py`` are integration tests, which
actually hit the Jodel servers. These can fail for any number of reasons
(eg. connectivity issues), which does not necessarily imply there is
something wrong with this library. As this library tries to make few
assumptions about the content of the json responses they test mostly for
status codes, not the contents of the responses (ie. they test whether
the API endpoints are still valid).

-  For the tests in ``class TestUnverifiedAccount`` a new account is
   created on every run and they test read-only functions for which the
   account does not need to be verified.
-  Tests in ``class TestVerifiedAccount`` need an already verified
   account to test voting and creating posts (posts are deleted after
   creation). To run these tests you need to verify an account by
   solving the captcha and save its ``device_uid`` in the
   environment variable ``JODEL_ACCOUNT``. Run
   ``j.get_account_data()['device_uid']`` to get the value.

   Linux:

   ::

       export JODEL_ACCOUNT=a8aa02[...]dba

   Windows (you need to restart the cmd/shell for this to take effect,
   or set it through gui):

   ::

       setx JODEL_ACCOUNT a8aa02[...]dba

   If this variable is not present, these tests will be skipped.

Clone the directory, install the library and run the tests with

.. code:: python

    python setup.py test

.. |Build Status| image:: https://travis-ci.org/nborrmann/jodel_api.svg?branch=master
   :target: https://travis-ci.org/nborrmann/jodel_api
.. |Coverage Status| image:: https://img.shields.io/codecov/c/github/nborrmann/jodel_api.svg
   :target: https://codecov.io/gh/nborrmann/jodel_api
.. |Health| image:: https://landscape.io/github/nborrmann/jodel_api/master/landscape.svg?style=flat
   :target: https://landscape.io/github/nborrmann/jodel_api/master
.. |Python Versions| image:: https://img.shields.io/pypi/pyversions/jodel_api.svg
   :target: https://pypi.python.org/pypi/jodel_api/
.. |PyPI Version| image:: https://img.shields.io/pypi/v/jodel_api.svg
   :target: https://pypi.python.org/pypi/jodel_api/
.. |License| image:: https://img.shields.io/pypi/l/jodel_api.svg
   :target: https://pypi.python.org/pypi/jodel_api/
