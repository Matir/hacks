container:
	docker build . -t matir/cadav

run:
	docker run -p 9999:9999 --rm -v cadav_data:/data -v cadav_config:/config -v cadav_webdav:/webdav -e CADDY_DEBUG=debug cadav:latest
