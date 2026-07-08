"""
tests/test_feed.py — Mixtape

Tests for feed logic (Friends Listening Now and Activity Feed).
"""

import pytest
from datetime import datetime, timedelta, timezone
from app import create_app, db
from models import User, Song, ListeningEvent
from services.feed_service import get_friends_listening_now, get_activity_feed


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def seed_feed_data(app):
    """Create users, songs, and listening events for testing."""
    with app.app_context():
        # Create main user
        main_user = User(username="main_user", email="main@example.com")
        db.session.add(main_user)
        db.session.flush()

        # Create friend users
        friend1 = User(username="friend1", email="friend1@example.com")
        friend2 = User(username="friend2", email="friend2@example.com")
        friend3 = User(username="friend3", email="friend3@example.com")
        non_friend = User(username="non_friend", email="nonfriend@example.com")
        db.session.add_all([friend1, friend2, friend3, non_friend])
        db.session.flush()

        # Set up friendships (main_user is friends with friend1, friend2, friend3)
        main_user.friends.append(friend1)
        main_user.friends.append(friend2)
        main_user.friends.append(friend3)
        db.session.commit()

        # Create songs
        songs = [
            Song(title=f"Song {i}", artist="Artist", shared_by=main_user.id)
            for i in range(1, 6)
        ]
        db.session.add_all(songs)
        db.session.flush()

        # Get current time and midnight UTC today
        now = datetime.now(timezone.utc)
        midnight_utc = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Create listening events
        # Friend 1: listened today (1 hour ago) - WILL APPEAR in listening_now
        event_f1_today = ListeningEvent(
            user_id=friend1.id,
            song_id=songs[0].id,
            listened_at=now - timedelta(hours=1)
        )

        # Friend 2: listened today (2 hours ago) - WILL APPEAR in listening_now
        event_f2_today = ListeningEvent(
            user_id=friend2.id,
            song_id=songs[1].id,
            listened_at=now - timedelta(hours=2)
        )

        # Friend 2: listened yesterday (before midnight) - WILL NOT appear in listening_now, WILL appear in activity
        event_f2_yesterday = ListeningEvent(
            user_id=friend2.id,
            song_id=songs[2].id,
            listened_at=midnight_utc - timedelta(hours=1)
        )

        # Friend 3: listened yesterday (before midnight) - WILL NOT appear in listening_now, WILL appear in activity
        event_f3_yesterday = ListeningEvent(
            user_id=friend3.id,
            song_id=songs[3].id,
            listened_at=midnight_utc - timedelta(hours=5)
        )

        # Non-friend: listened today (should NOT appear anywhere)
        event_nonfriend = ListeningEvent(
            user_id=non_friend.id,
            song_id=songs[4].id,
            listened_at=now - timedelta(minutes=30)
        )

        db.session.add_all([
            event_f1_today, event_f2_today, event_f2_yesterday,
            event_f3_yesterday, event_nonfriend
        ])
        db.session.commit()

        yield {
            "main_user": main_user,
            "friends": [friend1, friend2, friend3],
            "non_friend": non_friend,
            "songs": songs,
            "now": now,
            "midnight_utc": midnight_utc,
        }


class TestFriendsListeningNow:
    """Tests for get_friends_listening_now()"""

    def test_number_of_friends_listening_today(self, app, seed_feed_data):
        """
        Should return only friends who listened between midnight UTC today and now.
        Expected: Friend 1 and Friend 2 (both listened today after midnight UTC).
        """
        with app.app_context():
            main_user_id = seed_feed_data["main_user"].id
            feed = get_friends_listening_now(main_user_id)
            assert len(feed) == 2

    def test_one_song_per_friend(self, app, seed_feed_data):
        """
        Should show at most one song per friend (the most recent listening event).
        Friend 2 has 2 listening events, but only the most recent should appear.
        """
        with app.app_context():
            main_user_id = seed_feed_data["main_user"].id
            feed = get_friends_listening_now(main_user_id)

            # Count unique friends in feed
            friend_ids = [item["friend"]["id"] for item in feed]
            assert len(friend_ids) == len(set(friend_ids)), "Duplicate friend in feed"

    def test_inactive_friends_since_midnight(self, app, seed_feed_data):
        """
        Should not show friends with no activities between midnight UTC and now.
        Friend 3 last listened before midnight UTC today, so should not appear.
        """
        with app.app_context():
            main_user_id = seed_feed_data["main_user"].id
            feed = get_friends_listening_now(main_user_id)
            friend_ids = [item["friend"]["id"] for item in feed]

            friend3_id = seed_feed_data["friends"][2].id
            assert friend3_id not in friend_ids

    def test_only_shows_friends(self, app, seed_feed_data):
        """
        Should only show activities from friends, not from non-friends.
        """
        with app.app_context():
            main_user_id = seed_feed_data["main_user"].id
            feed = get_friends_listening_now(main_user_id)
            friend_ids = [item["friend"]["id"] for item in feed]

            non_friend_id = seed_feed_data["non_friend"].id
            assert non_friend_id not in friend_ids

    def test_ordered_by_recency_descending(self, app, seed_feed_data):
        """
        Activities should be ordered by most recent first.
        """
        with app.app_context():
            main_user_id = seed_feed_data["main_user"].id
            feed = get_friends_listening_now(main_user_id)

            # Check that listened_at is in descending order (most recent first)
            for i in range(len(feed) - 1):
                current_time = datetime.fromisoformat(feed[i]["listened_at"])
                next_time = datetime.fromisoformat(feed[i + 1]["listened_at"])
                assert current_time >= next_time, "Feed not ordered by recency (most recent first)"

    def test_empty_friend_list(self, app):
        """
        Should return empty list if user has no friends.
        """
        with app.app_context():
            user = User(username="lonely", email="lonely@example.com")
            db.session.add(user)
            db.session.commit()

            feed = get_friends_listening_now(user.id)
            assert feed == []

    def test_metadata(self, app, seed_feed_data):
        """
        Each item in the feed should contain friend, song, and listened_at data.
        """
        with app.app_context():
            main_user_id = seed_feed_data["main_user"].id
            feed = get_friends_listening_now(main_user_id)

            assert len(feed) > 0
            for item in feed:
                assert "friend" in item
                assert "song" in item
                assert "listened_at" in item
                assert "id" in item["friend"]
                assert "username" in item["friend"]
                assert "id" in item["song"]
                assert "title" in item["song"]


