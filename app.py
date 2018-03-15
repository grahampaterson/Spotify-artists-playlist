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

    # new_user = User(user_uri='user11')
    # new_playlist = Playlist(playlist_uri='dddddggdgfgfgg', user=new_user)
    # new_playlist2 = Playlist(playlist_uri='78gffgh5', user_id=11)
    # db.session.add(new_playlist)
    # db.session.add(new_playlist2)
    # db.session.commit()

    # query = User.query.filter_by(id=1).first().playlists[1].artists

    # SUBSCRIPTIONS FLOW
    # playlist = Playlist.query.filter_by(user_id=1).first().user.playlists[0]
    # artist = Artist(artist_uri='556ghh7')
    # print(playlist.artists)
    # playlist.artists.append(artist)
    # db.session.add(playlist)
    # db.session.commit()
    return redirect(auth.get_authorize_url())
    return redirect(url_for('logged_in'))

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
    session['user_uri'] = sp.current_user()['uri']
    session['user_id'] = sp.current_user()['id']
    current_user = add_user(session['user_uri'])

    # new_artist = add_artist_to_db('pop')
    # artist_to_playlist_db('spotify:user:1163565663:playlist:2Rhsn3R1yhAVkX2c4zDli5', new_artist)

    # search_results = search_artist('justin')
    # new_artist = add_artist_to_db(search_results[2]['uri'])
    # new_playlist = create_new_playlist('Spotipy', current_user)
    # artist_to_playlist_db(new_playlist.playlist_uri, new_artist)
    new_playlist('Test')
    return jsonify(sp.current_user())


# FUNCTIONS

# user_uri -> user
# takes a user uri and adds the user to db, if user does not exist creates it
# and returns user
def add_user(user_uri):
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
def new_playlist(playlist_name):
    sp = spotipy.client.Spotify(session['token'], True, creds)
    print(session['user_id'])
    print(sp.user_playlists(session['user_id']))


# playlist_name, user -> playlist database entry
# creates a new playlist in database associated with user and with name
# TODO make this just add playlist to database
def create_new_playlist(playlist_name, user):
    log("Creating playlist on Spotify")
    sp = spotipy.client.Spotify(session['token'], True, creds)
    new_playlist = sp.user_playlist_create(sp.current_user()['id'], playlist_name)
    log("Adding Playlist to Database")
    playlist_to_db = Playlist(playlist_uri=new_playlist['uri'], user=user)
    db.session.add(playlist_to_db)
    db.session.commit()
    log("Returning Database Playlist Entry")
    return playlist_to_db


# search_query -> listof_search_results
# takes a search query and returns a list of results
def search_artist(search):
    sp = spotipy.client.Spotify(session['token'], True, creds)
    search_results = sp.search(search, type='artist')

    return search_results['artists']['items']


# artist_uri -> artist
# Takes and artist uri and adds it to the database if it doesn't exist and returns
# the artist
def add_artist_to_db(artist_uri):
    query = Artist.query.filter_by(artist_uri=artist_uri).first()
    # create new user flow
    if query is None:
        log("Couldn't find artist: Creating artist")
        new_artist = Artist(artist_uri=artist_uri)
        db.session.add(new_artist)
        db.session.commit()
        log("New artist created: Returning artist")
        return new_artist
    log("Artist found: Returning artist")
    return query

# playlist_uri, artist -> playlist
# Takes an playlist_uri and artist and returns the playlist with the artist added
def artist_to_playlist_db(playlist_uri, artist):
    print(artist.artist_uri)
    # SUBSCRIPTIONS FLOW
    playlist = Playlist.query.filter_by(playlist_uri=playlist_uri).first()
    new_artist = add_artist_to_db(artist.artist_uri)
    playlist.artists.append(new_artist)
    db.session.add(playlist)
    db.session.commit()

if __name__ == "__main__":
    app.run(debug=True,port=PORT)
