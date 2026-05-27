package main

import (
	"context"
	"fmt"
	"os"
	"strings"

	"github.com/mdp/qrterminal/v3"
	"github.com/zelenin/go-tdlib/client"
	"golang.org/x/term"
)

type customAuthorizer struct {
	params *client.SetTdlibParametersRequest
	useQR  bool
}

func NewCustomAuthorizer(params *client.SetTdlibParametersRequest, useQR bool) *customAuthorizer {
	return &customAuthorizer{
		params: params,
		useQR:  useQR,
	}
}

func (a *customAuthorizer) Handle(c *client.Client, state client.AuthorizationState) error {
	switch state.AuthorizationStateConstructor() {
	case client.ConstructorAuthorizationStateWaitTdlibParameters:
		logDebug("AuthorizationState: WaitTdlibParameters")
		_, err := c.SetTdlibParameters(context.Background(), a.params)
		return err

	case client.ConstructorAuthorizationStateWaitPhoneNumber:
		logDebug("AuthorizationState: WaitPhoneNumber")
		if a.useQR {
			logDebug("Requesting QR code authentication...")
			_, err := c.RequestQrCodeAuthentication(context.Background(), &client.RequestQrCodeAuthenticationRequest{})
			return err
		}

		fmt.Print("Enter phone number: ")
		var phoneNumber string
		if _, err := fmt.Scanln(&phoneNumber); err != nil {
			return fmt.Errorf("read phone number: %w", err)
		}
		phoneNumber = strings.TrimSpace(phoneNumber)
		_, err := c.SetAuthenticationPhoneNumber(context.Background(), &client.SetAuthenticationPhoneNumberRequest{
			PhoneNumber: phoneNumber,
			Settings: &client.PhoneNumberAuthenticationSettings{
				AllowFlashCall:       false,
				IsCurrentPhoneNumber: false,
				AllowSmsRetrieverApi: false,
			},
		})
		return err

	case client.ConstructorAuthorizationStateWaitEmailAddress:
		return client.NotSupportedAuthorizationState(state)

	case client.ConstructorAuthorizationStateWaitEmailCode:
		return client.NotSupportedAuthorizationState(state)

	case client.ConstructorAuthorizationStateWaitCode:
		logDebug("AuthorizationState: WaitCode")
		fmt.Print("Enter verification code: ")
		var code string
		if _, err := fmt.Scanln(&code); err != nil {
			return fmt.Errorf("read code: %w", err)
		}
		code = strings.TrimSpace(code)
		_, err := c.CheckAuthenticationCode(context.Background(), &client.CheckAuthenticationCodeRequest{
			Code: code,
		})
		return err

	case client.ConstructorAuthorizationStateWaitOtherDeviceConfirmation:
		logDebug("AuthorizationState: WaitOtherDeviceConfirmation")
		if a.useQR {
			link := state.(*client.AuthorizationStateWaitOtherDeviceConfirmation).Link
			fmt.Println("\nScan this QR code with your Telegram app (Settings > Devices > Link Desktop Device):")
			qrterminal.GenerateHalfBlock(link, qrterminal.M, os.Stdout)
			fmt.Println() // extra newline
			return nil
		}
		return client.NotSupportedAuthorizationState(state)

	case client.ConstructorAuthorizationStateWaitRegistration:
		return client.NotSupportedAuthorizationState(state)

	case client.ConstructorAuthorizationStateWaitPassword:
		logDebug("AuthorizationState: WaitPassword")
		fmt.Print("Enter 2FA password: ")
		bytePassword, err := term.ReadPassword(int(os.Stdin.Fd()))
		if err != nil {
			return fmt.Errorf("read password: %w", err)
		}
		fmt.Println() // print newline after password input
		password := strings.TrimSpace(string(bytePassword))
		_, err = c.CheckAuthenticationPassword(context.Background(), &client.CheckAuthenticationPasswordRequest{
			Password: password,
		})
		return err

	case client.ConstructorAuthorizationStateReady:
		logDebug("AuthorizationState: Ready")
		return nil

	case client.ConstructorAuthorizationStateLoggingOut:
		return client.NotSupportedAuthorizationState(state)

	case client.ConstructorAuthorizationStateClosing:
		return nil

	case client.ConstructorAuthorizationStateClosed:
		return nil
	}

	return client.NotSupportedAuthorizationState(state)
}

func (a *customAuthorizer) Close() {}
