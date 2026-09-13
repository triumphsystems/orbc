package commands

import (
	"github.com/spf13/cobra"
	"github.com/leoemaxie/orbit/cli/internal/formatters"
	"github.com/leoemaxie/orbit/cli/internal/ui"
)

var noTruncFlag bool

var listCmd = &cobra.Command{
	Use:     "list",
	Aliases: []string{"ls"},
	Short:   "List all registered automations",
	RunE: func(cmd *cobra.Command, args []string) error {
		list, err := client.ListAutomations()
		if err != nil {
			ui.Error("Failed to list automations: %v", err)
			return err
		}

		if jsonFlag {
			return formatters.PrintJSON(list)
		}

		ui.PrintBanner()
		formatters.RenderAutomationsTable(list.Items, noTruncFlag)
		return nil
	},
}

func init() {
	listCmd.Flags().BoolVar(&noTruncFlag, "no-trunc", false, "Display full untruncated identifiers")
}
