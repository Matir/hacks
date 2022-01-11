package main

import (
	"context"
	"fmt"

	"systemoverlord.com/acmedns"
)

func main() {
	provider, err := acmedns.NewGCPDNSProvider(context.Background())
	if err != nil {
		panic(err)
	}
	cases := []string{
		"test1.rtgcptest.net.",
		"test2.rtgcptest.net.",
	}
	for _, c := range cases {
		resp, err := provider.GetTXT(c)
		fmt.Printf("%v: %v, %v\n", c, resp, err)
	}
	resp, err := provider.SetTXT("test2.rtgcptest.net.", "foo bar baz")
	fmt.Printf("Create: %v, %v\n", resp, err)
	resp, err = provider.SetTXT("test2.rtgcptest.net.", "foo bar baz bang")
	fmt.Printf("Update: %v, %v\n", resp, err)
	err = provider.DeleteTXT("test2.rtgcptest.net.")
	fmt.Printf("Delete: %v\n", err)
}
