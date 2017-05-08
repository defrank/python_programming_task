################################################################################
# IMPORTS
################################################################################

# Stdlib.
import re

# Related 3rd party.
from bottle import abort, request, response
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

    def setup(self, app):
        pass

    def apply(self, callback, context):
        """Replace the route callback with a wrapped one."""

        def wrapper(*args, **kwargs):
            self.process_request()
            body = callback(*args, **kwargs)
            self.process_response()
            return body

        return wrapper

    def close(self):
        pass

    def abort(self, msg=None, range_specifier=None):
        if msg is None:
            msg = 'range not satisfiable'
            if range_specifier is not None:
                msg += ': {0}'.format(range_specifier)
        abort(codes.RANGE_NOT_SATISFIABLE, msg)

    def process_request(self):
        """
        Parse the range value taken directly from the header or query.  May
        abort with a 416 for a specified range that cannot be satisfied.

        RFC2616:
        * Only range unit defined is "bytes" (3.12 Range Units)
          --> Implementation MAY ignore.  This implementation raise 416.
        * Accepts single and multi-part ranges (14.35 Ranges)

        References:
            https://www.ietf.org/rfc/rfc2616.txt
            https://developer.mozilla.org/en-US/docs/Web/HTTP/Range_requests
            https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Accept-Ranges

        Returns:
            list -- of tuples containing start and end integer values

        """
        specifiers = [
            request.headers.get(KEY),
            request.query.get(KEY),
        ]
        specifier = next((s for s in specifiers if s is not None), None)

        # Validate header and range values are equivalent if both are present.
        # Return if neither is present.
        print('SPECS:', specifiers)
        if sum(1 if s is None else 0 for s in specifiers) >= len(specifiers) - 1:
            if specifier is None:
                return
        elif any(s != specifier for s in specifiers if s is not None):
            self.abort('`{key}` range specifiers differ: {values}'.format(
                key=KEY,
                values=' != '.join(filter(lambda s: s is not None, specifiers)),
            ))

        try:
            units, range_set = specifier.split('=', 1)
        except ValueError:
            self.abort(range_specifier=specifier)

        # Validate specified units.
        if units.strip().lower() != UNITS:
            self.abort(range_specifier=specifier)

        # Get valid first and last byte range values.
        ranges = []
        specs = range_set.split(',')
        for spec in (s.strip() for s in specs if s.strip()):
            first = last = None  # first and last bytes.
            if RANGE_SPEC_REGEX.fullmatch(spec) is None:
                continue  # Prevent crashing on stuff like injecting negative numbers.
            elif spec.endswith('-'):
                first = int(spec.strip('- '))
            elif spec.startswith('-'):
                last = -int(spec.strip('- '))
            else:
                first, last = (int(b.strip()) for b in spec.split('-'))

            # Skip malformed parts.
            if all(b is None for b in [first, last]):
                continue
            elif first is None and abs(last) > content_length:
                continue
            elif last is None and first >= content_length:
                continue
            elif first > last:
                continue
            else:
                ranges.append((first, last))

        if specs and not ranges:
            abort(codes.RANGE_NOT_SATISFIABLE, 'unsatisfiable byte-range-set')

        return ranges

    def process_response(self, ranges=[]):
        if response.status_code == codes.PARTIAL_CONTENT:
            return  # Already dealt with.  TODO: Verify gzip encoded responses.
        elif response.status_code >= codes.bad:
            return # Do not process a bad response.

        # Show support for ranges.
        response.set_header('Accept-Ranges', UNITS)
