package main

import (
	"log"

	"github.com/BurntSushi/xgb"
	"github.com/BurntSushi/xgb/randr"
	"github.com/BurntSushi/xgb/xproto"
)

func main() {
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
			log.Printf("Error processing event: %s", xerr)
			continue
		}
		log.Printf("Event: %s\n", ev)
		if scn, ok := ev.(randr.ScreenChangeNotifyEvent); ok {
			width, height := scn.Width, scn.Height
			log.Printf("New size: %dx%d\n", width, height)
			if err := updateScreens(X, rootWindow, uint32(scn.Mwidth), uint32(scn.Mheight)); err != nil {
				log.Printf("Error updating screens: %v\n", err)
			}
			continue
		}
	}
}

func updateScreens(X *xgb.Conn, w xproto.Window, mmWidth, mmHeight uint32) error {
	if res, err := randr.GetScreenResources(X, w).Reply(); err != nil {
		return err
	} else {
		log.Printf("Resources: %+v\n", res)
		if szRange, err := randr.GetScreenSizeRange(X, w).Reply(); err != nil {
			return err
		} else {
			log.Printf("Size range: %+v\n", szRange)
		}
		for _, output := range res.Outputs {
			// TODO: parallelize
			info, err := randr.GetOutputInfo(X, output, 0).Reply()
			if err != nil {
				return err
			}
			name := string(info.Name)
			log.Printf("Output info: %s: %+v\n", name, info)
			if info.Connection != randr.ConnectionConnected {
				log.Printf("%s disconnected", name)
				continue
			}
			bestMode := info.Modes[0]
			var bestWidth uint16
			var bestHeight uint16
			for _, mode := range res.Modes {
				if randr.Mode(mode.Id) != bestMode {
					continue
				}
				log.Printf("Desired mode: %dx%d\n", mode.Width, mode.Height)
				bestWidth = mode.Width
				bestHeight = mode.Height
			}
			crtcInfo, err := randr.GetCrtcInfo(X, info.Crtc, res.ConfigTimestamp).Reply()
			if err != nil {
				return err
			}
			log.Printf("CRTC: %+v", crtcInfo)
			if crtcInfo.Width == bestWidth && crtcInfo.Height == bestHeight {
				log.Printf("CRTC Configured, no update needed.")
				continue
			}
			log.Printf("Setting dims: %vx%v, %vx%v", bestWidth, bestHeight, mmWidth, mmHeight)
			setScreen := func() error {
				if err := randr.SetScreenSizeChecked(X, w, bestWidth, bestHeight, mmWidth, mmHeight).Check(); err != nil {
					log.Printf("Error setting screen size: %v", err)
					return err
				}
				return nil
			}
			setCrtc := func() error {
				_, err = randr.SetCrtcConfig(X, info.Crtc, crtcInfo.Timestamp, res.ConfigTimestamp, crtcInfo.X, crtcInfo.Y, bestMode, crtcInfo.Rotation, crtcInfo.Outputs).Reply()
				if err != nil {
					log.Printf("Error configuring CRTC: %v", err)
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
