"""Refresh-token recovery for Spotify's desktop OAuth flow."""

import threading

from spotipy.exceptions import SpotifyOauthError
from spotipy.oauth2 import SpotifyOAuth


class RecoveringSpotifyOAuth(SpotifyOAuth):
    """Reauthorize in the browser if Spotify rejects an old refresh token."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._refresh_lock = threading.Lock()
        self.on_reauthorization_required = None

    def refresh_access_token(self, refresh_token):
        # Playback polling and button commands can race to refresh the same token.
        # Only one should refresh or launch a browser authorization at a time.
        with self._refresh_lock:
            cached = self.cache_handler.get_cached_token()
            if (
                cached
                and cached.get("access_token")
                and cached.get("scope")
                and self._is_scope_subset(self.scope, cached["scope"])
                and not self.is_token_expired(cached)
            ):
                return cached

            try:
                return super().refresh_access_token(refresh_token)
            except SpotifyOauthError as exc:
                if exc.error != "invalid_grant":
                    raise

                print("Spotify refresh token expired or revoked; reauthorizing in browser.")
                if self.on_reauthorization_required is not None:
                    self.on_reauthorization_required()
                # Bypass the stale token. Spotipy saves the new authorization
                # into the same cache file when the browser flow completes.
                return self.get_access_token(check_cache=False)
