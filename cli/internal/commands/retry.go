package commands

import (
	"fmt"

	"github.com/spf13/cobra"
	"github.com/leoemaxie/orbit/cli/internal/formatters"
	"github.com/leoemaxie/orbit/cli/internal/ui"
)

var retryCmd = &cobra.Command{
	Use:     "retry <run-id>",
	Aliases: []string{"rerun"},
	Short:   "Resume and retry an existing run from its last checkpoint",
	Args:    cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		runID := args[0]
		return executeRetry(runID)
	},
}

func executeRetry(runID string) error {
	if jsonFlag {
		run, err := client.RetryRun(runID)
		if err != nil {
			return err
		}
		return formatters.PrintJSON(run)
	}

	spinner := ui.NewSpinner(fmt.Sprintf("Resuming run %s from last checkpoint...", ui.ShortID(runID)))
	spinner.Start()

	run, err := client.RetryRun(runID)
	spinner.Stop()

	if err != nil {
		ui.Error("Retry failed: %v", err)
		return err
	}

	ui.Success("Run resumed successfully!")
	fmt.Printf("\nRun ID  : %s %s\n", ui.Cyan(run.ID), ui.FormatStatus(run.Status))
	fmt.Printf("Started : %s\n\n", run.StartedAt)

	ui.Info("Stream live telemetry and inspect results:")
	fmt.Printf("  orbc show %s\n", run.ID)
	fmt.Printf("  orbc data %s\n", run.ID)

	return nil
}
