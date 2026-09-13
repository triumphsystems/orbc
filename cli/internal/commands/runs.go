package commands

import (
	"github.com/spf13/cobra"
	"github.com/leoemaxie/orbit/cli/internal/formatters"
	"github.com/leoemaxie/orbit/cli/internal/ui"
)

var runsCmd = &cobra.Command{
	Use:   "runs <automation-id>",
	Short: "View execution history for an automation",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		automationID := args[0]
		runs, err := client.ListRuns(automationID)
		if err != nil {
			ui.Error("Failed to list runs: %v", err)
			return err
		}

		if jsonFlag {
			return formatters.PrintJSON(runs)
		}

		ui.PrintBanner()
		formatters.RenderRunsTable(runs, noTruncFlag)
		return nil
	},
}

func init() {
	runsCmd.Flags().BoolVar(&noTruncFlag, "no-trunc", false, "Display full untruncated identifiers")
}
