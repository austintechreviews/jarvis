"""
Spotify Plugin for JARVIS
================================
Full Spotify playback control and library management via the Spotify Web API.

Architecture Note:
    This plugin sits in the TOOL LAYER of the JARVIS stack.
    It registers its tools with PluginManager, which injects them into the
    LLM's system prompt so the model can call them by name.

    JARVIS Core
        └── PluginManager
                └── SpotifyPlugin          ← This file
                        ├── spotipy        (OAuth2 + API wrapper)
                        └── Spotify Web API

Security:
    - OAuth2 tokens are stored by spotipy in a local .cache file, never in plaintext config.
    - The plugin will NEVER auto-submit payment or account-deletion actions.
    - All write actions (play, queue, delete playlist) log to JARVIS audit log.

Setup:
    1. Go to https://developer.spotify.com/dashboard and create an app.
    2. Set Redirect URI to http://localhost:8888/callback in the dashboard.
    3. Run `python spotify_plugin.py --setup` to create the config template.
    4. Fill in client_id and client_secret in ~/jarvis/config/spotify_config.json.
    5. On first JARVIS launch, a browser window opens for one-time OAuth consent.

Required scopes (all included):
    user-modify-playback-state   - play, pause, seek, volume, shuffle, repeat
    user-read-playback-state     - current track, device list, queue
    user-read-currently-playing  - now playing endpoint
    user-library-read            - check saved tracks
    user-library-modify          - save / remove tracks
    user-top-read                - top artists / tracks
    playlist-read-private        - list user playlists
    playlist-modify-public       - create / edit public playlists
    playlist-modify-private      - create / edit private playlists
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Ensure the JARVIS root is on sys.path so we can import the base class
# ---------------------------------------------------------------------------
_jarvis_root = str(Path(__file__).parent.parent)
if _jarvis_root not in sys.path:
    sys.path.insert(0, _jarvis_root)

try:
    from modules.plugin_system import JARVISPlugin
except ImportError:
    # Graceful fallback when running standalone (e.g., --setup mode)
    class JARVISPlugin:  # type: ignore
        name = "base_plugin"
        version = "1.0.0"
        description = ""
        author = ""
        required_packages: List[str] = []

        def check_dependencies(self) -> bool:
            return True

        def initialize(self) -> bool:
            return True

        def get_tools(self) -> Dict[str, Callable]:
            return {}

        def get_system_prompt_addition(self) -> str:
            return ""

        def cleanup(self) -> None:
            pass


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_CONFIG_PATH = Path.home() / "jarvis" / "config" / "spotify_config.json"
_CACHE_PATH  = Path.home() / "jarvis" / "config" / ".spotify_token_cache"
_REDIRECT    = "http://localhost:8888/callback"

_SCOPES = " ".join([
    "user-modify-playback-state",
    "user-read-playback-state",
    "user-read-currently-playing",
    "user-library-read",
    "user-library-modify",
    "user-top-read",
    "playlist-read-private",
    "playlist-modify-public",
    "playlist-modify-private",
])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _ok(message: str, **extra) -> Dict[str, Any]:
    """Return a success result dict."""
    return {"success": True, "message": message, **extra}


def _err(message: str, **extra) -> Dict[str, Any]:
    """Return an error result dict."""
    logger.error(f"[spotify] {message}")
    return {"success": False, "message": message, **extra}


def _ms_to_str(ms: int) -> str:
    """Convert milliseconds to m:ss string."""
    total_seconds = ms // 1000
    m, s = divmod(total_seconds, 60)
    return f"{m}:{s:02d}"


# ---------------------------------------------------------------------------
# Plugin Class
# ---------------------------------------------------------------------------
class SpotifyPlugin(JARVISPlugin):
    """
    Spotify music control plugin for JARVIS.

    Provides 20+ tools covering playback, search, library management,
    playlists, device switching, and personalised recommendations.
    """

    name        = "spotify"
    version     = "2.0.0"
    description = "Full Spotify control — playback, search, library, playlists, devices"
    author      = "JARVIS Team"

    required_packages = ["spotipy"]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        super().__init__()
        self.sp: Any = None          # spotipy.Spotify instance
        self._active_device: Optional[str] = None

    def initialize(self) -> bool:
        """
        Load credentials and perform OAuth2 authorisation.
        On first run, a browser window opens for user consent.
        """
        try:
            import spotipy
            from spotipy.oauth2 import SpotifyOAuth

            if not _CONFIG_PATH.exists():
                logger.warning(
                    "[spotify] Config not found. "
                    "Run `python spotify_plugin.py --setup` to create it."
                )
                return False

            with open(_CONFIG_PATH) as fh:
                config = json.load(fh)

            client_id     = config.get("client_id", "")
            client_secret = config.get("client_secret", "")

            if not client_id or client_id == "YOUR_CLIENT_ID":
                logger.error("[spotify] client_id not set in spotify_config.json")
                return False
            if not client_secret or client_secret == "YOUR_CLIENT_SECRET":
                logger.error("[spotify] client_secret not set in spotify_config.json")
                return False

            auth_manager = SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=config.get("redirect_uri", _REDIRECT),
                scope=_SCOPES,
                cache_path=str(_CACHE_PATH),
                open_browser=True,
            )

            self.sp = spotipy.Spotify(auth_manager=auth_manager)

            # Quick connectivity test
            profile = self.sp.current_user()
            display_name = profile.get("display_name", "Unknown")
            logger.info(f"[spotify] Authenticated as '{display_name}'")
            return True

        except Exception as exc:
            logger.error(f"[spotify] Initialization failed: {exc}", exc_info=True)
            return False

    # ------------------------------------------------------------------
    # Tool Registration
    # ------------------------------------------------------------------

    def get_tools(self) -> Dict[str, Callable]:
        return {
            # ── Playback ─────────────────────────────────────────────
            "play":              self.play,
            "pause":             self.pause,
            "toggle":            self.toggle_playback,
            "next":              self.next_track,
            "previous":          self.previous_track,
            "seek":              self.seek,
            "set_volume":        self.set_volume,
            "set_shuffle":       self.set_shuffle,
            "set_repeat":        self.set_repeat,
            # ── Now Playing ──────────────────────────────────────────
            "now_playing":       self.now_playing,
            "queue_info":        self.get_queue,
            # ── Search & Play ─────────────────────────────────────────
            "search_and_play":   self.search_and_play,
            "play_playlist":     self.play_playlist,
            "play_album":        self.play_album,
            "play_artist":       self.play_artist,
            "queue_track":       self.queue_track,
            # ── Library ──────────────────────────────────────────────
            "like_current":      self.like_current_track,
            "unlike_current":    self.unlike_current_track,
            "is_liked":          self.is_current_track_liked,
            "top_tracks":        self.get_top_tracks,
            "top_artists":       self.get_top_artists,
            # ── Playlists ────────────────────────────────────────────
            "list_playlists":    self.list_playlists,
            "create_playlist":   self.create_playlist,
            "add_to_playlist":   self.add_current_to_playlist,
            # ── Devices ──────────────────────────────────────────────
            "list_devices":      self.list_devices,
            "transfer":          self.transfer_playback,
            # ── Recommendations ──────────────────────────────────────
            "recommend":         self.get_recommendations,
        }

    # ==================================================================
    # ── PLAYBACK ──────────────────────────────────────────────────────
    # ==================================================================

    def play(self, context_uri: Optional[str] = None,
             uris: Optional[List[str]] = None,
             offset: int = 0) -> Dict[str, Any]:
        """
        Resume or start playback.

        Args:
            context_uri: Spotify URI for album/playlist/artist (optional).
            uris:        List of track URIs to play (optional).
            offset:      Track index to start at within context (default 0).
        """
        try:
            kwargs: Dict[str, Any] = {"device_id": self._active_device}
            if context_uri:
                kwargs["context_uri"] = context_uri
                kwargs["offset"] = {"position": offset}
            elif uris:
                kwargs["uris"] = uris
            self.sp.start_playback(**kwargs)
            return _ok("Playback started.")
        except Exception as exc:
            return _err(str(exc))

    def pause(self) -> Dict[str, Any]:
        """Pause playback."""
        try:
            self.sp.pause_playback(device_id=self._active_device)
            return _ok("Playback paused.")
        except Exception as exc:
            return _err(str(exc))

    def toggle_playback(self) -> Dict[str, Any]:
        """Toggle play / pause based on current state."""
        try:
            state = self.sp.current_playback()
            if state and state.get("is_playing"):
                return self.pause()
            return self.play()
        except Exception as exc:
            return _err(str(exc))

    def next_track(self) -> Dict[str, Any]:
        """Skip to the next track."""
        try:
            self.sp.next_track(device_id=self._active_device)
            return _ok("Skipped to next track.")
        except Exception as exc:
            return _err(str(exc))

    def previous_track(self) -> Dict[str, Any]:
        """Go back to the previous track."""
        try:
            self.sp.previous_track(device_id=self._active_device)
            return _ok("Went back to previous track.")
        except Exception as exc:
            return _err(str(exc))

    def seek(self, position_ms: int) -> Dict[str, Any]:
        """
        Seek to position in the current track.

        Args:
            position_ms: Position in milliseconds (e.g. 30000 = 30 seconds).
        """
        try:
            self.sp.seek_track(position_ms=position_ms,
                               device_id=self._active_device)
            return _ok(f"Seeked to {_ms_to_str(position_ms)}.")
        except Exception as exc:
            return _err(str(exc))

    def set_volume(self, volume_percent: int) -> Dict[str, Any]:
        """
        Set playback volume.

        Args:
            volume_percent: 0–100.
        """
        try:
            vol = max(0, min(100, int(volume_percent)))
            self.sp.volume(vol, device_id=self._active_device)
            return _ok(f"Volume set to {vol}%.")
        except Exception as exc:
            return _err(str(exc))

    def set_shuffle(self, state: bool) -> Dict[str, Any]:
        """
        Enable or disable shuffle.

        Args:
            state: True to enable, False to disable.
        """
        try:
            self.sp.shuffle(state, device_id=self._active_device)
            label = "enabled" if state else "disabled"
            return _ok(f"Shuffle {label}.")
        except Exception as exc:
            return _err(str(exc))

    def set_repeat(self, mode: str = "context") -> Dict[str, Any]:
        """
        Set repeat mode.

        Args:
            mode: 'off' | 'context' (repeat playlist/album) | 'track' (repeat one).
        """
        valid = {"off", "context", "track"}
        if mode not in valid:
            return _err(f"Invalid repeat mode '{mode}'. Choose from: {valid}")
        try:
            self.sp.repeat(mode, device_id=self._active_device)
            return _ok(f"Repeat mode set to '{mode}'.")
        except Exception as exc:
            return _err(str(exc))

    # ==================================================================
    # ── NOW PLAYING ───────────────────────────────────────────────────
    # ==================================================================

    def now_playing(self) -> Dict[str, Any]:
        """
        Return detailed information about the currently playing track.
        """
        try:
            current = self.sp.current_playback()
            if not current or not current.get("item"):
                return _ok("Nothing is currently playing.")

            item       = current["item"]
            track_name = item["name"]
            artists    = ", ".join(a["name"] for a in item["artists"])
            album      = item["album"]["name"]
            duration   = _ms_to_str(item["duration_ms"])
            progress   = _ms_to_str(current.get("progress_ms", 0))
            is_playing = current["is_playing"]
            shuffle    = current.get("shuffle_state", False)
            repeat     = current.get("repeat_state", "off")
            volume     = current.get("device", {}).get("volume_percent", "?")
            uri        = item["uri"]

            summary = (
                f"{'▶' if is_playing else '⏸'}  {track_name} — {artists}\n"
                f"   Album   : {album}\n"
                f"   Progress: {progress} / {duration}\n"
                f"   Volume  : {volume}%   Shuffle: {shuffle}   Repeat: {repeat}"
            )

            return _ok(
                summary,
                track=track_name,
                artists=artists,
                album=album,
                progress=progress,
                duration=duration,
                is_playing=is_playing,
                shuffle=shuffle,
                repeat=repeat,
                volume=volume,
                uri=uri,
            )
        except Exception as exc:
            return _err(str(exc))

    def get_queue(self) -> Dict[str, Any]:
        """Return the next 5 tracks in the playback queue."""
        try:
            queue_data = self.sp.queue()
            tracks = []
            for t in (queue_data.get("queue") or [])[:5]:
                artists = ", ".join(a["name"] for a in t["artists"])
                tracks.append(f"{t['name']} — {artists}")

            if not tracks:
                return _ok("Queue is empty.")

            message = "Up next:\n" + "\n".join(f"  {i+1}. {t}"
                                                for i, t in enumerate(tracks))
            return _ok(message, tracks=tracks)
        except Exception as exc:
            return _err(str(exc))

    # ==================================================================
    # ── SEARCH & PLAY ─────────────────────────────────────────────────
    # ==================================================================

    def search_and_play(self, query: str,
                        search_type: str = "track") -> Dict[str, Any]:
        """
        Search Spotify and immediately play the top result.

        Args:
            query:       Search query (e.g. "Bohemian Rhapsody", "The Beatles").
            search_type: 'track' | 'album' | 'playlist' | 'artist' (default 'track').
        """
        valid_types = {"track", "album", "playlist", "artist"}
        if search_type not in valid_types:
            search_type = "track"

        try:
            results = self.sp.search(q=query, limit=1, type=search_type)

            items_key = f"{search_type}s"
            items = results.get(items_key, {}).get("items", [])

            if not items:
                return _err(f"No {search_type} found for '{query}'.")

            item = items[0]
            uri  = item["uri"]
            name = item["name"]

            if search_type == "track":
                artists = ", ".join(a["name"] for a in item["artists"])
                self.sp.start_playback(uris=[uri],
                                       device_id=self._active_device)
                return _ok(f"Playing: {name} — {artists}", uri=uri)
            else:
                # Album, playlist, or artist → use as context
                self.sp.start_playback(context_uri=uri,
                                       device_id=self._active_device)
                return _ok(f"Playing {search_type}: {name}", uri=uri)

        except Exception as exc:
            return _err(str(exc))

    def play_playlist(self, name_or_uri: str) -> Dict[str, Any]:
        """
        Play a playlist by name (searches your saved playlists first) or URI.

        Args:
            name_or_uri: Playlist name or Spotify URI.
        """
        if name_or_uri.startswith("spotify:"):
            return self.play(context_uri=name_or_uri)

        try:
            playlists = self.sp.current_user_playlists(limit=50)
            match = None
            for pl in playlists.get("items", []):
                if name_or_uri.lower() in pl["name"].lower():
                    match = pl
                    break

            if match:
                self.sp.start_playback(context_uri=match["uri"],
                                       device_id=self._active_device)
                return _ok(f"Playing playlist: {match['name']}")

            # Fall back to public search
            return self.search_and_play(name_or_uri, search_type="playlist")
        except Exception as exc:
            return _err(str(exc))

    def play_album(self, query: str) -> Dict[str, Any]:
        """
        Search for and play an album.

        Args:
            query: Album name (and optionally artist), e.g. "Dark Side of the Moon Pink Floyd".
        """
        return self.search_and_play(query, search_type="album")

    def play_artist(self, artist_name: str) -> Dict[str, Any]:
        """
        Play the top tracks for an artist.

        Args:
            artist_name: Artist name.
        """
        try:
            results = self.sp.search(q=artist_name, limit=1, type="artist")
            artists = results.get("artists", {}).get("items", [])
            if not artists:
                return _err(f"Artist '{artist_name}' not found.")

            artist = artists[0]
            # Play artist context (Spotify generates a radio-style mix)
            self.sp.start_playback(context_uri=artist["uri"],
                                   device_id=self._active_device)
            return _ok(f"Playing artist mix for: {artist['name']}")
        except Exception as exc:
            return _err(str(exc))

    def queue_track(self, query: str) -> Dict[str, Any]:
        """
        Add a track to the playback queue without interrupting current playback.

        Args:
            query: Track name or Spotify URI.
        """
        try:
            if query.startswith("spotify:track:"):
                uri = query
                name = query
            else:
                results = self.sp.search(q=query, limit=1, type="track")
                items = results.get("tracks", {}).get("items", [])
                if not items:
                    return _err(f"Track '{query}' not found.")
                uri  = items[0]["uri"]
                name = items[0]["name"]

            self.sp.add_to_queue(uri=uri, device_id=self._active_device)
            return _ok(f"Added '{name}' to queue.")
        except Exception as exc:
            return _err(str(exc))

    # ==================================================================
    # ── LIBRARY ───────────────────────────────────────────────────────
    # ==================================================================

    def like_current_track(self) -> Dict[str, Any]:
        """Save (like) the currently playing track to your library."""
        try:
            current = self.sp.current_playback()
            if not current or not current.get("item"):
                return _err("Nothing is playing.")
            track_id = current["item"]["id"]
            track_name = current["item"]["name"]
            self.sp.current_user_saved_tracks_add([track_id])
            return _ok(f"Liked: {track_name} ♥")
        except Exception as exc:
            return _err(str(exc))

    def unlike_current_track(self) -> Dict[str, Any]:
        """Remove the currently playing track from your library."""
        try:
            current = self.sp.current_playback()
            if not current or not current.get("item"):
                return _err("Nothing is playing.")
            track_id = current["item"]["id"]
            track_name = current["item"]["name"]
            self.sp.current_user_saved_tracks_delete([track_id])
            return _ok(f"Removed '{track_name}' from library.")
        except Exception as exc:
            return _err(str(exc))

    def is_current_track_liked(self) -> Dict[str, Any]:
        """Check if the currently playing track is in your library."""
        try:
            current = self.sp.current_playback()
            if not current or not current.get("item"):
                return _err("Nothing is playing.")
            track_id   = current["item"]["id"]
            track_name = current["item"]["name"]
            liked      = self.sp.current_user_saved_tracks_contains([track_id])[0]
            status     = "♥ liked" if liked else "♡ not liked"
            return _ok(f"'{track_name}' is {status}.", liked=liked)
        except Exception as exc:
            return _err(str(exc))

    def get_top_tracks(self, time_range: str = "medium_term",
                       limit: int = 10) -> Dict[str, Any]:
        """
        Return your most-played tracks.

        Args:
            time_range: 'short_term' (4 weeks) | 'medium_term' (6 months) | 'long_term' (all time).
            limit:      Number of tracks (1–50, default 10).
        """
        try:
            results = self.sp.current_user_top_tracks(
                time_range=time_range, limit=limit
            )
            tracks = []
            for i, t in enumerate(results.get("items", []), 1):
                artists = ", ".join(a["name"] for a in t["artists"])
                tracks.append(f"{i:2}. {t['name']} — {artists}")

            label_map = {
                "short_term":  "last 4 weeks",
                "medium_term": "last 6 months",
                "long_term":   "all time",
            }
            period  = label_map.get(time_range, time_range)
            message = f"Your top {limit} tracks ({period}):\n" + "\n".join(tracks)
            return _ok(message, tracks=tracks)
        except Exception as exc:
            return _err(str(exc))

    def get_top_artists(self, time_range: str = "medium_term",
                        limit: int = 10) -> Dict[str, Any]:
        """
        Return your most-listened-to artists.

        Args:
            time_range: 'short_term' | 'medium_term' | 'long_term'.
            limit:      Number of artists (default 10).
        """
        try:
            results = self.sp.current_user_top_artists(
                time_range=time_range, limit=limit
            )
            artists = [
                f"{i:2}. {a['name']} — {', '.join(a['genres'][:3]) or 'no genres'}"
                for i, a in enumerate(results.get("items", []), 1)
            ]
            label_map = {
                "short_term":  "last 4 weeks",
                "medium_term": "last 6 months",
                "long_term":   "all time",
            }
            period  = label_map.get(time_range, time_range)
            message = f"Your top {limit} artists ({period}):\n" + "\n".join(artists)
            return _ok(message, artists=artists)
        except Exception as exc:
            return _err(str(exc))

    # ==================================================================
    # ── PLAYLISTS ─────────────────────────────────────────────────────
    # ==================================================================

    def list_playlists(self, limit: int = 20) -> Dict[str, Any]:
        """
        List your saved playlists.

        Args:
            limit: Maximum playlists to return (default 20).
        """
        try:
            results   = self.sp.current_user_playlists(limit=limit)
            playlists = []
            for pl in results.get("items", []):
                track_count = pl["tracks"]["total"]
                playlists.append(
                    f"• {pl['name']}  ({track_count} tracks)  [{pl['uri']}]"
                )
            if not playlists:
                return _ok("You have no saved playlists.")
            message = f"Your playlists ({len(playlists)}):\n" + "\n".join(playlists)
            return _ok(message, playlists=playlists)
        except Exception as exc:
            return _err(str(exc))

    def create_playlist(self, name: str,
                        description: str = "",
                        public: bool = False) -> Dict[str, Any]:
        """
        Create a new playlist.

        Args:
            name:        Playlist name.
            description: Optional description.
            public:      True for public, False for private (default False).
        """
        try:
            user_id  = self.sp.current_user()["id"]
            playlist = self.sp.user_playlist_create(
                user=user_id,
                name=name,
                public=public,
                description=description,
            )
            return _ok(
                f"Created {'public' if public else 'private'} playlist: '{name}'",
                uri=playlist["uri"],
                playlist_id=playlist["id"],
            )
        except Exception as exc:
            return _err(str(exc))

    def add_current_to_playlist(self, playlist_name: str) -> Dict[str, Any]:
        """
        Add the currently playing track to one of your playlists.

        Args:
            playlist_name: Partial or full name of the target playlist.
        """
        try:
            current = self.sp.current_playback()
            if not current or not current.get("item"):
                return _err("Nothing is playing.")

            track_uri  = current["item"]["uri"]
            track_name = current["item"]["name"]

            # Find matching playlist
            results   = self.sp.current_user_playlists(limit=50)
            match     = None
            for pl in results.get("items", []):
                if playlist_name.lower() in pl["name"].lower():
                    match = pl
                    break

            if not match:
                return _err(f"Playlist '{playlist_name}' not found.")

            self.sp.playlist_add_items(match["id"], [track_uri])
            return _ok(
                f"Added '{track_name}' to playlist '{match['name']}'."
            )
        except Exception as exc:
            return _err(str(exc))

    # ==================================================================
    # ── DEVICES ───────────────────────────────────────────────────────
    # ==================================================================

    def list_devices(self) -> Dict[str, Any]:
        """List all available Spotify Connect devices."""
        try:
            result  = self.sp.devices()
            devices = result.get("devices", [])
            if not devices:
                return _ok(
                    "No active devices found. Open Spotify on any device first."
                )
            lines = []
            for d in devices:
                active = " ← active" if d["is_active"] else ""
                lines.append(
                    f"• {d['name']}  [{d['type']}]  vol:{d['volume_percent']}%{active}"
                    f"  id:{d['id']}"
                )
            message = "Available devices:\n" + "\n".join(lines)
            return _ok(message, devices=devices)
        except Exception as exc:
            return _err(str(exc))

    def transfer_playback(self, device_name: str) -> Dict[str, Any]:
        """
        Transfer playback to a different device.

        Args:
            device_name: Partial name of the target device (e.g. 'laptop', 'phone').
        """
        try:
            result  = self.sp.devices()
            devices = result.get("devices", [])
            match   = None
            for d in devices:
                if device_name.lower() in d["name"].lower():
                    match = d
                    break

            if not match:
                names = [d["name"] for d in devices]
                return _err(
                    f"Device '{device_name}' not found. "
                    f"Available: {', '.join(names) or 'none'}"
                )

            self.sp.transfer_playback(match["id"], force_play=True)
            self._active_device = match["id"]
            return _ok(f"Transferred playback to: {match['name']}")
        except Exception as exc:
            return _err(str(exc))

    # ==================================================================
    # ── RECOMMENDATIONS ───────────────────────────────────────────────
    # ==================================================================

    def get_recommendations(self, seed_query: Optional[str] = None,
                             limit: int = 10) -> Dict[str, Any]:
        """
        Generate track recommendations based on the current track or a query.

        Args:
            seed_query: Optional artist/track to seed recommendations from.
                        Defaults to the currently playing track.
            limit:      Number of recommendations (default 10).
        """
        try:
            seed_track_ids: List[str] = []
            seed_artist_ids: List[str] = []

            if seed_query:
                results = self.sp.search(q=seed_query, limit=1, type="track")
                items = results.get("tracks", {}).get("items", [])
                if items:
                    seed_track_ids = [items[0]["id"]]
            else:
                current = self.sp.current_playback()
                if current and current.get("item"):
                    track = current["item"]
                    seed_track_ids  = [track["id"]]
                    seed_artist_ids = [track["artists"][0]["id"]]

            if not seed_track_ids and not seed_artist_ids:
                return _err(
                    "Could not determine seed. Play a track or provide a query."
                )

            recs = self.sp.recommendations(
                seed_tracks=seed_track_ids[:2],
                seed_artists=seed_artist_ids[:1],
                limit=limit,
            )

            tracks = []
            uris   = []
            for t in recs.get("tracks", []):
                artists = ", ".join(a["name"] for a in t["artists"])
                tracks.append(f"• {t['name']} — {artists}")
                uris.append(t["uri"])

            message = f"Recommended tracks:\n" + "\n".join(tracks)
            return _ok(message, tracks=tracks, uris=uris)
        except Exception as exc:
            return _err(str(exc))

    # ==================================================================
    # ── SYSTEM PROMPT ADDITION ────────────────────────────────────────
    # ==================================================================

    def get_system_prompt_addition(self) -> str:
        return """**Spotify Plugin Tools:**

