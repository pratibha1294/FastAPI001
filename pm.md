# FastAPI001 — Functional Requirements Doc

## Purpose

You already have auth (register/login/update-password) built on raw SQL (`repo.py`), a thin service layer (`service.py`), and JWT (`jwt.py`). This doc extends the project into a **simple Dropbox clone** — the vehicle for practicing backend fundamentals without an ORM.

**Non-goals:** No SQLAlchemy models, no ORM query builder. `sqlalchemy` stays as a raw connection/engine tool at most; all queries are hand-written SQL via `pymysql`, same style as `repo.py` today.

## Why a spiral, not a waterfall

A normal feature list would have you build "File Upload" once and move on. Instead, this doc is organized in **cycles**. Every cycle revisits the *same* four modules — DB/Repo, File Container, Service Layer, ACL/Middleware — and pushes each one slightly harder than the last cycle did. You'll touch `repo.py` in cycle 1 with a single-table INSERT, and touch it again in cycle 4 with multi-table joins and transactions. This mirrors how real backend work actually happens: you don't "finish" the data layer, you keep coming back to it under new pressure.

Each cycle ends with something runnable and demoable. Don't start cycle N+1 until cycle N's demo works end-to-end.

## The four modules, tracked across every cycle

| Module | File(s) | What it means here |
|---|---|---|
| **DB/Repo** | `repo.py`, `alembic/versions/` | Raw SQL, schema design, migrations |
| **File Container** | new `storage.py` (or `filestore.py`) | Real S3-compatible object storage via [Garage](https://garagehq.deuxfleurs.fr/), talked to with `boto3` |
| **Service Layer** | `service.py` | Orchestration — calls repo + storage + ACL, no SQL of its own |
| **ACL/Middleware** | new `acl.py`, FastAPI dependencies in `app.py` | Who can do what to which resource |

---

## Cycle 1 — Foundation: a file has an owner

**Goal:** A logged-in user can upload a file and list/download only their own files. No sharing yet.

### DB/Repo
- New table `files`: `id, owner_id, filename, storage_key, size_bytes, content_type, created_at`.
- Alembic migration, raw SQL, following the existing `create_users_table` pattern.
- `repo.py` additions: `create_file_record(owner_id, filename, storage_key, size, content_type)`, `get_file(file_id)`, `list_files_for_user(owner_id)`.

### File Container
- Run [Garage](https://garagehq.deuxfleurs.fr/) locally (Docker is easiest for dev) as your object store — this is a real S3-compatible server, not a fake one, so everything you learn here (`boto3`, bucket/key model, presigned URLs in cycle 4) transfers directly to AWS S3 later.
  - `docker run -d -p 3900:3900 -p 3901:3901 -p 3902:3902 -p 3903:3903 dxflrs/garage:v2.3.0 /garage server --single-node --default-bucket`
  - One-time setup via the `garage` CLI: `garage bucket create dropbox-clone`, `garage key create app-key`, `garage bucket allow --read --write --owner dropbox-clone --key app-key`.
- Introduce `storage.py` wrapping a `boto3` S3 client, with a small interface even though it's a single-node local Garage instance for now:
  - `save(key: str, content: bytes) -> None` → `s3.put_object(Bucket=..., Key=key, Body=content)`
  - `read(key: str) -> bytes` → `s3.get_object(...)["Body"].read()`
  - `delete(key: str) -> None` → `s3.delete_object(...)`
  - Client config: `endpoint_url` pointing at your Garage instance (e.g. `http://localhost:3900`), `region_name="garage"`, access/secret key from `garage key create`, path-style addressing.
  - The `storage_key` in the DB is a UUID object key, **never** the original filename (this is the first ACL lesson: never trust or expose storage keys/paths directly — same reasoning applies whether the backing store is a filesystem or a bucket).
  - Keep credentials and endpoint in env vars / settings, not hardcoded — this is also how you'd point the same code at real AWS S3 later with zero code changes, just config.

### Service Layer
- `service.upload_file(user_id, filename, content)`: generates storage key, calls `storage.save`, calls `repo.create_file_record`. One function, three collaborators — your first taste of a "big service function."
- `service.download_file(user_id, file_id)`: fetch record, **check owner_id == user_id**, read from storage, return bytes.

### ACL/Middleware
- Introduce a real auth dependency in `app.py`: a `get_current_user` dependency that decodes the JWT (you already have `jwt.py`) and injects `user_id` into route handlers, replacing the pattern of passing `userId` in the request body (note: `UpdatePasswordReqDTO.userId` today trusts the client — fix this here).
- Ownership check lives in the service layer for now (`if file.owner_id != user_id: raise PermissionError`).

### Endpoints
- `POST /files` (multipart upload)
- `GET /files` (list own files)
- `GET /files/{id}` (download, owner-only)

### Side effects you'll get
- First real feel for "service function calling multiple repos/collaborators."
- First deliberate object-storage design decision (opaque keys vs. real filenames).

---

## Cycle 2 — Sharing: links between users

**Goal:** Owner can generate a link that lets another specific user (or "anyone with the link") access a file. This is where ACL becomes real.

### DB/Repo
- New table `file_shares`: `id, file_id, shared_by, shared_with (nullable), share_token (unique), permission (read), expires_at (nullable), created_at`.
- `shared_with` nullable = "anyone with the token"; non-null = targeted share.
- `repo.py`: `create_share(file_id, shared_by, shared_with, token, expires_at)`, `get_share_by_token(token)`, `list_shares_for_file(file_id)`, `revoke_share(share_id)`.
- Practice: composite `WHERE` with expiry check (`expires_at IS NULL OR expires_at > NOW()`).

### File Container
- No new capability yet — but now two access *paths* exist (owner path, share-token path) hitting the same `storage.read`. Forces you to centralize the read behind one service function instead of duplicating storage-client access.

### Service Layer
- `service.create_share_link(user_id, file_id, target_email=None, ttl_hours=None)`: verify caller owns the file, generate a signed/random token, write share row, return shareable URL.
- `service.resolve_share(token, requesting_user_id=None)`: look up share, check expiry, check `shared_with` matches if targeted, then delegate to the same download path as cycle 1.
- This is your second "big service function" — now with branching logic (owned vs targeted vs public-link, expired vs valid).

### ACL/Middleware
- First explicit **ACL check function**, `acl.can_access_file(user_id_or_none, file, share=None)`, extracted out of the service function so cycle 3+ can reuse it instead of re-deriving it inline.
- Middleware idea to introduce here: request logging middleware that logs `user_id + resource_id` for every file access — your first audit trail, and a standard "backend hygiene" practice.

### Endpoints
- `POST /files/{id}/share` (create link)
- `GET /files/{id}/shares` (owner views active shares)
- `DELETE /shares/{id}` (revoke)
- `GET /share/{token}` (public/targeted access via link)

### Side effects you'll get
- Real ACL modeling (owner vs shared-with vs public-link).
- First non-trivial SQL WHERE clauses (nullable joins, expiry).
- First middleware.

---

## Cycle 3 — Structure: folders, search, and quotas

**Goal:** Files live in folders (nested), users can search their own + shared files, and storage usage is capped per user.

### DB/Repo
- New table `folders`: `id, owner_id, parent_id (nullable, self-referencing), name, created_at`.
- `files.folder_id` FK added (migration, `ALTER TABLE`).
- Queries to practice deliberately:
  - Recursive-ish folder path resolution (either a recursive CTE if your MySQL version supports it, or iterative parent-walk in Python — pick the CTE for the SQL practice).
  - `list_files_in_folder(folder_id, user_id)` joined against `file_shares` so shared files also surface — this is your first real multi-table `JOIN` with `UNION` (owned files UNION shared files).
  - `sum_storage_used(user_id)` — `SUM(size_bytes)` aggregate query for quota checks.

### File Container
- Track size purely via DB sum, not via bucket listing (recommended — keeps the bucket dumb, matches how S3-backed systems actually work: the bucket doesn't know your quotas, your app does).

### Service Layer
- `service.upload_file` (revisited) now: resolves target folder, checks quota via `repo.sum_storage_used` **before** writing to Garage (order matters — never write the object before you know it's allowed), then proceeds as cycle 1.
- `service.move_file(user_id, file_id, new_folder_id)`, `service.create_folder(user_id, name, parent_id)`.
- `service.search(user_id, query)`: search own filenames + shared-with-me filenames — another UNION-based query, service just orchestrates.

### ACL/Middleware
- Folder ACL inherits from file ACL rules — decide explicitly: does sharing a folder share everything inside it? (Recommend: yes, and store share rows against `folder_id` too, checked recursively.) This is a genuine, non-trivial ACL design decision — write down your answer before coding it.
- Quota-exceeded becomes a proper `403`/`413` with a middleware-level or dependency-level check reusable across upload endpoints.

### Endpoints
- `POST /folders`, `GET /folders/{id}`
- `PATCH /files/{id}/move`
- `GET /search?q=`

### Side effects you'll get
- Recursive/self-referencing SQL, UNIONs, aggregates — the "complex query" ramp-up you asked for.
- Quota logic = first real pre-condition check spanning service+repo.

---

## Cycle 4 — Consistency: transactions, revocation, and signed links

**Goal:** Multi-step operations (delete a folder and everything in it; revoke all shares when a file is deleted) are atomic. Direct file access moves to real signed URLs instead of "hit the API every time."

### DB/Repo
- Wrap multi-statement operations in explicit `connection.begin()/commit()/rollback()` — first deliberate transaction boundary in the project (up to now everything's been single-statement autocommit-style).
- `delete_folder_cascade(folder_id)`: delete nested folders, files, and their shares in one transaction. Practice: does this cascade in SQL (`ON DELETE CASCADE` in the migration) or in application code? Do both once, compare — that comparison *is* the learning.
- `revoke_shares_for_file(file_id)` used on file delete.

### File Container
- Add `storage.generate_signed_url(key, ttl_seconds)` — because Garage is real S3-compatible storage, this is `s3.generate_presigned_url("get_object", Params={"Bucket": ..., "Key": key}, ExpiresIn=ttl_seconds)`. No need to hand-roll HMAC signing: `boto3` and Garage do the exact signature-in-query-param mechanism (SigV4) that real AWS S3 uses, so you're learning the actual protocol instead of a toy version of it.
- Read the generated URL and the [S3 compatibility notes](https://garagehq.deuxfleurs.fr/documentation/reference-manual/s3-compatibility/) closely enough to explain to yourself what `X-Amz-Signature`, `X-Amz-Expires`, and `X-Amz-Credential` are doing — that's the actual learning objective here, not just calling the function.
- Download endpoint changes: instead of streaming the file through your API on every request, `GET /files/{id}/download` now does the ACL check (owner/share) and then returns a presigned Garage URL — the client fetches bytes directly from Garage, not through your API. This is the "give me a link, not a session" pattern real file services use, and it's now literally true: the bytes never touch your FastAPI process.

### Service Layer
- `service.delete_file(user_id, file_id)`: ACL check, revoke shares, delete DB row, delete the object from Garage — all-or-nothing across DB+object-store (accept that the `s3.delete_object` call can't join the DB transaction; decide and document your ordering: DB commit first, then best-effort object cleanup with a retry/log-on-failure path — this is a real distributed-systems tradeoff, not a toy problem).
- `service.delete_folder(user_id, folder_id)`: uses the cascade repo function inside one transaction.
- Biggest "big service function" yet: `service.get_download_link(user_id_or_none, file_id, share_token=None)` unifying owner path, share path, and signed-URL generation — the natural endpoint of the branching logic you started in cycle 2.

### ACL/Middleware
- Central `acl.py` now has 3+ call sites (download, share-create, delete) — refactor duplication out here rather than earlier, so you feel *why* the extraction was worth waiting for.
- Rate-limiting middleware on the public `/share/{token}` and signed-download routes, since those are your only unauthenticated endpoints and the obvious abuse target.

### Endpoints
- `DELETE /folders/{id}` (cascade)
- `DELETE /files/{id}` (revokes shares too)
- `GET /files/{id}/download` → returns a presigned Garage URL (no separate `/blobs/{key}` route needed — Garage itself serves the bytes once the URL is presigned)

### Side effects you'll get
- Transactions, cascades, and an honest DB-vs-object-store consistency tradeoff.
- Real S3 presigned-URL mechanics (SigV4, expiry) — the actual S3 familiarity you wanted, not a simulation of it.
- A justified refactor, not a premature one.

---

## Cycle 5 — Operate it: audit, observability, and hardening

**Goal:** The system behaves like something you'd trust in production for a small team — not new features, but making cycles 1–4 observable and safe.

### DB/Repo
- `access_log` table (promote the cycle-2 log-middleware output from stdout into a real table): `id, user_id (nullable), file_id, action, ip, created_at`.
- Query practice: "who accessed file X in the last 7 days" and "top 10 most-shared files" — GROUP BY / ORDER BY / LIMIT reporting queries, a different SQL muscle than the transactional queries so far.

### File Container
- Orphan-object cleanup script: `s3.list_objects_v2` the Garage bucket, diff the keys against `files.storage_key` in the DB, and reconcile any objects with no matching row (from the best-effort-delete tradeoff in cycle 4). This is the payoff for the honest tradeoff you documented earlier, and it's the same reconciliation job real S3-backed systems run.

### Service Layer
- No new business feature — instead, wrap existing service functions with structured logging/timing, surfacing where a "big service function" is doing too much (candidate for splitting) vs. where it's fine.

### ACL/Middleware
- Global exception-handling middleware in `app.py` (right now `ValueError` is caught ad hoc in one route — generalize it).
- Auth dependency hardening: token expiry handling, consistent 401 vs 403 semantics (401 = not authenticated, 403 = authenticated but not permitted — audit every route against this rule).

### Side effects you'll get
- The "standard practices" ask directly: consistent error semantics, structured logging, a real audit trail, middleware used for cross-cutting concerns instead of sprinkled logic.

---

## Cycle 6 — One feature, event-driven: share notifications via Kafka

**Goal:** Add exactly one new feature — notify a user when someone shares a file with them — and build it event-driven instead of inline, purely so you feel the producer/consumer pattern on a small, contained slice. Everything else in the project (upload, download, quotas, folders) stays exactly as it was in cycles 1–5; this cycle does not refactor them onto Kafka.

### DB/Repo
- One new table: `notifications`: `id, user_id, message, read, created_at`. Written only by the new consumer below, never by a route handler directly.
- Practice: idempotent insert in the consumer (dedupe on a Kafka message key, e.g. `share_id`, via `INSERT ... ON DUPLICATE KEY UPDATE` or a unique constraint) — at-least-once delivery means the consumer will eventually see the same message twice.

### File Container
- No changes. This feature doesn't touch storage at all.

### Service Layer
- Run Kafka locally (Docker is easiest): `docker run -d --name kafka -p 9092:9092 apache/kafka:3.7.0` (KRaft mode, no Zookeeper needed).
- Introduce a small `events.py` wrapping `confluent-kafka` (or `aiokafka`), scoped to just this feature:
  - `publish(topic: str, key: str, value: dict) -> None`
  - `consume(topic: str, group_id: str, handler: Callable) -> None`
- One topic: `share-events`.
- Touch exactly one existing function: `service.create_share_link` (cycle 2) — after the DB commit succeeds, additionally publish `{"type": "share.created", "share_id", "file_id", "shared_by", "shared_with"}`. Nothing else about that function's behavior changes; this is additive, not a rewrite. Publish-after-commit, not before, so you never notify about a share that got rolled back.
- Write one standalone consumer process, `consumers/notifier.py`: subscribes to `share-events`, and on `share.created` where `shared_with` is non-null, inserts a row into `notifications`. Runs as its own process (`python -m consumers.notifier`), not inside the FastAPI app.
- This is the whole point of the cycle: compare this one function (publish a fact, let something else react) against every other service function in the project, which calls its collaborators directly. You don't need to generalize the pattern beyond this to learn it.

### ACL/Middleware
- Consumer-side check: `notifier.py` should not blindly trust the event — before writing a notification, decide whether it needs to re-verify anything, or whether trusting your own producer's payload is acceptable here (it's an internal topic, not user input, so this is a good place to explicitly reason about *when* re-validation is and isn't necessary).
- Failure mode to think through and document: if `notifier.py` is down, `share.created` events queue up in Kafka rather than being lost (it's a log, not a fire-and-forget queue) — so a share still succeeds for the sharer even if notifications are delayed. Confirm this is true by killing the consumer, creating a share, and restarting the consumer to watch it catch up.

### Endpoints
- `GET /notifications` (list a user's notifications), `PATCH /notifications/{id}/read`.
- `POST /files/{id}/share` (cycle 2) is otherwise unchanged from the caller's perspective — same request/response, just an added side effect happening asynchronously behind it.

### Side effects you'll get
- First message-broker integration, kept small: one topic, one producer call, one consumer.
- A direct, felt comparison between synchronous (everything else in the project) and asynchronous (this one path) side effects, without having to rebuild the whole system to get it.

---

## How to use this doc

- Work top to bottom; don't skip a module within a cycle even if it feels thin (e.g. cycle 1's ACL is one `if` statement — that's intentional, it grows on purpose).
- Before starting a cycle, write the migration and table schema first, then repo functions, then service, then routes+ACL last. This ordering itself is a backend habit worth building.
- When a service function in a later cycle starts calling 4+ repo/storage functions, that's not a smell to fix immediately — sit with it until cycle 5's "should this split?" pass, so you learn to recognize the pressure before reflexively refactoring it away.
