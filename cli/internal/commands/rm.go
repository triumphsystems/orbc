package commands

import (
	"github.com/leoemaxie/orbit/cli/internal/formatters"
	"github.com/leoemaxie/orbit/cli/internal/ui"
	"github.com/spf13/cobra"
)

var rmCmd = &cobra.Command{
	Use:     "rm <automation-id>",
	Aliases: []string{"delete"},
	Short:   "Remove an automation and all associated runs",
	Args:    cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		automationID := args[0]
		return executeRm(automationID)
	},
}

func executeRm(automationID string) error {
	err := client.DeleteAutomation(automationID)
	if err != nil {
		if jsonFlag {
			return formatters.PrintJSON(map[string]any{
				"success": false,
				"error":   err.Error(),
			})
		}
		ui.Error("Failed to remove automation: %v", err)
		return err
	}

	if jsonFlag {
		return formatters.PrintJSON(map[string]any{
			"success":       true,
			"automation_id": automationID,
			"message":       "Automation removed successfully",
		})
	}

	ui.Success("Automation %s and all associated runs removed successfully.", ui.Cyan(automationID))
	return nil
}
