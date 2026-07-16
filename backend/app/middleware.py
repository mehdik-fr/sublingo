from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestBodyLimitMiddleware:
    """Reject oversized HTTP bodies before validation or provider work starts."""

    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = _content_length(scope)

        if content_length is not None and content_length > self.max_body_bytes:
            await _send_too_large(scope, receive, send)
            return

        messages: list[Message] = []
        total_bytes = 0
        more_body = True

        while more_body:
            message = await receive()
            messages.append(message)

            if message["type"] == "http.disconnect":
                break

            total_bytes += len(message.get("body", b""))

            if total_bytes > self.max_body_bytes:
                await _send_too_large(scope, receive, send)
                return

            more_body = message.get("more_body", False)

        async def replay_receive() -> Message:
            if messages:
                return messages.pop(0)

            return await receive()

        await self.app(scope, replay_receive, send)


def _content_length(scope: Scope) -> int | None:
    for name, value in scope.get("headers", []):
        if name.lower() != b"content-length":
            continue

        try:
            return int(value)
        except ValueError:
            return None

    return None


async def _send_too_large(scope: Scope, receive: Receive, send: Send) -> None:
    response = JSONResponse(
        {"detail": "Request body too large"},
        status_code=413,
    )
    await response(scope, receive, send)


class RateLimitMiddleware:
    """Apply a bounded in-memory rate limit to the public analysis route."""

    def __init__(self, app: ASGIApp, requests_per_minute: int) -> None:
        self.app = app
        self.requests_per_minute = requests_per_minute
        self.max_tracked_clients = 10_000
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()
        self._last_cleanup = monotonic()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope.get("method") != "POST"
            or scope.get("path") != "/v1/subtitles/analyze"
        ):
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        client_host = client[0] if client else "unknown"
        origin = next(
            (
                value.decode("latin-1")
                for name, value in scope.get("headers", [])
                if name.lower() == b"origin"
            ),
            "no-origin",
        )
        key = f"{client_host}\0{origin}"
        now = monotonic()

        with self._lock:
            if now - self._last_cleanup >= 60:
                for existing_key, existing_window in list(self._requests.items()):
                    while existing_window and existing_window[0] <= now - 60:
                        existing_window.popleft()

                    if not existing_window:
                        del self._requests[existing_key]

                self._last_cleanup = now

            if key not in self._requests and len(self._requests) >= self.max_tracked_clients:
                limited = True
            else:
                window = self._requests[key]

                while window and window[0] <= now - 60:
                    window.popleft()

                if len(window) >= self.requests_per_minute:
                    limited = True
                else:
                    window.append(now)
                    limited = False

        if limited:
            response = JSONResponse(
                {"detail": "Rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": "1"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