class TestActivityFeed:
    """Tests for get_activity_feed()"""

    def test_activity_limit_high_bound(self, app, seed_feed_data):
        """
        Should return at most `limit` activities from friends.
        With default limit=20 or limit > actual activity count, it should return 4 activities 
        (Friend1 has 1, Friend2 has 2, Friend3 has 1).
        """
        with app.app_context():
            main_user_id = seed_feed_data["main_user"].id
            feed = get_activity_feed(main_user_id)
            # 1 from Friend1 + 2 from Friend2 + 1 from Friend3
            assert len(feed) == 4
            
            feed = get_activity_feed(main_user_id, limit=5)
            assert len(feed) <= 5  

    def test_activity_limit_low_bound(self, app, seed_feed_data):
        """
        Should return exactly limit activities when limit is less than available.
        """
        with app.app_context():
            main_user_id = seed_feed_data["main_user"].id

            # Limit to 1
            feed = get_activity_feed(main_user_id, limit=1)
            assert len(feed) == 1

            # Limit to 2
            feed = get_activity_feed(main_user_id, limit=2)
            assert len(feed) == 2

            # Limit to 4
            feed = get_activity_feed(main_user_id, limit=4)
            assert len(feed) == 4

    def test_only_shows_friends(self, app, seed_feed_data):
        """
        Should only show activities from friends, not from non-friends.
        """
        with app.app_context():
            main_user_id = seed_feed_data["main_user"].id
            feed = get_activity_feed(main_user_id)

            friend_ids = [item["friend"]["id"] for item in feed]
            non_friend_id = seed_feed_data["non_friend"].id
            assert non_friend_id not in friend_ids

    def test_ordered_by_recency_descending(self, app, seed_feed_data):
        """
        Activities should be ordered by most recent first.
        """
        with app.app_context():
            main_user_id = seed_feed_data["main_user"].id
            feed = get_activity_feed(main_user_id)

            # Check that listened_at is in descending order (most recent first)
            for i in range(len(feed) - 1):
                current_time = datetime.fromisoformat(feed[i]["listened_at"])
                next_time = datetime.fromisoformat(feed[i + 1]["listened_at"])
                assert current_time >= next_time, "Feed not ordered by recency (most recent first)"

    def test_empty_friend_list(self, app):
        """
        Should return empty list if user has no friends.
        """
        with app.app_context():
            user = User(username="lonely", email="lonely@example.com")
            db.session.add(user)
            db.session.commit()

            feed = get_activity_feed(user.id)
            assert feed == []

    def test_metadata(self, app, seed_feed_data):
        """
        Each item in the feed should contain friend, song, and listened_at data.
        """
        with app.app_context():
            main_user_id = seed_feed_data["main_user"].id
            feed = get_activity_feed(main_user_id)

            assert len(feed) > 0
            for item in feed:
                assert "friend" in item
                assert "song" in item
                assert "listened_at" in item
                assert "id" in item["friend"]
                assert "username" in item["friend"]
                assert "id" in item["song"]
                assert "title" in item["song"]

    def test_default_limit_is_20(self, app, seed_feed_data):
        """
        Default limit should be 20 when not specified.
        """
        with app.app_context():
            main_user_id = seed_feed_data["main_user"].id

            # Call without limit parameter (should use default)
            feed1 = get_activity_feed(main_user_id)
            # Call with explicit limit=20
            feed2 = get_activity_feed(main_user_id, limit=20)

            assert len(feed1) == len(feed2)


class TestFeedEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_listening_now_VS_recent_activity(self, app, seed_feed_data):
        """
        Verify the key difference: listening_now filters by current day,
        activity_feed does not.
        """
        with app.app_context():
            main_user_id = seed_feed_data["main_user"].id

            listening_now = get_friends_listening_now(main_user_id)
            activity_feed = get_activity_feed(main_user_id)

            # Activity feed should have more or equal activities than listening_now
            # because it includes yesterday's events
            assert len(activity_feed) >= len(listening_now)

    def test_user_not_found_raises_error(self, app):
        """
        Should raise ValueError when user is not found.
        """
        with app.app_context():
            fake_user_id = "non-existent-user-id"

            with pytest.raises(ValueError, match="not found"):
                get_friends_listening_now(fake_user_id)

            with pytest.raises(ValueError, match="not found"):
                get_activity_feed(fake_user_id)
