package formatters

import (
	"encoding/csv"
	"fmt"
	"os"
	"sort"

	"github.com/leoemaxie/orbit/cli/pkg/orbc"
)

// ExportResultsCSV exports extracted records to standard CSV output.
func ExportResultsCSV(results []orbc.ResultOut) error {
	if len(results) == 0 {
		return nil
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

	headers := append([]string{"id", "valid", "url"}, keys...)

	writer := csv.NewWriter(os.Stdout)
	defer writer.Flush()

	if err := writer.Write(headers); err != nil {
		return err
	}

	for _, res := range results {
		validStr := "false"
		if res.Valid {
			validStr = "true"
		}
		row := []string{res.ID, validStr, res.URL}
		for _, k := range keys {
			val := res.Data[k]
			if val == nil {
				row = append(row, "")
			} else {
				row = append(row, fmt.Sprintf("%v", val))
			}
		}
		if err := writer.Write(row); err != nil {
			return err
		}
	}
	return nil
}
