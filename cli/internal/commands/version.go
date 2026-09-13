package commands

import (
	"fmt"

	"github.com/spf13/cobra"
	"github.com/leoemaxie/orbit/cli/internal/formatters"
	"github.com/leoemaxie/orbit/cli/internal/ui"
)

const CLIVersion = "0.2.0"

var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "Print the version of orbc CLI and Orbit Server",
	RunE: func(cmd *cobra.Command, args []string) error {
		health, err := client.Health()

		serverVer := "offline / unreachable"
		if err == nil {
			serverVer = health.Version
		}

		if jsonFlag {
			return formatters.PrintJSON(map[string]interface{}{
				"cli_version":    CLIVersion,
				"server_version": serverVer,
				"server_status":  err == nil,
			})
		}

		ui.PrintBanner()
		fmt.Printf("orbc CLI Version     : %s\n", ui.Cyan(CLIVersion))
		if err == nil {
			fmt.Printf("Orbit Server Version : %s (%s)\n", ui.Green(serverVer), health.Environment)
		} else {
			fmt.Printf("Orbit Server Version : %s\n", ui.Red(serverVer))
		}
		return nil
	},
}
