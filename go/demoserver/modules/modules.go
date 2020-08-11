package modules

import (
	"fmt"
	"net/http"
)

type ServerModule interface {
	http.Handler
	fmt.Stringer
	Prefix() string
	RandomPrefix() bool
}

var moduleRegistry map[string]ServerModule

func RegisterModule(sm ServerModule) {
	if moduleRegistry == nil {
		moduleRegistry = make(map[string]ServerModule)
	}
	moduleRegistry[sm.String()] = sm
}

func GetModuleByName(n string) ServerModule {
	if sm, ok := moduleRegistry[n]; ok {
		return sm
	}
	return nil
}
