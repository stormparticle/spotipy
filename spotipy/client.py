
# shows a user's playlists (need to be authenticated via oauth)

from __future__ import print_function
import sys
import os
import socket
import errno


PY3 = sys.version_info.major == 3

if PY3:
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from urllib.parse import urlparse, parse_qsl
else:
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
    from urlparse import urlparse, parse_qsl


from . import oauth2
import spotipy

def prompt_for_user_token(username, scope=None, client_id = None,
        client_secret = None, redirect_uri = None, cache_path = None):
    ''' prompts the user to login if necessary and returns
        the user token suitable for use with the spotipy.Spotify 
        constructor

        Parameters:

         - username - the Spotify username
         - scope - the desired scope of the request
         - client_id - the client id of your app
         - client_secret - the client secret of your app
         - redirect_uri - the redirect URI of your app
         - cache_path - path to location to save tokens

    '''

    if not client_id:
        client_id = os.getenv('SPOTIPY_CLIENT_ID')

    if not client_secret:
        client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')

    if not redirect_uri:
        redirect_uri = os.getenv('SPOTIPY_REDIRECT_URI')

    if not client_id:
        print('''
            You need to set your Spotify API credentials. You can do this by
            setting environment variables like so:

            export SPOTIPY_CLIENT_ID='your-spotify-client-id'
            export SPOTIPY_CLIENT_SECRET='your-spotify-client-secret'
            export SPOTIPY_REDIRECT_URI='your-app-redirect-url'

            Get your credentials at     
                https://developer.spotify.com/my-applications
        ''')
        raise spotipy.SpotifyException(550, -1, 'no credentials set')

    cache_path = cache_path or ".cache-" + username
    sp_oauth = oauth2.SpotifyOAuth(client_id, client_secret, redirect_uri, 
        scope=scope, cache_path=cache_path)

    # try to get a valid token for this user, from the cache,
    # if not in the cache, the create a new (this will send
    # the user to a web page where they can authorize this app)

    token_info = sp_oauth.get_cached_token()

    if not token_info:
        print('''

            User authentication requires interaction with your
            web browser. Once you enter your credentials and
            give authorization, you will be redirected to
            a url.  Paste that url you were directed to to
            complete the authorization.

        ''')
        auth_url = sp_oauth.get_authorize_url()
        try:
            import webbrowser
            webbrowser.open(auth_url)
            print("Opened %s in your browser" % auth_url)
        except:
            print("Please navigate here: %s" % auth_url)

        print()
        print()
        try:
            response = raw_input("Enter the URL you were redirected to: ")
        except NameError:
            response = input("Enter the URL you were redirected to: ")

        print()
        print() 

        code = sp_oauth.parse_response_code(response)
        token_info = sp_oauth.get_access_token(code)
    # Auth'ed API request
    if token_info:
        return token_info['access_token']
    else:
        return None


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        query_s = urlparse(self.path).query
        form = dict(parse_qsl(query_s))

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()

        if "code" in form:
            self.server.auth_code = form["code"]
            self.server.error = None
            status = "successful"
        elif "error" in form:
            self.server.error = form["error"]
            self.server.auth_code = None
            status = "failed ({})".format(form["error"])
        else:
            self._write("<html><body><h1>Invalid request</h1></body></html>")
            return

        self._write(
            "<html><body><h1>Authentication status: {}</h1>Now you can close this window.</body></html>".format(status))

    def _write(self, text):
        return self.wfile.write(text.encode("utf-8"))

    def log_message(self, format, *args):
        return

def start_local_http_server(port, handler=RequestHandler):
    while True:
        try:
            server = HTTPServer(("127.0.0.1", port), handler)
        except socket.error as err:
            if err.errno != errno.EADDRINUSE:
                raise
        else:
            server.auth_code = None
            return server


def obtain_token_localhost(username, client_id, client_secret, redirect_uri, cache_path=None, scope=None):
    cache_path = cache_path or ".cache-" + username

    sp_oauth = oauth2.SpotifyOAuth(client_id, client_secret, redirect_uri, scope=scope, cache_path=cache_path)

    token_info = sp_oauth.get_cached_token()

    if token_info:
        return token_info['access_token']

    print("Authorzing User...")
    auth_url = sp_oauth.get_authorize_url()
    try:
        import webbrowser
        webbrowser.open(auth_url)
        #print("Opened %s in your browser" % auth_url)
    except:
        print("Please navigate here: %s" % auth_url)
    url_info = urlparse(redirect_uri)
    netloc = url_info.netloc
    if ":" in netloc:
        port = int(netloc.split(":", 1)[1])
    else:
        port = 80

    server = start_local_http_server(port)
    server.handle_request()
    if server.auth_code:
        token_info = sp_oauth.get_access_token(server.auth_code)
        print("Authorized!")
        return token_info['access_token']