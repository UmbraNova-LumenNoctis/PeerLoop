# Frontend

## Role
React and Vite web app. Handles client-side auth, protected pages, and the main social UI through the API gateway.

## Stack
- React 19 + TypeScript
- Vite
- Chakra UI
- React Router

## Main routes
- `/login`
- `/register`
- `/`
- `/chat`
- `/friends`
- `/invitations`
- `/notification`
- `/profile`
- `/profile/:userId`

## Runtime
- In production, the Vite build is served by Nginx on container port `3000`.
- In local Docker, public access is via Nginx at `https://localhost:8443`.
- Frontend healthcheck is `GET /health` on the internal Nginx.

## Environment
- `VITE_API_SERVER_URL`

## Local development
- `npm install`
- `npm run dev`
- `npm run build`
- `npm run preview`

## Implementation notes
- The app uses providers for auth, user profile, alerts, and notifications.
- The Dockerfile uses three stages: `build`, `development`, and `production`.
- Vite config enables React and TypeScript path aliases.
