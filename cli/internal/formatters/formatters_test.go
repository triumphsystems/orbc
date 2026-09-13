package formatters

import (
	"bytes"
	"encoding/csv"
	"encoding/json"
	"io"
	"os"
	"strings"
	"testing"

	"github.com/leoemaxie/orbit/cli/pkg/orbc"
)

// captureOutput redirects os.Stdout during function execution and returns the captured output.
func captureOutput(f func()) string {
	r, w, err := os.Pipe()
	if err != nil {
		return ""
	}

	origStdout := os.Stdout
	os.Stdout = w

	outC := make(chan string)
	go func() {
		var buf bytes.Buffer
		_, _ = io.Copy(&buf, r)
		outC <- buf.String()
	}()

	f()

	_ = w.Close()
	os.Stdout = origStdout
	out := <-outC
	_ = r.Close()

	return out
}

func TestPrintJSON(t *testing.T) {
	t.Run("valid struct", func(t *testing.T) {
		data := map[string]interface{}{
			"id":     "auto-123",
			"active": true,
			"count":  42,
		}

		out := captureOutput(func() {
			err := PrintJSON(data)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
		})

		var parsed map[string]interface{}
		if err := json.Unmarshal([]byte(out), &parsed); err != nil {
			t.Fatalf("output is not valid JSON: %v, raw: %s", err, out)
		}

		if parsed["id"] != "auto-123" || parsed["active"] != true {
			t.Errorf("unexpected parsed content: %+v", parsed)
		}
	})

	t.Run("empty object", func(t *testing.T) {
		out := captureOutput(func() {
			_ = PrintJSON(map[string]string{})
		})
		if strings.TrimSpace(out) != "{}" {
			t.Errorf("expected empty json object, got %q", out)
		}
	})
}

func TestExportResultsCSV(t *testing.T) {
	t.Run("empty results", func(t *testing.T) {
		out := captureOutput(func() {
			err := ExportResultsCSV([]orbc.ResultOut{})
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
		})
		if out != "" {
			t.Errorf("expected no output for empty results, got %q", out)
		}
	})

	t.Run("multiple records with varying keys and special characters", func(t *testing.T) {
		results := []orbc.ResultOut{
			{
				ID:    "res-1",
				URL:   "https://example.com/product/1",
				Valid: true,
				Data: map[string]interface{}{
					"title": "PlayStation 5, Digital Edition",
					"price": 380000,
				},
			},
			{
				ID:    "res-2",
				URL:   "https://example.com/product/2",
				Valid: false,
				Data: map[string]interface{}{
					"title": "Xbox Series X",
					"notes": "Out of stock, check later",
				},
			},
		}

		out := captureOutput(func() {
			err := ExportResultsCSV(results)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
		})

		reader := csv.NewReader(strings.NewReader(out))
		records, err := reader.ReadAll()
		if err != nil {
			t.Fatalf("failed to read generated CSV: %v\nOutput was:\n%s", err, out)
		}

		if len(records) != 3 { // 1 header + 2 rows
			t.Fatalf("expected 3 CSV rows, got %d", len(records))
		}

		headers := records[0]
		// Keys sorted: notes, price, title => headers: id, valid, url, notes, price, title
		expectedHeaders := []string{"id", "valid", "url", "notes", "price", "title"}
		for i, h := range expectedHeaders {
			if headers[i] != h {
				t.Errorf("header[%d] expected %q, got %q", i, h, headers[i])
			}
		}

		// Check row 1
		row1 := records[1]
		if row1[0] != "res-1" || row1[1] != "true" || row1[2] != "https://example.com/product/1" {
			t.Errorf("unexpected row1 metadata: %+v", row1)
		}
		if row1[4] != "380000" || row1[5] != "PlayStation 5, Digital Edition" {
			t.Errorf("unexpected row1 data values: %+v", row1)
		}

		// Check row 2 (invalid record, missing price)
		row2 := records[2]
		if row2[0] != "res-2" || row2[1] != "false" {
			t.Errorf("unexpected row2 metadata: %+v", row2)
		}
		if row2[3] != "Out of stock, check later" || row2[4] != "" {
			t.Errorf("unexpected row2 missing/present fields: %+v", row2)
		}
	})
}

