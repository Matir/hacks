# Docker Proxy

**NOTE:** This is alpha software, do not rely on it for anything!

This is a tool for proxying docker API requests and responses. With this tool,
we can do the following:

- View/log request/response structures
- Deny requests based on a configurable policy

It is intended to be forwarded into a container or other environment that would
not otherwise have access to Docker.
