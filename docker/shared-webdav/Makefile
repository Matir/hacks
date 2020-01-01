up: webdav.env
	docker-compose up -d

webdav.env:
	echo -n UID= > $@
	id -u >> $@
	echo -n GID= >> $@
	id -g >> $@

docker:
	docker build -t matir/webdav .

