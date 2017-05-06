#!/usr/bin/env bash
################################################################################
#
# Dependencies:
#     curl
#
################################################################################

################################################################################
# OPTIONS
################################################################################

#set -e  # Exit if any command fails.
set -o pipefail


################################################################################
# GLOBALS
################################################################################

# Program metadata.
progname="$0"
exit_success=true

# Program options.
debug=false
headers=false
failfast=false

# Proxy specific.
export http_proxy="http://localhost:8080"

# Test specific.
test_domain='www.google.com'
test_origin="http://${test_domain}"
test_url="${test_origin}/"
# https://linhost.info/2013/10/download-test-files/
# CacheFly
test_url_1='http://cachefly.cachefly.net/100mb.test'
# SoftLayer
test_url_2='http://speedtest.dal01.softlayer.com/downloads/test100.zip'
test_url_3='http://speedtest.sea01.softlayer.com/downloads/test100.zip'
# Linode
test_url_4='http://mirror.nl.leaseweb.net/speedtest/1000mb.bin'
test_url_5='http://mirror.us.leaseweb.net/speedtest/1000mb.bin'


################################################################################
# HELPERS
################################################################################

pass() {
    local code="$1"
    local name="$2"
    local url="$3"
    shift 3

    echo "PASSED $code $name: $url $@"
}

fail() {
    local code="$1"
    local name="$2"
    local url="$3"
    shift 3

    echo "FAILED $code $name: $url $@"

    exit_success=false
    if [ "$failfast" = true ]; then
        exit 1
    fi
}

test_get() {
    # Prints the status code to stdout.
    local code="$1"
    local url="$2"
    local name="$3"
    shift 3

    local output="$(curl \
                        --silent \
                        --output /dev/null \
                        --dump-header - \
                        --write-out "%{http_code}" \
                        "$@" \
                        "$url" \
                        )"

    # Split output between stdout and stderr.
    # status code to stdout
    if [ "$(tail -n 1 <(echo "$output"))" -eq "$code" ]; then
        pass "$code" "$name" "$url"
    else
        fail "$code" "$name" "$url"
    fi

    if [ "$headers" = true ]; then
        head -n -2 <(echo "$output") | sed -e 's/^/    /' >&2  # headers to stderr
    fi
}

test_post() {
    # Prints the status code to stdout.
    # Should still use `--data` or `--form` option.
    test_get "$@" --request POST
}

test_head() {
    # Prints the status code to stdout.
    test_get "$@" --head
}

test_put() {
    # Prints the status code to stdout.
    # Should still use `--data` option?
    # Really need to use something other than curl...
    test_get "$@" --request PUT
}

test_delete() {
    # Prints the status code to stdout.
    # Should still use `--data` option?
    # Really need to use something other than curl...
    test_get "$@" --request DELETE
}


################################################################################
# MAIN - OPTIONS
################################################################################

show_usage() {
    echo "Usage: ${progname} [-h/-?] [-i|-d] [-f]"
}

show_help() {
    show_usage
    echo
    echo 'Help:'
    echo '    -h,-?     Show help.'
    echo '    -i        Enable header printing.'
    echo '    -d        Enable debug printing.  Forces -i on.'
    echo '    -f        Enable fail fast.'
}

OPTIND=1
while getopts 'h?idf' opt; do
    if [ "${OPTARG:0:1}" = '-' ]; then
        show_usage
        exit 2
    fi

    case "$opt" in
        h|\?)  # --help
            show_help
            exit 0
            ;;
        d)  # --debug
            debug=true
            ;&
        i)  # --headers
            headers=true
            ;;
        f)  # --failfast
            failfast=true
            ;;
    esac
done


################################################################################
# MAIN - VALIDATE INPUT
################################################################################

echo "http_proxy: ${http_proxy}"
echo

echo '################################'
echo 'Proxy Tests'
old_failfast=$failfast
failfast=true
test_head 200 "${test_url}" 'validate url 0'
test_head 200 "${test_url_1}" 'validate url 1'
test_head 200 "${test_url_2}" 'validate url 2'
test_head 200 "${test_url_3}" 'validate url 3'
test_head 200 "${test_url_4}" 'validate url 4'
test_head 200 "${test_url_5}" 'validate url 5'
failfast=$old_failfast


################################################################################
# MAIN - TESTS
################################################################################

echo '################################'
echo 'Proxy Tests'
test_get 200 "${test_origin}/" 'basic success'
test_get 200 "${test_domain}/" 'missing protocol succeeds'
test_get 502 'http://senrsent.rsienresaitn.aiertsnresitn/' 'invalid host fails'
echo '#### Range tests'
test_get 200 "${test_origin}/?range=1-50" 'basic range query param'
test_get 200 "${test_origin}/" 'basic range header' --header 'Range: 1-50'
test_get 200 "${test_origin}/?foobar=barbaz" 'basic other query param'
test_get 200 "${test_origin}/" 'basic other header' --header 'Foobar: barbaz'
test_get 416 "${test_origin}/?range=1-50" 'ranges differ' --header 'Range: 5-10'
test_get 200 "${test_origin}/?range=1-50" 'ranges equal' --header 'Range: 1-50'
test_get 200 "${test_origin}/?rAnGe=1-50" 'differing ranges mixed case succeeds' --header 'RangE: 5-10'

echo

echo '################################'
echo 'Stats Tests'
test_get 200 "${http_proxy}/stats" 'basic success'
echo

if [ "$exit_success" = false ]; then
    exit 1
else
    echo 'VALID!'
fi
