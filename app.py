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
    album_uri = db.Column(db.String(), nullable=False)
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
    # print(response_data)
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
    log("------------------START------------------")
    # artist_playlist_flow('Spotipy', 'spotify:artist:0DK7FqcaL3ks9TfFn9y1sD')
    # update_playlist('spotify:user:1163565663:playlist:0uYoHJ9AOSLvQEZWNVMwOI')
    update_all_playlists(session['user_uri'])
    # delete_playlist_name('Spotipy')
    # search_first_artist('Justinfeffegfegg')
    # artist_playlist_flow('Spotipy', search_first_artist('A Wilhelm Scream'))
    log("-------------------END-------------------")


    return jsonify(user_data)


# FUNCTIONS

# user_uri -> user_db
# takes a user uri and adds the user to db, if user does not exist creates it
# and returns user
def add_user(user_uri):
    log('001o: Trying to add user {}'.format(user_uri))
    query = User.query.filter_by(user_uri=user_uri).first()
    # create new user flow
    if query is None:
        log("Couldn't find user: Creating user")
        new_user = User(user_uri=user_uri)
        db.session.add(new_user)
        db.session.commit()
        log("New user created: Returning user")
        return new_user
    log("001c: User found: Returning User")
    return query

# playlist_name -> playlist_uri
# takes a playlist name and creates it on spotify or returns the URI if it already exists
def new_spotify_playlist(playlist_name):
    log("002o: Searching for playlist {} on spotify".format(playlist_name))
    sp = spotipy.client.Spotify(session['token'], True, creds)
    # offset = 0
    # playlists = sp.user_playlists(session['user_id'], offset=offset)
    # has_next = True
    # while (has_next is not None):
    #     for playlist in playlists['items']:
    #         if playlist['name'] == playlist_name:
    #             log("Found playlist {} in your spotify".format(playlist_name))
    #             return playlist['uri']
    #     has_next = playlists['next']
    #     offset = offset + 50
    #     playlists = sp.user_playlists(session['user_id'], offset=offset)
    already_exist = find_spotify_playlist(playlist_name)
    if already_exist is not None:
        return already_exist
    log("Couldn't find playlist, Creating playlist {} on Spotify".format(playlist_name))
    new_playlist = sp.user_playlist_create(sp.current_user()['id'], playlist_name)
    log("002c: Done Searching for playlist")
    return new_playlist['uri']

# playlist_name -> playlist_uri | None
# returns a playlist uri if the name exists on spotify or returns None
def find_spotify_playlist(playlist_name):
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
    return None

# playlist_uri, user_db -> playlist_db
# take a playlist uri and adds it to dataabse associated to user
def add_playlist_to_db(playlist_uri, user):
    log("003o: Trying to add playlist {} to database".format(playlist_uri))
    query = Playlist.query.filter_by(playlist_uri=playlist_uri).first()
    if query is None:
        log("Playlist not in database, adding")
        playlist_to_db = Playlist(playlist_uri=playlist_uri, user=user)
        db.session.add(playlist_to_db)
        db.session.commit()
        log("Returning Database Playlist Entry")
        return playlist_to_db
    log("003c: Playlist already in database, returning playlist")
    return query

# playlist_name -> playlist_uri
# takes a playlist name and a user, adds playlist to user in database and returns uri for
# playlist on spotify
def make_playlist(playlist_name):
    user = add_user(session['user_uri'])
    log("004o: Creating playlist {}".format(playlist_name))
    playlist = new_spotify_playlist(playlist_name)
    add_playlist = add_playlist_to_db(playlist, user)
    log("004c: Done creating playlist {}, ".format(playlist_name, playlist))
    return playlist

# search_query -> listof_search_results
# takes a search query and returns a list of results
def search_artist(search):
    log("005o: Searching for artist {}".format(search))
    sp = spotipy.client.Spotify(session['token'], True, creds)
    search_results = sp.search(search, type='artist')
    log("005c: Returning search results")
    return search_results['artists']['items']

# search_query -> first_artist_uri
# takes a search query and returns the first result
def search_first_artist(search):
    artists = search_artist(search)
    if len(artists) is 0:
        return None
    return artists[0]['uri']

# artist_uri -> artist_db
# Takes and artist uri and adds it to the database, creates it if it doesn't exist,
# and returns the artist db object
def add_artist_to_db(artist_uri):
    log("006o: Adding artist {} to database".format(artist_uri))
    query = Artist.query.filter_by(artist_uri=artist_uri).first()
    # create new user flow
    if query is None:
        log("Couldn't find artist in database: Creating artist")
        new_artist = Artist(artist_uri=artist_uri)
        db.session.add(new_artist)
        db.session.commit()
        log("New artist created: Returning artist")
        return new_artist
    log("006c: Artist found in database: Returning artist")
    return query

