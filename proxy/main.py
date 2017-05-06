################################################################################
# IMPORTS
################################################################################

# Important preconfiguration.
from gevent import monkey; monkey.patch_all()

# Stdlib.
from os import environ, path as ospath
from time import sleep, time
from urllib.parse import urlparse, urlunparse

# Related 3rd party.
import requests
from bottle import abort, get, post, request, route, template


################################################################################
# DATABASE
################################################################################

def store_proxy(db, url, status_code, content=''):
    """Logs the proxy response information to the database."""

    query = '''
        INSERT INTO proxy_log (url, status_code, size)
        VALUES (?, ?, ?)
        ;
    '''

    db.execute(query, [url, status_code, len(content)])


def load_stats(db, *fields):
    """Retrieves the stored proxy statistics."""

    if not fields:
        fields = ['id', 'url', 'status_code', 'size']

    query = '''
        SELECT {fields}
        FROM proxy_log
        WHERE size > ?
        ;
    '''.format(fields=', '.join(fields))

    return db.execute(query, [0]).fetchall()


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

    stats = load_stats(db, 'size')
    return dict(uptime=time() - start_time,
                total_bytes_transferred=sum(s['size'] for s in stats))


@route('<url:re:.+>', method=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])
def proxy(db, url):
    """
    Proxy the `url` for the client.
    Logs the proxied response data in the database.

    """
    # Get parameters.
    url = urlparse(url.strip(), scheme='http')

    # Validate parameters.
    if not url.netloc:
        abort(400, '`URL` does not contain a valid host')

    # Log and return proxied response.
    url = urlunparse(url)
    try:
        response = requests.request(request.method, url)
    except requests.exceptions.ConnectionError:
        store_proxy(db, url, 502)  # Logs 0 bytes, so doesn't get counted in stats.
        abort(502, 'Unable to proxy `{url}`'.format(url=url))
    else:
        store_proxy(db, url, response.status_code, response.content)
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
