from flask import Flask, render_template, request, g, url_for, jsonify, make_response, redirect, session
import datetime
import json
import base64
import urllib
import requests
import sys
import os
import xml.etree.ElementTree as ET
import plistlib
import spotipy

app = Flask(__name__)

KEYS = open('client-secret.json').read()
key_data = json.loads(KEYS)

# set the secret key.  keep this really secret: for session usage
app.secret_key = key_data['FlaskKey']

#  Client Keys
CLIENT_ID = key_data['ClientID']
CLIENT_SECRET = key_data['ClientSecret']

# Spotify URLS
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com"
API_VERSION = "v1"
SPOTIFY_API_URL = "{}/{}".format(SPOTIFY_API_BASE_URL, API_VERSION)

# Server-side Parameters
CLIENT_SIDE_URL = "http://127.0.0.1"
PORT = 5000
REDIRECT_URI = "{}:{}/callback/q".format(CLIENT_SIDE_URL, PORT)
SCOPE = "playlist-modify-public playlist-modify-private"
STATE = ""
SHOW_DIALOG_bool = True
SHOW_DIALOG_str = str(SHOW_DIALOG_bool).lower()


auth_query_parameters = {
    "response_type": "code",
    "redirect_uri": REDIRECT_URI,
    "scope": SCOPE,
    # "state": STATE,
    # "show_dialog": SHOW_DIALOG_str,
    "client_id": CLIENT_ID
}

@app.route("/")
def index():
    # if session.get('token'):
    #     return redirect(url_for('dashboard'))

    # Auth Step 1: Authorization
    url_args = "&".join(["{}={}".format(key,urllib.parse.quote(val)) for key,val in auth_query_parameters.items()])
    auth_url = "{}/?{}".format(SPOTIFY_AUTH_URL, url_args)
    return redirect(auth_url)


