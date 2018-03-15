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
    artist_uri = db.Column(db.String(), nullable=False)
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
    current_user = add_user(session['user_uri'])

    # sp.user_playlist_create(sp.current_user()['id'], 'Spotipy')
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


if __name__ == "__main__":
    app.run(debug=True,port=PORT)
