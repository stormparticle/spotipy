
from __future__ import print_function
import base64
import requests
import os
import json
import time
import sys

# Workaround to support both python 2 & 3
try:
\timport urllib.request, urllib.error
\timport urllib.parse as urllibparse
except ImportError:
\timport urllib as urllibparse



class SpotifyOauthError(Exception):
\tpass


class SpotifyClientCredentials(object):
\tOAUTH_TOKEN_URL = 'https://accounts.spotify.com/api/token'

\tdef __init__(self, client_id=None, client_secret=None, proxies=None):
\t\t"""
\t\tYou can either provid a client_id and client_secret to the
\t\tconstructor or set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET
\t\tenvironment variables
\t\t"""
\t\tif not client_id:
\t\t\tclient_id = os.getenv('SPOTIPY_CLIENT_ID')

\t\tif not client_secret:
\t\t\tclient_secret = os.getenv('SPOTIPY_CLIENT_SECRET')

\t\tif not client_id:
\t\t\traise SpotifyOauthError('No client id')

\t\tif not client_secret:
\t\t\traise SpotifyOauthError('No client secret')

\t\tself.client_id = client_id
\t\tself.client_secret = client_secret
\t\tself.token_info = None
\t\tself.proxies = proxies

\tdef get_access_token(self):
\t\t"""
\t\tIf a valid access token is in memory, returns it
\t\tElse feches a new token and returns it
\t\t"""
\t\tif self.token_info and not self._is_token_expired(self.token_info):
\t\t\treturn self.token_info['access_token']

\t\ttoken_info = self._request_access_token()
\t\ttoken_info = self._add_custom_values_to_token_info(token_info)
\t\tself.token_info = token_info
\t\treturn self.token_info['access_token']

\tdef _request_access_token(self):
\t\t"""Gets client credentials access token """
\t\tpayload = { 'grant_type': 'client_credentials'}

\t\tif sys.version_info[0] >= 3: # Python 3
\t\t\tauth_header = base64.b64encode(str(self.client_id + ':' + self.client_secret).encode())
\t\t\theaders = {'Authorization': 'Basic %s' % auth_header.decode()}
\t\telse: # Python 2
\t\t\tauth_header = base64.b64encode(self.client_id + ':' + self.client_secret)
\t\t\theaders = {'Authorization': 'Basic %s' % auth_header}

\t\tresponse = requests.post(self.OAUTH_TOKEN_URL, data=payload,
\t\t\theaders=headers, verify=True, proxies=self.proxies)
\t\tif response.status_code is not 200:
\t\t\traise SpotifyOauthError(response.reason)
\t\ttoken_info = response.json()
\t\treturn token_info

\tdef _is_token_expired(self, token_info):
\t\tnow = int(time.time())
\t\treturn token_info['expires_at'] - now < 60

\tdef _add_custom_values_to_token_info(self, token_info):
\t\t"""
\t\tStore some values that aren't directly provided by a Web API
\t\tresponse.
\t\t"""
\t\ttoken_info['expires_at'] = int(time.time()) + token_info['expires_in']
\t\treturn token_info


class SpotifyOAuth(object):
\t'''
\tImplements Authorization Code Flow for Spotify's OAuth implementation.
\t'''

\tOAUTH_AUTHORIZE_URL = 'https://accounts.spotify.com/authorize'
\tOAUTH_TOKEN_URL = 'https://accounts.spotify.com/api/token'

\tdef __init__(self, client_id, client_secret, redirect_uri,
\t\t\tstate=None, scope=None, cache_path=None, proxies=None):
\t\t'''
\t\t\tCreates a SpotifyOAuth object

\t\t\tParameters:
\t\t\t\t - client_id - the client id of your app
\t\t\t\t - client_secret - the client secret of your app
\t\t\t\t - redirect_uri - the redirect URI of your app
\t\t\t\t - state - security state
\t\t\t\t - scope - the desired scope of the request
\t\t\t\t - cache_path - path to location to save tokens
\t\t'''

\t\tself.client_id = client_id
\t\tself.client_secret = client_secret
\t\tself.redirect_uri = redirect_uri
\t\tself.state=state
\t\tself.cache_path = cache_path
\t\tself.scope=self._normalize_scope(scope)
\t\tself.proxies = proxies

\tdef get_cached_token(self):
\t\t''' Gets a cached auth token
\t\t'''
\t\ttoken_info = None
\t\tif self.cache_path:
\t\t\ttry:
\t\t\t\tf = open(self.cache_path)
\t\t\t\ttoken_info_string = f.read()
\t\t\t\tf.close()
\t\t\t\ttoken_info = json.loads(token_info_string)

\t\t\t\t# if scopes don't match, then bail
\t\t\t\tif 'scope' not in token_info or not self._is_scope_subset(self.scope, token_info['scope']):
\t\t\t\t\treturn None

\t\t\t\tif self._is_token_expired(token_info):
\t\t\t\t\ttoken_info = self.refresh_access_token(token_info['refresh_token'])

\t\t\texcept IOError:
\t\t\t\tpass
\t\treturn token_info

