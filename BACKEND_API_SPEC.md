# Pendo Backend API Specification

> Auto-generated from Flutter frontend analysis — **March 12, 2026**
>
> Base URL: configurable via `API_BASE_URL` env var (default: `http://10.0.2.2:5000`)
> API Prefix: `/api/v1`
> Backend expected: **Flask + Flask-SocketIO**

---

## Table of Contents

1. [Authentication Flow](#1-authentication-flow)
2. [REST API Endpoints](#2-rest-api-endpoints)
3. [Endpoint Contract Table](#3-endpoint-contract-table)
4. [Data Models](#4-data-models)
5. [Socket.IO Events](#5-socketio-events)
6. [Backend Entities](#6-backend-entities)
7. [Pagination Convention](#7-pagination-convention)
8. [Error Response Convention](#8-error-response-convention)

---

## 1. Authentication Flow

```
Mobile App                    Firebase                  Your Backend
─────────                    ────────                  ────────────
1. Phone OTP / Google Sign-In ──►
                              ◄── Firebase User + ID Token
2. POST /api/v1/auth/verify ──────────────────────────►
   { id_token: "<firebase_id_token>" }
                              ◄────────────────────────
   { access_token, refresh_token, user_id, is_new_user }
3. Store JWT pair in secure storage
4. Connect Socket.IO with { auth: { token: "<access_token>" } }
```

**Key points:**

- Firebase handles Phone OTP and Google OAuth on the client side
- Backend receives the **Firebase ID token**, verifies it with Firebase Admin SDK, creates/finds the user, and returns a **JWT pair** (access + refresh)
- All subsequent API calls use `Authorization: Bearer <access_token>`
- On 401, the client automatically attempts refresh via `/api/v1/auth/refresh`
- If refresh fails → session expired → user is signed out

**Public endpoints (no JWT required):**

- `POST /api/v1/auth/verify`
- `POST /api/v1/auth/refresh`
- `GET /health`
- `GET /health/ready`

---

## 2. REST API Endpoints

### 2.1 Auth

#### `POST /api/v1/auth/verify`

Exchange Firebase ID token for backend JWT pair.

|                  | Details                                                                                                          |
| ---------------- | ---------------------------------------------------------------------------------------------------------------- |
| **Auth**         | ❌ Public                                                                                                        |
| **Request Body** | `{ "id_token": "string" }`                                                                                       |
| **Response 200** | `{ "access_token": "string", "refresh_token": "string", "user_id": "string (UUID)", "is_new_user": true/false }` |

#### `POST /api/v1/auth/refresh`

Refresh an expired access token.

|                  | Details                         |
| ---------------- | ------------------------------- |
| **Auth**         | ❌ Public                       |
| **Request Body** | `{ "refresh_token": "string" }` |
| **Response 200** | `{ "access_token": "string" }`  |

---

### 2.2 Users

#### `GET /api/v1/users/me`

Fetch the authenticated user's full profile.

|                  | Details                         |
| ---------------- | ------------------------------- |
| **Auth**         | ✅ Bearer Token                 |
| **Request Body** | None                            |
| **Response 200** | [UserModel JSON](#41-usermodel) |

#### `PUT /api/v1/users/me`

Update the authenticated user's profile fields.

|                  | Details                              |
| ---------------- | ------------------------------------ |
| **Auth**         | ✅ Bearer Token                      |
| **Request Body** | Partial object — any combination of: |

```json
{
  "display_name": "string",
  "bio": "string",
  "date_of_birth": "YYYY-MM-DD",
  "gender": "male" | "female" | "non-binary",
  "looking_for": "male" | "female" | "everyone",
  "discovery_radius_km": 50,
  "age_min": 18,
  "age_max": 45
}
```

| **Response 200** | Updated [UserModel JSON](#41-usermodel) |

#### `PUT /api/v1/users/me/location`

Update the authenticated user's geolocation.

|                  | Details                                        |
| ---------------- | ---------------------------------------------- |
| **Auth**         | ✅ Bearer Token                                |
| **Request Body** | `{ "latitude": 1.2345, "longitude": 36.7890 }` |
| **Response 200** | Success acknowledgment                         |

#### `POST /api/v1/users/me/photos`

Upload a profile photo. Uses **multipart/form-data**.

|                  | Details                                                                                                   |
| ---------------- | --------------------------------------------------------------------------------------------------------- |
| **Auth**         | ✅ Bearer Token                                                                                           |
| **Content-Type** | `multipart/form-data`                                                                                     |
| **Form Field**   | `photo` — the image file                                                                                  |
| **Response 200** | `{ "id": "string (UUID)", "url": "string", "position": 0, "is_primary": false, "created_at": "ISO8601" }` |

#### `DELETE /api/v1/users/me/photos/{photo_id}`

Delete a profile photo.

|                  | Details                |
| ---------------- | ---------------------- |
| **Auth**         | ✅ Bearer Token        |
| **Path Param**   | `photo_id` — UUID      |
| **Response 200** | Success acknowledgment |

#### `GET /api/v1/users/{user_id}`

View another user's public profile.

|                  | Details                                              |
| ---------------- | ---------------------------------------------------- |
| **Auth**         | ✅ Bearer Token                                      |
| **Path Param**   | `user_id` — UUID                                     |
| **Response 200** | [UserModel JSON](#41-usermodel) (public fields only) |

---

### 2.3 Discovery

#### `GET /api/v1/discover`

Fetch paginated discovery profiles ranked by the backend.

|                  | Details                                               |
| ---------------- | ----------------------------------------------------- |
| **Auth**         | ✅ Bearer Token                                       |
| **Query Params** | `page` (int, default 1), `per_page` (int, default 20) |
| **Response 200** |                                                       |

```json
{
  "profiles": [
    {
      "id": "string (UUID)",
      "display_name": "string",
      "bio": "string | null",
      "age": 25,
      "gender": "male" | "female" | "non-binary" | null,
      "photo_url": "string | null",
      "is_verified": false,
      "ranking_score": 0.85
    }
  ],
  "page": 1,
  "pages": 5,
  "total": 100
}
```

**Backend must:**

- Exclude the current user
- Exclude users already swiped on
- Exclude blocked users (both directions)
- Filter by the current user's `looking_for`, `age_min`, `age_max`, `discovery_radius_km`
- Return `ranking_score` (optional, for internal ranking)

---

### 2.4 Swipes

#### `POST /api/v1/swipes`

Record a swipe action.

|                  | Details         |
| ---------------- | --------------- |
| **Auth**         | ✅ Bearer Token |
| **Request Body** |                 |

```json
{
  "target_user_id": "string (UUID)",
  "direction": "like" | "dislike" | "super_like"
}
```

| **Response 200** | |

```json
{
  "swipe_id": "string (UUID)",
  "is_match": true,
  "duplicate": false
}
```

**Backend must:**

- Create a Swipe record (swiper_id from JWT, target_user_id, direction)
- Check if the target user has already swiped `like`/`super_like` on the current user
- If mutual → create a Match and return `is_match: true`
- If duplicate swipe → return `duplicate: true`

---

### 2.5 Matches

#### `GET /api/v1/matches`

List the authenticated user's matches (paginated).

|                  | Details                                               |
| ---------------- | ----------------------------------------------------- |
| **Auth**         | ✅ Bearer Token                                       |
| **Query Params** | `page` (int, default 1), `per_page` (int, default 20) |
| **Response 200** |                                                       |

```json
{
  "matches": [
    {
      "match_id": "string (UUID)",
      "matched_at": "ISO8601",
      "is_active": true,
      "other_user": {
        "id": "string (UUID)",
        "display_name": "string",
        "photo_url": "string | null"
      }
    }
  ],
  "page": 1,
  "pages": 3,
  "total": 42
}
```

#### `GET /api/v1/matches/{match_id}`

Get details of a specific match.

|                  | Details                                  |
| ---------------- | ---------------------------------------- |
| **Auth**         | ✅ Bearer Token                          |
| **Path Param**   | `match_id` — UUID                        |
| **Response 200** | Single [MatchModel JSON](#44-matchmodel) |

#### `POST /api/v1/matches/{match_id}/unmatch`

Unmatch (deactivate a match).

|                  | Details                |
| ---------------- | ---------------------- |
| **Auth**         | ✅ Bearer Token        |
| **Path Param**   | `match_id` — UUID      |
| **Request Body** | None                   |
| **Response 200** | Success acknowledgment |

---

### 2.6 Chat (REST)

> Real-time messaging uses **Socket.IO** (see section 5).
> These REST endpoints are for loading history and read receipts.

#### `GET /api/v1/matches/{match_id}/chat`

Load chat message history (newest first, paginated).

|                  | Details                                               |
| ---------------- | ----------------------------------------------------- |
| **Auth**         | ✅ Bearer Token                                       |
| **Path Param**   | `match_id` — UUID                                     |
| **Query Params** | `page` (int, default 1), `per_page` (int, default 50) |
| **Response 200** |                                                       |

```json
{
  "messages": [
    {
      "id": "string (UUID)",
      "sender_id": "string (UUID)",
      "body": "string",
      "message_type": "text" | "image" | "gif",
      "is_read": false,
      "created_at": "ISO8601",
      "match_id": "string (UUID)"
    }
  ],
  "page": 1,
  "pages": 10,
  "total": 500
}
```

#### `POST /api/v1/matches/{match_id}/chat`

Send a message via REST (fallback — prefer Socket.IO).

|                  | Details                                        |
| ---------------- | ---------------------------------------------- |
| **Auth**         | ✅ Bearer Token                                |
| **Path Param**   | `match_id` — UUID                              |
| **Request Body** | `{ "body": "Hello!", "message_type": "text" }` |
| **Response 200** | Single [MessageModel JSON](#45-messagemodel)   |

#### `POST /api/v1/matches/{match_id}/chat/read`

Mark all messages in a match conversation as read.

|                  | Details                |
| ---------------- | ---------------------- |
| **Auth**         | ✅ Bearer Token        |
| **Path Param**   | `match_id` — UUID      |
| **Request Body** | None                   |
| **Response 200** | Success acknowledgment |

---

### 2.7 Safety (Blocks)

#### `POST /api/v1/blocks`

Block a user.

|                  | Details                                                 |
| ---------------- | ------------------------------------------------------- | ------------ |
| **Auth**         | ✅ Bearer Token                                         |
| **Request Body** | `{ "target_user_id": "string (UUID)", "reason": "string | optional" }` |
| **Response 200** | Block confirmation object                               |

#### `GET /api/v1/blocks`

List blocked users (paginated).

|                  | Details                                               |
| ---------------- | ----------------------------------------------------- |
| **Auth**         | ✅ Bearer Token                                       |
| **Query Params** | `page` (int, default 1), `per_page` (int, default 20) |
| **Response 200** | Paginated list of blocked users                       |

#### `DELETE /api/v1/blocks/{target_user_id}`

Unblock a user.

|                  | Details                 |
| ---------------- | ----------------------- |
| **Auth**         | ✅ Bearer Token         |
| **Path Param**   | `target_user_id` — UUID |
| **Response 200** | Success acknowledgment  |

---

### 2.8 Health

#### `GET /health`

Basic health check.

|                  | Details              |
| ---------------- | -------------------- |
| **Auth**         | ❌ Public            |
| **Response 200** | `{ "status": "ok" }` |

#### `GET /health/ready`

Readiness check (DB, Redis, etc.).

|                  | Details                 |
| ---------------- | ----------------------- |
| **Auth**         | ❌ Public               |
| **Response 200** | `{ "status": "ready" }` |

---

## 3. Endpoint Contract Table

| Endpoint                               | Method | Request Body                    | Response Key Fields                                 | Auth |
| -------------------------------------- | ------ | ------------------------------- | --------------------------------------------------- | ---- |
| `/api/v1/auth/verify`                  | POST   | `{ id_token }`                  | `access_token, refresh_token, user_id, is_new_user` | ❌   |
| `/api/v1/auth/refresh`                 | POST   | `{ refresh_token }`             | `access_token`                                      | ❌   |
| `/api/v1/users/me`                     | GET    | —                               | Full UserModel                                      | ✅   |
| `/api/v1/users/me`                     | PUT    | Partial user fields             | Updated UserModel                                   | ✅   |
| `/api/v1/users/me/location`            | PUT    | `{ latitude, longitude }`       | —                                                   | ✅   |
| `/api/v1/users/me/photos`              | POST   | `multipart: photo`              | `{ id, url, position, is_primary, created_at }`     | ✅   |
| `/api/v1/users/me/photos/{photo_id}`   | DELETE | —                               | —                                                   | ✅   |
| `/api/v1/users/{user_id}`              | GET    | —                               | UserModel (public)                                  | ✅   |
| `/api/v1/discover`                     | GET    | Query: `page, per_page`         | `{ profiles[], page, pages, total }`                | ✅   |
| `/api/v1/swipes`                       | POST   | `{ target_user_id, direction }` | `{ swipe_id, is_match, duplicate }`                 | ✅   |
| `/api/v1/matches`                      | GET    | Query: `page, per_page`         | `{ matches[], page, pages, total }`                 | ✅   |
| `/api/v1/matches/{match_id}`           | GET    | —                               | MatchModel                                          | ✅   |
| `/api/v1/matches/{match_id}/unmatch`   | POST   | —                               | —                                                   | ✅   |
| `/api/v1/matches/{match_id}/chat`      | GET    | Query: `page, per_page`         | `{ messages[], page, pages, total }`                | ✅   |
| `/api/v1/matches/{match_id}/chat`      | POST   | `{ body, message_type }`        | MessageModel                                        | ✅   |
| `/api/v1/matches/{match_id}/chat/read` | POST   | —                               | —                                                   | ✅   |
| `/api/v1/blocks`                       | POST   | `{ target_user_id, reason? }`   | Block object                                        | ✅   |
| `/api/v1/blocks`                       | GET    | Query: `page, per_page`         | Paginated blocked list                              | ✅   |
| `/api/v1/blocks/{target_user_id}`      | DELETE | —                               | —                                                   | ✅   |
| `/health`                              | GET    | —                               | `{ status }`                                        | ❌   |
| `/health/ready`                        | GET    | —                               | `{ status }`                                        | ❌   |

---

## 4. Data Models

### 4.1 UserModel

> Corresponds to backend `UserSchema` / SQLAlchemy model.

| Field             | JSON Key              | Type              | Nullable | Notes                                      |
| ----------------- | --------------------- | ----------------- | -------- | ------------------------------------------ |
| id                | `id`                  | String (UUID)     | ❌       | Primary key                                |
| displayName       | `display_name`        | String            | ❌       |                                            |
| email             | `email`               | String            | ✅       | From Firebase                              |
| phone             | `phone`               | String            | ✅       | From Firebase                              |
| bio               | `bio`                 | String            | ✅       | Max ~500 chars                             |
| dateOfBirth       | `date_of_birth`       | String            | ✅       | Format: `"YYYY-MM-DD"`                     |
| gender            | `gender`              | String            | ✅       | Enum: `"male"`, `"female"`, `"non-binary"` |
| lookingFor        | `looking_for`         | String            | ✅       | Enum: `"male"`, `"female"`, `"everyone"`   |
| discoveryRadiusKm | `discovery_radius_km` | int               | ✅       | Default discovery range                    |
| ageMin            | `age_min`             | int               | ✅       | Min age filter                             |
| ageMax            | `age_max`             | int               | ✅       | Max age filter                             |
| isActive          | `is_active`           | bool              | ❌       | Default: true                              |
| isVerified        | `is_verified`         | bool              | ❌       | Default: false                             |
| createdAt         | `created_at`          | String (ISO8601)  | ✅       |                                            |
| updatedAt         | `updated_at`          | String (ISO8601)  | ✅       |                                            |
| lastActiveAt      | `last_active_at`      | String (ISO8601)  | ✅       |                                            |
| photos            | `photos`              | List\<UserPhoto\> | ❌       | Default: []                                |

### 4.2 UserPhoto

| Field     | JSON Key     | Type             | Nullable | Notes                |
| --------- | ------------ | ---------------- | -------- | -------------------- |
| id        | `id`         | String (UUID)    | ❌       | Primary key          |
| url       | `url`        | String           | ❌       | Full URL to photo    |
| position  | `position`   | int              | ❌       | Sort order (0-based) |
| isPrimary | `is_primary` | bool             | ❌       | Default: false       |
| createdAt | `created_at` | String (ISO8601) | ✅       |                      |

### 4.3 DiscoveryProfile

> Lightweight user card returned in discovery feed.

| Field        | JSON Key        | Type          | Nullable | Notes                       |
| ------------ | --------------- | ------------- | -------- | --------------------------- |
| id           | `id`            | String (UUID) | ❌       | User ID                     |
| displayName  | `display_name`  | String        | ❌       |                             |
| bio          | `bio`           | String        | ✅       |                             |
| age          | `age`           | int           | ✅       | Computed from date_of_birth |
| gender       | `gender`        | String        | ✅       |                             |
| photoUrl     | `photo_url`     | String        | ✅       | Primary photo URL           |
| isVerified   | `is_verified`   | bool          | ❌       | Default: false              |
| rankingScore | `ranking_score` | double        | ✅       | Backend internal score      |

### 4.4 MatchModel

| Field     | JSON Key     | Type             | Nullable | Notes                              |
| --------- | ------------ | ---------------- | -------- | ---------------------------------- |
| matchId   | `match_id`   | String (UUID)    | ❌       | Primary key                        |
| matchedAt | `matched_at` | String (ISO8601) | ❌       |                                    |
| isActive  | `is_active`  | bool             | ❌       | Default: true, false after unmatch |
| otherUser | `other_user` | MatchUserSummary | ❌       | The other participant              |

### 4.5 MatchUserSummary

> Embedded in MatchModel — summary of the other user.

| Field       | JSON Key       | Type          | Nullable | Notes             |
| ----------- | -------------- | ------------- | -------- | ----------------- |
| id          | `id`           | String (UUID) | ❌       | User ID           |
| displayName | `display_name` | String        | ❌       |                   |
| photoUrl    | `photo_url`    | String        | ✅       | Primary photo URL |

### 4.6 MessageModel

| Field       | JSON Key       | Type             | Nullable | Notes                              |
| ----------- | -------------- | ---------------- | -------- | ---------------------------------- |
| id          | `id`           | String (UUID)    | ❌       | Primary key                        |
| senderId    | `sender_id`    | String (UUID)    | ❌       | The user who sent it               |
| body        | `body`         | String           | ❌       | Message content                    |
| messageType | `message_type` | String           | ❌       | Enum: `"text"`, `"image"`, `"gif"` |
| isRead      | `is_read`      | bool             | ❌       | Default: false                     |
| createdAt   | `created_at`   | String (ISO8601) | ❌       |                                    |
| matchId     | `match_id`     | String (UUID)    | ✅       | Present in Socket.IO events        |

### 4.7 SwipeResponse

| Field     | JSON Key    | Type          | Nullable | Notes                          |
| --------- | ----------- | ------------- | -------- | ------------------------------ |
| swipeId   | `swipe_id`  | String (UUID) | ❌       | Created swipe ID               |
| isMatch   | `is_match`  | bool          | ❌       | Did this swipe create a match? |
| duplicate | `duplicate` | bool          | ❌       | Was this a repeated swipe?     |

### 4.8 AuthResponse

| Field        | JSON Key        | Type          | Nullable | Notes                |
| ------------ | --------------- | ------------- | -------- | -------------------- |
| accessToken  | `access_token`  | String        | ❌       | JWT access token     |
| refreshToken | `refresh_token` | String        | ❌       | JWT refresh token    |
| userId       | `user_id`       | String (UUID) | ❌       | Backend user ID      |
| isNewUser    | `is_new_user`   | bool          | ❌       | true if just created |

### 4.9 PlayerCardModel

> User's sports player card (not yet wired to backend API — local/future).

| Field         | JSON Key         | Type                   | Nullable | Notes                |
| ------------- | ---------------- | ---------------------- | -------- | -------------------- |
| id            | `id`             | String (UUID)          | ❌       |                      |
| userId        | `user_id`        | String (UUID)          | ❌       |                      |
| displayName   | `display_name`   | String                 | ✅       |                      |
| position      | `position`       | String                 | ✅       | e.g. "Forward"       |
| sport         | `sport`          | String                 | ✅       | Sport name           |
| team          | `team`           | String                 | ✅       | Team name            |
| jerseyNumber  | `jersey_number`  | String                 | ✅       |                      |
| avatarUrl     | `avatar_url`     | String                 | ✅       |                      |
| backgroundUrl | `background_url` | String                 | ✅       | Card background      |
| stats         | `stats`          | Map\<String, dynamic\> | ✅       | Sport-specific stats |
| createdAt     | `created_at`     | String (ISO8601)       | ❌       |                      |
| updatedAt     | `updated_at`     | String (ISO8601)       | ✅       |                      |

### 4.10 PlayerProfile

> Onboarding profile data. Currently stored locally — future backend sync.

| Field                | JSON Key               | Type             | Nullable | Notes          |
| -------------------- | ---------------------- | ---------------- | -------- | -------------- |
| id                   | `id`                   | String           | ✅       |                |
| name                 | `name`                 | String           | ❌       |                |
| location             | `location`             | String           | ✅       |                |
| profileImagePath     | `profileImagePath`     | String           | ✅       | Local path     |
| birthday             | `birthday`             | String (ISO8601) | ✅       |                |
| heightRange          | `heightRange`          | String           | ✅       | e.g. "5' - 6'" |
| competitivenessLevel | `competitivenessLevel` | int              | ✅       | 1-4            |
| playerNumber         | `playerNumber`         | int              | ✅       |                |
| sports               | `sports`               | List\<Sport\>    | ❌       |                |

### 4.11 Sport

| Field | JSON Key | Type   | Nullable | Notes                    |
| ----- | -------- | ------ | -------- | ------------------------ |
| id    | `id`     | String | ❌       | e.g. "football"          |
| name  | `name`   | String | ❌       | e.g. "Football (Soccer)" |
| emoji | `emoji`  | String | ❌       | e.g. "⚽"                |

**Predefined sports:** football, cricket, rugby, hockey, golf, tennis, volleyball, table_tennis, basketball, baseball

### 4.12 EventModel

> Currently stored in SharedPreferences locally — future backend entity.

| Field                | JSON Key               | Type             | Nullable | Notes                                         |
| -------------------- | ---------------------- | ---------------- | -------- | --------------------------------------------- |
| id                   | `id`                   | String           | ❌       |                                               |
| eventType            | `eventType`            | int (enum index) | ❌       | 0=league, 1=tournament, 2=community, 3=pickup |
| eventName            | `eventName`            | String           | ❌       |                                               |
| sport                | `sport`                | String           | ❌       |                                               |
| startDate            | `startDate`            | String (ISO8601) | ❌       |                                               |
| endDate              | `endDate`              | String (ISO8601) | ❌       |                                               |
| startTime            | `startTime`            | String           | ❌       |                                               |
| endTime              | `endTime`              | String           | ❌       |                                               |
| location             | `location`             | String           | ❌       |                                               |
| description          | `description`          | String           | ❌       |                                               |
| imagePaths           | `imagePaths`           | List\<String\>   | ❌       |                                               |
| skillLevel           | `skillLevel`           | String           | ✅       |                                               |
| ageGroup             | `ageGroup`             | String           | ✅       |                                               |
| gender               | `gender`               | String           | ✅       |                                               |
| registrationDeadline | `registrationDeadline` | String (ISO8601) | ✅       |                                               |
| maxTeams             | `maxTeams`             | int              | ✅       |                                               |
| maxPlayers           | `maxPlayers`           | int              | ✅       |                                               |
| numberOfTeams        | `numberOfTeams`        | int              | ✅       |                                               |
| seasonLengthWeeks    | `seasonLengthWeeks`    | int              | ✅       |                                               |
| matchFrequency       | `matchFrequency`       | String           | ✅       |                                               |
| scheduleCreation     | `scheduleCreation`     | String           | ✅       |                                               |
| bracketType          | `bracketType`          | String           | ✅       |                                               |
| seedingMethod        | `seedingMethod`        | String           | ✅       |                                               |
| isPaid               | `isPaid`               | bool             | ❌       | Default: false                                |
| entryFee             | `entryFee`             | double           | ✅       |                                               |
| useRallyPay          | `useRallyPay`          | bool             | ❌       | Default: false                                |
| createdAt            | `createdAt`            | String (ISO8601) | ❌       |                                               |
| creatorName          | `creatorName`          | String           | ❌       |                                               |
| creatorAvatarPath    | `creatorAvatarPath`    | String           | ✅       |                                               |

### 4.13 FeedPost

> Currently stored locally — future backend entity.

| Field             | JSON Key              | Type             | Nullable | Notes |
| ----------------- | --------------------- | ---------------- | -------- | ----- |
| id                | `id`                  | String           | ❌       |       |
| content           | `content`             | String           | ❌       |       |
| imagePaths        | `image_paths`         | List\<String\>   | ❌       |       |
| createdAt         | `created_at`          | String (ISO8601) | ❌       |       |
| creatorName       | `creator_name`        | String           | ❌       |       |
| creatorAvatarPath | `creator_avatar_path` | String           | ✅       |       |

### 4.14 PostModel

> Alternative post model (used alongside FeedPost).

| Field         | JSON Key         | Type             | Nullable | Notes                                    |
| ------------- | ---------------- | ---------------- | -------- | ---------------------------------------- |
| id            | `id`             | String           | ❌       |                                          |
| userId        | `user_id`        | String           | ❌       |                                          |
| content       | `content`        | String           | ✅       |                                          |
| imageUrl      | `image_url`      | String           | ✅       |                                          |
| likesCount    | `likes_count`    | int              | ❌       | Default: 0                               |
| commentsCount | `comments_count` | int              | ❌       | Default: 0                               |
| createdAt     | `created_at`     | String (ISO8601) | ❌       |                                          |
| updatedAt     | `updated_at`     | String (ISO8601) | ✅       |                                          |
| author        | `profiles`       | UserModel        | ✅       | Nested author object (key is `profiles`) |

---

## 5. Socket.IO Events

> Transport: **WebSocket** (not polling)
> Protocol: **Socket.IO v4** (Flask-SocketIO compatible)
> Auth: `{ auth: { token: "<JWT access_token>" } }` passed at connection time

### 5.1 Connection Events (Built-in + Custom)

| Event           | Direction     | Payload                         | Description                               |
| --------------- | ------------- | ------------------------------- | ----------------------------------------- |
| `connect`       | Client→Server | (automatic)                     | Socket.IO handshake, JWT in auth dict     |
| `connected`     | Server→Client | `{ ... }` (server confirmation) | Server acknowledges successful connection |
| `disconnect`    | Bidirectional | —                               | Disconnect event                          |
| `connect_error` | Server→Client | `error`                         | Connection failure                        |
| `reconnect`     | Client-side   | —                               | Auto-reconnection                         |

### 5.2 Chat Room Events

#### Client → Server (Emits)

| Event              | Payload                                                                                | Description               |
| ------------------ | -------------------------------------------------------------------------------------- | ------------------------- |
| `join_match_room`  | `{ "match_id": "UUID" }`                                                               | Join a match's chat room  |
| `leave_match_room` | `{ "match_id": "UUID" }`                                                               | Leave a match's chat room |
| `send_message`     | `{ "match_id": "UUID", "body": "string", "message_type": "text" \| "image" \| "gif" }` | Send a real-time message  |
| `typing_indicator` | `{ "match_id": "UUID", "is_typing": true/false }`                                      | Notify typing status      |
| `read_receipt`     | `{ "match_id": "UUID" }`                                                               | Mark messages as read     |

#### Server → Client (Listens)

| Event              | Payload                                                                                                                      | Description                  |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------- | ---------------------------- |
| `new_message`      | [MessageModel JSON](#46-messagemodel) — `{ "id", "sender_id", "body", "message_type", "is_read", "created_at", "match_id" }` | New incoming message         |
| `typing_indicator` | `{ "match_id": "UUID", "user_id": "UUID", "is_typing": true/false }`                                                         | Other user typing status     |
| `messages_read`    | `{ "match_id": "UUID", "read_by": "UUID" }`                                                                                  | Read receipt from other user |
| `room_joined`      | `{ ... }`                                                                                                                    | Confirmation of room join    |
| `user_joined`      | `{ ... }`                                                                                                                    | Another user joined the room |
| `user_left`        | `{ ... }`                                                                                                                    | Another user left the room   |
| `error`            | `{ ... }`                                                                                                                    | Server-side error            |

---

## 6. Backend Entities (Database Tables)

Based on the frontend analysis, the backend **must** have these entities:

### Core Entities

| Entity        | Table Name (suggested) | Description                           |
| ------------- | ---------------------- | ------------------------------------- |
| **User**      | `users`                | User account — linked to Firebase UID |
| **UserPhoto** | `user_photos`          | Profile photos (1:N with User)        |
| **Swipe**     | `swipes`               | Like/Dislike/SuperLike actions        |
| **Match**     | `matches`              | Mutual likes between two users        |
| **Message**   | `messages`             | Chat messages within a match          |
| **Block**     | `blocks`               | User blocking another user            |

### Future/Local Entities (currently SharedPreferences, likely need backend tables)

| Entity            | Table Name (suggested) | Description                  |
| ----------------- | ---------------------- | ---------------------------- |
| **Sport**         | `sports`               | Predefined sports catalog    |
| **PlayerProfile** | `player_profiles`      | Sports profile/card per user |
| **PlayerCard**    | `player_cards`         | Sports card with stats       |
| **Event**         | `events`               | Community/sports events      |
| **FeedPost**      | `feed_posts`           | Social feed posts            |
| **Subscription**  | `subscriptions`        | Premium subscription records |

### Onboarding Data (currently local, should sync to User profile)

| Data            | Where to Store                   | Fields                                                                                            |
| --------------- | -------------------------------- | ------------------------------------------------------------------------------------------------- |
| Selected Sports | `user_sports` junction table     | user_id, sport_id                                                                                 |
| About Me        | `users` table or `user_profiles` | relationship_goal, interests, personality_traits, zodiac_sign, communication_style, love_language |
| Photos          | `user_photos` table              | Already exists                                                                                    |
| Location        | `users` table                    | latitude, longitude (already in API)                                                              |

---

## 7. Pagination Convention

All paginated endpoints use a consistent format:

**Request Query Parameters:**

```
?page=1&per_page=20
```

**Response Envelope:**

```json
{
  "<collection_key>": [ ... ],
  "page": 1,
  "pages": 5,
  "total": 100
}
```

Collection keys by endpoint:

- Discovery: `"profiles"`
- Matches: `"matches"`
- Chat: `"messages"`

---

## 8. Error Response Convention

The Flutter app parses errors from `DioException.response.data`:

```json
{
  "error": "Human-readable error message",
  "message": "Alternative message field"
}
```

The app checks `data['error']` first, then falls back to `data['message']`.

### Standard HTTP Status Codes Expected

| Status | Meaning      | Flutter Handling               |
| ------ | ------------ | ------------------------------ |
| 200    | Success      | Parse response body            |
| 400    | Bad Request  | Show error message             |
| 401    | Unauthorized | Auto-refresh token, retry once |
| 403    | Forbidden    | Show "Access denied"           |
| 404    | Not Found    | Show "Resource not found"      |
| 408    | Timeout      | Show timeout message           |
| 500    | Server Error | Show generic error             |

---

## 9. Additional Backend Requirements

### 9.1 JWT Configuration

- **Access token**: Short-lived (e.g. 15 minutes)
- **Refresh token**: Long-lived (e.g. 30 days)
- The client stores both in `flutter_secure_storage`
- Refresh flow: `POST /api/v1/auth/refresh` with `{ refresh_token }`

### 9.2 Firebase Admin SDK

- The backend must verify Firebase ID tokens using Firebase Admin SDK
- Extract user info (email, phone, display_name) from the Firebase token
- Create or retrieve the user in the local database

### 9.3 File Storage

- Photo uploads via `POST /api/v1/users/me/photos` use multipart form data
- The backend must store files (S3, GCS, or local) and return a full URL
- Field name for the file: `photo`

### 9.4 Socket.IO Server

- Must use **Flask-SocketIO** (or compatible Socket.IO server)
- JWT authentication at connection time via `auth.token`
- Rooms are per-match (match_id as room name)
- Messages sent via socket should also be persisted to the database

### 9.5 Paystack Integration

- The app uses **Paystack** for payments (KES currency)
- Uses `flutter_paystack_plus` package
- Calls Paystack API directly from the client for plan listing
- Backend should have a webhook or verification endpoint for payment confirmation
- Premium packages: daily (KES 99), weekly (KES 299), monthly (KES 899)

### 9.6 Geolocation

- Location stored as `latitude`/`longitude` floats
- Discovery filtering by `discovery_radius_km` requires geospatial queries
- Consider PostGIS or Haversine formula

---

## 10. Quick-Start Checklist for Backend

- [ ] Set up Flask + Flask-SocketIO + SQLAlchemy
- [ ] Integrate Firebase Admin SDK for token verification
- [ ] Implement JWT (access + refresh) issuance
- [ ] Create database tables: `users`, `user_photos`, `swipes`, `matches`, `messages`, `blocks`
- [ ] Implement auth routes: `/auth/verify`, `/auth/refresh`
- [ ] Implement user routes: `GET/PUT /users/me`, photo upload/delete, location update
- [ ] Implement discovery with geospatial filtering and ranking
- [ ] Implement swipe logic with automatic match detection
- [ ] Implement match listing and unmatch
- [ ] Implement chat history REST endpoints
- [ ] Implement Socket.IO events for real-time chat
- [ ] Implement block/unblock functionality
- [ ] Implement health check endpoints
- [ ] Set up file storage for photos (S3/GCS)
- [ ] Add Paystack webhook for payment verification
- [ ] Add CORS configuration for the API
- [ ] Set up pagination helpers (page, pages, total pattern)
