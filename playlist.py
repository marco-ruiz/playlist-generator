"""
   Copyright 2002-2019 the original author or authors.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

"""XSPF Playlist Generator

This script generates a VLC compatible XSPF file (playlist file) listing
all the videos found under a specified folder path (script argument). 

The XSPF generated includes metadata of the media files scanned including 
total duration and corresponding nesting structure (subfolders). 

The script scans for media files of type MP4, MPG, MPEG, AVI, MKV, MOV, 
FLV, WMV, WEBM.

The XSPF file generated is saved under the corresponding root folder, with 
the same name of the folder plus the extension '.xspf' and it is ready to be
opened with VLC.

The generation of the playlist is multithreaded, since the main function of 
this script in fact takes an array of folders, in order to provide the ability
to generate multiple playlists at once.

Usage: python playlist.py [ROOT_FOLDER]
Author: Marco Ruiz
"""

import re
import os
import sys
from concurrent.futures.thread import ThreadPoolExecutor
from urllib.parse import quote
from pymediainfo import MediaInfo


def xml_escape(str):
    str = str.replace("&", "&amp;")
    str = str.replace("<", "&lt;")
    str = str.replace(">", "&gt;")
    str = str.replace("\"", "&quot;")
    return str


def sorted_nicely(l):
    """ Sorts the given iterable in the way that is expected.

    Required arguments:
    l -- The iterable to be sorted.

    """
    convert = lambda text: int(text) if text.isdigit() else text
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(l, key=alphanum_key)


def element(tag, content, indentation_level = 0):
    return indent("<{0}>{1}</{0}>".format(tag, content), indentation_level)


def indent(line, indentation_level):
    return ("\t" * indentation_level) + line + "\n"


def link(path, indentation_level, quoted = False):
    if not quoted: path = quote(path)
    return indent(r'<link rel="file://{0}">Source</link>'.format(path), indentation_level)


def split_all(path):
    result = []
    while True:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            result.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            result.insert(0, parts[1])
            break
        else:
            path = parts[0]
            result.insert(0, parts[1])
    return result


video_file_extensions = ("mp4", "mpg", "mpeg", "avi", "mkv", "mov", "flv", "wmv", "webm")


def is_video_file(file):
    return os.path.splitext(file)[1][1:] in video_file_extensions


class Playlist:
    header = r'<?xml version="1.0" encoding="UTF-8"?>' + "\n" + \
             r'<playlist version="1" xmlns="http://xspf.org/ns/0/" xmlns:vlc="http://www.videolan.org/vlc/playlist/ns/0/">' + "\n"

    ext_start = r'<extension application="http://www.videolan.org/vlc/playlist/0">'
    breaker = '\t</trackList>\n\t' + ext_start + "\n"

    def __init__(self, path, force_creation = False, out_file = ""):
        self.path = path
        self.force_creation = force_creation
        self.out_file = out_file

        if self.is_already_fullfilled(): return

        self.tracks = self.find_tracks()
        self.nodes = []
        self.prepare()

    def is_already_fullfilled(self):
        return not self.force_creation and os.path.exists(self.playlist_file())

    def write_xspf(self):
        if self.is_already_fullfilled(): return
        with open(self.playlist_file(), "wt") as f:
            f.write(self.create_xspf())

    def playlist_file(self):
        if self.out_file == "": self.out_file = os.path.basename(self.path)
        if not self.out_file.endswith(".xspf"): self.out_file += ".xspf"
        return os.path.join(self.path, self.out_file)

    def find_tracks(self):
        paths = []
        for root, dirs, files in os.walk(self.path, topdown=False):
            full_path_files = [os.path.join(root, name) for name in files]
            paths += [path for path in full_path_files if is_video_file(path)]
        return [Track(path) for path in sorted_nicely(paths)]

    def prepare(self):
        """
        Adds corresponding id and parent to each track dictionary
        :return:
        """
        nodes_paths = self.compute_nodes_paths()

        self.nodes = []
        for node_path in nodes_paths:
            node = {"path": node_path, "tracks": []}
            self.nodes.append(node)
            for track in self.tracks:
                if track.node == node["path"]:
                    node["tracks"].append(track)

    def compute_nodes_paths(self):
        nodes_paths = []
        for num, track in enumerate(self.tracks):
            dir_from_playlist = os.path.dirname(track.path).replace(self.path, "", 1)
            if (len(dir_from_playlist) > 0 and dir_from_playlist[0] == "/"):
                dir_from_playlist = dir_from_playlist[1:]
            track.id = num
            track.node = " - ".join(split_all(dir_from_playlist))
#            track.node = dir_from_playlist
            if track.node not in nodes_paths:
                nodes_paths.append(track.node)

        return sorted_nicely(nodes_paths)

    def create_xspf(self):
        """
        :param playlist: Format
        {path: "", tracks: [{path: "", duration: ""}, ...]}
        :return:
        """
        playlist_dirname, playlist_basename = os.path.split(self.path)
        encodedPath = quote(self.path)

        result = Playlist.header
        result += element("title", xml_escape(playlist_basename), 1)
        result += element("location", encodedPath, 1)
        result += link(encodedPath, 1, True)
        result += indent("<trackList>", 1)
        result += "".join([track.render() for track in self.tracks])    # Render tracks
        result += Playlist.breaker
        result += self.create_vlc_extension()
        return result + "\t</extension>\n</playlist>"

    def create_vlc_extension(self):
        result = ""
        for node in self.nodes:
            title = xml_escape(node["path"])
            if title == "":
                result += self.create_vlc_items(node, 2)
            else:
                result += indent(r'<vlc:node title="{}">'.format(title), 2)
                result += self.create_vlc_items(node, 3)
                result += indent(r'</vlc:node>', 2)
        return result

    def create_vlc_items(self, node, indentation_level):
        return "".join([track.create_vlc_item(indentation_level) for track in node["tracks"]])


class Track:

    def __init__(self, path):
        self.id = -1
        self.path = path
        self.duration = self.get_video_duration()
        self.node = []

    def get_video_duration(self):
        try:
            return MediaInfo.parse(self.path).tracks[0].duration
        except:
            return 0

    def render(self):
        encodedPath = quote(self.path)
        title = xml_escape(os.path.basename(self.path))
        return indent("<track>", 2) + \
               element("trackNum", self.id + 1, 3) + \
               element("title", title, 3) + \
               element("location", encodedPath, 3) + \
               element("duration", self.duration, 3) + \
               link(encodedPath, 3, True) + \
               indent(Playlist.ext_start, 3) + \
               element("vlc:id", self.id, 4) + \
               indent("</extension>", 3) + \
               indent("</track>", 2)

    def create_vlc_item(self, indent_level):
        return indent(r'<vlc:item tid="{}"/>'.format(self.id), indent_level)


def write_course_xspf(course, force_creation):
    Playlist(course, force_creation).write_xspf()
    print(course)


def main(courses_iter, force_creation = False):
    with ThreadPoolExecutor(max_workers = 16) as executor:
        for course in courses_iter:
            executor.submit(write_course_xspf, course, force_creation)
#            write_course_xspf(course)


if __name__ == "__main__":
    main(sys.argv)

