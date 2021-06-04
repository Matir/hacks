## What

This is a simple container to run a React-based SPA.

## Running

```
docker run -p 8123:8080 --mount type=bind,src=$(pwd)/demo,dst=/app/src,readonly --rm -d matir/react-spa
```
