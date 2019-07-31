# coding: utf-8


from __future__ import print_function
import sys
import requests
import json
import time

import six

''' A simple and thin Python library for the Spotify Web API
'''


class SpotifyException(Exception):
\tdef __init__(self, http_status, code, msg, headers=None):
\t\tself.http_status = http_status
\t\tself.code = code
\t\tself.msg = msg
\t\t# `headers` is used to support `Retry-After` in the event of a
\t\t# 429 status code.
\t\tif headers is None:
\t\t\theaders = {}
\t\tself.headers = headers

\tdef __str__(self):
\t\treturn 'http status: {0}, code:{1} - {2}'.format(
\t\t\tself.http_status, self.code, self.msg)


class Spotify(object):
\t'''
\t\tExample usage::

\t\t\timport spotipy

\t\t\turn = 'spotify:artist:3jOstUTkEu2JkjvRdBA5Gu'
\t\t\tsp = spotipy.Spotify()

\t\t\tsp.trace = True # turn on tracing
\t\t\tsp.trace_out = True # turn on trace out

\t\t\tartist = sp.artist(urn)
\t\t\tprint(artist)

\t\t\tuser = sp.user('plamere')
\t\t\tprint(user)
\t'''

\ttrace = False  # Enable tracing?
\ttrace_out = False
\tmax_get_retries = 10

\tdef __init__(self, auth=None, requests_session=True,
\t\tclient_credentials_manager=None, proxies=None, requests_timeout=None):
\t\t'''
\t\tCreate a Spotify API object.

\t\t:param auth: An authorization token (optional)
\t\t:param requests_session:
\t\t\tA Requests session object or a truthy value to create one.
\t\t\tA falsy value disables sessions.
\t\t\tIt should generally be a good idea to keep sessions enabled
\t\t\tfor performance reasons (connection pooling).
\t\t:param client_credentials_manager:
\t\t\tSpotifyClientCredentials object
\t\t:param proxies:
\t\t\tDefinition of proxies (optional)
\t\t:param requests_timeout:
\t\t\tTell Requests to stop waiting for a response after a given number of seconds
\t\t'''
\t\tself.prefix = 'https://api.spotify.com/v1/'
\t\tself._auth = auth
\t\tself.client_credentials_manager = client_credentials_manager
\t\tself.proxies = proxies
\t\tself.requests_timeout = requests_timeout

\t\tif isinstance(requests_session, requests.Session):
\t\t\tself._session = requests_session
\t\telse:
\t\t\tif requests_session:  # Build a new session.
\t\t\t\tself._session = requests.Session()
\t\t\telse:  # Use the Requests API module as a "session".
\t\t\t\tfrom requests import api
\t\t\t\tself._session = api

\tdef _auth_headers(self):
\t\tif self._auth:
\t\t\treturn {'Authorization': 'Bearer {0}'.format(self._auth)}
\t\telif self.client_credentials_manager:
\t\t\ttoken = self.client_credentials_manager.get_access_token()
\t\t\treturn {'Authorization': 'Bearer {0}'.format(token)}
\t\telse:
\t\t\treturn {}

\tdef _internal_call(self, method, url, payload, params):
\t\targs = dict(params=params)
\t\targs["timeout"] = self.requests_timeout
\t\tif not url.startswith('http'):
\t\t\turl = self.prefix + url
\t\theaders = self._auth_headers()
\t\theaders['Content-Type'] = 'application/json'

\t\tif payload:
\t\t\targs["data"] = json.dumps(payload)

\t\tif self.trace_out:
\t\t\tprint(url)
\t\tr = self._session.request(method, url, headers=headers, proxies=self.proxies, **args)

\t\tif self.trace:  # pragma: no cover
\t\t\tprint()
\t\t\tprint ('headers', headers)
\t\t\tprint ('http status', r.status_code)
\t\t\tprint(method, r.url)
\t\t\tif payload:
\t\t\t\tprint("DATA", json.dumps(payload))

\t\ttry:
\t\t\tr.raise_for_status()
\t\texcept:
\t\t\tif r.text and len(r.text) > 0 and r.text != 'null':
\t\t\t\traise SpotifyException(r.status_code,
\t\t\t\t\t-1, '%s:\n %s' % (r.url, r.json()['error']['message']),
\t\t\t\t\theaders=r.headers)
\t\t\telse:
\t\t\t\traise SpotifyException(r.status_code,
\t\t\t\t\t-1, '%s:\n %s' % (r.url, 'error'), headers=r.headers)
\t\tfinally:
\t\t\tr.connection.close()
\t\tif r.text and len(r.text) > 0 and r.text != 'null':
\t\t\tresults = r.json()
\t\t\tif self.trace:  # pragma: no cover
\t\t\t\tprint('RESP', results)
\t\t\t\tprint()
\t\t\treturn results
\t\telse:
\t\t\treturn None

