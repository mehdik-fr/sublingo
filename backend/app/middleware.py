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

            return {"type": "http.request", "body": b"", "more_body": False}

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
