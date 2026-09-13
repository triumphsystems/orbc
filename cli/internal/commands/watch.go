package commands

import (
	"fmt"

	"github.com/leoemaxie/orbit/cli/internal/formatters"
	"github.com/leoemaxie/orbit/cli/internal/ui"
	"github.com/leoemaxie/orbit/cli/pkg/orbc"
	"github.com/spf13/cobra"
)

var watchCmd = &cobra.Command{
	Use:   "watch <run-id>",
	Short: "Stream live telemetry and logs for an autonomous run in real time",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		runID := args[0]
		return executeWatch(runID)
	},
}

func executeWatch(targetID string) error {
	resolvedRunID := targetID

	// If targetID is an automation ID, resolve to its latest run
	runs, err := client.ListRuns(targetID)
	if err == nil && len(runs) > 0 {
		resolvedRunID = runs[0].ID
		ui.Info("Watching latest run %s for automation %s", ui.Cyan(ui.ShortID(resolvedRunID)), ui.Cyan(ui.ShortID(targetID)))
	} else if err == nil && len(runs) == 0 {
		ui.Warning("Automation %s has no execution runs yet. Trigger one with: orbc run %s", ui.Cyan(ui.ShortID(targetID)), targetID)
		return fmt.Errorf("no runs found for automation %s", targetID)
	}

	ui.Header(fmt.Sprintf("🛰️ Orbit Stream — Tailing Run %s", ui.ShortID(resolvedRunID)))
	lastStatus := ""

	streamErr := client.StreamRunTelemetry(resolvedRunID, func(event string, run *orbc.RunOut) error {
		if run.Status != lastStatus {
			lastStatus = run.Status
			switch run.Status {
			case "discovering":
				ui.Info("[Stage: Discover] Finding web sources and search queries...")
			case "retrieving":
				ui.Info("[Stage: Retrieve] Resilient proxy fetch across %d source(s)...", len(run.SourcesFound))
			case "extracting":
				ui.Info("[Stage: Extract] LLM entity and schema extraction active...")
			case "validating":
				ui.Info("[Stage: Validate] Anomaly detection and statistical validation...")
			case "storing":
				ui.Info("[Stage: Store] Writing results and generating export sinks...")
			case "verified":
				ui.Success("[Stage: Verified] Run verified successfully with %d valid record(s).", run.ValidatedCount)
			case "failed":
				ui.Error("[Stage: Failed] Execution failed: %s", formatError(run.Error))
			}
		}

		if event == "complete" {
			if len(run.Results) > 0 {
				fmt.Println()
				fmt.Printf("%s\n", ui.Cyan("Extracted Data Records:"))
				formatters.RenderResultsTable(run.Results)
			}
		}
		return nil
	})

	if streamErr != nil {
		ui.Error("Stream error: %v", streamErr)
	}

	return streamErr
}

func formatError(err *string) string {
	if err == nil || *err == "" {
		return "Unknown error"
	}
	return *err
}