\tdef _get(self, url, args=None, payload=None, **kwargs):
\t\tif args:
\t\t\tkwargs.update(args)
\t\tretries = self.max_get_retries
\t\tdelay = 1
\t\twhile retries > 0:
\t\t\ttry:
\t\t\t\treturn self._internal_call('GET', url, payload, kwargs)
\t\t\texcept SpotifyException as e:
\t\t\t\tretries -= 1
\t\t\t\tstatus = e.http_status
\t\t\t\t# 429 means we hit a rate limit, backoff
\t\t\t\tif status == 429 or (status >= 500 and status < 600):
\t\t\t\t\tif retries < 0:
\t\t\t\t\t\traise
\t\t\t\t\telse:
\t\t\t\t\t\tsleep_seconds = int(e.headers.get('Retry-After', delay))
\t\t\t\t\t\tprint ('retrying ...' + str(sleep_seconds) + 'secs')
\t\t\t\t\t\ttime.sleep(sleep_seconds + 1)
\t\t\t\t\t\tdelay += 1
\t\t\t\telse:
\t\t\t\t\traise
\t\t\texcept Exception as e:
\t\t\t\traise
\t\t\t\tprint ('exception', str(e))
\t\t\t\t# some other exception. Requests have
\t\t\t\t# been know to throw a BadStatusLine exception
\t\t\t\tretries -= 1
\t\t\t\tif retries >= 0:
\t\t\t\t\tsleep_seconds = int(e.headers.get('Retry-After', delay))
\t\t\t\t\tprint ('retrying ...' + str(delay) + 'secs')
\t\t\t\t\ttime.sleep(sleep_seconds + 1)
\t\t\t\t\tdelay += 1
\t\t\t\telse:
\t\t\t\t\traise

\tdef _post(self, url, args=None, payload=None, **kwargs):
\t\tif args:
\t\t\tkwargs.update(args)
\t\treturn self._internal_call('POST', url, payload, kwargs)

\tdef _delete(self, url, args=None, payload=None, **kwargs):
\t\tif args:
\t\t\tkwargs.update(args)
\t\treturn self._internal_call('DELETE', url, payload, kwargs)

\tdef _put(self, url, args=None, payload=None, **kwargs):
\t\tif args:
\t\t\tkwargs.update(args)
\t\treturn self._internal_call('PUT', url, payload, kwargs)

\tdef next(self, result):
\t\t''' returns the next result given a paged result

\t\t\tParameters:
\t\t\t\t- result - a previously returned paged result
\t\t'''
\t\tif result['next']:
\t\t\treturn self._get(result['next'])
\t\telse:
\t\t\treturn None

\tdef previous(self, result):
\t\t''' returns the previous result given a paged result

\t\t\tParameters:
\t\t\t\t- result - a previously returned paged result
\t\t'''
\t\tif result['previous']:
\t\t\treturn self._get(result['previous'])
\t\telse:
\t\t\treturn None

\tdef _warn_old(self, msg):
\t\tprint('warning:' + msg, file=sys.stderr)

\tdef _warn(self, msg, *args):
\t\tprint('warning:' + msg.format(*args), file=sys.stderr)

\tdef track(self, track_id):
\t\t''' returns a single track given the track's ID, URI or URL

\t\t\tParameters:
\t\t\t\t- track_id - a spotify URI, URL or ID
\t\t'''

\t\ttrid = self._get_id('track', track_id)
\t\treturn self._get('tracks/' + trid)

\tdef tracks(self, tracks, market = None):
\t\t''' returns a list of tracks given a list of track IDs, URIs, or URLs

\t\t\tParameters:
\t\t\t\t- tracks - a list of spotify URIs, URLs or IDs
\t\t\t\t- market - an ISO 3166-1 alpha-2 country code.
\t\t'''

\t\ttlist = [self._get_id('track', t) for t in tracks]
\t\treturn self._get('tracks/?ids=' + ','.join(tlist), market = market)

\tdef artist(self, artist_id):
\t\t''' returns a single artist given the artist's ID, URI or URL

\t\t\tParameters:
\t\t\t\t- artist_id - an artist ID, URI or URL
\t\t'''

\t\ttrid = self._get_id('artist', artist_id)
\t\treturn self._get('artists/' + trid)

\tdef artists(self, artists):
\t\t''' returns a list of artists given the artist IDs, URIs, or URLs

\t\t\tParameters:
\t\t\t\t- artists - a list of  artist IDs, URIs or URLs
\t\t'''

\t\ttlist = [self._get_id('artist', a) for a in artists]
\t\treturn self._get('artists/?ids=' + ','.join(tlist))

\tdef artist_albums(self, artist_id, album_type=None, country=None, limit=20,
\t\t\t\t\t  offset=0):
\t\t''' Get Spotify catalog information about an artist's albums

\t\t\tParameters:
\t\t\t\t- artist_id - the artist ID, URI or URL
\t\t\t\t- album_type - 'album', 'single', 'appears_on', 'compilation'
\t\t\t\t- country - limit the response to one particular country.
\t\t\t\t- limit  - the number of albums to return
\t\t\t\t- offset - the index of the first album to return
\t\t'''

\t\ttrid = self._get_id('artist', artist_id)
\t\treturn self._get('artists/' + trid + '/albums', album_type=album_type,
\t\t\t\t\t\t country=country, limit=limit, offset=offset)

\tdef artist_top_tracks(self, artist_id, country='US'):
\t\t''' Get Spotify catalog information about an artist's top 10 tracks
\t\t\tby country.

\t\t\tParameters:
\t\t\t\t- artist_id - the artist ID, URI or URL
\t\t\t\t- country - limit the response to one particular country.
\t\t'''

