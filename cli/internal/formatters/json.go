package formatters

import (
	"encoding/json"
	"fmt"
	"os"
)

// PrintJSON prints any Go object as indented, syntax-safe JSON.
func PrintJSON(v interface{}) error {
	b, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return err
	}
	fmt.Println(string(b))
	return nil
}

// PrintJSONToWriter outputs JSON to a specific writer.
func PrintJSONToWriter(w *os.File, v interface{}) error {
	enc := json.NewEncoder(w)
	enc.SetIndent("", "  ")
	return enc.Encode(v)
}
