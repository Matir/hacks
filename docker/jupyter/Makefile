build:
	docker build -t matir/lab .

buildx:
	docker buildx build --push --platform=linux/arm64,linux/amd64 -t matir/lab .

buildx-amd64:
	docker buildx build --push --platform=linux/amd64 -t matir/lab .

run:
	docker run -v jupyter:/home/jovian/lab -p 9999:9999 -e JUPYTER_PASSWORD=secretpass12 matir/lab

run-covid:
	docker run -v covidjupyter:/home/jovian/lab -v /mnt/covid/COVID-19:/home/jovian/lab/COVID-19 -p 9998:9999 -e JUPYTER_PASSWORD=secretpass12 matir/lab
