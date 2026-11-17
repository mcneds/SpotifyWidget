"""Regression tests for expired Spotify refresh-token recovery."""

import threading
import time
import unittest
from unittest.mock import Mock, patch

from spotipy.exceptions import SpotifyOauthError
from spotipy.oauth2 import SpotifyOAuth

from spotify_auth import RecoveringSpotifyOAuth


class RecoveringSpotifyOAuthTests(unittest.TestCase):
    def setUp(self):
        # No actual network, cache files, or browser authorization is needed.
        self.oauth = object.__new__(RecoveringSpotifyOAuth)
        self.oauth._refresh_lock = threading.Lock()
        self.oauth.on_reauthorization_required = Mock()
        self.oauth.scope = "user-read-playback-state"
        self.oauth.cache_handler = Mock()
        self.oauth.cache_handler.get_cached_token.return_value = {
            "access_token": "expired",
            "refresh_token": "old_refresh",
            "scope": "user-read-playback-state",
            "expires_at": 0,
        }

    def test_invalid_grant_prompts_for_new_authorization(self):
        replacement = {"access_token": "new", "refresh_token": "new_refresh"}
        with patch.object(
            SpotifyOAuth,
            "refresh_access_token",
            side_effect=SpotifyOauthError("revoked", error="invalid_grant"),
        ), patch.object(self.oauth, "get_access_token", return_value=replacement) as login:
            self.assertEqual(self.oauth.refresh_access_token("old_refresh"), replacement)
            login.assert_called_once_with(check_cache=False)
            self.oauth.on_reauthorization_required.assert_called_once_with()

    def test_other_oauth_errors_do_not_trigger_login(self):
        with patch.object(
            SpotifyOAuth,
            "refresh_access_token",
            side_effect=SpotifyOauthError("bad client", error="invalid_client"),
        ), patch.object(self.oauth, "get_access_token") as login:
            with self.assertRaises(SpotifyOauthError):
                self.oauth.refresh_access_token("old_refresh")
            login.assert_not_called()
            self.oauth.on_reauthorization_required.assert_not_called()

    def test_successful_refresh_is_unchanged(self):
        replacement = {"access_token": "refreshed", "refresh_token": "same_refresh"}
        with patch.object(SpotifyOAuth, "refresh_access_token", return_value=replacement) as refresh:
            self.assertEqual(self.oauth.refresh_access_token("old_refresh"), replacement)
            refresh.assert_called_once_with("old_refresh")
            self.oauth.on_reauthorization_required.assert_not_called()

    def test_concurrent_refresh_uses_new_cache(self):
        # A second request may have started with the old token, but the first
        # has already saved a valid new token; don't refresh or prompt again.
        cached = {
            "access_token": "new",
            "refresh_token": "new_refresh",
            "scope": "user-read-playback-state",
            "expires_at": time.time() + 3600,
        }
        self.oauth.cache_handler.get_cached_token.return_value = cached
        with patch.object(SpotifyOAuth, "refresh_access_token") as refresh:
            self.assertIs(self.oauth.refresh_access_token("old_refresh"), cached)
            refresh.assert_not_called()
            self.oauth.on_reauthorization_required.assert_not_called()


if __name__ == "__main__":
    unittest.main()
