# XSPF Playlist Generator

This script generates a VLC compatible XSPF file (playlist file) with
all the media files found under a specified folder path (script argument). 

The XSPF generated includes metadata of the media files scanned including 
total duration and corresponding nesting structure (subfolders). The media 
types scanned include MP4, MPG, MPEG, AVI, MKV, MOV, FLV, WMV and WEBM.

The XSPF file generated is saved under the corresponding root folder, with 
the same name of the folder plus the extension '.xspf' and it is ready to be
opened and use within VLC.

The generation of the playlist is multithreaded, since the main function of 
this script in fact takes an array of folders, in order to provide the ability
to generate multiple playlists at once.

### Setup

- Clone this repository and from within the cloned directory run the following command:
 
```
sudo pip install -r requirements.txt
```

### Usage

- Run a command like the following the the root folder to be scanned:

```
python playlist.py [ROOT_FOLDER]
```