@app.route("/callback/q")
def callback():
    # Auth Step 4: Requests refresh and access tokens
    auth_token = request.args['code']
    code_payload = {
        "grant_type": "authorization_code",
        "code": str(auth_token),
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    # client_data = "{}:{}".format(CLIENT_ID, CLIENT_SECRET)
    # base64encoded = base64.b64encode(bytes(client_data,'utf-8'))
    # headers = {"Authorization": "Basic {}".format(base64encoded)}
    post_request = requests.post(SPOTIFY_TOKEN_URL, data=code_payload)

    # Auth Step 5: Tokens are Returned to Application
    response_data = json.loads(post_request.text)
    access_token = response_data["access_token"]
    refresh_token = response_data["refresh_token"]
    token_type = response_data["token_type"]
    expires_in = response_data["expires_in"]

    # save access token in session
    session['token'] = access_token

    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if session.get('token') == False:
        return redirect(url_for('index'))

    return render_template("dashboard.html")

# POST(playlist, artsts) -> Populate Playlist & Redirect dashboard
# Receives a post request with playlist and artist data and creates the Spotify
# playlist with all songs data
@app.route("/make-playlist", methods=['POST'])
def make_playlist():
    if session.get('token') == False:
        return redirect(url_for('index'))

    if request.method == 'POST':
        playlist = request.form['playlist']
        artists = request.form['artists'].split(",")
        create_playlist(artists, playlist)
    else:
        return redirect(url_for('dashboard'))

    return redirect(url_for('dashboard'))

# POST(playlist, artsts) -> Playlist Data, Artists data
# Receives a post request with playlist and artist data and returns the playlists
# data as well as the artists data + search query
@app.route("/search_artists", methods=['POST'])
def search_artists():
    if session.get('token') == False:
        return redirect(url_for('index'))

    if request.method == 'POST':
        playlist = request.form['playlist']
        artists = request.form['artists'].split(",")
        playlist_data = find_playlist(playlist)
        artists_data = find_artists(artists)
        return jsonify({
        'playlist_data': playlist_data,
        'artists_data': artists_data
        })
    else:
        return redirect(url_for('dashboard'))


# HELPER FUNCTIONS
# get playlist info
# name, optional:number -> playlist data || false
# searches for a playlist with name and an optional offset number
# playlist data object or false
def find_playlist(name, off=0):
    access_token=session['token']
    # Auth Step 6: Use the access token to access Spotify API
    authorization_header = {"Authorization":"Bearer {}".format(access_token)}
    offset = off
    playlists_api = "{}/me/playlists?offset={}".format(SPOTIFY_API_URL, offset)
    playlists_response = requests.get(playlists_api, headers=authorization_header)
    playlists_data = json.loads(playlists_response.text)
    for playlist in playlists_data['items']:
        # print(playlist['name'])
        if playlist['name'] == name:
            print('found playlist with name')
            return playlist

    # if can't find playlist create it and return data
    # TODO factor this out into separate function
    if playlists_data['next'] == None:
        print('couldnt find playlist, trying to create it')
        # get user id
        user_url = "{}/me".format(SPOTIFY_API_URL)
        user_response = requests.get(user_url, headers=authorization_header)
        user_id = json.loads(user_response.text)['id']
        print(user_id)
        # create playlist
        create_playlist_url = "{}/users/{}/playlists".format(SPOTIFY_API_URL, user_id)
        new_playlist = {"name": name}
        new_playlist_response = requests.post(create_playlist_url, json=new_playlist, headers=authorization_header)
        new_playlist_data = json.loads(new_playlist_response.text)
        print('created it playlist')
        return new_playlist_data

    return find_playlist(name, (offset + 20))

# list of artists -> list of artist data
# takes a list of artists and returns the artist data for each artist including
# the search query
def find_artists(artists_list):
    artists_data = []
    for artist in artists_list:
        artists_data.append({
        'search_term': artist,
        'data': find_artist(artist)
        })
    return artists_data

# ArtistName -> Listof{name,id,imageurl}
# Takes an artist name (string) and searches for the artists name, returning
# a dict with all potential artist name, id and image source
def find_artist(artist_name):
    access_token=session['token']
    # Auth Step 6: Use the access token to access Spotify API
    authorization_header = {"Authorization":"Bearer {}".format(access_token)}
    print(artist_name)
    s_artist = urllib.parse.quote(artist_name)

    search_artist_url = "{}/search?q={}%20&type=artist".format(SPOTIFY_API_URL, s_artist)
    search_response = requests.get(search_artist_url, headers=authorization_header)
    print(search_response)

    artist_info = []
    try:
        returned_data = json.loads(search_response.text)['artists']['items']
        for artist in returned_data:
            data = {'name' : artist['name'],
            'id': artist['id'] #, 'image_src': artist['images'][0]['url'] NOTE add this back in at some point
            }
            artist_info.append(data)
        return artist_info
    except:
        print('failed to get artist data')
        return []

def create_playlist(artists, playlist):

    access_token=session['token']
    # Auth Step 6: Use the access token to access Spotify API
    authorization_header = {"Authorization":"Bearer {}".format(access_token)}

    # Track name, Artist -> TrackUri
    # takes a song name and artist and returns the spotify track uri
    def find_track(name, artist):
        s_track = urllib.parse.quote(name)
        s_artist = urllib.parse.quote(artist)

        search_track_url = "{}/search?q={}%20artist:{}&type=track".format(SPOTIFY_API_URL, s_track, s_artist)
        search_response = requests.get(search_track_url, headers=authorization_header)
        print(search_response)
        # gets data for first search result only
        # TODO check if data is returned
        try:
            returned_data = json.loads(search_response.text)['tracks']['items'][0]
            return returned_data['uri']
        except:
            return False

    # ArtistId -> listOfAlbumIds
    # Takes an artist Id (string) and returns a list of all the artist's album's IDs
    def get_albumlist(artist_id, offset=0):
        print(offset)
        get_albums_url = "{}/artists/{}/albums?offset={}&album_type=album".format(SPOTIFY_API_URL, artist_id, offset)
        search_response = requests.get(get_albums_url, headers=authorization_header)
        print(search_response)
        album_ids = []
        returned_data = json.loads(search_response.text)['items']

        for album in returned_data:
            if album['album_type'] == 'album':
                album_ids.append(album['id'])
                print(album['name'])

        if json.loads(search_response.text)['next'] == None:
            return album_ids
        else:
            album_ids = album_ids + get_albumlist(artist_id, (offset + 20))
            return album_ids


    # AlbumId -> List of tracks uris
    # takes an album id and returns a list of all the track uris
    def album_track(album_id):
        print('gettings tracks for album')
        get_tracks_url = "{}/albums/{}/tracks?limit=50".format(SPOTIFY_API_URL, album_id)
        search_response = requests.get(get_tracks_url, headers=authorization_header)
        print(search_response)
        track_uris = []
        returned_data = json.loads(search_response.text)['items']
        for track in returned_data:
            track_uris.append(track['uri'])

        # print(track_uris)
        return track_uris

    # ListofAlbumIds -> ListofTrackUris
    # takes a list of album ids and returns a list of track track_uris
    def albums_to_tracks(album_list):
        track_list = []
        for album in album_list:
            track_list = track_list + album_track(album)

        return track_list

    # playlistName, listOftrackURI -> Adds track to playlists
    # takes a playlist name and list of trackUri and adds them to the playlist and returns
    # True if successful
    def add_tracks(playlist_name, track_uris):
        # finds playlist w/name or creates it
        try:
            playlist_url = find_playlist(playlist_name)['href']
        except:
            print('couldnt create playlist in add tracks')
            return False

        # TODO store playlist current track data and ensure no duplicates

        add_track_url = "{}/tracks".format(playlist_url)
        # list -> Void
        # takes a list and adds it to playlist in chunks of 100
        def list_chunks(track_list):
            if len(track_list) > 99:
                chunk = track_list[0:100]
                tracks = {"uris": chunk}
                add_track_response = requests.post(add_track_url, json=tracks, headers=authorization_header)
                list_chunks(track_list[100:])
            else:
                tracks = {"uris": track_list}
                add_track_response = requests.post(add_track_url, json=tracks, headers=authorization_header)

        list_chunks(track_uris)

        # tracks = {"uris": track_uris}
        # print(tracks)
        # add_track_response = requests.post(add_track_url, json=tracks, headers=authorization_header)
        # print(add_track_response)
        return True

    # [list of dicts {track artist}] -> (list of track uris)
    # takes an array of track,artist dicts and returns an array of track uris
    def track_uris(tracks):
        uris = []
        for entry in tracks:
            uri = find_track(entry['track'],entry['artist'])
            if uri == False:
                continue
            else:
                uris.append(find_track(entry['track'],entry['artist']))
        print(uris)
        return uris

    # itunes xml -> [list of dicts {track artist}]
    # takes itunes xml file location and returns an array of track,artists dicts
    # TODO
    def xml_to_tracklist(xml_file):
        f = open(xml_file, 'rb')
        data = plistlib.load(f)
        tracklist = []
        for key in data['Tracks']:
            entry = {
            'track': data['Tracks'][key]['Name'],
            'artist': data['Tracks'][key]['Artist']}
            # print(data['Tracks'][key]['Artist'])
            tracklist.append(entry)
        print(tracklist)
        return tracklist

    # Artist Name, playlist name -> Playlist entry
    # takes an artist name and a playlist name and adds all the tracks by artists
    # to the playlist
    def artist_tracks_to_playlist(artist_name, playlist_name):
        artist = find_artist(artist_name)
        album_list = get_albumlist(artist[0]['id'])
        track_list =  albums_to_tracks(album_list)
        add_tracks(playlist_name, track_list)

    # list of Artists, playlist nam -> Playlist entry
    # takes a list of artists and creates a playlist with all their songs
    def artists_to_playlist(artist_list, playlist_name):
        for artist in artist_list:
            artist_tracks_to_playlist(artist, playlist_name)

    artists_to_playlist(artists, playlist)

if __name__ == "__main__":
    app.run(debug=True,port=PORT)
