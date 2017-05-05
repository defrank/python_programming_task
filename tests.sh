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
test_path='/resume/'  # for $test_domain


################################################################################
# HELPERS
################################################################################

get() {
    local url="$1"
    curl -s -o /dev/null -w "%{http_code}" "$url"
}

pass() {
    local code="$1"
    local name="$2"
    local url="$3"

    echo "PASSED $code $name: $url"
}

fail() {
    local code="$1"
    local name="$2"
    local url="$3"

    echo "FAILED $code $name: $url"
    exit 1
}

test_get() {
    local code="$1"
    local url="$2"
    local name="$3"
    if [ $(get "$url") -eq "$code" ]; then
        pass "$code" "$name" "$url"
    else
        fail "$code" "$name" "$url"
    fi
}


################################################################################
# TESTS
################################################################################

echo "http_proxy: ${http_proxy}"

echo
echo '################################'
echo 'Proxy Tests'
test_get 200 "http://${test_domain}/" 'basic success'
test_get 200 "${test_domain}/" 'missing protocol succeeds'
test_get 502 'http://senrsent.rsienresaitn.aiertsnresitn/' 'invalid host fails'

echo
echo '################################'
echo 'Stats Tests'
test_get 200 "${http_proxy}/stats" 'basic success'
