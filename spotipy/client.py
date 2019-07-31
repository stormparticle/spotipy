
# shows a user's playlists (need to be authenticated via oauth)

from __future__ import print_function
import sys
import os
import socket
import errno


PY3 = sys.version_info.major == 3

if PY3:
\tfrom http.server import HTTPServer, BaseHTTPRequestHandler
\tfrom urllib.parse import urlparse, parse_qsl
else:
\tfrom BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
\tfrom urlparse import urlparse, parse_qsl


from . import oauth2
import spotipy

def prompt_for_user_token(username, scope=None, client_id = None,
\t\tclient_secret = None, redirect_uri = None, cache_path = None):
\t''' prompts the user to login if necessary and returns
\t\tthe user token suitable for use with the spotipy.Spotify 
\t\tconstructor

\t\tParameters:

\t\t - username - the Spotify username
\t\t - scope - the desired scope of the request
\t\t - client_id - the client id of your app
\t\t - client_secret - the client secret of your app
\t\t - redirect_uri - the redirect URI of your app
\t\t - cache_path - path to location to save tokens

\t'''

\tif not client_id:
\t\tclient_id = os.getenv('SPOTIPY_CLIENT_ID')

\tif not client_secret:
\t\tclient_secret = os.getenv('SPOTIPY_CLIENT_SECRET')

\tif not redirect_uri:
\t\tredirect_uri = os.getenv('SPOTIPY_REDIRECT_URI')

\tif not client_id:
\t\tprint('''
\t\t\tYou need to set your Spotify API credentials. You can do this by
\t\t\tsetting environment variables like so:

\t\t\texport SPOTIPY_CLIENT_ID='your-spotify-client-id'
\t\t\texport SPOTIPY_CLIENT_SECRET='your-spotify-client-secret'
\t\t\texport SPOTIPY_REDIRECT_URI='your-app-redirect-url'

\t\t\tGet your credentials at\t 
\t\t\t\thttps://developer.spotify.com/my-applications
\t\t''')
\t\traise spotipy.SpotifyException(550, -1, 'no credentials set')

\tcache_path = cache_path or ".cache-" + username
\tsp_oauth = oauth2.SpotifyOAuth(client_id, client_secret, redirect_uri, 
\t\tscope=scope, cache_path=cache_path)

\t# try to get a valid token for this user, from the cache,
\t# if not in the cache, the create a new (this will send
\t# the user to a web page where they can authorize this app)

\ttoken_info = sp_oauth.get_cached_token()

\tif not token_info:
\t\tprint('''

\t\t\tUser authentication requires interaction with your
\t\t\tweb browser. Once you enter your credentials and
\t\t\tgive authorization, you will be redirected to
\t\t\ta url.  Paste that url you were directed to to
\t\t\tcomplete the authorization.

\t\t''')
\t\tauth_url = sp_oauth.get_authorize_url()
\t\ttry:
\t\t\timport webbrowser
\t\t\twebbrowser.open(auth_url)
\t\t\tprint("Opened %s in your browser" % auth_url)
\t\texcept:
\t\t\tprint("Please navigate here: %s" % auth_url)

\t\tprint()
\t\tprint()
\t\ttry:
\t\t\tresponse = raw_input("Enter the URL you were redirected to: ")
\t\texcept NameError:
\t\t\tresponse = input("Enter the URL you were redirected to: ")

\t\tprint()
\t\tprint() 

\t\tcode = sp_oauth.parse_response_code(response)
\t\ttoken_info = sp_oauth.get_access_token(code)
\t# Auth'ed API request
\tif token_info:
\t\treturn token_info['access_token']
\telse:
\t\treturn None


class RequestHandler(BaseHTTPRequestHandler):
\tdef do_GET(self):
\t\tquery_s = urlparse(self.path).query
\t\tform = dict(parse_qsl(query_s))

\t\tself.send_response(200)
\t\tself.send_header("Content-Type", "text/html")
\t\tself.end_headers()

\t\tif "code" in form:
\t\t\tself.server.auth_code = form["code"]
\t\t\tself.server.error = None
\t\t\tstatus = "successful"
\t\telif "error" in form:
\t\t\tself.server.error = form["error"]
\t\t\tself.server.auth_code = None
\t\t\tstatus = "failed ({})".format(form["error"])
\t\telse:
\t\t\tself._write("<html><body><h1>Invalid request</h1></body></html>")
\t\t\treturn

\t\tself._write(
\t\t\t"<html><body><h1>Authentication status: {}</h1>Now you can close this window.</body></html>".format(status))

\tdef _write(self, text):
\t\treturn self.wfile.write(text.encode("utf-8"))

\tdef log_message(self, format, *args):
\t\treturn

def start_local_http_server(port, handler=RequestHandler):
\twhile True:
\t\ttry:
\t\t\tserver = HTTPServer(("127.0.0.1", port), handler)
\t\texcept socket.error as err:
\t\t\tif err.errno != errno.EADDRINUSE:
\t\t\t\traise
\t\telse:
\t\t\tserver.auth_code = None
\t\t\treturn server


def obtain_token_localhost(username, client_id, client_secret, redirect_uri, cache_path=None, scope=None):
\tcache_path = cache_path or ".cache-" + username

\tsp_oauth = oauth2.SpotifyOAuth(client_id, client_secret, redirect_uri, scope=scope, cache_path=cache_path)

\ttoken_info = sp_oauth.get_cached_token()

\tif token_info:
\t\treturn token_info['access_token']

\tprint("Authorzing User...")
\tauth_url = sp_oauth.get_authorize_url()
\ttry:
\t\timport webbrowser
\t\twebbrowser.open(auth_url)
\t\t#print("Opened %s in your browser" % auth_url)
\texcept:
\t\tprint("Please navigate here: %s" % auth_url)
\turl_info = urlparse(redirect_uri)
\tnetloc = url_info.netloc
\tif ":" in netloc:
\t\tport = int(netloc.split(":", 1)[1])
\telse:
\t\tport = 80

\tserver = start_local_http_server(port)
\tserver.handle_request()
\tif server.auth_code:
\t\ttoken_info = sp_oauth.get_access_token(server.auth_code)
\t\tprint("Authorized!")
\t\treturn token_info['access_token']