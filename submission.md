## AI Usage
**Instance 1:**
* *What I gave the AI:* The source code in `routes/` and `services/`, a list of services and their corresponding features, a short data flow description of the feature *Rate a Song* to use as an example, and a request of complete the data flow description for the remaining features.  
* *What it produced:* A complete data flow description for each feature, providing a clear overview of how data flows through the application.  
* *What I changed or overrode:* After I fixed all bugs, I came back to double-check, make a few changes, add more inforamtion to the [Codebase Map](#codebase-map). Because in the beginning, the source code contained logical bugs and the AI could misunderstand and assume they were the actualy features of the services. Bugs are not features.  


**Instance 2:**
* *What I gave the AI:* The source code of `services/feed_service.py` and `tests/test_playlists.py` (as a template to follow), a request to create a comprehensive `pytest` framework for testing all functions in `services/feed_service.py`, and test requirements: verify correct record counts, test deduplication (one song per friend), ensure only friends' activities are shown (not non-friends), verify recency ordering, and validate the limit parameter.
* *What it produced:* A complete test suite in `tests/test_feed.py` with 17 test cases organized into 3 test classes: `TestFriendsListeningNow` (7 tests), `TestActivityFeed` (8 tests), and `TestFeedEdgeCases` (2 tests). It included a test scenario with 4 users (main user, 3 friends, 1 non-friend) and 5 listening events distributed across different time periods to test boundary conditions like midnight UTC cutoffs.
* *What I changed or overrode:* I removed similar test cases and refactored some of the test function names. More importantly, I fixed 2 of the test cases regarding Recent Activity features, as they made a mistake by assuming there were 3 recent activities from friends while there were 4 in total, according to the test scenario. 

## Codebase Map
### Overview
* `app.py` sets up Flask API and SQLAlchemy database for the service.  
* `models.py` defines 7 SQLAlchemy models: **User**, **Tag**, **Song**, **ListeningEvent**, **Rating**, **Playlist**, and **Notification**. Plus, there are 3 association tables: **Friendships**, **Song Tags**, and **Playlist Entries**.
* The URL routes are built by source code inside `routes/`. They perform input parsing and response formatting, while delegating immediately to a corresponding service function, built by source code inside `services/`.
* All business logic lives in `services/`, so the business data is mainly processed and updated in there.

### Data Flow
#### Song Service
* **Rate a Song:** `POST /songs/<id>/rate` in `routes/songs.py` calls `notification_service.rate_song(user_id, song_id, score)`. The function creates or updates a *Rating* record with the user's score (1-5).
* **Search for a Song:** `GET /songs/search?q=<query>` in `routes/songs.py` calls `search_service.search_songs(query)`. Returns all *Song* records where the title or artist contains the query string (case-insensitive), along with their associated tags.
* **Listen to a Song:** `POST /songs/<song_id>/listen` in `routes/songs.py` calls `streak_service.record_listening_event(user_id, song_id)`. Creates a *ListeningEvent* record and updates the user's *listening_streak* and *last_listened_at* timestamp based on consecutive listening days.
* **View a Song:** `GET /songs/<song_id>` in `routes/songs.py` calls `search_service.get_song(song_id)`. Returns a single *Song* record with all its fields and associated tags.
  
#### User Service
* **View listening streak:** `GET /users/<user_id>/streak` in `routes/users.py` calls `streak_service.get_streak(user_id)`. Returns the user's current *listening_streak* value.
* **View Notifications:** `GET /users/<user_id>/notifications` in `routes/users.py` calls `notification_service.get_notifications(user_id, unread_only)`. Returns a list of *Notification* records ordered by most recent first, optionally filtered to unread notifications only.
* **Mark a notification as read:** `POST /users/notifications/<notification_id>/read` in `routes/users.py` calls `notification_service.mark_as_read(notification_id)`. Updates the *Notification* record's *read* field to True.
  
#### Playlist Service
* **Create a playlist:** `POST /playlists/` in `routes/playlists.py` calls `playlist_service.create_playlist(name, created_by, is_collaborative)`. Creates a new *Playlist* record with the specified name, creator, and collaboration setting.
* **View a playlist:** `GET /playlists/<playlist_id>` in `routes/playlists.py` calls `playlist_service.get_playlist(playlist_id)`. Returns a *Playlist* record (name, creator, collaboration setting, timestamps).
* **View songs in a playlist:** `GET /playlists/<playlist_id>/songs` in `routes/playlists.py` calls `playlist_service.get_playlist_songs(playlist_id)`. Returns all *Song* records in the playlist, ordered by their position.
* **Add a song to a playlist:** `POST /playlists/<playlist_id>/songs` in `routes/playlists.py` calls `notification_service.add_to_playlist(playlist_id, song_id, added_by_user_id)`. Adds the *Song* to the *Playlist* and creates a *Notification* record for the song's original sharer (if different from the user adding it).
  
#### User's Feed Service
* **Show Friends Listening Now feed:** `GET /feed/<user_id>/listening-now` in `routes/feed.py` calls `feed_service.get_friends_listening_now(user_id)`. Returns the most recent *ListeningEvent* from each friend within the current day, deduplicated to show only one song per friend.
* **Show Recent Activities from friends:** `GET /feed/<user_id>/activity` in `routes/feed.py` calls `feed_service.get_activity_feed(user_id, limit)`. Returns the N most recent *ListeningEvent* records from all friends (default limit is 20), ordered by most recent first.

## Root Cause Analysis
### Bug #1
**Issue number:** 1  
**Title:** My listening streak keeps resetting  
**Reproduction Process:** I ran the test cases in `tests/test_streaks.py` and encountered 1 failed tests and 4 passed test.   
<!-- What steps did you take to confirm the bug exists before touching any code? What inputs, sequence of actions, or data condition triggered the behavior? !-->
**Discovery Process:** After reading the failure report and the failed test case (`test_streak_increments_on_sunday`), I found out that the streaking service did not increment the listening streak on Sundays. This test case primarily executed `update_listening_streak` function. Therefore, the bug must have lived there.   
<!-- Which files did you look at? What was your navigation path? What moment made you confident you'd found the right place — not just a suspicious area, but the specific cause? !-->
**Bug Description:** Inside the `update_listening_streak` lies the streak-counting rules, implemented using an `if-elif-else` statement. However, in the increment condition, there was a code that prevented the streak from increasing if the current date was Sunday, i.e. `today.weekday() != 6`. As a result, the increment logic was skipped on Sundays, causing execution to fall to the `else` branch and incorrectly reset the user's listening streak.
<!-- explain the specific condition, comparison, logic error, or missing step that caused the problem. !-->
**Solution:** Simply remove `today.weekday() != 6` from the increment condition. This lets the function increment the listening streak, regardless of the day of the week.  
<!-- What did you change and why does that change fix the root cause? What related functionality did you check afterward to confirm you didn't break anything? !-->
**Side-effect Check:** I re-ran the test in `tests/test_streaks.py`, including the test cases for streak initialization, reset, increment, and no change on same day. All tests passed successfully.  


### Bug #2
**Issue number:** 2  
**Title:** *Friends Listening Now* shows people from yesterday  
**Reproduction Process:** I seeded the database with test data by executing `seed_data.py` and ran the application. To retrieve user IDs, I executed the command `sqlite3 instance/mixtape.db "SELECT * FROM user;"` and inspected the Listening Now feed for several users. Simone's feed showed his friend, Nova, was listening to a song from yesterday. This scenario confirmed the reported bug.  
**Discovery Process:** According to the [Data Flow](#data-flow), the `get_friends_listening_now` function in `services/feed_service.py` is responsible for Listening Now service. Its docstring also confirmed its responsibility.    
**Bug Description:** The root cause was the `cutoff` variable. The query filtered `ListeningEvent` records using the timestamp stored in this variable, which was defined as 24 hours before the current time. As a result, friends who listened within the last 24 hours, including yesterday, appeared in the Friends Listening Now feed.       
**Solution:** I removed `RECENT_THRESHOLD` and re-defined `cutoff`:
```
cutoff = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
```
New `cutoff` will let the query return listening events that only occurred since midnight UTC of the current day.   
**Side-effect Check:** I re-inspected the Listening Now feed for all testing users and every records correctly showed only activities within the current day. Plus, the datameta of the records were correctly returned.  

### Bug #3
**Issue number:** 3   
**Title:** The same song keeps showing up twice in search  
**Reproduction Process:** After multiple attempts to reproduce the bug, there was no success. The bug did not appear and did not fail any test cases by `tests/test_search.py`. Moreoever, command-line testing with `sqlite3` (to create new data on `mixtape.db`) and `curl` (to get search result back from the application) did not catch any issues related to this report.   
**Discovery Process:** According to the [Data Flow](#data-flow), the `search_songs` function in `services/search_service.py` is responsible for Song Searching service. Its docstring also confirmed its responsibility.   
**Bug Description:** The bug actually never happens. The source code of `search_songs` function uses `.all()` on the query and as per **SQLAlchemy** documentation, it will automatically deduplicate the results by primary key. So even if the `.outerjoin()` creates duplicate songs in the SQL result set, `.all()` returns a list with only unique songs.  
**Solution:** N/A  
**Side-effect Check:** N/A  

### Bug #4
**Issue number:** 4   
**Title:** I got notified when a friend added my song to a playlist but not when they rated it
**Reproduction Process:** Using `sqlite3` command, I created 2 new users and 1 song. I marked the new song as shared by User 1. Then, I rated this song as User 2 using `curl` and viewed the list of notifications of User 1. After checking notifications, I confirmed that the rating activity from User 2 did not appear in User 1's notification feed.    
**Discovery Process:** According to the [Data Flow](#data-flow), the `rate_song` function in `services/notification_service.py` is responsible for Song Rating service. Its docstring also confirmed its responsibility.  
**Bug Description:** As I compared code implementation of two functions, `rate_song` and `add_to_playlist`, I discovered that the latter function established a notification to the song sharer after user added a song to their playlist, while the former function did not.    
**Solution:** I added an `if` condition, similar to the one in `add_to_playlist`, to create a notification for the user who originially shared the song. This code block will be executed after the rating score is made and updated to the database.
```python
if song.shared_by != user_id:
    create_notification(
        user_id=song.shared_by,
        notification_type="song_rated",
        body=f"{rater.username} rated your song '{song.title}' {score} star{'s' if score > 1 else ''}.",
    )
```
**Side-effect Check:** I rated different songs with different scores and the rating activity correctly showed up on the sharer's notifications. Plus, I let one of the user rate the song they shared and no notification was made, as expected.  

### Bug #5
**Issue number:** 5   
**Title:** The last song in a playlist never shows up
**Reproduction Process:** I ran the test cases in `tests/test_playlists.py` and encountered 2 failed tests and 1 passed test.  
**Discovery Process:** After reading the test summary, I found out that the service returned 4 songs in the testing playlist when it was supposed to be 5 of them. I read the two of the failed test cases (`test_playlist_returns_all_songs` and `test_playlist_returns_songs_in_order`) and confirmed the main function used in these test cases was `get_playlist_songs`. Therefore, the bug must have lived there. 
**Bug Description:** The last line of code of the `get_playlist_songs()` function used list comprehension to quickly convert query results to a list of dictionary. However, the code also indexed the list of query results from the first position up to the last position exclusively, NOT inclusively, `songs[:-1]`. In Python, a list slice `[start:stop]` is inclusive of the start but exclusive of the stop. This caused the playlist display service to skip the last queried song and introduced a bug.
**Solution:** Simply remove the list slicing, i.e. `[:-1]`. This lets the function retrieve and process the whole query results stored in the `songs` list, instead of a part of it.
**Side-effect Check:** I re-ran the test in `tests/test_playlists.py`, including the test cases for empty playlist and song order, and all tests passed.


## Regression Test
<!-- A test that would have caught the fixed bugs before it was introduced. Reference the test and explain what behavior it verifies and why that test would have failed against the buggy code. !-->
**Test Subject:** Feed Service

**Overview:** This regression test framework for the feed service is made with `pytest` and stored in `tests/test_feed.py`. It includes comprehensive test cases that would have caught bugs in the feed logic before they were introduced.

**For Bug #2:**

- `TestFriendsListeningNow.test_inactive_friends_since_midnight()`
  - **Behavior verified:** Friends who last listened before midnight UTC today should NOT appear in the Listening Now feed.
  - **Why it would fail against buggy code:** If `cutoff` was incorrectly set to 24 hours ago (instead of midnight UTC today), Friend 3 (who listened before midnight) would appear in the feed when they shouldn't. This test would fail because the actual feed length would be 3 instead of the expected 2.

- `TestFriendsListeningNow.test_number_of_friends_listening_today()`
  - **Behavior verified:** Only friends with activities between midnight UTC and current time appear in the feed.
  - **Why it would fail against buggy code:** The buggy 24-hour cutoff would include yesterday's activities, causing the test to return 3 friends instead of the expected 2.

**For General Feed Logic Correctness:**

- **Test:** `TestFriendsListeningNow.test_one_song_per_friend()`
  - **Behavior verified:** Deduplication works correctly—each friend appears at most once, showing only their most recent listening event.
  - **Why it would fail:** If the deduplication logic in `get_friends_listening_now()` was broken, Friend 2 (who has 2 listening events) would appear twice in the feed.

- **Test:** `TestFriendsListeningNow.test_only_shows_friends()`
  - **Behavior verified:** Only activities from actual friends are included; non-friends are excluded.
  - **Why it would fail:** If the friend filtering was incorrect, the non-friend's activity would appear in the Listening Now feed, causing an assertion error.

- **Test:** `TestFriendsListeningNow.test_ordered_by_recency_descending()`
  - **Behavior verified:** Activities are ordered by most recent first.
  - **Why it would fail:** If the ordering logic was incorrect, the test would fail when comparing adjacent timestamps and find that they're not in descending order.

- **Test:** `TestActivityFeed.test_activity_limit_high_bound()`
  - **Behavior verified:** The activity feed returns 4 activities, despite the limit parameter being greater.
  - **Why it would fail:** If limit logic was broken or activities were being incorrectly filtered, the actual count would not match the expected count of 4.

- **Test:** `TestActivityFeed.test_activity_limit_low_bound()`
  - **Behavior verified:** The activity feed returns the exact number of activities denoted by the limit, as the limit is lower than the activity count.
  - **Why it would fail:** If limit logic was broken or activities were being incorrectly filtered, the actual count would not match the limit value.

- **Test:** `TestActivityFeed.test_only_shows_friends()`
  - **Behavior verified:** The activity feed only includes activities from friends, not other users.
  - **Why it would fail:** If friend filtering was broken, non-friend activities would appear in the Recent Activity feed, failing the assertion.

- **Test:** `TestFeedEdgeCases.test_listening_now_VS_recent_activity()`
  - **Behavior verified:** Listening Now filters by current day; Activity Feed does not.
  - **Why it would fail:** If both feeds used the same cutoff logic, this test would fail because activity feed would have the same or fewer results than listening_now, which contradicts the expected behavior.

**Why These Tests Are Effective:**

These tests use carefully seeded data that creates simple yet realistic scenarios:
- Friend 1: 1 activity today
- Friend 2: 2 activities (1 today, 1 yesterday)
- Friend 3: 1 activity yesterday
- Non-friend: 1 activity today (excluded from feeds)

This setup allows tests to verify boundary conditions (midnight UTC cutoff), deduplication logic, ordering, filtering, and limit handling—all of which are critical to preventing feed-related bugs from reoccurring.
