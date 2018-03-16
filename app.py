import os
import sys
import spotipy
import spotipy.util as util
from spotipy.oauth2 import SpotifyClientCredentials
import json
import requests
from flask import Flask, redirect, request, session, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from helpers import log

# Init flask app
app = Flask(__name__)
# Config flask_sqlalchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.sqlite'
db = SQLAlchemy(app)

# Configure Database Structure
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_uri = db.Column(db.String(), unique=True, nullable=False)
    playlists = db.relationship('Playlist', backref='user', lazy=True)

    def __repr__(self):
        return '<Id: {}, Uri: {}>'.format(self.id, self.user_uri)

subscriptions = db.Table('subscriptions',
db.Column('playlist_id', db.Integer, db.ForeignKey('playlist.id'), primary_key=True),
db.Column('artist_id', db.Integer, db.ForeignKey('artist.id'), primary_key=True)
)

class Playlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    playlist_uri = db.Column(db.String(), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    artists = db.relationship('Artist', secondary=subscriptions, lazy='subquery', backref=db.backref('playlists', lazy=True))

    def __repr__(self):
        return '<Id: {}, Uri: {}, UserID: {}>'.format(self.id, self.playlist_uri, self.user_id)

class Artist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    artist_uri = db.Column(db.String(), unique=True, nullable=False)
    songs = db.relationship('Song', backref='artist', lazy=True)

    def __repr__(self):
        return '<Id: {}, Uri: {}>'.format(self.id, self.artist_uri)

class Song(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    song_uri = db.Column(db.String(), unique=True, nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey('artist.id'), nullable=False)

    def __repr__(self):
        return '<Id: {}, Uri: {}, ArtistID: {}>'.format(self.id, self.song_uri, self.artist_id)


# API KEYS
KEYS = open('client-secret.json')
key_data = json.load(KEYS)
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

@app.route('/auth')
def reauth():
    return redirect(auth.get_authorize_url())

@app.route('/callback/q')
def callback():
    response_data = auth.get_access_token(request.args['code'])
    print(response_data)
    token_info = response_data
    access_token = response_data['access_token']
    refresh_token = response_data['refresh_token']

    #add token to session
    session['token'] = access_token

    return redirect(url_for('logged_in'))

@app.route('/logged-in')
def logged_in():
    if session.get('token') == False:
        return redirect(auth.get_authorize_url())

    sp = spotipy.client.Spotify(session['token'], True, creds)
    user_data = sp.current_user()
    session['user_uri'] = user_data['uri']
    session['user_id'] = user_data['id']
    current_user = add_user(session['user_uri']) # Database User Object

    # new_artist = add_artist_to_db('pop')
    # artist_to_playlist_db('spotify:user:1163565663:playlist:2Rhsn3R1yhAVkX2c4zDli5', new_artist)

    # search_results = search_artist('justin')
    # new_artist = add_artist_to_db(search_results[2]['uri'])
    # new_playlist = create_new_playlist('Spotipy', current_user)
    # artist_to_playlist_db(new_playlist.playlist_uri, new_artist)

    # spotify_playlist = new_spotify_playlist('Spotipy2')
    # add_playlist_to_db(spotify_playlist, current_user)

    # print(get_artist_albums('spotify:artist:4S2yOnmsWW97dT87yVoaSZ'))
    # print(get_album_songs('spotify:album:57uGBzqdUGPAawFu51YoGk'))
    # add_songs(get_album_songs('spotify:album:57uGBzqdUGPAawFu51YoGk'), add_artist_to_db('spotify:artist:4S2yOnmsWW97dT87yVoaSZ'))


    sub_flow('Spotipy2', 'spotify:artist:2nnbJlskqUuJcGLE4a9nIu')

    return jsonify(user_data)


# FUNCTIONS

# user_uri -> user_db
# takes a user uri and adds the user to db, if user does not exist creates it
# and returns user
def add_user(user_uri):
    log('Trying to add user {}'.format(user_uri))
    query = User.query.filter_by(user_uri=user_uri).first()
    # create new user flow
    if query is None:
        log("Couldn't find user: Creating user")
        new_user = User(user_uri=user_uri)
        db.session.add(new_user)
        db.session.commit()
        log("New user created: Returning user")
        return new_user
    log("User found: Returning User")
    return query

# playlist_name -> playlist_uri
# takes a playlist name and creates it on spotify or returns the URI if it already exists
def new_spotify_playlist(playlist_name):
    log("Searching for playlist {} on spotify".format(playlist_name))
    sp = spotipy.client.Spotify(session['token'], True, creds)
    offset = 0
    playlists = sp.user_playlists(session['user_id'], offset=offset)
    has_next = True
    while (has_next is not None):
        for playlist in playlists['items']:
            if playlist['name'] == playlist_name:
                log("Found playlist {} in your spotify".format(playlist_name))
                return playlist['uri']
        has_next = playlists['next']
        offset = offset + 50
        playlists = sp.user_playlists(session['user_id'], offset=offset)
    log("Couldn't find playlist, Creating playlist {} on Spotify".format(playlist_name))
    new_playlist = sp.user_playlist_create(sp.current_user()['id'], playlist_name)
    return new_playlist['uri']

# playlist_uri -> playlist_db
# take a playlist uri and adds it to dataabse associated to user
def add_playlist_to_db(playlist_uri):
    user = add_user(session['user_uri'])
    log("Trying to add playlist {} to database".format(playlist_uri))
    query = Playlist.query.filter_by(playlist_uri=playlist_uri).first()
    if query is None:
        log("Playlist not in database, adding")
        playlist_to_db = Playlist(playlist_uri=playlist_uri, user=user)
        db.session.add(playlist_to_db)
        db.session.commit()
        log("Returning Database Playlist Entry")
        return playlist_to_db
    log("Playlist already in database, returning playlist")
    return query

# playlist_name -> playlist_uri
# takes a playlist name and a user, adds playlist to user in database and returns uri for
# playlist on spotify
def make_playlist(playlist_name):
    user = add_user(session['user_uri'])
    log("Creating playlist {}".format(playlist_name))
    playlist = new_spotify_playlist(playlist_name)
    add_playlist = add_playlist_to_db(playlist)
    log("Done creating playlist {}, ".format(playlist_name, playlist))
    return playlist

# search_query -> listof_search_results
# takes a search query and returns a list of results
def search_artist(search):
    log("Searching for artist {}".format(artist))
    sp = spotipy.client.Spotify(session['token'], True, creds)
    search_results = sp.search(search, type='artist')
    log("Returning search results")
    return search_results['artists']['items']

# artist_uri -> artist_db
# Takes and artist uri and adds it to the database, creates it if it doesn't exist,
# and returns the artist db object
def add_artist_to_db(artist_uri):
    log("Adding artist {} to database".format(artist_uri))
    query = Artist.query.filter_by(artist_uri=artist_uri).first()
    # create new user flow
    if query is None:
        log("Couldn't find artist in database: Creating artist")
        new_artist = Artist(artist_uri=artist_uri)
        db.session.add(new_artist)
        db.session.commit()
        log("New artist created: Returning artist")
        return new_artist
    log("Artist found in database: Returning artist")
    return query

# playlist_uri, artist_db -> playlist_db
# Takes an playlist_uri and artist subscribes artist to playlist. Returns playlist
def subscribe_artist(playlist_uri, artist):
    log("Subscribing artist {} to playlist {}".format(artist.artist_uri, playlist_uri))
    # SUBSCRIPTIONS FLOW
    playlist = Playlist.query.filter_by(playlist_uri=playlist_uri).first()
    if playlist is None:
        log("Playlist didnt exist in database, creating it")
        playlist = make_playlist("Untitled", add_user(session['user_uri']))
    # new_artist = add_artist_to_db(artist.artist_uri)
    playlist.artists.append(artist)
    db.session.add(playlist)
    db.session.commit()
    log("Done subscribing artist {} to playlist {}".format(artist.artist_uri, playlist.playlist_uri))
    return playlist

# playlist_name, artist_uri -> playlist_db
# takes a playlist name, a user and a artist uri and creates the subscription on the db
# returns the playlist
def sub_flow(playlist_name, artist_uri):
    playlist_uri = make_playlist(playlist_name)
    artist = artist_songs_flow(artist_uri)
    new_sub = subscribe_artist(playlist_uri, artist)
    return new_sub


# artist_uri -> list_of_artist_album_uris
# takes an artist uri and returns all the artist's albums from spotify as a list
def get_artist_albums(artist_uri):
    log("Getting all albums belonging to: {}".format(artist_uri))
    sp = spotipy.client.Spotify(session['token'], True, creds)
    offset = 0
    response = sp.artist_albums(artist_uri, offset=offset)
    artist_albums = response['items']
    while response['next'] is not None:
        offset = offset + 20
        response = sp.artist_albums(artist_uri, offset=offset)
        artist_albums.append(response['items'])
    log("Got all albums belonging to: {}".format(artist_uri))
    return list(map(lambda x: x['uri'], artist_albums))

# album_uri -> list_of_song_uris
# takes an album uri and returns all of the album's songs uris from spotify  as a list
def get_album_songs(album_uri):
    log("Getting all songs belonging to: {}".format(album_uri))
    sp = spotipy.client.Spotify(session['token'], True, creds)
    offset = 0
    response = sp.album_tracks(album_uri, offset=offset)
    album_songs = response['items']
    while response['next'] is not None:
        offset = offset + 50
        response = sp.album_tracks(album_uri, offset=offset)
        album_songs.append(response['items'])
    log("Got all songs belonging to: {}".format(album_uri))
    return list(map(lambda x: x['uri'], album_songs))

# list_of_tracks, artist -> song_db
# takes a list of tracks and adds them to the db
def add_songs(songs, artist):
    log("Addings all songs to artist {}".format(artist))
    for song in songs:
        new_song = Song(song_uri=song, artist=artist)
        db.session.add(new_song)
        try:
            db.session.commit()
        except:
            db.session.rollback()
    log("Done adding songs to database")

# arist_uri -> artist_db
# takes an artist uri, gets all their songs and adds them to the database. Returns
# artist db object
def artist_songs_flow(artist_uri):
    log("Adding all artist {} songs to database".format(artist_uri))
    artist = add_artist_to_db(artist_uri)
    all_albums = get_artist_albums(artist_uri)
    for album in all_albums:
        album_songs = get_album_songs(album)
        add_songs(album_songs, artist)
    log("Done adding all artist {} songs to database".format(artist_uri))
    return artist

if __name__ == "__main__":
    app.run(debug=True,port=PORT)