# playlist_uri, artist_db -> playlist_db
# Takes an playlist_uri and artist subscribes artist to playlist. Returns playlist
def subscribe_artist(playlist_uri, artist):
    log("007o: Subscribing artist {} to playlist {}".format(artist.artist_uri, playlist_uri))
    # SUBSCRIPTIONS FLOW
    playlist = Playlist.query.filter_by(playlist_uri=playlist_uri).first()
    if playlist is None:
        log("Playlist didnt exist in database, creating it")
        playlist = make_playlist("Untitled", add_user(session['user_uri']))
    # new_artist = add_artist_to_db(artist.artist_uri)
    playlist.artists.append(artist)
    db.session.add(playlist)
    db.session.commit()
    log("007c: Done subscribing artist {} to playlist {}".format(artist.artist_uri, playlist.playlist_uri))
    return playlist

# playlist_name, artist_uri -> playlist_db
# takes a playlist name, a user and a artist uri and creates the subscription on the db
# returns the playlist
def sub_flow(playlist_name, artist_uri):
    log("008o: Starting Sub flow")
    playlist_uri = make_playlist(playlist_name)
    artist = artist_songs_flow(artist_uri)
    new_sub = subscribe_artist(playlist_uri, artist)
    log("008c: Sub flow completed")
    return new_sub


# artist_uri -> list_of_artist_album_uris
# takes an artist uri and returns all the artist's albums from spotify as a list
def get_artist_albums(artist_uri):
    log("009o: Getting all albums belonging to: {}".format(artist_uri))
    sp = spotipy.client.Spotify(session['token'], True, creds)
    offset = 0
    response = sp.artist_albums(artist_uri, offset=offset)
    artist_albums = response['items']
    while response['next'] is not None:
        offset = offset + 20
        response = sp.artist_albums(artist_uri, type='album', offset=offset)
        artist_albums = artist_albums + response['items']
    log("009c: Got all albums belonging to: {}".format(artist_uri))
    return list(map(lambda x: x['uri'], artist_albums))

# album_uri -> list_of_song_uris
# takes an album uri and returns all of the album's songs uris from spotify  as a list
def get_album_songs(album_uri):
    log("010o: Getting all songs belonging to: {}".format(album_uri))
    sp = spotipy.client.Spotify(session['token'], True, creds)
    offset = 0
    response = sp.album_tracks(album_uri, offset=offset)
    album_songs = response['items']
    while response['next'] is not None:
        offset = offset + 50
        response = sp.album_tracks(album_uri, offset=offset)
        album_songs = album_songs + response['items']
    log("010c: Got all songs belonging to: {}".format(album_uri))
    return list(map(lambda x: x['uri'], album_songs))

# list_of_tracks, album,uri, artist -> song_db
# takes a list of tracks and adds them to the db
def add_songs(songs, album_uri, artist):
    log("011o: Addings all songs to artist {}".format(artist.artist_uri))
    for song in songs:
        new_song = Song(song_uri=song, album_uri=album_uri, artist=artist)
        db.session.add(new_song)
        try:
            db.session.commit()
        except:
            db.session.rollback()
    log("011c: Done adding songs to database")
    return artist

# arist_uri -> artist_db
# takes an artist uri, gets all their songs and adds them to the database. Returns
# artist db object
def artist_songs_flow(artist_uri):
    log("012o: Adding all artist {} songs to database".format(artist_uri))
    artist = add_artist_to_db(artist_uri)
    all_albums = get_artist_albums(artist_uri)
    for album_uri in all_albums:
        # check if album is already in db and if it is doesn't get new tracks
        query = Song.query.filter_by(album_uri=album_uri).first()
        if query is not None:
            log("Album is already in database, skipping")
            continue
        album_songs = get_album_songs(album_uri)
        add_songs(album_songs, album_uri, artist)
    log("012c: Done adding all artist {} songs to database".format(artist_uri))
    return artist


# Playlist_name -> playlist_uri
# Takes a playlist name and gets all the songs assoiciated with it and adds them to
# spotify if they aren't already in the playlist. Creates playlist if it doesn't exist
def songs_to_playlist_name(playlist_name):
    log("013o: Adding all songs for playlist {} to spotify".format(playlist_name))
    playlist_uri = make_playlist(playlist_name)
    log("013c: Done adding all songs for playlist {} to spotify".format(playlist_name))
    return songs_to_playlist_uri(playlist_uri)

