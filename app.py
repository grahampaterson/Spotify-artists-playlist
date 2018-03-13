import sys
import spotipy
import spotipy.util as util
from spotipy.oauth2 import SpotifyClientCredentials
import json
import requests
from flask import Flask, redirect, request, session, url_for, jsonify

# Init flask app
app = Flask(__name__)

# API KEYS
KEYS = open('client-secret.json').read()
key_data = json.loads(KEYS)
# set the secret key.  keep this really secret: for session usage
app.secret_key = key_data['FlaskKey']
#  Spotify Client Keys
CLIENT_ID = key_data['ClientID']
CLIENT_SECRET = key_data['ClientSecret']

# CONSTANTS
PORT = 5000
creds = spotipy.oauth2.SpotifyClientCredentials(CLIENT_ID, CLIENT_SECRET)
auth = spotipy.oauth2.SpotifyOAuth(CLIENT_ID, CLIENT_SECRET,'http://127.0.0.1:5000/callback/q', None, 'playlist-modify-private playlist-modify-public playlist-read-private')

# ROUTES
@app.route('/')
def index():
    if session.get('token') == False:
        return redirect(auth.get_authorize_url())

    return redirect(url_for('logged_in'))

@app.route('/callback/q')
def callback():
    access_token = auth.get_access_token(request.args['code'])
    session['token'] = access_token['access_token']

    return redirect(url_for('logged_in'))

@app.route('/logged-in')
def logged_in():
    if session.get('token') == False:
        return redirect(auth.get_authorize_url())

    sp = spotipy.client.Spotify(session['token'], True, creds)

    # sp.user_playlist_create(sp.current_user()['id'], 'Spotipy')
    return jsonify(sp.current_user())


if __name__ == "__main__":
    app.run(debug=True,port=PORT)
