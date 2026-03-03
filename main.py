import sys
import urllib
import urllib2
import urlparse
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs
import json
import base64
import os

addonID = 'plugin.audio.radiobrowser'
addon = xbmcaddon.Addon(id=addonID)

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = urlparse.parse_qs(sys.argv[2][1:])

xbmcplugin.setContent(addon_handle, 'songs')

my_stations = {}
profile = xbmc.translatePath(addon.getAddonInfo('profile')).decode("utf-8")
mystations_path = profile + '/mystations.json'
br_json_path = os.path.join(xbmc.translatePath(addon.getAddonInfo('path')).decode("utf-8"), 'br.json')

import socket
import random

def LANGUAGE(id):
    return addon.getLocalizedString(id).encode('utf-8')

def build_url(query):
    return base_url + '?' + urllib.urlencode(query)

def addLink(stationuuid, name, url, favicon, bitrate='128'):
    li = xbmcgui.ListItem(name, iconImage=favicon)
    li.setProperty('IsPlayable', 'true')
    li.setInfo(type="Music", infoLabels={"Title": name, "Size": bitrate})
    localUrl = build_url({'mode': 'play', 'stationuuid': stationuuid})

    if stationuuid in my_stations:
        contextTitle = LANGUAGE(32009)
        contextUrl = build_url({'mode': 'delstation', 'stationuuid': stationuuid})
    else:
        contextTitle = LANGUAGE(32010)
        contextUrl = build_url({'mode': 'addstation', 'stationuuid': stationuuid, 'name': name.encode('utf-8'), 'url': url, 'favicon': favicon, 'bitrate': bitrate})

    li.addContextMenuItems([(contextTitle, 'RunPlugin(%s)'%(contextUrl))])

    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localUrl, listitem=li, isFolder=False)

def readFile(filepath):
    try:
        with open(filepath, 'r') as read_file:
            return json.load(read_file)
    except Exception as e:
        xbmc.log("Failed to read file: %s - %s" % (filepath, str(e)), xbmc.LOGERROR)
        return []

def writeFile(filepath, data):
    try:
        with open(filepath, 'w') as write_file:
            json.dump(data, write_file)
    except Exception as e:
        xbmc.log("Failed to write file: %s - %s" % (filepath, str(e)), xbmc.LOGERROR)

def addToMyStations(stationuuid, name, url, favicon, bitrate):
    my_stations[stationuuid] = {'stationuuid': stationuuid, 'name': name, 'url': url, 'bitrate': bitrate, 'favicon': favicon}
    writeFile(mystations_path, my_stations)

def delFromMyStations(stationuuid):
    if stationuuid in my_stations:
        del my_stations[stationuuid]
        writeFile(mystations_path, my_stations)
        xbmc.executebuiltin('Container.Refresh')

# Ensure profiles exist
if not xbmcvfs.exists(profile):
    xbmcvfs.mkdir(profile)

if xbmcvfs.exists(mystations_path):
    my_stations = readFile(mystations_path)
else:
    writeFile(mystations_path, {})

# Load local stations once at startup (cache)
stations_from_br = readFile(br_json_path)

mode = args.get('mode', None)

if mode is None:
    # Instead of fetching from radio-browser, show all stations from br.json
    li = xbmcgui.ListItem(LANGUAGE(32000), iconImage='DefaultFolder.png')
    li.setProperty('Fanart_Image', 'special://home/addons/plugin.audio.radiobrowser/fanart.jpg')
    xbmcplugin.addDirectoryItem(handle=addon_handle,
                                url=build_url({'mode': 'stations', 'url': 'all'}),
                                listitem=li,
                                isFolder=True)
    # Optionally: Add other static folders with no remote dependency
    # E.g., filter by country or tag (if your br.json has countrycode etc.)
    # For now, just one top-level list

    xbmcplugin.endOfDirectory(addon_handle)

elif mode[0] == 'stations':
    # Handle filtering by tag, country, or show all
    all_stations = stations_from_br

    # Now add them
    for station in all_stations:
        # Fallback bitrate if not present (optional)
        bitrate = station.get('bitrate', '128')
        addLink(
            station['stationuuid'],
            station['name'],
            station['url'],
            station.get('favicon', ''),
            str(bitrate)
        )

    xbmcplugin.endOfDirectory(addon_handle)

elif mode[0] == 'play':
    stationuuid = args['stationuuid'][0]
    # Look up station in local data (cached in stations_from_br)
    target = None
    for s in stations_from_br:
        if s.get('stationuuid') == stationuuid:
            target = s
            break

    if target:
        uri = target['url']
        xbmcplugin.setResolvedUrl(addon_handle, True, xbmcgui.ListItem(path=uri))
    else:
        xbmcplugin.setResolvedUrl(addon_handle, False, xbmcgui.ListItem())

elif mode[0] == 'mystations':
    for station in my_stations.values():
        addLink(station['stationuuid'], station['name'], station['url'], station['favicon'], station['bitrate'])

    xbmcplugin.endOfDirectory(addon_handle)

elif mode[0] == 'addstation':
    favicon = args['favicon'][0] if 'favicon' in args else ''
    addToMyStations(args['stationuuid'][0], args['name'][0], args['url'][0], favicon, args['bitrate'][0])

elif mode[0] == 'delstation':
    delFromMyStations(args['stationuuid'][0])