\t\ttrid = self._get_id('artist', artist_id)
\t\treturn self._get('artists/' + trid + '/top-tracks', country=country)

\tdef artist_related_artists(self, artist_id):
\t\t''' Get Spotify catalog information about artists similar to an
\t\t\tidentified artist. Similarity is based on analysis of the
\t\t\tSpotify community's listening history.

\t\t\tParameters:
\t\t\t\t- artist_id - the artist ID, URI or URL
\t\t'''
\t\ttrid = self._get_id('artist', artist_id)
\t\treturn self._get('artists/' + trid + '/related-artists')

\tdef album(self, album_id):
\t\t''' returns a single album given the album's ID, URIs or URL

\t\t\tParameters:
\t\t\t\t- album_id - the album ID, URI or URL
\t\t'''

\t\ttrid = self._get_id('album', album_id)
\t\treturn self._get('albums/' + trid)

\tdef album_tracks(self, album_id, limit=50, offset=0):
\t\t''' Get Spotify catalog information about an album's tracks

\t\t\tParameters:
\t\t\t\t- album_id - the album ID, URI or URL
\t\t\t\t- limit  - the number of items to return
\t\t\t\t- offset - the index of the first item to return
\t\t'''

\t\ttrid = self._get_id('album', album_id)
\t\treturn self._get('albums/' + trid + '/tracks/', limit=limit,
\t\t\t\t\t\t offset=offset)

\tdef albums(self, albums):
\t\t''' returns a list of albums given the album IDs, URIs, or URLs

\t\t\tParameters:
\t\t\t\t- albums - a list of  album IDs, URIs or URLs
\t\t'''

\t\ttlist = [self._get_id('album', a) for a in albums]
\t\treturn self._get('albums/?ids=' + ','.join(tlist))

\tdef search(self, q, limit=10, offset=0, type='track', market=None):
\t\t''' searches for an item

\t\t\tParameters:
\t\t\t\t- q - the search query
\t\t\t\t- limit  - the number of items to return
\t\t\t\t- offset - the index of the first item to return
\t\t\t\t- type - the type of item to return. One of 'artist', 'album',
\t\t\t\t\t\t 'track' or 'playlist'
\t\t\t\t- market - An ISO 3166-1 alpha-2 country code or the string from_token.
\t\t'''
\t\treturn self._get('search', q=q, limit=limit, offset=offset, type=type, market=market)

\tdef user(self, user):
\t\t''' Gets basic profile information about a Spotify User

\t\t\tParameters:
\t\t\t\t- user - the id of the usr
\t\t'''
\t\treturn self._get('users/' + user)

\tdef current_user_playlists(self, limit=50, offset=0):
\t\t""" Get current user playlists without required getting his profile
\t\t\tParameters:
\t\t\t\t- limit  - the number of items to return
\t\t\t\t- offset - the index of the first item to return
\t\t"""
\t\treturn self._get("me/playlists", limit=limit, offset=offset)

\tdef user_playlists(self, user, limit=50, offset=0):
\t\t''' Gets playlists of a user

\t\t\tParameters:
\t\t\t\t- user - the id of the usr
\t\t\t\t- limit  - the number of items to return
\t\t\t\t- offset - the index of the first item to return
\t\t'''
\t\treturn self._get("users/%s/playlists" % user, limit=limit,
\t\t\t\t\t\t offset=offset)

\tdef user_playlist(self, user, playlist_id=None, fields=None):
\t\t''' Gets playlist of a user
\t\t\tParameters:
\t\t\t\t- user - the id of the user
\t\t\t\t- playlist_id - the id of the playlist
\t\t\t\t- fields - which fields to return
\t\t'''
\t\tif playlist_id is None:
\t\t\treturn self._get("users/%s/starred" % (user), fields=fields)
\t\tplid = self._get_id('playlist', playlist_id)
\t\treturn self._get("users/%s/playlists/%s" % (user, plid), fields=fields)

\tdef user_playlist_tracks(self, user, playlist_id=None, fields=None,
\t\t\t\t\t\t\t limit=100, offset=0, market=None):
\t\t''' Get full details of the tracks of a playlist owned by a user.

\t\t\tParameters:
\t\t\t\t- user - the id of the user
\t\t\t\t- playlist_id - the id of the playlist
\t\t\t\t- fields - which fields to return
\t\t\t\t- limit - the maximum number of tracks to return
\t\t\t\t- offset - the index of the first track to return
\t\t\t\t- market - an ISO 3166-1 alpha-2 country code.
\t\t'''
\t\tplid = self._get_id('playlist', playlist_id)
\t\treturn self._get("users/%s/playlists/%s/tracks" % (user, plid),
\t\t\t\t\t\t limit=limit, offset=offset, fields=fields,
\t\t\t\t\t\t market=market)

\tdef user_playlist_create(self, user, name, public=True):
\t\t''' Creates a playlist for a user

\t\t\tParameters:
\t\t\t\t- user - the id of the user
\t\t\t\t- name - the name of the playlist
\t\t\t\t- public - is the created playlist public
\t\t\t\t- description - the description of the playlist
\t\t'''
\t\tdata = {'name': name, 'public': public, 'description': description}
\t\treturn self._post("users/%s/playlists" % (user,), payload=data)

