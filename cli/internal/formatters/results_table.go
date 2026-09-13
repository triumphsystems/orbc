package formatters

import (
	"fmt"
	"os"
	"sort"

	"github.com/leoemaxie/orbit/cli/pkg/orbc"
	"github.com/olekukonko/tablewriter"
)

// RenderRunsTable renders a list of runs into an ASCII table.
func RenderRunsTable(runs []orbc.RunOut, noTrunc bool) {
	table := tablewriter.NewWriter(os.Stdout)
	table.SetHeader([]string{"RUN ID", "STATUS", "EXTRACTED", "VALIDATED", "CONDITION", "STARTED AT"})
	table.SetBorder(true)
	table.SetHeaderColor(
		tablewriter.Colors{tablewriter.Bold, tablewriter.FgCyanColor},
		tablewriter.Colors{tablewriter.Bold, tablewriter.FgCyanColor},
		tablewriter.Colors{tablewriter.Bold, tablewriter.FgCyanColor},
		tablewriter.Colors{tablewriter.Bold, tablewriter.FgCyanColor},
		tablewriter.Colors{tablewriter.Bold, tablewriter.FgCyanColor},
		tablewriter.Colors{tablewriter.Bold, tablewriter.FgCyanColor},
	)

	for _, r := range runs {
		cond := "-"
		if r.ConditionMatched != nil {
			if *r.ConditionMatched {
				cond = "MATCHED"
			} else {
				cond = "NO"
			}
		}
		idStr := r.ID
		if !noTrunc && len(idStr) > 8 {
			idStr = idStr[:8]
		}
		table.Append([]string{
			idStr,
			r.Status,
			fmt.Sprintf("%d", r.ExtractedCount),
			fmt.Sprintf("%d", r.ValidatedCount),
			cond,
			r.StartedAt,
		})
	}
	table.Render()
}

// RenderResultsTable dynamically renders arbitrary extracted records into an aligned table.
func RenderResultsTable(results []orbc.ResultOut) {
	if len(results) == 0 {
		fmt.Println("No records extracted.")
		return
	}

	keySet := make(map[string]bool)
	for _, res := range results {
		for k := range res.Data {
			keySet[k] = true
		}
	}

	keys := make([]string, 0, len(keySet))
	for k := range keySet {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	headers := append([]string{"VALID"}, keys...)
	headers = append(headers, "URL")

	table := tablewriter.NewWriter(os.Stdout)
	table.SetHeader(headers)
	table.SetBorder(true)
	table.SetAutoWrapText(true)

	for _, res := range results {
		validStr := "✓"
		if !res.Valid {
			validStr = "✖"
		}
		row := []string{validStr}
		for _, k := range keys {
			val := res.Data[k]
			if val == nil {
				row = append(row, "-")
			} else {
				row = append(row, fmt.Sprintf("%v", val))
			}
		}
		urlStr := res.URL
		if len(urlStr) > 40 {
			urlStr = urlStr[:37] + "..."
		}
		row = append(row, urlStr)
		table.Append(row)
	}
	table.Render()
}