\tdef _save_token_info(self, token_info):
\t\tif self.cache_path:
\t\t\ttry:
\t\t\t\tf = open(self.cache_path, 'w')
\t\t\t\tf.write(json.dumps(token_info))
\t\t\t\tf.close()
\t\t\texcept IOError:
\t\t\t\tself._warn("couldn't write token cache to " + self.cache_path)
\t\t\t\tpass

\tdef _is_scope_subset(self, needle_scope, haystack_scope):
\t\tneedle_scope = set(needle_scope.split())
\t\thaystack_scope = set(haystack_scope.split())

\t\treturn needle_scope <= haystack_scope

\tdef _is_token_expired(self, token_info):
\t\tnow = int(time.time())
\t\treturn token_info['expires_at'] < now

\tdef get_authorize_url(self):
\t\t""" Gets the URL to use to authorize this app
\t\t"""
\t\tpayload = {'client_id': self.client_id,
\t\t\t\t   'response_type': 'code',
\t\t\t\t   'redirect_uri': self.redirect_uri}
\t\tif self.scope:
\t\t\tpayload['scope'] = self.scope
\t\tif self.state:
\t\t\tpayload['state'] = self.state

\t\turlparams = urllibparse.urlencode(payload)

\t\treturn "%s?%s" % (self.OAUTH_AUTHORIZE_URL, urlparams)

\tdef parse_response_code(self, url):
\t\t""" Parse the response code in the given response url

\t\t\tParameters:
\t\t\t\t- url - the response url
\t\t"""

\t\ttry:
\t\t\treturn url.split("?code=")[1].split("&")[0]
\t\texcept IndexError:
\t\t\treturn None

\tdef get_access_token(self, code):
\t\t""" Gets the access token for the app given the code

\t\t\tParameters:
\t\t\t\t- code - the response code
\t\t"""

\t\tpayload = {'redirect_uri': self.redirect_uri,
\t\t\t\t   'code': code,
\t\t\t\t   'grant_type': 'authorization_code'}
\t\tif self.scope:
\t\t\tpayload['scope'] = self.scope
\t\tif self.state:
\t\t\tpayload['state'] = self.state

\t\tif sys.version_info[0] >= 3: # Python 3
\t\t\tauth_header = base64.b64encode(str(self.client_id + ':' + self.client_secret).encode())
\t\t\theaders = {'Authorization': 'Basic %s' % auth_header.decode()}
\t\telse: # Python 2
\t\t\tauth_header = base64.b64encode(self.client_id + ':' + self.client_secret)
\t\t\theaders = {'Authorization': 'Basic %s' % auth_header}

\t\tresponse = requests.post(self.OAUTH_TOKEN_URL, data=payload,
\t\t\theaders=headers, verify=True, proxies=self.proxies)
\t\tif response.status_code is not 200:
\t\t\traise SpotifyOauthError(response.reason)
\t\ttoken_info = response.json()
\t\ttoken_info = self._add_custom_values_to_token_info(token_info)
\t\tself._save_token_info(token_info)
\t\treturn token_info

\tdef _normalize_scope(self, scope):
\t\tif scope:
\t\t\tscopes = scope.split()
\t\t\tscopes.sort()
\t\t\treturn ' '.join(scopes)
\t\telse:
\t\t\treturn None

\tdef refresh_access_token(self, refresh_token):
\t\tpayload = { 'refresh_token': refresh_token,
\t\t\t\t   'grant_type': 'refresh_token'}

\t\tif sys.version_info[0] >= 3: # Python 3
\t\t\tauth_header = base64.b64encode(str(self.client_id + ':' + self.client_secret).encode())
\t\t\theaders = {'Authorization': 'Basic %s' % auth_header.decode()}
\t\telse: # Python 2
\t\t\tauth_header = base64.b64encode(self.client_id + ':' + self.client_secret)
\t\t\theaders = {'Authorization': 'Basic %s' % auth_header}

\t\tresponse = requests.post(self.OAUTH_TOKEN_URL, data=payload,
\t\t\theaders=headers, proxies=self.proxies)
\t\tif response.status_code != 200:
\t\t\tif False:  # debugging code
\t\t\t\tprint('headers', headers)
\t\t\t\tprint('request', response.url)
\t\t\tself._warn("couldn't refresh token: code:%d reason:%s" \
\t\t\t\t% (response.status_code, response.reason))
\t\t\treturn None
\t\ttoken_info = response.json()
\t\ttoken_info = self._add_custom_values_to_token_info(token_info)
\t\tif not 'refresh_token' in token_info:
\t\t\ttoken_info['refresh_token'] = refresh_token
\t\tself._save_token_info(token_info)
\t\treturn token_info

\tdef _add_custom_values_to_token_info(self, token_info):
\t\t'''
\t\tStore some values that aren't directly provided by a Web API
\t\tresponse.
\t\t'''
\t\ttoken_info['expires_at'] = int(time.time()) + token_info['expires_in']
\t\ttoken_info['scope'] = self.scope
\t\treturn token_info

\tdef _warn(self, msg):
\t\tprint('warning:' + msg, file=sys.stderr)

