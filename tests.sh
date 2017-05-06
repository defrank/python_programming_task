#!/usr/bin/env bash

################################################################################
# OPTIONS
################################################################################

#set -e  # Exit if any command fails.
set -o pipefail


################################################################################
# GLOBALS
################################################################################

export http_proxy="http://localhost:8080"

test_domain='derekmfrank.com'
test_origin="http://${test_domain}"
test_path='/assets/img/dmf-snowboarding-lens-flare.jpg'
test_url="${test_origin}${test_path}"



################################################################################
# HELPERS
################################################################################

get() {
    local url="$1"
    shift 1

    curl -s -o /dev/null -w "%{http_code}" "$@" "$url"
}

post() {
    # Should still use `--data` or `--form` option.
    get "$@" --request POST
}

head() {
    get "$@" --head
}

put() {
    # Should still use `--data` option?
    # Really need to use something other than curl...
    get "$@" --request PUT
}

delete() {
    # Should still use `--data` option?
    # Really need to use something other than curl...
    get "$@" --request DELETE
}

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
    local code="$1"
    local url="$2"
    local name="$3"
    shift 3

    if [ $(get "$url" "$@") -eq "$code" ]; then
        pass "$code" "$name" "$url"
    else
        fail "$code" "$name" "$url"
    fi
}

test_post() {
    local code="$1"
    local url="$2"
    local name="$3"
    shift 3

    if [ $(post "$url" "$@") -eq "$code" ]; then
        pass "$code" "$name" "$url $@"
    else
        fail "$code" "$name" "$url $@"
    fi
}


################################################################################
# TESTS
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
