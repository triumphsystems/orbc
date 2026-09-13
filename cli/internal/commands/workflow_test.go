package commands

import (
	"encoding/json"
	"strings"
	"testing"
)

func TestCommand_Workflow(t *testing.T) {
	t.Run("table output contains pipeline stages", func(t *testing.T) {
		out, err := executeCommand("workflow")
		if err != nil {
			t.Fatalf("workflow command failed: %v", err)
		}

		if !strings.Contains(out, "Orbit Pipeline Studio Topology") {
			t.Errorf("expected workflow header in output: %s", out)
		}
		if !strings.Contains(out, "Schedule Trigger") || !strings.Contains(out, "S3 Object Storage") {
			t.Errorf("expected adapters in output: %s", out)
		}
	})

	t.Run("json output contains valid adapter list", func(t *testing.T) {
		out, err := executeCommand("workflow", "--json")
		if err != nil {
			t.Fatalf("workflow --json failed: %v", err)
		}

		var adapters []AdapterInfo
		if err := json.Unmarshal([]byte(out), &adapters); err != nil {
			t.Fatalf("invalid json from workflow: %v, raw: %s", err, out)
		}

		if len(adapters) == 0 {
			t.Fatalf("expected at least 1 adapter, got %d", len(adapters))
		}
		if adapters[0].Adapter != "Schedule Trigger" {
			t.Errorf("unexpected first adapter: %s", adapters[0].Adapter)
		}
	})
}
