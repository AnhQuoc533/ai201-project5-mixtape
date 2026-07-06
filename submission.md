## AI Usage
**Instance 1:**
* *What I gave the AI:* 
* *What it produced:* 
* *What I changed or overrode:* After I fixed all bugs, I came back to double-check, make a few changes, add more inforamtion to the [Codebase Map](#codebase-map). Because in the beginning, the source code contained logical bugs and the AI could misunderstand and assume they were the actualy features of the services. Bugs are not features.


**Instance 2:**
* *What I gave the AI:* 
* *What it produced:* 
* *What I changed or overrode:* 

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
* **View a playlist:** `GET /playlists/<playlist_id>` in `routes/playlists.py` calls `playlist_service.get_playlist(playlist_id)`. Returns a *Playlist* record's metadata (name, creator, collaboration setting, timestamps).
* **View the list of songs in a playlist:** `GET /playlists/<playlist_id>/songs` in `routes/playlists.py` calls `playlist_service.get_playlist_songs(playlist_id)`. Returns all *Song* records in the playlist, ordered by their position in the playlist.
* **Add a song to a playlist:** `POST /playlists/<playlist_id>/songs` in `routes/playlists.py` calls `notification_service.add_to_playlist(playlist_id, song_id, added_by_user_id)`. Adds the *Song* to the *Playlist* and creates a *Notification* record for the song's original sharer (if different from the user adding it).
  
#### User's Feed Service
* **Show recent activities within 24 hours from friends:** `GET /feed/<user_id>/listening-now` in `routes/feed.py` calls `feed_service.get_friends_listening_now(user_id)`. Returns the most recent *ListeningEvent* from each friend within the last 24 hours, deduplicated to show only one song per friend.
* **Show a number of recent activities from friends:** `GET /feed/<user_id>/activity` in `routes/feed.py` calls `feed_service.get_activity_feed(user_id, limit)`. Returns the N most recent *ListeningEvent* records from all friends (default limit is 20), ordered by most recent first.

## Root Cause Analysis
### Bug #1
**Issue number:** 1  
**Title:** My listening streak keeps resetting  
**Preproduction Process:**  
<!-- What steps did you take to confirm the bug exists before touching any code? What inputs, sequence of actions, or data condition triggered the behavior? !-->
**Discovery Process:**  
<!-- Which files did you look at? What was your navigation path? What moment made you confident you'd found the right place — not just a suspicious area, but the specific cause? !-->
**Bug Description:**  
<!-- explain the specific condition, comparison, logic error, or missing step that caused the problem. !-->
**Solution:**  
<!-- What did you change and why does that change fix the root cause? What related functionality did you check afterward to confirm you didn't break anything? !-->
**Side-effect Check:**  


### Bug #2
**Issue number:** 2  
**Title:** *Friends Listening Now* shows people from yesterday  
**Preproduction Process:**  
**Discovery Process:**  
**Bug Description:**  
**Solution:**  
**Side-effect Check:**  

### Bug #3
**Issue number:** 3   
**Title:** The same song keeps showing up twice in search  
**Preproduction Process:**  
**Discovery Process:**  
**Bug Description:**  
**Solution:**  
**Side-effect Check:**  

### Bug #4
**Issue number:** 4   
**Title:** I got notified when a friend added my song to a playlist but not when they rated it
**Preproduction Process:**  
**Discovery Process:**  
**Bug Description:**  
**Solution:**  
**Side-effect Check:**  

### Bug #5
**Issue number:** 5   
**Title:** The last song in a playlist never shows up
**Preproduction Process:**  
**Discovery Process:**  
**Bug Description:** The last line of code of the `get_playlist_songs()` function used list comprehension to quickly convert query results to a list of dictionary. However, the code also indexed the list of query results from the first position up to the last position exclusively, NOT inclusively, `songs[:-1]`. In Python, a list slice `[start:stop]` is inclusive of the start but exclusive of the stop. This caused the playlist display service to skip the last queried song and introduced a bug.
**Solution:** Simply remove the list slicing, i.e. `[:-1]`. This will let the function retrieve and process the whole query results stored in the `songs` list, instead of a part of it.
**Side-effect Check:**  


## Regression Test
<!-- A test that would have caught the fixed bugs before it was introduced. Reference the test and explain what behavior it verifies and why that test would have failed against the buggy code. !-->