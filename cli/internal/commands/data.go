package commands

import (
	"fmt"

	"github.com/leoemaxie/orbit/cli/internal/formatters"
	"github.com/leoemaxie/orbit/cli/internal/ui"
	"github.com/leoemaxie/orbit/cli/pkg/orbc"
	"github.com/spf13/cobra"
)

var (
	validOnlyFlag bool
	followFlag    bool
)

var dataCmd = &cobra.Command{
	Use:   "data <run-id>",
	Short: "View and export extracted records for a run",
	Example: `  orbc data 8f2c34a1
  orbc data 8f2c34a1 --follow
  orbc data 8f2c34a1 --format csv > results.csv
  orbc data 8f2c34a1 --format json | jq .`,
	Args: cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		targetID := args[0]
		resolvedRunID := targetID

		run, err := client.GetRun(targetID)
		if err != nil {
			// Fallback: check if targetID is an automation ID
			runs, listErr := client.ListRuns(targetID)
			if listErr == nil && len(runs) > 0 {
				run = &runs[0]
				resolvedRunID = run.ID
			} else {
				ui.Error("Failed to fetch data for run: %v", err)
				return err
			}
		}

		if followFlag {
			ui.Header(fmt.Sprintf("🛰️ Orbit Data Stream — Tailing records for Run %s", ui.ShortID(resolvedRunID)))
			return client.StreamRunResults(resolvedRunID, func(record *orbc.ResultOut) error {
				if validOnlyFlag && !record.Valid {
					return nil
				}
				if formatFlag == "json" {
					return formatters.PrintJSON(record)
				}
				statusIcon := ui.Green("✓")
				if !record.Valid {
					statusIcon = ui.Yellow("⚠")
				}
				fmt.Printf("[%s] ID: %s | URL: %s\n", statusIcon, ui.ShortID(record.ID), record.URL)
				return nil
			})
		}

		results := run.Results
		if validOnlyFlag {
			filtered := make([]orbc.ResultOut, 0)
			for _, r := range results {
				if r.Valid {
					filtered = append(filtered, r)
				}
			}
			results = filtered
		}

		switch formatFlag {
		case "json":
			return formatters.PrintJSON(results)
		case "csv":
			return formatters.ExportResultsCSV(results)
		case "table":
			formatters.RenderResultsTable(results)
			return nil
		default:
			return fmt.Errorf("unsupported format '%s', choose from table, json, csv", formatFlag)
		}
	},
}

func init() {
	dataCmd.Flags().BoolVar(&validOnlyFlag, "valid-only", false, "Show only records that passed validation")
	dataCmd.Flags().BoolVarP(&followFlag, "follow", "w", false, "Follow / stream incoming data records in real time")
}
