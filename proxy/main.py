################################################################################
# IMPORTS
################################################################################

# Important preconfiguration.
from gevent import monkey; monkey.patch_all()

# Stdlib.
from time import sleep

# Related 3rd party.
from bottle import route, run, template


################################################################################
# VIEWS
################################################################################

@route('/')
def proxy():
    return template('proxy')


@route('/foo')
def foobar():
    sleep(20)
    return 'foobar for 20 seconds!'


################################################################################
# MAIN
################################################################################

if __name__ == '__main__':
    run(server='gevent', host='0.0.0.0', port=8080, debug=True)
