################################################################################
# IMPORTS
################################################################################

# Important preconfiguration.
from gevent import monkey; monkey.patch_all()

# Stdlib.
from os import environ, path as ospath
from time import sleep
from urllib.parse import urlparse, urlunparse

# Related 3rd party.
import requests
from bottle import abort, get, post, request, template


################################################################################
# GLOBALS
################################################################################

# Program specific.
PROJECT_DIRECTORY = ospath.dirname(ospath.abspath(__file__))
PROG_NAME = 'proxy'
PROG_TITLE = 'Asynchronous HTTP Proxy'

# Template stuff.
TPL_DEFAULTS = {
    'title': PROG_TITLE,
}


################################################################################
# RENDER
################################################################################

def rendered(name, **kwargs):
    """Include template defaults when rendering."""
    return template(name, dict(TPL_DEFAULTS, **kwargs))


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


################################################################################
# VIEWS
################################################################################

@get('/')
def preproxy():
    """The view that asks the user what to proxy."""
    return rendered('proxy')


@post('/')
def proxy(db):
    """
    Proxy the POSTed `url` for the client.
    Logs the proxied response data in the database.

    """
    # Get parameters.
    url = urlparse(request.forms.get('url'), scheme='http')

    # Validate parameters.
    if not url.netloc:
        abort(400, '`URL` does not contain a valid host')

    # Log and return proxied response.
    url = urlunparse(url)
    try:
        response = requests.get(url)
    except requests.exceptions.ConnectionError:
        store_proxy(db, url, 502)  # Logs 0 bytes, so doesn't get counted in stats.
        abort(502, 'Unable to proxy `{url}`'.format(url=url))
    else:
        store_proxy(db, url, response.status_code, response.content)
        return response


@get('/stats')
def stats(db):
    abort(501, 'Not implemented!')


################################################################################
# MAIN
################################################################################

if __name__ == '__main__':
    from bottle import install, run
    from bottle.ext.sqlite import SQLitePlugin

    install(SQLitePlugin(dbfile=environ.get('DB'), dictrows=True))
    run(server='gevent', host='0.0.0.0', port=8080, debug=True)