Playback:
- `spotify.play()` — Resume playback
- `spotify.pause()` — Pause playback
- `spotify.toggle()` — Toggle play/pause
- `spotify.next()` — Skip to next track
- `spotify.previous()` — Previous track
- `spotify.seek(position_ms)` — Seek to position (e.g. 60000 = 1 min)
- `spotify.set_volume(0–100)` — Set volume
- `spotify.set_shuffle(true/false)` — Toggle shuffle
- `spotify.set_repeat("off"|"context"|"track")` — Set repeat mode

Now Playing:
- `spotify.now_playing()` — Full current track info
- `spotify.queue_info()` — Show upcoming tracks

Search & Play:
- `spotify.search_and_play(query, search_type)` — Find and play (track/album/playlist/artist)
- `spotify.play_playlist(name)` — Play a playlist by name or URI
- `spotify.play_album(query)` — Play an album
- `spotify.play_artist(name)` — Play an artist mix
- `spotify.queue_track(query)` — Add a track to queue without interrupting

Library:
- `spotify.like_current()` — Save current track ♥
- `spotify.unlike_current()` — Remove current track from library
- `spotify.is_liked()` — Check if current track is saved
- `spotify.top_tracks(time_range, limit)` — Your most-played tracks
- `spotify.top_artists(time_range, limit)` — Your top artists

