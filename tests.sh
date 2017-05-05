#!/usr/bin/env bash

set -e  # Exit if any command fails.
set -o pipefail

proxy_url="http://localhost:8080"

curl --form "url=http://derekmfrank.com" "$proxy_url" >/dev/null
