# Client

## Use with certbot

This client attempts to implement the `--manual-auth-hook` for certbot as
described in the certbot documentation
[here](https://eff-certbot.readthedocs.io/en/stable/using.html#hooks).

You must set `ACMEPROXY_ENDPOINT` to the Cloud Function endpoint for your AcmeDNS
configuration.

It additionally requires that the `GOOGLE_APPLICATION_CREDENTIALS` environment
variable is set *unless* running on GCP (i.e., in a GCE VM) where the ephemeral
credentials can be used.

This results in an invocation equivalent to:

```
GOOGLE_APPLICATION_CREDENTIALS=<path> \
  CERTBOT_DOMAIN=<domain> \
  CERTBOT_VALIDATION=<token> \
  ACMEPROXY_ENDPOINT=<url> \
  ./client
```
