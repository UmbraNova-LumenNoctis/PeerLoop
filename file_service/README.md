# File Service

## Role
Media upload service. Validates incoming files, uploads them to ImageKit, and stores metadata in `media_files`.

## Responsibilities
- Validate extension, detected MIME type, and size limits.
- Upload files to ImageKit and store metadata in Supabase.
- Resolve preview URLs for image assets.
- Emit internal notifications for new uploads.

## Endpoints
- `GET /health`, `GET /metrics`
- `POST /upload`

## Upload pipeline (algorithm)
1. Authenticate the request via `x-access-token` or trusted gateway headers.
2. Validate filename and declared content type against the allowlist.
3. Stream the upload to a temp file in 1MB chunks and enforce size limits.
4. Detect MIME type with `python-magic` and validate against the allowlist.
5. Upload to ImageKit with tags and a unique filename.
6. Insert a `media_files` row with URL, ImageKit file id, detected type, and size.
7. Emit an internal `file_created` notification.
8. On failure, delete the uploaded ImageKit file and clean up temp files.

## Dependencies
- ImageKit for remote storage
- Supabase table `media_files`
- Notification service for internal events
- Vault for secrets
- `python-magic` for MIME detection

## Runtime config
- `IMAGEKIT_PRIVATE_KEY`, `IMAGEKIT_PUBLIC_KEY`, `IMAGEKIT_URL`
- `SUPABASE_URL`, `SUPABASE_KEY`
- `NOTIFICATION_SERVICE_URL`, `INTERNAL_SERVICE_TOKEN`
- `INTERNAL_TLS_VERIFY`
- `MAX_FILE_SIZE_MB`

## Implementation notes
- Auth falls back to gateway headers when token introspection fails.
- The service computes and returns a `preview_url` for image files.
