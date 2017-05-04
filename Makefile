# Only supports macOS environment.

MKFILE      = Makefile
GMAKE       = ${MAKE} --no-print-directory
UNAME      ?= ${shell uname -s}

ifeq (${UNAME}, Darwin)
COPY = pbcopy
PASTE = pbpaste
endif

PROXY_NAME = pythonprogrammingtask_proxy_1

copy_id :
	@ docker ps | tail -n +2 | awk '/${PROXY_NAME}/ {print $$1}' | ${COPY}
	@ ${PASTE}

down :
	docker-compose down

build : down
	docker-compose build

up : build
	docker-compose up -d

restart :
	docker-compose restart

ssh : copy_id
	docker exec -it $(shell ${PASTE}) /bin/bash