\tdef user_playlist_change_details(
\t\t\tself, user, playlist_id, name=None, public=None,
\t\t\tcollaborative=None, description=None):
\t\t''' Changes a playlist's name and/or public/private state

\t\t\tParameters:
\t\t\t\t- user - the id of the user
\t\t\t\t- playlist_id - the id of the playlist
\t\t\t\t- name - optional name of the playlist
\t\t\t\t- public - optional is the playlist public
\t\t\t\t- collaborative - optional is the playlist collaborative
\t\t\t\t- description - optional description of the playlist
\t\t'''
\t\tdata = {}
\t\tif isinstance(name, six.string_types):
\t\t\tdata['name'] = name
\t\tif isinstance(public, bool):
\t\t\tdata['public'] = public
\t\tif isinstance(collaborative, bool):
\t\t\tdata['collaborative'] = collaborative
\t\tif isinstance(description, six.string_types):
\t\t\tdata['description'] = description
\t\treturn self._put("users/%s/playlists/%s" % (user, playlist_id),
\t\t\t\t\t\t payload=data)

\tdef user_playlist_unfollow(self, user, playlist_id):
\t\t''' Unfollows (deletes) a playlist for a user

\t\t\tParameters:
\t\t\t\t- user - the id of the user
\t\t\t\t- name - the name of the playlist
\t\t'''
\t\treturn self._delete("users/%s/playlists/%s/followers" % (user, playlist_id))

\tdef user_playlist_add_tracks(self, user, playlist_id, tracks,
\t\t\t\t\t\t\t\t position=None):
\t\t''' Adds tracks to a playlist

\t\t\tParameters:
\t\t\t\t- user - the id of the user
\t\t\t\t- playlist_id - the id of the playlist
\t\t\t\t- tracks - a list of track URIs, URLs or IDs
\t\t\t\t- position - the position to add the tracks
\t\t'''
\t\tplid = self._get_id('playlist', playlist_id)
\t\tftracks = [self._get_uri('track', tid) for tid in tracks]
\t\treturn self._post("users/%s/playlists/%s/tracks" % (user, plid),
\t\t\t\t\t\t  payload=ftracks, position=position)

\tdef user_playlist_replace_tracks(self, user, playlist_id, tracks):
\t\t''' Replace all tracks in a playlist

\t\t\tParameters:
\t\t\t\t- user - the id of the user
\t\t\t\t- playlist_id - the id of the playlist
\t\t\t\t- tracks - the list of track ids to add to the playlist
\t\t'''
\t\tplid = self._get_id('playlist', playlist_id)
\t\tftracks = [self._get_uri('track', tid) for tid in tracks]
\t\tpayload = {"uris": ftracks}
\t\treturn self._put("users/%s/playlists/%s/tracks" % (user, plid),
\t\t\t\t\t\t payload=payload)

\tdef user_playlist_reorder_tracks(
\t\t\tself, user, playlist_id, range_start, insert_before,
\t\t\trange_length=1, snapshot_id=None):
\t\t''' Reorder tracks in a playlist

\t\t\tParameters:
\t\t\t\t- user - the id of the user
\t\t\t\t- playlist_id - the id of the playlist
\t\t\t\t- range_start - the position of the first track to be reordered
\t\t\t\t- range_length - optional the number of tracks to be reordered (default: 1)
\t\t\t\t- insert_before - the position where the tracks should be inserted
\t\t\t\t- snapshot_id - optional playlist's snapshot ID
\t\t'''
\t\tplid = self._get_id('playlist', playlist_id)
\t\tpayload = {"range_start": range_start,
\t\t\t\t   "range_length": range_length,
\t\t\t\t   "insert_before": insert_before}
\t\tif snapshot_id:
\t\t\tpayload["snapshot_id"] = snapshot_id
\t\treturn self._put("users/%s/playlists/%s/tracks" % (user, plid),
\t\t\t\t\t\t payload=payload)

\tdef user_playlist_remove_all_occurrences_of_tracks(
\t\t\tself, user, playlist_id, tracks, snapshot_id=None):
\t\t''' Removes all occurrences of the given tracks from the given playlist

\t\t\tParameters:
\t\t\t\t- user - the id of the user
\t\t\t\t- playlist_id - the id of the playlist
\t\t\t\t- tracks - the list of track ids to add to the playlist
\t\t\t\t- snapshot_id - optional id of the playlist snapshot

\t\t'''

\t\tplid = self._get_id('playlist', playlist_id)
\t\tftracks = [self._get_uri('track', tid) for tid in tracks]
\t\tpayload = {"tracks": [{"uri": track} for track in ftracks]}
\t\tif snapshot_id:
\t\t\tpayload["snapshot_id"] = snapshot_id
\t\treturn self._delete("users/%s/playlists/%s/tracks" % (user, plid),
\t\t\t\t\t\t\tpayload=payload)

\tdef user_playlist_remove_specific_occurrences_of_tracks(
\t\t\tself, user, playlist_id, tracks, snapshot_id=None):
\t\t''' Removes all occurrences of the given tracks from the given playlist

\t\t\tParameters:
\t\t\t\t- user - the id of the user
\t\t\t\t- playlist_id - the id of the playlist
\t\t\t\t- tracks - an array of objects containing Spotify URIs of the tracks to remove with their current positions in the playlist.  For example:
\t\t\t\t\t[  { "uri":"4iV5W9uYEdYUVa79Axb7Rh", "positions":[2] },
\t\t\t\t\t   { "uri":"1301WleyT98MSxVHPZCA6M", "positions":[7] } ]
\t\t\t\t- snapshot_id - optional id of the playlist snapshot
\t\t'''

