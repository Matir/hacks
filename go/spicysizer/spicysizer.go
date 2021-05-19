package main

import (
	"flag"
	"io/ioutil"
	"log"
	"os"

	"github.com/BurntSushi/xgb"
	"github.com/BurntSushi/xgb/randr"
	"github.com/BurntSushi/xgb/xproto"
)

var infoLog = log.New(os.Stderr, "", log.LstdFlags)

func main() {
	verboseFlag := flag.Bool("-v", false, "Verbose output.")
	flag.Parse()

	if !*verboseFlag {
		infoLog.SetOutput(ioutil.Discard)
	}

	X, err := xgb.NewConn()
	if err != nil {
		log.Fatal(err)
	}

	if err := randr.Init(X); err != nil {
		log.Fatal(err)
	}

	rootWindow := xproto.Setup(X).DefaultScreen(X).Root

	notifications := uint16(randr.NotifyMaskScreenChange |
		randr.NotifyMaskCrtcChange |
		randr.NotifyMaskOutputChange |
		randr.NotifyMaskOutputProperty)
	if err := randr.SelectInputChecked(X, rootWindow, notifications).Check(); err != nil {
		log.Fatal(err)
	}

	for {
		ev, xerr := X.WaitForEvent()
		if xerr != nil {
			infoLog.Printf("Error processing event: %s", xerr)
			continue
		}
		infoLog.Printf("Event: %s\n", ev)
		if scn, ok := ev.(randr.ScreenChangeNotifyEvent); ok {
			width, height := scn.Width, scn.Height
			infoLog.Printf("New size: %dx%d\n", width, height)
			if err := updateScreens(X, rootWindow, uint32(scn.Mwidth), uint32(scn.Mheight)); err != nil {
				infoLog.Printf("Error updating screens: %v\n", err)
			}
			continue
		}
	}
}

func updateScreens(X *xgb.Conn, w xproto.Window, mmWidth, mmHeight uint32) error {
	if res, err := randr.GetScreenResources(X, w).Reply(); err != nil {
		return err
	} else {
		infoLog.Printf("Resources: %+v\n", res)
		if szRange, err := randr.GetScreenSizeRange(X, w).Reply(); err != nil {
			return err
		} else {
			infoLog.Printf("Size range: %+v\n", szRange)
		}
		for _, output := range res.Outputs {
			// TODO: parallelize
			info, err := randr.GetOutputInfo(X, output, 0).Reply()
			if err != nil {
				return err
			}
			name := string(info.Name)
			infoLog.Printf("Output info: %s: %+v\n", name, info)
			if info.Connection != randr.ConnectionConnected {
				infoLog.Printf("%s disconnected", name)
				continue
			}
			bestMode := info.Modes[0]
			var bestWidth uint16
			var bestHeight uint16
			for _, mode := range res.Modes {
				if randr.Mode(mode.Id) != bestMode {
					continue
				}
				infoLog.Printf("Desired mode: %dx%d\n", mode.Width, mode.Height)
				bestWidth = mode.Width
				bestHeight = mode.Height
			}
			crtcInfo, err := randr.GetCrtcInfo(X, info.Crtc, res.ConfigTimestamp).Reply()
			if err != nil {
				return err
			}
			infoLog.Printf("CRTC: %+v", crtcInfo)
			if crtcInfo.Width == bestWidth && crtcInfo.Height == bestHeight {
				infoLog.Printf("CRTC Configured, no update needed.")
				continue
			}
			infoLog.Printf("Setting dims: %vx%v, %vx%v", bestWidth, bestHeight, mmWidth, mmHeight)
			setScreen := func() error {
				if err := randr.SetScreenSizeChecked(X, w, bestWidth, bestHeight, mmWidth, mmHeight).Check(); err != nil {
					infoLog.Printf("Error setting screen size: %v", err)
					return err
				}
				return nil
			}
			setCrtc := func() error {
				_, err = randr.SetCrtcConfig(X, info.Crtc, crtcInfo.Timestamp, res.ConfigTimestamp, crtcInfo.X, crtcInfo.Y, bestMode, crtcInfo.Rotation, crtcInfo.Outputs).Reply()
				if err != nil {
					infoLog.Printf("Error configuring CRTC: %v", err)
					return err
				}
				return nil
			}
			if bestWidth < crtcInfo.Width || bestHeight < crtcInfo.Height {
				// Getting smaller
				return callOrFail(setCrtc, setScreen)
			} else {
				return callOrFail(setScreen, setCrtc)
			}
		}
	}
	return nil
}

func callOrFail(funcs ...func() error) error {
	for _, f := range funcs {
		if err := f(); err != nil {
			return err
		}
	}
	return nil
}
