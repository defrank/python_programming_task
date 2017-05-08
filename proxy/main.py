################################################################################
# IMPORTS
################################################################################

# Important preconfiguration.
from gevent import monkey; monkey.patch_all()

# Stdlib.
from contextlib import closing
from functools import reduce
from itertools import chain
from io import BytesIO
from operator import and_
from os import environ, path as ospath
from time import sleep, time
from urllib.parse import urlparse, urlunparse

# Related 3rd party.
import requests
from bottle import abort, get, request, response, route, template
from bottle.ext.sqlite import sqlite3 as database


################################################################################
# GLOBALS
################################################################################

DATABASE = environ.get('DB')


################################################################################
# HELPERS
################################################################################

def bytesize(s):
    """Return the size in bytes of given string, bytes or BytesIO."""
    if isinstance(s, bytes):
        s = s
    elif isinstance(s, str):
        s = s.encode('utf-8')
    elif isinstance(s, BytesIO):
        s = s.getbuffer()
    else:
        raise AssertionError('`s` must be bytes encodable: {0}'.format(type(s)))
    return len(s)


def dictsize(d):
    """Return the size in bytes of the keys and values in the given dictionary."""
    return sum(bytesize(s) for s in chain.from_iterable(d.items()))


def get_size(r):
    """Return the size of a request or response object."""
    payload = max(0,
                  bytesize(getattr(r, 'content', '')),
                  bytesize(getattr(r, 'body', '')),
                  bytesize(getattr(r, 'text', '')))
    headers = dictsize(r.headers)
    return payload + headers


################################################################################
# VALIDATORS
################################################################################

def validate_url(url):
    # Strip and parse.
    url = urlparse(url.strip(), scheme='http')

    # Must have a hostname.
    if not url.netloc:
        abort(400, '`URL` does not contain a valid host')

    return urlunparse(url)


def validate_headers_and_query_equal(request, **only):
    """
    Compare the header and query parameter values of the same key if they are
    specified in `only` as keys.  Raises an HTTPError exception if the values
    exist as a header and query parameter, but do not match.

    Assume case matches for `only` and `request.query` keys.  Header keys are
    treated case-insensitively via WSGIHeaderDict.

    Status codes must be given as values in `only`.  They are used when raising
    aborting.

    Arguments:
        request -- instance of Request containing header and query mappings
        only -- mapping of header/query keys to error status_codes

    """
    headers, query = request.headers, request.query
    # Compare unique keys that exist in `only`, `query`, and `header`.
    for key in reduce(and_, map(set, [only, query])):
        if key in headers and query[key] != headers[key]:
            abort(only[key], '`{key}` query parameter differs from header: {v1} != {v2}'.format(
                key=key,
                v1=query[key],
                v2=headers[key],
            ))


################################################################################
# DATABASE
################################################################################

def dbquery(query, *args):
    with database.connect(DATABASE) as conn:
        cursor = conn.cursor()
        return cursor.execute(query, args).fetchall()


def store_proxy(url, status_code, request_size, response_size=0):
    """Logs the proxy response information to the database."""
    assert all(size >= 0 for size in [request_size, response_size]), \
            '`size` cannot be negative'

    query = '''
        INSERT INTO proxy_log (url, status_code, request_size, response_size)
        VALUES (?, ?, ?, ?)
        ;
    '''

    return dbquery(query, url, status_code, request_size, response_size)


def load_stats(*fields):
    """Retrieves the stored proxy statistics."""

    if not fields:
        fields = ['id', 'url', 'status_code', 'request_size', 'response_size']

    query = '''
        SELECT {fields}
        FROM proxy_log
        ;
    '''.format(fields=', '.join(fields))

    return dbquery(query)


################################################################################
# VIEWS
################################################################################

@get('/stats')
def stats():
    """
    Display proxy statistics:
        * uptime
        * total bytes transferred

    """
    start_time = globals().get('START_TIME', None)
    assert start_time is not None, 'bottle app is not properly configured'

    stats = load_stats('request_size', 'response_size')
    return dict(uptime=time() - start_time,
                total_bytes_transferred=sum(reqsize + respsize
                                            for reqsize, respsize in stats))


@route('<url:re:.+>', method=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])
def proxy(url):
    """
    Proxy the `url` for the client.
    Logs the proxied response data in the database.

    """
    # Validations.
    url = validate_url(url)
    validate_headers_and_query_equal(request, range=416)

    for h, v in request.headers.items():
        print('    ', h, v)

    # Log client's request.
    store_proxy(url, 0, get_size(request), 0)
    # Log and return proxied response.
    with requests.Session() as session:
        with closing(session.request(stream=True,
                                     method=request.method,
                                     url=url,
                                     headers=request.headers,
                                     files=request.files,
                                     data=request.forms or request.body,
                                     json=request.json,
                                     params=request.query,
                                     auth=request.auth,
                                     cookies=request.cookies)) as proxied:
            store_proxy(url, proxied.status_code, 0, bytesize(proxied.content))

            # Forward proxied response headers to client.
            response.status = proxied.status_code
            for h,v in proxied.headers.items():
                if h.lower() not in ['content-length', 'content-encoding']:
                    response.set_header(h, v)
            for c, v in proxied.cookies.items():
                response.set_cookie(c, v)

            # Build the client's response in chunks.
            for chunk in proxied.iter_content(chunk_size=None):
                yield chunk


################################################################################
# MAIN
################################################################################

if __name__ == '__main__':
    from bottle import install, run

    START_TIME = time()
    run(server='gevent', host='0.0.0.0', port=8080, debug=True)