\t\tplid = self._get_id('playlist', playlist_id)
\t\tftracks = []
\t\tfor tr in tracks:
\t\t\tftracks.append({
\t\t\t\t"uri": self._get_uri("track", tr["uri"]),
\t\t\t\t"positions": tr["positions"],
\t\t\t})
\t\tpayload = {"tracks": ftracks}
\t\tif snapshot_id:
\t\t\tpayload["snapshot_id"] = snapshot_id
\t\treturn self._delete("users/%s/playlists/%s/tracks" % (user, plid),
\t\t\t\t\t\t\tpayload=payload)

\tdef user_playlist_follow_playlist(self, playlist_owner_id, playlist_id):
\t\t'''
\t\tAdd the current authenticated user as a follower of a playlist.

\t\tParameters:
\t\t\t- playlist_owner_id - the user id of the playlist owner
\t\t\t- playlist_id - the id of the playlist

\t\t'''
\t\treturn self._put("users/{}/playlists/{}/followers".format(playlist_owner_id, playlist_id))

\tdef user_playlist_is_following(self, playlist_owner_id, playlist_id, user_ids):
\t\t'''
\t\tCheck to see if the given users are following the given playlist

\t\tParameters:
\t\t\t- playlist_owner_id - the user id of the playlist owner
\t\t\t- playlist_id - the id of the playlist
\t\t\t- user_ids - the ids of the users that you want to check to see if they follow the playlist. Maximum: 5 ids.

\t\t'''
\t\treturn self._get("users/{}/playlists/{}/followers/contains?ids={}".format(playlist_owner_id, playlist_id, ','.join(user_ids)))

\tdef me(self):
\t\t''' Get detailed profile information about the current user.
\t\t\tAn alias for the 'current_user' method.
\t\t'''
\t\treturn self._get('me/')

\tdef current_user(self):
\t\t''' Get detailed profile information about the current user.
\t\t\tAn alias for the 'me' method.
\t\t'''
\t\treturn self.me()

\tdef current_user_playing_track(self):
\t\t''' Get information about the current users currently playing track.
\t\t'''
\t\treturn self._get('me/player/currently-playing')

\tdef current_user_recently_played(self, limit=50):
\t\t''' Gets a list of the albums saved in the current authorized user's
\t\t\t"Your Music" library

\t\t\tParameters:
\t\t\t\t- limit - the number of albums to return
\t\t\t\t- offset - the index of the first album to return
\t\t'''  
\t\treturn self._get('me/player/recently-played', limit=limit)
\t\t
\tdef current_user_saved_albums(self, limit=20, offset=0):
\t\t''' Gets a list of the albums saved in the current authorized user's
\t\t\t"Your Music" library

\t\t\tParameters:
\t\t\t\t- limit - the number of albums to return
\t\t\t\t- offset - the index of the first album to return

\t\t'''
\t\treturn self._get('me/albums', limit=limit, offset=offset)

\tdef current_user_saved_tracks(self, limit=20, offset=0):
\t\t''' Gets a list of the tracks saved in the current authorized user's
\t\t\t"Your Music" library

\t\t\tParameters:
\t\t\t\t- limit - the number of tracks to return
\t\t\t\t- offset - the index of the first track to return

\t\t'''
\t\treturn self._get('me/tracks', limit=limit, offset=offset)

\tdef current_user_followed_artists(self, limit=20, after=None):
\t\t''' Gets a list of the artists followed by the current authorized user

\t\t\tParameters:
\t\t\t\t- limit - the number of tracks to return
\t\t\t\t- after - ghe last artist ID retrieved from the previous request

\t\t'''
\t\treturn self._get('me/following', type='artist', limit=limit,
\t\t\t\t\t\t after=after)

\tdef current_user_saved_tracks_delete(self, tracks=None):
\t\t''' Remove one or more tracks from the current user's
\t\t\t"Your Music" library.

\t\t\tParameters:
\t\t\t\t- tracks - a list of track URIs, URLs or IDs
\t\t'''
\t\ttlist = []
\t\tif tracks is not None:
\t\t\ttlist = [self._get_id('track', t) for t in tracks]
\t\treturn self._delete('me/tracks/?ids=' + ','.join(tlist))

\tdef current_user_saved_tracks_contains(self, tracks=None):
\t\t''' Check if one or more tracks is already saved in
\t\t\tthe current Spotify user’s “Your Music” library.

\t\t\tParameters:
\t\t\t\t- tracks - a list of track URIs, URLs or IDs
\t\t'''
\t\ttlist = []
\t\tif tracks is not None:
\t\t\ttlist = [self._get_id('track', t) for t in tracks]
\t\treturn self._get('me/tracks/contains?ids=' + ','.join(tlist))

\tdef current_user_saved_tracks_add(self, tracks=None):
\t\t''' Add one or more tracks to the current user's
\t\t\t"Your Music" library.

\t\t\tParameters:
\t\t\t\t- tracks - a list of track URIs, URLs or IDs
\t\t'''
\t\ttlist = []
\t\tif tracks is not None:
\t\t\ttlist = [self._get_id('track', t) for t in tracks]
\t\treturn self._put('me/tracks/?ids=' + ','.join(tlist))