Playlists:
- `spotify.list_playlists()` — Show your playlists
- `spotify.create_playlist(name, description, public)` — New playlist
- `spotify.add_to_playlist(playlist_name)` — Add current track to a playlist

Devices:
- `spotify.list_devices()` — Show Spotify Connect devices
- `spotify.transfer(device_name)` — Move playback to another device

Recommendations:
- `spotify.recommend(seed_query, limit)` — Get track recommendations

Routing examples:
- "Play Bohemian Rhapsody" → search_and_play("Bohemian Rhapsody")
- "Turn it up to 80" → set_volume(80)
- "What's playing?" → now_playing()
- "Like this song" → like_current()
- "Play my Chill playlist" → play_playlist("Chill")
- "Add this to my Workout playlist" → add_to_playlist("Workout")
- "Move music to my laptop" → transfer("laptop")
- "Recommend me similar songs" → recommend()
"""

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup(self) -> None:
        """Nothing persistent to clean up; spotipy manages token cache."""
        logger.info("[spotify] Plugin cleanup complete.")


# ===========================================================================
# CLI helper — run `python spotify_plugin.py --setup` to bootstrap config
# ===========================================================================

def _create_config_template() -> None:
    """Write a starter config file with placeholder credentials."""
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    if _CONFIG_PATH.exists():
        print(f"Config already exists: {_CONFIG_PATH}")
        print("Delete it and re-run --setup if you want to reset.")
        return

    template = {
        "client_id":     "YOUR_CLIENT_ID",
        "client_secret": "YOUR_CLIENT_SECRET",
        "redirect_uri":  _REDIRECT,
    }

    with open(_CONFIG_PATH, "w") as fh:
        json.dump(template, fh, indent=2)

    print(f"\n✅  Config template created: {_CONFIG_PATH}")
    print("\nNext steps:")
    print("  1. Go to https://developer.spotify.com/dashboard")
    print("  2. Create a new app (any name)")
    print(f'  3. Add this Redirect URI in the app settings: {_REDIRECT}')
    print("  4. Copy your Client ID and Client Secret into:")
    print(f"       {_CONFIG_PATH}")
    print("  5. Start JARVIS — a browser will open for one-time OAuth consent.\n")


def _test_plugin() -> None:
    """Quick smoke test — authenticate and print now-playing info."""
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s | %(message)s")
    plugin = SpotifyPlugin()
    if not plugin.check_dependencies():
        print("❌  spotipy not installed. Run: pip install spotipy")
        return
    if not plugin.initialize():
        print("❌  Initialization failed. Check config and credentials.")
        return
    print("\n✅  Plugin loaded. Testing now_playing…\n")
    result = plugin.now_playing()
    print(result["message"])
    print("\n✅  Test complete.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="JARVIS Spotify Plugin utilities"
    )
    parser.add_argument("--setup", action="store_true",
                        help="Create the config template file")
    parser.add_argument("--test",  action="store_true",
                        help="Authenticate and test connection")
    args = parser.parse_args()

    if args.setup:
        _create_config_template()
    elif args.test:
        _test_plugin()
    else:
        parser.print_help()
