package commands

import (
	"fmt"

	"github.com/spf13/cobra"
	"github.com/leoemaxie/orbit/cli/internal/formatters"
	"github.com/leoemaxie/orbit/cli/internal/ui"
)

var showCmd = &cobra.Command{
	Use:   "show <run-id>",
	Short: "Inspect execution details and verification audit trail for a run",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		targetID := args[0]
		run, err := client.GetRun(targetID)
		if err != nil {
			// Fallback: check if targetID is an automation ID
			runs, listErr := client.ListRuns(targetID)
			if listErr == nil && len(runs) > 0 {
				run = &runs[0]
				ui.Info("Showing latest run %s for automation %s\n", ui.Cyan(ui.ShortID(run.ID)), ui.Cyan(ui.ShortID(targetID)))
			} else {
				ui.Error("Failed to fetch run: %v", err)
				return err
			}
		}

		if jsonFlag {
			return formatters.PrintJSON(run)
		}

		ui.PrintBanner()
		fmt.Printf("Run Details: %s %s\n", ui.Cyan(run.ID), ui.FormatStatus(run.Status))
		ui.Info("Automation ID : %s", run.AutomationID)
		ui.Info("Started At    : %s", run.StartedAt)
		if run.FinishedAt != nil {
			ui.Info("Finished At   : %s", *run.FinishedAt)
		}
		ui.Info("Records Stats : %d extracted, %d valid", run.ExtractedCount, run.ValidatedCount)

		if run.ConditionMatched != nil {
			ui.Info("Condition     : %s", *run.ConditionMessage)
		}

		fmt.Println()
		ui.Info("Discovered Sources (%d):", len(run.SourcesFound))
		for i, s := range run.SourcesFound {
			fmt.Printf("    [%d] %s\n", i+1, s)
		}

		fmt.Println()
		ui.Info("Retrieved Pages (%d):", len(run.PagesRetrieved))
		for i, p := range run.PagesRetrieved {
			fmt.Printf("    [%d] %s\n", i+1, p)
		}

		if len(run.ReasoningLog) > 0 {
			fmt.Println()
			ui.Warning("Agent Reasoning & Self-Correction Trail:")
			for _, item := range run.ReasoningLog {
				fmt.Printf("    %v\n", item)
			}
		}

		if len(run.Results) > 0 {
			fmt.Println()
			ui.Info("Extracted Data:")
			formatters.RenderResultsTable(run.Results)
		}

		return nil
	},
}