\tdef current_user_top_artists(self, limit=20, offset=0,
\t\t\t\t\t\t\t\t time_range='medium_term'):
\t\t''' Get the current user's top artists

\t\t\tParameters:
\t\t\t\t- limit - the number of entities to return
\t\t\t\t- offset - the index of the first entity to return
\t\t\t\t- time_range - Over what time frame are the affinities computed
\t\t\t\t  Valid-values: short_term, medium_term, long_term
\t\t'''
\t\treturn self._get('me/top/artists', time_range=time_range, limit=limit,
\t\t\t\t\t\t offset=offset)

\tdef current_user_top_tracks(self, limit=20, offset=0,
\t\t\t\t\t\t\t\ttime_range='medium_term'):
\t\t''' Get the current user's top tracks

\t\t\tParameters:
\t\t\t\t- limit - the number of entities to return
\t\t\t\t- offset - the index of the first entity to return
\t\t\t\t- time_range - Over what time frame are the affinities computed
\t\t\t\t  Valid-values: short_term, medium_term, long_term
\t\t'''
\t\treturn self._get('me/top/tracks', time_range=time_range, limit=limit,
\t\t\t\t\t\t offset=offset)

\tdef current_user_saved_albums_add(self, albums=[]):
\t\t''' Add one or more albums to the current user's
\t\t\t"Your Music" library.
\t\t\tParameters:
\t\t\t\t- albums - a list of album URIs, URLs or IDs
\t\t'''
\t\talist = [self._get_id('album', a) for a in albums]
\t\tr = self._put('me/albums?ids=' + ','.join(alist))
\t\treturn r

\tdef featured_playlists(self, locale=None, country=None, timestamp=None,
\t\t\t\t\t\t   limit=20, offset=0):
\t\t''' Get a list of Spotify featured playlists

\t\t\tParameters:
\t\t\t\t- locale - The desired language, consisting of a lowercase ISO
\t\t\t\t  639 language code and an uppercase ISO 3166-1 alpha-2 country
\t\t\t\t  code, joined by an underscore.

\t\t\t\t- country - An ISO 3166-1 alpha-2 country code.

\t\t\t\t- timestamp - A timestamp in ISO 8601 format:
\t\t\t\t  yyyy-MM-ddTHH:mm:ss. Use this parameter to specify the user's
\t\t\t\t  local time to get results tailored for that specific date and
\t\t\t\t  time in the day

\t\t\t\t- limit - The maximum number of items to return. Default: 20.
\t\t\t\t  Minimum: 1. Maximum: 50

\t\t\t\t- offset - The index of the first item to return. Default: 0
\t\t\t\t  (the first object). Use with limit to get the next set of
\t\t\t\t  items.
\t\t'''
\t\treturn self._get('browse/featured-playlists', locale=locale,
\t\t\t\t\t\t country=country, timestamp=timestamp, limit=limit,
\t\t\t\t\t\t offset=offset)

\tdef new_releases(self, country=None, limit=20, offset=0):
\t\t''' Get a list of new album releases featured in Spotify

\t\t\tParameters:
\t\t\t\t- country - An ISO 3166-1 alpha-2 country code.

\t\t\t\t- limit - The maximum number of items to return. Default: 20.
\t\t\t\t  Minimum: 1. Maximum: 50

\t\t\t\t- offset - The index of the first item to return. Default: 0
\t\t\t\t  (the first object). Use with limit to get the next set of
\t\t\t\t  items.
\t\t'''
\t\treturn self._get('browse/new-releases', country=country, limit=limit,
\t\t\t\t\t\t offset=offset)

\tdef categories(self, country=None, locale=None, limit=20, offset=0):
\t\t''' Get a list of new album releases featured in Spotify

\t\t\tParameters:
\t\t\t\t- country - An ISO 3166-1 alpha-2 country code.
\t\t\t\t- locale - The desired language, consisting of an ISO 639
\t\t\t\t  language code and an ISO 3166-1 alpha-2 country code, joined
\t\t\t\t  by an underscore.

\t\t\t\t- limit - The maximum number of items to return. Default: 20.
\t\t\t\t  Minimum: 1. Maximum: 50

\t\t\t\t- offset - The index of the first item to return. Default: 0
\t\t\t\t  (the first object). Use with limit to get the next set of
\t\t\t\t  items.
\t\t'''
\t\treturn self._get('browse/categories', country=country, locale=locale,
\t\t\t\t\t\t limit=limit, offset=offset)

\tdef category_playlists(self, category_id=None, country=None, limit=20,
\t\t\t\t\t\t   offset=0):
\t\t''' Get a list of new album releases featured in Spotify

\t\t\tParameters:
\t\t\t\t- category_id - The Spotify category ID for the category.

\t\t\t\t- country - An ISO 3166-1 alpha-2 country code.

\t\t\t\t- limit - The maximum number of items to return. Default: 20.
\t\t\t\t  Minimum: 1. Maximum: 50

\t\t\t\t- offset - The index of the first item to return. Default: 0
\t\t\t\t  (the first object). Use with limit to get the next set of
\t\t\t\t  items.
\t\t'''
\t\treturn self._get('browse/categories/' + category_id + '/playlists',
\t\t\t\t\t\t country=country, limit=limit, offset=offset)

