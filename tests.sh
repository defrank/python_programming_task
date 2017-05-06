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

# Program options.
debug=false

# Proxy specific.
export http_proxy="http://localhost:8080"

# Test specific.
test_domain='derekmfrank.com'
test_origin="http://${test_domain}"
test_path='/assets/img/dmf-snowboarding-lens-flare.jpg'
test_url="${test_origin}${test_path}"


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
    exit 1
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

    if [ "$debug" = true ]; then
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
    echo "Usage: ${progname} [-h/-?] [-d]"
}

show_help() {
    show_usage
    echo
    echo 'Help:'
    echo '    -h,-?     Show help.'
    echo '    -d        Enable debug printing.'
}

OPTIND=1
while getopts 'h?d' opt; do
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
            ;;
    esac
done


################################################################################
# MAIN - TESTS
################################################################################

echo "http_proxy: ${http_proxy}"

echo
echo '################################'
echo 'Proxy Tests'
test_get 200 "${test_origin}/" 'basic success'
test_get 200 "${test_domain}/" 'missing protocol succeeds'
test_get 502 'http://senrsent.rsienresaitn.aiertsnresitn/' 'invalid host fails'

echo
echo '################################'
echo 'Stats Tests'
test_get 200 "${http_proxy}/stats" 'basic success'
