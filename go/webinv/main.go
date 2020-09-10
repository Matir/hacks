package main

func main() {
	svc, err := DefaultChromeDriver()
	if err != nil {
		panic(err)
	}
	defer svc.Stop()
	worker, err := NewWebWorker(svc, GetPort(), &ScriptEnumerator{})
	if err != nil {
		panic(err)
	}
	worker.RunPage("https://systemoverlord.com/")
}