\tdef recommendations(self, seed_artists=None, seed_genres=None,
\t\t\t\t\t\tseed_tracks=None, limit=20, country=None, **kwargs):
\t\t''' Get a list of recommended tracks for one to five seeds.

\t\t\tParameters:
\t\t\t\t- seed_artists - a list of artist IDs, URIs or URLs

\t\t\t\t- seed_tracks - a list of artist IDs, URIs or URLs

\t\t\t\t- seed_genres - a list of genre names. Available genres for
\t\t\t\t  recommendations can be found by calling recommendation_genre_seeds

\t\t\t\t- country - An ISO 3166-1 alpha-2 country code. If provided, all
\t\t\t\t  results will be playable in this country.

\t\t\t\t- limit - The maximum number of items to return. Default: 20.
\t\t\t\t  Minimum: 1. Maximum: 100

\t\t\t\t- min/max/target_<attribute> - For the tuneable track attributes listed
\t\t\t\t  in the documentation, these values provide filters and targeting on
\t\t\t\t  results.
\t\t'''
\t\tparams = dict(limit=limit)
\t\tif seed_artists:
\t\t\tparams['seed_artists'] = ','.join(
\t\t\t\t[self._get_id('artist', a) for a in seed_artists])
\t\tif seed_genres:
\t\t\tparams['seed_genres'] = ','.join(seed_genres)
\t\tif seed_tracks:
\t\t\tparams['seed_tracks'] = ','.join(
\t\t\t\t[self._get_id('track', t) for t in seed_tracks])
\t\tif country:
\t\t\tparams['market'] = country

\t\tfor attribute in ["acousticness", "danceability", "duration_ms",
\t\t\t\t\t\t  "energy", "instrumentalness", "key", "liveness",
\t\t\t\t\t\t  "loudness", "mode", "popularity", "speechiness",
\t\t\t\t\t\t  "tempo", "time_signature", "valence"]:
\t\t\tfor prefix in ["min_", "max_", "target_"]:
\t\t\t\tparam = prefix + attribute
\t\t\t\tif param in kwargs:
\t\t\t\t\tparams[param] = kwargs[param]
\t\treturn self._get('recommendations', **params)

\tdef recommendation_genre_seeds(self):
\t\t''' Get a list of genres available for the recommendations function.
\t\t'''
\t\treturn self._get('recommendations/available-genre-seeds')

\tdef audio_analysis(self, track_id):
\t\t''' Get audio analysis for a track based upon its Spotify ID
\t\t\tParameters:
\t\t\t\t- track_id - a track URI, URL or ID
\t\t'''
\t\ttrid = self._get_id('track', track_id)
\t\treturn self._get('audio-analysis/' + trid)

\tdef audio_features(self, tracks=[]):
\t\t''' Get audio features for one or multiple tracks based upon their Spotify IDs
\t\t\tParameters:
\t\t\t\t- tracks - a list of track URIs, URLs or IDs, maximum: 50 ids
\t\t'''
\t\tif isinstance(tracks, str):
\t\t\ttrackid = self._get_id('track', tracks)
\t\t\tresults = self._get('audio-features/?ids=' + trackid)
\t\telse:
\t\t\ttlist = [self._get_id('track', t) for t in tracks]
\t\t\tresults = self._get('audio-features/?ids=' + ','.join(tlist))
\t\t# the response has changed, look for the new style first, and if
\t\t# its not there, fallback on the old style
\t\tif 'audio_features' in results:
\t\t\treturn results['audio_features']
\t\telse:
\t\t\treturn results

\tdef audio_analysis(self, id):
\t\t''' Get audio analysis for a track based upon its Spotify ID
\t\t\tParameters:
\t\t\t\t- id - a track URIs, URLs or IDs
\t\t'''
\t\tid = self._get_id('track', id)
\t\treturn self._get('audio-analysis/'+id)

\tdef devices(self):
\t\t''' Get a list of user's available devices.
\t\t'''
\t\treturn self._get("me/player/devices")

\tdef current_playback(self, market = None):
\t\t''' Get information about user's current playback.

\t\t\tParameters:
\t\t\t\t- market - an ISO 3166-1 alpha-2 country code.
\t\t'''
\t\treturn self._get("me/player", market = market)

\tdef currently_playing(self, market = None):
\t\t''' Get user's currently playing track.

\t\t\tParameters:
\t\t\t\t- market - an ISO 3166-1 alpha-2 country code.
\t\t'''
\t\treturn self._get("me/player/currently-playing", market = market)

\tdef transfer_playback(self, device_id, force_play = True):
\t\t''' Transfer playback to another device.
\t\t\tNote that the API accepts a list of device ids, but only
\t\t\tactually supports one.

\t\t\tParameters:
\t\t\t\t- device_id - transfer playback to this device
\t\t\t\t- force_play - true: after transfer, play. false:
\t\t\t\t\t\t\t   keep current state.
\t\t'''
\t\tdata = {
\t\t\t'device_ids': [device_id],
\t\t\t'play': force_play
\t\t}
\t\treturn self._put("me/player", payload=data)

