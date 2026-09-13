package formatters

import (
	"os"

	"github.com/leoemaxie/orbit/cli/pkg/orbc"
	"github.com/olekukonko/tablewriter"
)

// RenderTable renders a generic headers and rows matrix into an aligned ASCII table.
func RenderTable(headers []string, rows [][]string) {
	table := tablewriter.NewWriter(os.Stdout)
	table.SetHeader(headers)
	table.SetBorder(true)
	table.SetAutoWrapText(true)
	for _, row := range rows {
		table.Append(row)
	}
	table.Render()
}

// RenderAutomationsTable renders a list of automations into an ASCII table.
func RenderAutomationsTable(automations []orbc.AutomationOut, noTrunc bool) {
	table := tablewriter.NewWriter(os.Stdout)
	table.SetHeader([]string{"ID", "OBJECTIVE", "DOMAIN", "FREQUENCY", "ACTIVE", "NEXT RUN"})
	table.SetBorder(true)
	table.SetAutoWrapText(true)
	table.SetHeaderColor(
		tablewriter.Colors{tablewriter.Bold, tablewriter.FgCyanColor},
		tablewriter.Colors{tablewriter.Bold, tablewriter.FgCyanColor},
		tablewriter.Colors{tablewriter.Bold, tablewriter.FgCyanColor},
		tablewriter.Colors{tablewriter.Bold, tablewriter.FgCyanColor},
		tablewriter.Colors{tablewriter.Bold, tablewriter.FgCyanColor},
		tablewriter.Colors{tablewriter.Bold, tablewriter.FgCyanColor},
	)

	for _, a := range automations {
		nextRun := "-"
		if a.NextRunAt != nil {
			nextRun = *a.NextRunAt
		}
		activeStr := "Yes"
		if !a.Active {
			activeStr = "No"
		}
		idStr := a.ID
		if !noTrunc && len(idStr) > 8 {
			idStr = idStr[:8]
		}
		table.Append([]string{
			idStr,
			a.Plan.Objective,
			a.Plan.Domain,
			a.Plan.Frequency,
			activeStr,
			nextRun,
		})
	}
	table.Render()
}
