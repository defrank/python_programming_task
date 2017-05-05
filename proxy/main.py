################################################################################
# IMPORTS
################################################################################

# Important preconfiguration.
from gevent import monkey; monkey.patch_all()

# Stdlib.
from os import path as ospath
from time import sleep

# Related 3rd party.
from bottle import get, post, run, template


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
# VIEWS
################################################################################

@get('/')
def preproxy():
    """The view that asks the user what to proxy."""
    return rendered('proxy')


@post('/')
def proxy():
    return 'Not implemented!'


@get('/stats')
def stats():
    return 'Not implemented!'


################################################################################
# MAIN
################################################################################

if __name__ == '__main__':
    run(server='gevent', host='0.0.0.0', port=8080, debug=True)