\tdef start_playback(self, device_id = None, context_uri = None, uris = None, offset = None):
\t\t''' Start or resume user's playback.

\t\t\tProvide a `context_uri` to start playback or a album,
\t\t\tartist, or playlist.

\t\t\tProvide a `uris` list to start playback of one or more
\t\t\ttracks.

\t\t\tProvide `offset` as {"position": <int>} or {"uri": "<track uri>"}
\t\t\tto start playback at a particular offset.

\t\t\tParameters:
\t\t\t\t- device_id - device target for playback
\t\t\t\t- context_uri - spotify context uri to play
\t\t\t\t- uris - spotify track uris
\t\t\t\t- offset - offset into context by index or track
\t\t'''
\t\tif context_uri is not None and uris is not None:
\t\t\tself._warn('specify either context uri or uris, not both')
\t\t\treturn
\t\tif uris is not None and not isinstance(uris, list):
\t\t\tself._warn('uris must be a list')
\t\t\treturn
\t\tdata = {}
\t\tif context_uri is not None:
\t\t\tdata['context_uri'] = context_uri
\t\tif uris is not None:
\t\t\tdata['uris'] = uris
\t\tif offset is not None:
\t\t\tdata['offset'] = offset
\t\treturn self._put(self._append_device_id("me/player/play", device_id), payload=data)

\tdef pause_playback(self, device_id = None):
\t\t''' Pause user's playback.

\t\t\tParameters:
\t\t\t\t- device_id - device target for playback
\t\t'''
\t\treturn self._put(self._append_device_id("me/player/pause", device_id))

\tdef next_track(self, device_id = None):
\t\t''' Skip user's playback to next track.

\t\t\tParameters:
\t\t\t\t- device_id - device target for playback
\t\t'''
\t\treturn self._post(self._append_device_id("me/player/next", device_id))

\tdef previous_track(self, device_id = None):
\t\t''' Skip user's playback to previous track.

\t\t\tParameters:
\t\t\t\t- device_id - device target for playback
\t\t'''
\t\treturn self._post(self._append_device_id("me/player/previous", device_id))

\tdef seek_track(self, position_ms, device_id = None):
\t\t''' Seek to position in current track.

\t\t\tParameters:
\t\t\t\t- position_ms - position in milliseconds to seek to
\t\t\t\t- device_id - device target for playback
\t\t'''
\t\tif not isinstance(position_ms, int):
\t\t\tself._warn('position_ms must be an integer')
\t\t\treturn
\t\treturn self._put(self._append_device_id("me/player/seek?position_ms=%s" % position_ms, device_id))

\tdef repeat(self, state, device_id = None):
\t\t''' Set repeat mode for playback.

\t\t\tParameters:
\t\t\t\t- state - `track`, `context`, or `off`
\t\t\t\t- device_id - device target for playback
\t\t'''
\t\tif state not in ['track', 'context', 'off']:
\t\t\tself._warn('invalid state')
\t\t\treturn
\t\tself._put(self._append_device_id("me/player/repeat?state=%s" % state, device_id))

\tdef volume(self, volume_percent, device_id = None):
\t\t''' Set playback volume.

\t\t\tParameters:
\t\t\t\t- volume_percent - volume between 0 and 100
\t\t\t\t- device_id - device target for playback
\t\t'''
\t\tif not isinstance(volume_percent, int):
\t\t\tself._warn('volume must be an integer')
\t\t\treturn
\t\tif volume_percent < 0 or volume_percent > 100:
\t\t\tself._warn('volume must be between 0 and 100, inclusive')
\t\t\treturn
\t\tself._put(self._append_device_id("me/player/volume?volume_percent=%s" % volume_percent, device_id))

\tdef shuffle(self, state, device_id = None):
\t\t''' Toggle playback shuffling.

\t\t\tParameters:
\t\t\t\t- state - true or false
\t\t\t\t- device_id - device target for playback
\t\t'''
\t\tif not isinstance(state, bool):
\t\t\tself._warn('state must be a boolean')
\t\t\treturn
\t\tstate = str(state).lower()
\t\tself._put(self._append_device_id("me/player/shuffle?state=%s" % state, device_id))

\tdef _append_device_id(self, path, device_id):
\t\t''' Append device ID to API path.

\t\t\tParameters:
\t\t\t\t- device_id - device id to append
\t\t'''
\t\tif device_id:
\t\t\tif '?' in path:
\t\t\t\tpath += "&device_id=%s" % device_id
\t\t\telse:
\t\t\t\tpath += "?device_id=%s" % device_id
\t\treturn path

\tdef _get_id(self, type, id):
\t\tfields = id.split(':')
\t\tif len(fields) >= 3:
\t\t\tif type != fields[-2]:
\t\t\t\tself._warn('expected id of type %s but found type %s %s',
\t\t\t\t\t\t   type, fields[-2], id)
\t\t\treturn fields[-1]
\t\tfields = id.split('/')
\t\tif len(fields) >= 3:
\t\t\titype = fields[-2]
\t\t\tif type != itype:
\t\t\t\tself._warn('expected id of type %s but found type %s %s',
\t\t\t\t\t\t   type, itype, id)
\t\t\treturn fields[-1]
\t\treturn id

\tdef _get_uri(self, type, id):
\t\treturn 'spotify:' + type + ":" + self._get_id(type, id)
