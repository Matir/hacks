package main

import (
	"context"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"strings"

	"google.golang.org/api/idtoken"
	"systemoverlord.com/acmedns"
)

const (
	ACMEPROXY_ENDPOINT_VAR = "ACMEPROXY_ENDPOINT"
	AUDIENCE_VAR           = "AUTH_AUDIENCE"
	CMD_UPDATE             = "update"
	CMD_DELETE             = "delete"
	CMD_GET                = "get"
	CERTBOT_DOMAIN         = "CERTBOT_DOMAIN"
	CERTBOT_VALIDATION     = "CERTBOT_VALIDATION"
)

type ACMEProxyClient struct {
	endpoint string
	client   *http.Client
}

func main() {
	endpointFlag := flag.String("endpoint", os.Getenv(ACMEPROXY_ENDPOINT_VAR), "Endpoint to update the DNS records.")
	audienceFlag := flag.String("auth-audience", os.Getenv(AUDIENCE_VAR), "Auth audience for authentication.")
	domainFlag := flag.String("domain", os.Getenv(CERTBOT_DOMAIN), "Domain to operate on.")
	tokenFlag := flag.String("token", os.Getenv(CERTBOT_VALIDATION), "Token to use for ACME.")
	flag.Parse()

	if *endpointFlag == "" {
		log.Printf("Must specify an endpoint, either with environment variable %s or flag -endpoint.", ACMEPROXY_ENDPOINT_VAR)
		os.Exit(1)
	}
	audience := firstString(*audienceFlag, *endpointFlag)
	if *domainFlag == "" {
		log.Printf("Must specify domain to operate on!")
		os.Exit(1)
	}

	ctx := context.Background()
	idclient, err := idtoken.NewClient(ctx, strings.TrimSuffix(audience, "/"))
	if err != nil {
		log.Printf("Error building client: %v", err)
		os.Exit(1)
	}

	command := ""
	if flag.NArg() > 0 {
		command = flag.Args()[0]
	}
	if command == "" {
		command = findCertbotCommand()
	}

	client := NewACMEProxyClient(*endpointFlag, idclient)
	data := ""
	switch command {
	case CMD_GET:
		data, err = client.GetTXT(*domainFlag)
	case CMD_UPDATE:
		data, err = client.SetTXT(*domainFlag, *tokenFlag)
	case CMD_DELETE:
		err = client.DeleteTXT(*domainFlag)
	default:
		log.Printf("Command %s is not known!", command)
		os.Exit(2)
	}
	if err != nil {
		log.Printf("Error executing: %v", err)
		os.Exit(1)
	}
	fmt.Printf("%s\n", data)
}

func firstString(opts ...string) string {
	for _, o := range opts {
		if o != "" {
			return o
		}
	}
	return ""
}

func NewACMEProxyClient(endpoint string, client *http.Client) *ACMEProxyClient {
	if !strings.HasSuffix(endpoint, "/") {
		endpoint = endpoint + "/"
	}
	return &ACMEProxyClient{
		endpoint: endpoint,
		client:   client,
	}
}

func (c *ACMEProxyClient) GetTXT(name string) (string, error) {
	resp, err := c.client.Get(c.endpointForDomain(name))
	if err != nil {
		return "", err
	}
	if resp.StatusCode == http.StatusOK {
		return readResponseBody(resp)
	}
	return "", fmt.Errorf("HTTP Error: %d %v", resp.StatusCode, resp.Status)
}

func (c *ACMEProxyClient) SetTXT(name, value string) (string, error) {
	v := url.Values{}
	v.Set(acmedns.TokenValueVar, value)
	resp, err := c.client.PostForm(c.endpointForDomain(name), v)
	if err != nil {
		return "", err
	}
	if resp.StatusCode == http.StatusOK {
		return readResponseBody(resp)
	}
	return "", fmt.Errorf("HTTP Error: %d %v", resp.StatusCode, resp.Status)
}

func (c *ACMEProxyClient) DeleteTXT(name string) error {
	req, err := http.NewRequest(http.MethodDelete, c.endpointForDomain(name), nil)
	if err != nil {
		return err
	}
	resp, err := c.client.Do(req)
	if err != nil {
		return err
	}
	if resp.StatusCode == http.StatusOK {
		_, err := readResponseBody(resp)
		return err
	}
	return fmt.Errorf("HTTP Error: %d %v", resp.StatusCode, resp.Status)
}

func (c *ACMEProxyClient) endpointForDomain(name string) string {
	return c.endpoint + name
}

func readResponseBody(r *http.Response) (string, error) {
	buf := new(strings.Builder)
	_, err := io.Copy(buf, r.Body)
	if err != nil {
		return "", err
	}
	return buf.String(), nil
}

func findCertbotCommand() string {
	hasEnv := func(key string) bool {
		return os.Getenv(key) != ""
	}
	if !hasEnv(CERTBOT_DOMAIN) || !hasEnv(CERTBOT_VALIDATION) {
		return ""
	}
	if hasEnv("CERTBOT_AUTH_OUTPUT") {
		return CMD_DELETE
	}
	return CMD_UPDATE
}
