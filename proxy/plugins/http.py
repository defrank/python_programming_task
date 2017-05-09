################################################################################
# IMPORTS
################################################################################

# Stdlib.
import re
from uuid import uuid4

# Related 3rd party.
from bottle import abort, parse_range_header, request, response, \
        HTTPResponse, HTTPError
from requests import codes


################################################################################
# CLASSES
################################################################################

# Regex.
RANGE_SPEC_REGEX = re.compile(r'^(?:\d+-\d*)|(?:-\d+)$')

# Variables instead of preprocessor.
UNITS = 'bytes'
KEY = 'range'


################################################################################
# CLASSES
################################################################################

class RangeRequestsPlugin(object):
    """
    Middleware/plugin to deal with HTTP Range Requests.  Follows RFC2616
    specifications for validating.  Also allows a query parameter, `range`, to
    mimic the behavior of the Range header.

    Potential response codes:
        206 -- Partial content
        416 -- Range not satisfiable

    """

    name = 'ranges'
    api = 2

    def __init__(self, callback=None):
        """
        Initialize this instance.

        Arguments:
            callback -- function that get called with the processed response
                content

        """
        self.callback = callback

    def setup(self, app):
        """
        Called as soon as the plugin is installed to an application.  The only
        parameter is the associated application.

        """
        pass

    def apply(self, callback, context):
        """Replace the route callback with a wrapped one."""

        def wrapper(*args, **kwargs):
            ranges_specifier = self.process_request()
            content = callback(*args, **kwargs)
            partial_content = self.process_response(content, ranges_specifier)
            if partial_content is not None:
                content = partial_content
            if callable(self.callback):
                self.callback(content)
            return content

        return wrapper

    def close(self):
        """
        Called immediately before the plugin is uninstalled or the application
        is closed.

        """
        pass

    @classmethod
    def abort(self, msg=None, ranges_specifier=None):
        if msg is None:
            msg = 'range not satisfiable'
            if ranges_specifier is not None:
                msg += ': {0}'.format(ranges_specifier)
        abort(codes.RANGE_NOT_SATISFIABLE, msg)

    def process_request(self):
        """
        Get the range value taken directly from the header or query.  Will
        abort with a 416 if range is specified in more than one place (e.g.,
        header and query), but the values are not equal.

        Returns:
            str or None -- ranges specifier as specified by client request

        """
        specifiers = [
            request.headers.get(KEY),
            request.query.get(KEY),
        ]
        specifier = next((s for s in specifiers if s is not None), None)

        # Validate header and range values are equivalent if both are present.
        # Return if neither is present.
        # Allows for `specifiers` to be more than just a header and range value.
        if sum(1 if s is None else 0 for s in specifiers) >= len(specifiers) - 1:
            if specifier is None:
                return
        elif any(s != specifier for s in specifiers if s is not None):
            self.abort('`{key}` range specifiers differ: {values}'.format(
                key=KEY,
                values=' != '.join(filter(lambda s: s is not None, specifiers)),
            ))

        return specifier

    def process_response(self, content, ranges_specifier=None):
        """
        Determine if and what partial content should be sent to the client.
        Modifies response headers to accomodate partial content.

        Since we only care about ranges for proxied content, only process the
        ranges of content of a specific type (i.e., bytes and iterables of bytes).

        References:
            https://www.ietf.org/rfc/rfc2616.txt
            https://developer.mozilla.org/en-US/docs/Web/HTTP/Range_requests
            https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Accept-Ranges

        Arguments:
            content -- response content of a type that Bottle accepts
            ranges_specifier -- str of RFC2616 ranges specified by client

        Returns:
            bytes or None -- partial content specified by ranges

        """
        if response.status_code == codes.PARTIAL_CONTENT:
            return  # Already dealt with.
        elif response.status_code >= codes.bad:
            return  # Do not process a bad response.

        # Assume a proxied content type will only be bytes or iterable of bytes.
        # TODO: consider content size and use a buffer or file object.
        if not isinstance(content, bytes):
            try:
                content = b''.join(b for b in (content() if callable(content) else content))
            except TypeError:
                return

        # Show support for ranges.
        response.set_header('Accept-Ranges', UNITS)

        clen = len(content)
        # `parse_range_header` follows RFC2616 specification for parsing byte
        # ranges.
        ranges = list(parse_range_header(ranges_specifier, clen))
        if ranges_specifier and not ranges:
            self.abort(ranges_specifier=ranges_specifier)
        elif ranges:
            response.status = codes.PARTIAL_CONTENT

            if len(ranges) == 1:
                # Single-part ranges.
                start, end = ranges[0]

                response.set_header('Content-Range', '{units} {start}-{end}/{clen}'.format(
                    units=UNITS,
                    start=start,
                    end=end - 1,
                    clen=clen,
                ))

                # Set partial content.
                content = content[start:end]
                clen = end - start
            else:
                # Multi-part ranges.
                ctype = response.content_type
                charset = response.charset
                while True:
                    boundary = uuid4().hex.encode(response.charset)
                    if boundary not in content:
                        break

                response.set_header(
                        'Content-Type',
                        'multipart/byteranges; boundary={0}'.format(boundary.decode()))

                # Build partial content bytes that will be joined by newlines.
                parts = []
                for start, end in ranges:
                    parts.extend([
                        b'--%s' % boundary,
                        b'Content-Type: %s' % ctype.encode(charset),
                        b'Content-Range: %(units)s %(start)d-%(end)d/%(clen)d' % {
                            b'units': UNITS.encode(charset),
                            b'start': start,
                            b'end': end - 1,
                            b'clen': clen,
                        },
                        b'',  # Separate content from headers with a newline.
                        content[start:end],
                    ])
                parts.append(b'--%s--' % boundary)

                # Set partial content.
                content = b'\n'.join(parts)
                clen = len(content)

        response.content_length = str(clen)
        return content
