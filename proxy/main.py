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
# DATABASE
################################################################################

def dbquery(query, *args):
    with database.connect(DATABASE) as conn:
        cursor = conn.cursor()
        return cursor.execute(query, args).fetchall()


def store_stats(url, status_code, content_length=-1):
    """Logs the response information to the database."""
    if content_length is None:
        content_length = response.content_length

    query = '''
        INSERT INTO proxy_log (url, status_code, size)
        VALUES (?, ?, ?)
        ;
    '''

    return dbquery(query, url, status_code, content_length)


def load_stats(*fields):
    """Retrieves the stored proxy statistics."""

    if not fields:
        fields = ['id', 'url', 'status_code', 'size']

    query = '''
        SELECT {fields}
        FROM proxy_log
        WHERE size > 0
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

    return {
        'uptime': time() - start_time,
        'total_bytes_transferred': sum(s[0] for s in load_stats('size')),
    }


@route('<url:re:.+>', method=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])
def proxy(url):
    """
    Proxy the `url` for the client.
    Logs the proxied response data in the database.

    """
    # Return proxied response.
    with requests.Session() as session:
        with closing(session.request(method=request.method,
                                     stream=False,  # TODO: Support streaming.
                                     url=url,
                                     headers=request.headers,
                                     files=request.files,
                                     data=request.forms or request.body,
                                     json=request.json,
                                     params=request.query,
                                     auth=request.auth,
                                     cookies=request.cookies)) as proxied:

            # Forward proxied response headers to client.
            response.status = proxied.status_code
            for h,v in proxied.headers.items():
                # TODO: support encoding GZip responses.
                if h.lower() != 'content-encoding':
                    response.set_header(h, v)
            for c, v in proxied.cookies.items():
                response.set_cookie(c, v)

            # Build the client's response in chunks.
            for chunk in proxied.iter_content(chunk_size=None):
                yield chunk


################################################################################
# HOOKS/CALLBACKS
################################################################################

def request_range_callback(content):
    """Store the size in bytes of the response."""
    try:
        size = response.content_length
    except ValueError:
        if isinstance(content, bytes):
            size = len(content)
        else:
            size = -1
    store_stats(request.url, response.status_code, size)


################################################################################
# MAIN
################################################################################

if __name__ == '__main__':
    from bottle import install, run
    from plugins.http import RangeRequestsPlugin

    START_TIME = time()
    install(RangeRequestsPlugin(request_range_callback))
    run(server='gevent', host='0.0.0.0', port=8080, debug=True)