func TestRenderAutomationsTable(t *testing.T) {
	nextRun := "2026-08-24T08:00:00Z"
	automations := []orbc.AutomationOut{
		{
			ID: "12345678-abcd-ef01-2345-6789abcdef01",
			Plan: orbc.ExecutionPlan{
				Objective: "Track PS5 prices daily",
				Domain:    "ecommerce",
				Frequency: "daily",
			},
			Active:    true,
			NextRunAt: &nextRun,
		},
		{
			ID: "87654321-fedc-ba98-7654-3210fedcba98",
			Plan: orbc.ExecutionPlan{
				Objective: "Monitor Remote Golang Jobs",
				Domain:    "jobs",
				Frequency: "weekly",
			},
			Active:    false,
			NextRunAt: nil,
		},
	}

	t.Run("truncated by default", func(t *testing.T) {
		out := captureOutput(func() {
			RenderAutomationsTable(automations, false)
		})

		if !strings.Contains(out, "12345678") || !strings.Contains(out, "Track PS5 prices daily") {
			t.Errorf("table output missing automation 1: %s", out)
		}
		if strings.Contains(out, "12345678-abcd") {
			t.Errorf("expected truncated ID, got full UUID: %s", out)
		}
		if !strings.Contains(out, "87654321") || !strings.Contains(out, "Monitor Remote Golang Jobs") {
			t.Errorf("table output missing automation 2: %s", out)
		}
		if !strings.Contains(out, "Yes") || !strings.Contains(out, "No") {
			t.Errorf("table output missing active status strings: %s", out)
		}
	})

	t.Run("no-trunc displays full UUID", func(t *testing.T) {
		out := captureOutput(func() {
			RenderAutomationsTable(automations, true)
		})

		if !strings.Contains(out, "12345678-abcd-ef01-2345-6789abcdef01") {
			t.Errorf("expected full untruncated UUID in output: %s", out)
		}
	})
}

func TestRenderRunsTable(t *testing.T) {
	condMatched := true
	condNotMatched := false

	runs := []orbc.RunOut{
		{
			ID:               "run-11112222-3333",
			Status:           "completed",
			ExtractedCount:   5,
			ValidatedCount:   5,
			ConditionMatched: &condMatched,
			StartedAt:        "2026-08-23T10:00:00Z",
		},
		{
			ID:               "run-44445555-6666",
			Status:           "failed",
			ExtractedCount:   0,
			ValidatedCount:   0,
			ConditionMatched: &condNotMatched,
			StartedAt:        "2026-08-23T11:00:00Z",
		},
	}

	t.Run("truncated by default", func(t *testing.T) {
		out := captureOutput(func() {
			RenderRunsTable(runs, false)
		})

		if !strings.Contains(out, "run-1111") || !strings.Contains(out, "MATCHED") {
			t.Errorf("runs table output missing run 1 or MATCHED indicator: %s", out)
		}
		if strings.Contains(out, "run-11112222-3333") {
			t.Errorf("expected truncated run ID: %s", out)
		}
		if !strings.Contains(out, "run-4444") || !strings.Contains(out, "NO") {
			t.Errorf("runs table output missing run 2 or NO indicator: %s", out)
		}
	})

	t.Run("no-trunc displays full ID", func(t *testing.T) {
		out := captureOutput(func() {
			RenderRunsTable(runs, true)
		})

		if !strings.Contains(out, "run-11112222-3333") {
			t.Errorf("expected full untruncated run ID in output: %s", out)
		}
	})
}

func TestRenderResultsTable(t *testing.T) {
	t.Run("empty results", func(t *testing.T) {
		out := captureOutput(func() {
			RenderResultsTable([]orbc.ResultOut{})
		})
		if !strings.Contains(out, "No records extracted.") {
			t.Errorf("expected 'No records extracted.' message, got: %s", out)
		}
	})

	t.Run("valid and invalid records with long URLs", func(t *testing.T) {
		results := []orbc.ResultOut{
			{
				ID:    "res-1",
				URL:   "https://example.com/very/long/url/path/that/exceeds/forty/characters/product/item",
				Valid: true,
				Data: map[string]interface{}{
					"title": "Golang Backend Engineer",
					"rate":  120,
				},
			},
			{
				ID:    "res-2",
				URL:   "https://short.com/p",
				Valid: false,
				Data: map[string]interface{}{
					"title": "Junior Python Dev",
					"rate":  nil,
				},
			},
		}

		out := captureOutput(func() {
			RenderResultsTable(results)
		})

		if !strings.Contains(out, "Golang Backend Engineer") || !strings.Contains(out, "Junior Python Dev") {
			t.Errorf("results table missing titles: %s", out)
		}
		// Check URL truncation
		if !strings.Contains(out, "...") {
			t.Errorf("expected long URL to be truncated with '...': %s", out)
		}
	})
}
