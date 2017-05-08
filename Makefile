# Only supports macOS environment.

MKFILE      = Makefile
GMAKE       = ${MAKE} --no-print-directory
UNAME      ?= ${shell uname -s}

ifeq (${UNAME}, Darwin)
COPY = pbcopy
PASTE = pbpaste
endif

NAME_PREFIX = pythonprogrammingtask_
PROXY_NAME = ${NAME_PREFIX}proxy_1

DOCKER_IDS = docker-ids.tmp

ids :
	docker ps | tail -n +2 | awk '/${NAME_PREFIX}/ {print $$1}' > ${DOCKER_IDS}
	
logs : ids
	for id in $(shell cat ${DOCKER_IDS}); do docker logs "$${id}"; done

down :
	docker-compose down
	docker ps | tail -n +2 | awk '/${NAME_PREFIX}/ {print $$1}' | xargs docker kill

clean : down
	- docker images | tail -n +2 | awk '/${NAME_PREFIX}/ {print $$3}' | xargs docker rmi
	find . -type f -name "*.tmp" -exec rm {} + ;

hardclean : clean
	docker ps | tail -n +2 | awk '/${NAME_PREFIX}/ {print $$1}' | xargs docker kill -f
	docker images | tail -n +2 | awk '/${NAME_PREFIX}/ {print $$3}' | xargs docker rmi -f


build : down clean
	docker-compose build

up :
	docker-compose up -d

hardup : build up
	@ echo

stop :
	docker-compose stop

restart :
	docker-compose restart

test :
	./tests.sh

stats :
	curl 'http://localhost:8080/stats'

wait :
	sleep 4

hardtest : up restart wait test

proxy_id :
	@ docker ps | tail -n +2 | awk '/${PROXY_NAME}/ {print $$1}' | ${COPY}
	@ ${PASTE}

log : proxy_id
	docker logs $(shell ${PASTE})

logf : proxy_id
	docker logs -f $(shell ${PASTE})

ssh : proxy_id
	docker exec -it $(shell ${PASTE}) /bin/bash

py : proxy_id
	docker exec -it $(shell ${PASTE}) /usr/bin/env bpython

sql : proxy_id
	docker exec -it $(shell ${PASTE}) /usr/bin/env sqlite3 /var/tmp/proxy.sqlite

tail : proxy_id
	docker exec -it $(shell ${PASTE}) /usr/bin/env sqlite3 /var/tmp/proxy.sqlite 'SELECT * FROM proxy_log;'
