package commands

import (
	"fmt"

	"github.com/spf13/cobra"
	"github.com/leoemaxie/orbit/cli/internal/formatters"
	"github.com/leoemaxie/orbit/cli/internal/ui"
)

var streamFlag bool

func init() {
	runCmd.Flags().BoolVarP(&streamFlag, "stream", "s", false, "Stream live execution telemetry and logs via SSE")
}

var runCmd = &cobra.Command{
	Use:   "run <automation-id>",
	Short: "Execute an automation on-demand",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		automationID := args[0]
		return executeRun(automationID)
	},
}

func executeRun(automationID string) error {
	if streamFlag {
		run, err := client.RunAutomation(automationID)
		if err != nil {
			ui.Error("Failed to trigger run: %v", err)
			return err
		}
		return executeWatch(run.ID)
	}

	if jsonFlag {
		run, err := client.RunAutomation(automationID)
		if err != nil {
			return err
		}
		return formatters.PrintJSON(run)
	}

	spinner := ui.NewSpinner(fmt.Sprintf("Executing autonomous agent run for %s...", ui.ShortID(automationID)))
	spinner.Start()

	run, err := client.RunAutomation(automationID)
	spinner.Stop()

	if err != nil {
		ui.Error("Run failed: %v", err)
		return err
	}

	fmt.Printf("\nRun ID: %s %s\n", ui.Cyan(run.ID), ui.FormatStatus(run.Status))
	fmt.Printf("Started: %s\n\n", run.StartedAt)

	ui.Info("Execution Audit Trail:")
	ui.Success("[1. Discover]  %d source URLs discovered", len(run.SourcesFound))
	ui.Success("[2. Retrieve]  %d/%d pages retrieved", len(run.PagesRetrieved), len(run.SourcesFound))
	ui.Success("[3. Extract]   %d records extracted", run.ExtractedCount)
	ui.Success("[4. Validate]  %d passed schema validation", run.ValidatedCount)

	if run.ConditionMatched != nil {
		if *run.ConditionMatched {
			ui.Success("[5. Condition] Condition MATCHED: %s", *run.ConditionMessage)
		} else {
			ui.Info("[5. Condition] Condition evaluated: %s", *run.ConditionMessage)
		}
	}

	if run.Error != nil && *run.Error != "" {
		ui.Error("Verification error: %s", *run.Error)
	} else {
		ui.Success("[6. Verify]    Run verified successfully")
	}

	fmt.Println()
	if len(run.Results) > 0 {
		fmt.Printf("%s\n", ui.Cyan("Extracted Data Records:"))
		formatters.RenderResultsTable(run.Results)
	}

	return nil
}
