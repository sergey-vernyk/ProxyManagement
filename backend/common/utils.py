from fastapi import Request


def get_base_url(request: Request) -> str:
    """
    Returns base URL depends on the port and scheme.

    Args:
        request (Request): HTTP request.

    Returns:
        str: base url like:
            non-standard port:
                http://example.com:1234 or https://example.com:1234.
            standard port:
                http://example.com or https://example.com.
    """
    host = request.base_url.hostname
    port = request.headers.get("X-Forwarded-Port", request.base_url.port)
    scheme = request.headers.get("X-Forwarded-Proto", request.base_url.scheme)

    if int(port) in {80, 443}:
        return f"{scheme}://{host}"

    return f"{scheme}://{host}:{port}"