# Playlist_uri -> playlist_uri
# Takes a playlist_uri and gets all the songs assoiciated with it and adds them to
# spotify if they aren't already in the playlist
def songs_to_playlist_uri(playlist_uri):
    log("015o: Adding all songs for playlist {} to spotify".format(playlist_uri))
    user = session['user_id']
    playlist = Playlist.query.filter_by(playlist_uri=playlist_uri).first()
    tracks = []

    for artist in playlist.artists:
        for song in artist.songs:
            tracks.append(song.song_uri)

    new_tracks = filter_songs(get_playlist_songs(playlist_uri), tracks)
    sp = spotipy.client.Spotify(session['token'], True, creds)

    # TODO check if user has playlist with this uri, if not just skip it and delete from db maybe
    # NOTE for some reason user_playlist_follow doesn't accept a uri so needs
    # to be converted to just an id
    playlist_id = playlist_uri[(playlist_uri.find('playlist:') + len('playlist:')):]
    response = sp.user_playlist_is_following(user, playlist_id, [user])
    if response[0] is False:
        log("Couldn't update playlist because it no longer exists on spotify, deleted from DB")
        return delete_playlist(playlist_uri)

    for i in range(0, len(new_tracks), 100):
        sp.user_playlist_add_tracks(user, playlist_uri, new_tracks[i:i+100])
    log("015c: Done adding all songs for playlist {} to spotify".format(playlist_uri))
    return playlist_uri

# Playlist_uri -> playlist_uri
# takes a playlist uri, finds every artist subscribed and updates their data in the
# the database and then updates each of the playlists
# ASSUME playlist_uri exists in database and belongs to current user
def update_playlist(playlist_uri):
    playlist = Playlist.query.filter_by(playlist_uri=playlist_uri).first()
    for artist in playlist.artists:
        artist_songs_flow(artist.artist_uri)
    songs_to_playlist_uri(playlist_uri)
    return playlist_uri

# user_uri -> user_uri
# takes a user_uri and updates all their playlists to be up to date
# TODO add logging for this function
def update_all_playlists(user_uri):
    user = add_user(user_uri)
    for playlist in user.playlists:
        if len(playlist.artists) is 0:
            continue
        update_playlist(playlist.playlist_uri)
    return user_uri

# list_of_song_uris, list_of_song_uris -> list_of_song_uris
# takes a list of existing songs and songs and retunrs a list of songs minus
# the existing songs
def filter_songs(existing_songs, songs):
    new_songs = [x for x in songs if x not in existing_songs]
    return new_songs

# playlist_uri -> list_of_song_uris
# takes a spotify playlist uri and returns all the songs in the playlist
def get_playlist_songs(playlist_uri):
    user = session['user_id']
    sp = spotipy.client.Spotify(session['token'], True, creds)

    # sp = spotipy.client.Spotify(session['token'], True, creds)
    offset = 0
    response = sp.user_playlist_tracks(user, playlist_id=playlist_uri, fields='items.track.uri, next', offset=offset)
    # TODO what if playlist doesn't exist?
    playlist_songs = response['items']
    while response['next'] is not None:
        offset = offset + 100
        response = sp.user_playlist_tracks(user, playlist_id=playlist_uri, fields='items.track.uri, next', offset=offset)
        playlist_songs = playlist_songs + response['items']

    return list(map(lambda x: x['track']['uri'], playlist_songs))

# Playlist_name, artist_uri -> playlist_uri
# takes a playlist name and artist and creates database entries, subscriptions and
# adds all tracks to playlist on spotify
def artist_playlist_flow(playlist_name, artist_uri):
    log("014o: Starting full flow to add artist to playlist")
    playlist = sub_flow(playlist_name, artist_uri)
    songs_to_playlist_name(playlist_name)
    log("014c: Done full flow to add artist to playlist")
    return playlist.playlist_uri

# playlist_uri -> Playlist_uri
# takes a playlist uri and deletes all it's subscriptions. this does not delete
# the playlist, artist, or it's songs. It simply removes the relationship
def delete_playlist(playlist_uri):
    playlist = Playlist.query.filter_by(playlist_uri=playlist_uri).first()
    playlist.artists = []
    db.session.commit()
    return playlist_uri

# playlist_name -> Boolean
# takes a playlist name of a spotify playlist and deletes the playlist and all
# db subscriptions. returns true if successful else false
def delete_playlist_name(playlist_name):
    user = session['user_id']
    sp = spotipy.client.Spotify(session['token'], True, creds)

    playlist_uri = find_spotify_playlist(playlist_name)
    if playlist_uri is None:
        log('Couldnt find playlist on spotify')
        return False
    # NOTE for some reason user_playlist_follow doesn't accept a uri so needs
    # to be converted to just an id
    playlist_id = playlist_uri[(playlist_uri.find('playlist:') + len('playlist:')):]
    sp.user_playlist_unfollow(user, playlist_id=playlist_id)
    delete_playlist(playlist_uri)
    return True

if __name__ == "__main__":
    app.run(debug=True,port=PORT)
