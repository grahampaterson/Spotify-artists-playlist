Spotify Full Artist playlists
========================

Make playlists from a list of artists' albums

TODO
---------------
Update playlists automatically
DONE Migrate to spotipy module
DONE When checking for new music don't look up songs if the album already exists in database
Sort out Auth token expiration
DONE Only add artist to playlist, not compilation artists
UI
Only add song to database for artist if it matches that artist (ie, no compilations)
DONE Only delete playlists if they are in the database so users can't delete their own playlists
DONE add form to index page to access routes

"FEATURES"
---------------
If you rename a playlist it will no longer associate with that playlist and creates a new playlist with NAME
If you try use the name of an existing playlist it will replace all the songs in that playlist
You cannot delete a playlist if you did not create it with this tool, but if you add songs to an existing playlist then you are able to
