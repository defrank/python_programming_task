################################################################################
# IMPORTS
################################################################################

# Important preconfiguration.
from gevent import monkey; monkey.patch_all()

# Stdlib.
from functools import reduce
from itertools import chain
from io import BytesIO
from operator import and_
from os import environ, path as ospath
from time import sleep, time
from urllib.parse import urlparse, urlunparse

# Related 3rd party.
import requests
from bottle import abort, get, request, response, route, template, \
        LocalResponse


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

def store_proxy(db, url, status_code, request_size, response_size=0):
    """Logs the proxy response information to the database."""
    assert all(size >= 0 for size in [request_size, response_size]), \
            '`size` cannot be negative'

    query = '''
        INSERT INTO proxy_log (url, status_code, request_size, response_size)
        VALUES (?, ?, ?, ?)
        ;
    '''

    db.execute(query, [url, status_code, request_size, response_size])


def load_stats(db, *fields):
    """Retrieves the stored proxy statistics."""

    if not fields:
        fields = ['id', 'url', 'status_code', 'request_size', 'response_size']

    query = '''
        SELECT {fields}
        FROM proxy_log
        ;
    '''.format(fields=', '.join(fields))

    return db.execute(query).fetchall()


################################################################################
# VIEWS
################################################################################

@get('/stats')
def stats(db):
    """
    Display proxy statistics:
        * uptime
        * total bytes transferred

    """
    start_time = globals().get('START_TIME', None)
    assert start_time is not None, 'bottle app is not properly configured'

    stats = load_stats(db, 'request_size', 'response_size')
    return dict(uptime=time() - start_time,
                total_bytes_transferred=sum(s['request_size'] + s['response_size']
                                            for s in stats))


@route('<url:re:.+>', method=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])
def proxy(db, url):
    """
    Proxy the `url` for the client.
    Logs the proxied response data in the database.

    """
    # Validations.
    url = validate_url(url)
    validate_headers_and_query_equal(request, range=416)

    # Log and return proxied response.
    try:
        proxy_response = requests.request(method=request.method,
                                          url=url,
                                          headers=request.headers,
                                          files=request.files,
                                          data=request.forms or request.body,
                                          json=request.json,
                                          params=request.query,
                                          auth=request.auth,
                                          cookies=request.cookies)
    except (requests.exceptions.ConnectionError,
            requests.packages.urllib3.exceptions.NewConnectionError):
        # Logs 0 bytes for reponse, so doesn't get counted in stats.
        store_proxy(db, url, 502, get_size(request))
        abort(502, 'Unable to proxy `{url}`'.format(url=url))
    else:
        store_proxy(db,
                    url,
                    proxy_response.status_code,
                    get_size(request),
                    get_size(proxy_response))

        response = LocalResponse(body=proxy_response.text,
                                 status=proxy_response.status_code,
                                 headers=dict(proxy_response.headers))

        # Add cookies.
        for c, v in proxy_response.cookies.items():
            response.set_cookie(c, v)

        return response


################################################################################
# MAIN
################################################################################

if __name__ == '__main__':
    from bottle import install, run
    from bottle.ext.sqlite import SQLitePlugin

    START_TIME = time()
    install(SQLitePlugin(dbfile=environ.get('DB'), dictrows=True))
    run(server='gevent', host='0.0.0.0', port=8080, debug=True)
