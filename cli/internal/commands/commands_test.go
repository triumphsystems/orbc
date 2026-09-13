package commands

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/leoemaxie/orbit/cli/pkg/orbc"
	"github.com/spf13/viper"
)

// resetFlags resets package-level flags before running a command test
func resetFlags() {
	apiURLFlag = ""
	jsonFlag = false
	verboseFlag = false
	runImmediatelyFlag = false
	quietFlag = false
	formatFlag = ""
	validOnlyFlag = false
	followFlag = false
	streamFlag = false
	noTruncFlag = false
	scheduleWaitFlag = false
	scheduleSecretFlag = ""
	viper.Reset()
}

func executeCommand(args ...string) (string, error) {
	resetFlags()

	r, w, _ := os.Pipe()
	origStdout := os.Stdout
	os.Stdout = w

	outC := make(chan string)
	go func() {
		var buf bytes.Buffer
		_, _ = io.Copy(&buf, r)
		outC <- buf.String()
	}()

	RootCmd.SetArgs(args)
	err := RootCmd.Execute()

	_ = w.Close()
	os.Stdout = origStdout
	out := <-outC
	_ = r.Close()

	return out, err
}

func setupMockServer() *httptest.Server {
	mockAuto := orbc.AutomationOut{
		ID:      "auto-5555",
		RawGoal: "Track laptop prices",
		Plan: orbc.ExecutionPlan{
			Objective:   "Find laptops under $1000",
			Domain:      "ecommerce",
			SearchQuery: "laptops sale",
			Frequency:   "daily",
			ExtractionSchema: orbc.DynamicExtractionSchema{
				EntityName: "laptop",
				Fields: []orbc.ExtractionField{
					{Name: "brand", Type: "string", Required: true, Description: "Brand name"},
					{Name: "price", Type: "number", Required: true, Description: "Price in USD"},
				},
			},
		},
		Active:    true,
		CreatedAt: "2026-08-23T00:00:00Z",
	}

	condMatched := true
	condMsg := "Price < 1000"
	mockRun := orbc.RunOut{
		ID:               "run-7777",
		AutomationID:     "auto-5555",
		Status:           "completed",
		StartedAt:        "2026-08-23T12:00:00Z",
		ExtractedCount:   2,
		ValidatedCount:   2,
		ConditionMatched: &condMatched,
		ConditionMessage: &condMsg,
		SourcesFound:     []string{"https://store.com/item1"},
		PagesRetrieved:   []string{"https://store.com/item1"},
		Results: []orbc.ResultOut{
			{
				ID:    "res-1",
				URL:   "https://store.com/item1",
				Valid: true,
				Data: map[string]interface{}{
					"brand": "Dell",
					"price": 850,
				},
			},
		},
	}

	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		switch {
		case r.URL.Path == "/api/v1/health":
			_ = json.NewEncoder(w).Encode(orbc.HealthResponse{
				Status:           "ok",
				Version:          "0.2.0",
				Environment:      "test",
				SchedulerEnabled: true,
			})
		case r.URL.Path == "/api/v1/automations" && r.Method == http.MethodPost:
			_ = json.NewEncoder(w).Encode(mockAuto)
		case r.URL.Path == "/api/v1/automations" && r.Method == http.MethodGet:
			_ = json.NewEncoder(w).Encode(orbc.AutomationListOut{
				Items: []orbc.AutomationOut{mockAuto},
				Total: 1,
			})
		case r.URL.Path == "/api/v1/automations/auto-5555" && r.Method == http.MethodGet:
			_ = json.NewEncoder(w).Encode(mockAuto)
		case r.URL.Path == "/api/v1/automations/auto-5555/run" && r.Method == http.MethodPost:
			_ = json.NewEncoder(w).Encode(mockRun)
		case r.URL.Path == "/api/v1/automations/auto-5555/runs" && r.Method == http.MethodGet:
			_ = json.NewEncoder(w).Encode([]orbc.RunOut{mockRun})
		case r.URL.Path == "/api/v1/runs/run-7777" && r.Method == http.MethodGet:
			_ = json.NewEncoder(w).Encode(mockRun)
		case r.URL.Path == "/api/v1/scheduler/status" && r.Method == http.MethodGet:
			_ = json.NewEncoder(w).Encode(orbc.SchedulerStatusResponse{
				ServerTimeUTC:       "2026-08-23T12:00:00Z",
				ActiveScheduleCount: 1,
				Schedules: []orbc.ScheduledItem{
					{
						AutomationID: "auto-5555",
						Objective:    "Find laptops under $1000",
						Frequency:    "daily",
						Timezone:     "UTC",
						IsDue:        false,
					},
				},
			})
		case r.URL.Path == "/api/v1/scheduler/trigger-due" && r.Method == http.MethodPost:
			_ = json.NewEncoder(w).Encode(orbc.SchedulerTriggerResponse{
				Status:                 "success",
				DueCount:               1,
				TriggeredAutomationIDs: []string{"auto-5555"},
				Wait:                   false,
				ServerTimeUTC:          "2026-08-23T12:00:00Z",
			})
		case r.URL.Path == "/api/v1/workflows/topology" && r.Method == http.MethodGet:
			_ = json.NewEncoder(w).Encode([]orbc.WorkflowNodeOut{
				{
					ID:          "9",
					Label:       "Slack Notifications",
					Category:    "notify",
					Mode:        "custom",
					Engine:      "Slack Incoming Webhook",
					Status:      "active",
					Description: "Slack alert webhooks with signed report links",
				},
			})
		case r.URL.Path == "/api/v1/workflows/pipeline" && r.Method == http.MethodGet:
			_ = json.NewEncoder(w).Encode([]map[string]interface{}{
				{
					"id":       "1",
					"label":    "Schedule Trigger",
					"category": "trigger",
					"engine":   "Cron & Webhook Engine",
					"status":   "active",
				},
				{
					"id":       "9",
					"label":    "Slack Notifications",
					"category": "notify",
					"engine":   "Slack Incoming Webhook",
					"status":   "active",
				},
			})
		case r.URL.Path == "/api/v1/workflows/deploy" && r.Method == http.MethodPost:
			_ = json.NewEncoder(w).Encode(orbc.WorkflowDeployResponse{
				Status:     "success",
				PipelineID: "pipe-9999",
				NodeCount:  2,
				Message:    "Workflow pipeline deployed successfully",
			})
		case r.URL.Path == "/api/v1/workflows/test-connection" && r.Method == http.MethodPost:
			_ = json.NewEncoder(w).Encode(orbc.TestConnectionResponse{
				Success: true,
				Message: "Slack webhook verified and reachable",
			})
		case strings.HasPrefix(r.URL.Path, "/api/v1/workflows/adapters/") && strings.HasSuffix(r.URL.Path, "/config") && r.Method == http.MethodPost:
			_ = json.NewEncoder(w).Encode(orbc.SaveAdapterConfigResponse{
				Status:    "success",
				AdapterID: "slack",
				Message:   "Configuration updated",
			})
		case strings.HasPrefix(r.URL.Path, "/api/v1/runs/") && strings.HasSuffix(r.URL.Path, "/stream"):
			w.Header().Set("Content-Type", "text/event-stream")
			payload, _ := json.Marshal(mockRun)
			_, _ = fmt.Fprintf(w, "event: complete\ndata: %s\n\n", string(payload))
		default:
			http.NotFound(w, r)
		}
	}))
}

func TestCommand_Goal(t *testing.T) {
	ts := setupMockServer()
	defer ts.Close()

	t.Run("interactive display", func(t *testing.T) {
		out, err := executeCommand("goal", "Find laptops under $1000", "--api-url", ts.URL)
		if err != nil {
			t.Fatalf("goal command failed: %v", err)
		}

		if !strings.Contains(out, "auto-5555") || !strings.Contains(out, "Find laptops under $1000") {
			t.Errorf("expected goal output to contain automation ID and objective: %s", out)
		}
	})

	t.Run("quiet flag returns only ID", func(t *testing.T) {
		out, err := executeCommand("goal", "Find laptops", "--quiet", "--api-url", ts.URL)
		if err != nil {
			t.Fatalf("goal --quiet failed: %v", err)
		}

		if strings.TrimSpace(out) != "auto-5555" {
			t.Errorf("expected quiet output 'auto-5555', got %q", out)
		}
	})

	t.Run("json flag returns valid json", func(t *testing.T) {
		out, err := executeCommand("goal", "Find laptops", "--json", "--api-url", ts.URL)
		if err != nil {
			t.Fatalf("goal --json failed: %v", err)
		}

		var parsed map[string]interface{}
		if err := json.Unmarshal([]byte(out), &parsed); err != nil {
			t.Fatalf("expected valid JSON output: %v, raw: %s", err, out)
		}
		if parsed["id"] != "auto-5555" {
			t.Errorf("unexpected JSON content: %+v", parsed)
		}
	})

	t.Run("missing arguments fails validation", func(t *testing.T) {
		_, err := executeCommand("goal", "--api-url", ts.URL)
		if err == nil {
			t.Fatalf("expected error when goal argument is missing")
		}
	})
}

func TestCommand_List(t *testing.T) {
	ts := setupMockServer()
	defer ts.Close()

	t.Run("table output", func(t *testing.T) {
		out, err := executeCommand("list", "--api-url", ts.URL)
		if err != nil {
			t.Fatalf("list failed: %v", err)
		}

		if !strings.Contains(out, "auto-555") {
			t.Errorf("list output missing auto-555: %s", out)
		}
	})

	t.Run("no-trunc table output", func(t *testing.T) {
		out, err := executeCommand("list", "--no-trunc", "--api-url", ts.URL)
		if err != nil {
			t.Fatalf("list --no-trunc failed: %v", err)
		}

		if !strings.Contains(out, "auto-5555") {
			t.Errorf("list --no-trunc missing full ID auto-5555: %s", out)
		}
	})

	t.Run("json output", func(t *testing.T) {
		out, err := executeCommand("list", "--json", "--api-url", ts.URL)
		if err != nil {
			t.Fatalf("list --json failed: %v", err)
		}

		var list orbc.AutomationListOut
		if err := json.Unmarshal([]byte(out), &list); err != nil {
			t.Fatalf("invalid json from list: %v, raw: %s", err, out)
		}
		if list.Total != 1 || list.Items[0].ID != "auto-5555" {
			t.Errorf("unexpected list output: %+v", list)
		}
	})
}

func TestCommand_Run_And_Runs(t *testing.T) {
	ts := setupMockServer()
	defer ts.Close()

	t.Run("run command execution", func(t *testing.T) {
		out, err := executeCommand("run", "auto-5555", "--api-url", ts.URL)
		if err != nil {
			t.Fatalf("run failed: %v", err)
		}

		if !strings.Contains(out, "run-7777") || !strings.Contains(out, "Execution Audit Trail") {
			t.Errorf("unexpected run output: %s", out)
		}
	})

	t.Run("runs list history", func(t *testing.T) {
		out, err := executeCommand("runs", "auto-5555", "--api-url", ts.URL)
		if err != nil {
			t.Fatalf("runs failed: %v", err)
		}

		if !strings.Contains(out, "run-7777") {
			t.Errorf("runs table missing run-7777: %s", out)
		}
	})

	t.Run("runs list history with no-trunc", func(t *testing.T) {
		out, err := executeCommand("runs", "auto-5555", "--no-trunc", "--api-url", ts.URL)
		if err != nil {
			t.Fatalf("runs --no-trunc failed: %v", err)
		}

		if !strings.Contains(out, "run-7777") {
			t.Errorf("runs table missing full run-7777: %s", out)
		}
	})
}

func TestCommand_Show(t *testing.T) {
	ts := setupMockServer()
	defer ts.Close()

	out, err := executeCommand("show", "run-7777", "--api-url", ts.URL)
	if err != nil {
		t.Fatalf("show command failed: %v", err)
	}

	if !strings.Contains(out, "run-7777") || !strings.Contains(out, "Discovered Sources") {
		t.Errorf("unexpected show output: %s", out)
	}
}

func TestCommand_Data(t *testing.T) {
	ts := setupMockServer()
	defer ts.Close()

	t.Run("json format", func(t *testing.T) {
		out, err := executeCommand("data", "run-7777", "--format", "json", "--api-url", ts.URL)
		if err != nil {
			t.Fatalf("data --format json failed: %v", err)
		}

		var results []orbc.ResultOut
		if err := json.Unmarshal([]byte(out), &results); err != nil {
			t.Fatalf("invalid json data: %v, raw: %s", err, out)
		}
		if len(results) != 1 || results[0].Data["brand"] != "Dell" {
			t.Errorf("unexpected results data: %+v", results)
		}
	})

	t.Run("csv format", func(t *testing.T) {
		out, err := executeCommand("data", "run-7777", "--format", "csv", "--api-url", ts.URL)
		if err != nil {
			t.Fatalf("data --format csv failed: %v", err)
		}

		if !strings.Contains(out, "id,valid,url,brand,price") || !strings.Contains(out, "Dell,850") {
			t.Errorf("unexpected csv output: %s", out)
		}
	})

	t.Run("invalid format returns error", func(t *testing.T) {
		_, err := executeCommand("data", "run-7777", "--format", "yaml", "--api-url", ts.URL)
		if err == nil {
			t.Fatalf("expected error for unsupported format 'yaml'")
		}
	})
}

func TestCommand_Version(t *testing.T) {
	ts := setupMockServer()
	defer ts.Close()

	t.Run("version with connected server", func(t *testing.T) {
		out, err := executeCommand("version", "--json", "--api-url", ts.URL)
		if err != nil {
			t.Fatalf("version failed: %v", err)
		}

		var ver map[string]interface{}
		if err := json.Unmarshal([]byte(out), &ver); err != nil {
			t.Fatalf("invalid json: %v, raw: %s", err, out)
		}

		if ver["cli_version"] != CLIVersion || ver["server_version"] != "0.2.0" {
			t.Errorf("unexpected version json: %+v", ver)
		}
	})
}

func TestCommand_Watch_ShortID(t *testing.T) {
	ts := setupMockServer()
	defer ts.Close()

	out, err := executeCommand("watch", "dkdkd", "--api-url", ts.URL)
	if err != nil {
		t.Fatalf("watch with short ID failed: %v", err)
	}

	if !strings.Contains(out, "dkdkd") {
		t.Errorf("expected watch output to contain short ID 'dkdkd': %s", out)
	}
}

func TestCommand_Schedule(t *testing.T) {
	ts := setupMockServer()
	defer ts.Close()

	t.Run("schedule list", func(t *testing.T) {
		out, err := executeCommand("schedule", "list", "--api-url", ts.URL)
		if err != nil {
			t.Fatalf("schedule list failed: %v", err)
		}
		if !strings.Contains(out, "auto-555") {
			t.Errorf("expected schedule list output to contain auto-555: %s", out)
		}
	})

	t.Run("schedule trigger", func(t *testing.T) {
		out, err := executeCommand("schedule", "trigger", "--api-url", ts.URL)
		if err != nil {
			t.Fatalf("schedule trigger failed: %v", err)
		}
		if !strings.Contains(out, "Scheduler hook triggered successfully") {
			t.Errorf("expected trigger success message: %s", out)
		}
	})
}

func TestCommand_APIErrorDoesNotShowUsage(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, `{"detail":"Automation not found"}`, http.StatusNotFound)
	}))
	defer ts.Close()

	out, err := executeCommand("show", "invalid-id", "--api-url", ts.URL)
	if err == nil {
		t.Fatalf("expected command to return error on 404 API response")
	}

	if !strings.Contains(out, "Failed to fetch run") {
		t.Errorf("expected output to contain API error message, got: %s", out)
	}

	if strings.Contains(out, "Usage:") || strings.Contains(out, "Flags:") {
		t.Errorf("expected output NOT to contain help/usage text on API error, got: %s", out)
	}
}

func TestCommand_Config(t *testing.T) {
	tmpHome := t.TempDir()
	t.Setenv("USERPROFILE", tmpHome)
	t.Setenv("HOME", tmpHome)

	t.Run("config set and config show key", func(t *testing.T) {
		out, err := executeCommand("config", "set", "api-url", "http://localhost:8000")
		if err != nil {
			t.Fatalf("config set api-url failed: %v, out: %s", err, out)
		}
		if !strings.Contains(out, "Configuration updated") {
			t.Errorf("unexpected output from config set: %s", out)
		}

		outShow, err := executeCommand("config", "show", "api_url")
		if err != nil {
			t.Fatalf("config show api_url failed: %v, out: %s", err, outShow)
		}
		if !strings.Contains(outShow, "http://localhost:8000") {
			t.Errorf("expected config show api_url to return 'http://localhost:8000', got: %s", outShow)
		}

		outGet, err := executeCommand("config", "get", "api-url")
		if err != nil {
			t.Fatalf("config get api-url failed: %v, out: %s", err, outGet)
		}
		if !strings.Contains(outGet, "http://localhost:8000") {
			t.Errorf("expected config get api-url to return 'http://localhost:8000', got: %s", outGet)
		}
	})

	t.Run("config show all", func(t *testing.T) {
		outAll, err := executeCommand("config", "show")
		if err != nil {
			t.Fatalf("config show failed: %v, out: %s", err, outAll)
		}
		if !strings.Contains(outAll, "http://localhost:8000") || !strings.Contains(outAll, "API URL") {
			t.Errorf("unexpected config show output: %s", outAll)
		}
	})
}

func TestCommand_FormatPrecedence(t *testing.T) {
	ts := setupMockServer()
	defer ts.Close()

	t.Run("config format json outputs JSON automatically", func(t *testing.T) {
		tmpHome := t.TempDir()
		t.Setenv("USERPROFILE", tmpHome)
		t.Setenv("HOME", tmpHome)
		t.Setenv("ORBC_FORMAT", "json")

		out, err := executeCommand("list", "--api-url", ts.URL)
		if err != nil {
			t.Fatalf("list failed: %v, out: %s", err, out)
		}

		var list orbc.AutomationListOut
		if err := json.Unmarshal([]byte(out), &list); err != nil {
			t.Fatalf("expected valid json when ORBC_FORMAT=json, got error: %v, raw: %s", err, out)
		}
		if list.Total != 1 || list.Items[0].ID != "auto-5555" {
			t.Errorf("unexpected list output: %+v", list)
		}
	})

	t.Run("explicit flag overrides config format", func(t *testing.T) {
		tmpHome := t.TempDir()
		t.Setenv("USERPROFILE", tmpHome)
		t.Setenv("HOME", tmpHome)
		t.Setenv("ORBC_FORMAT", "json")

		out, err := executeCommand("list", "--format", "table", "--api-url", ts.URL)
		if err != nil {
			t.Fatalf("list --format table failed: %v, out: %s", err, out)
		}

		if !strings.Contains(out, "auto-555") {
			t.Errorf("expected table output when overriding with --format table: %s", out)
		}
	})
}

func TestCommand_WorkflowSuite(t *testing.T) {
	ts := setupMockServer()
	defer ts.Close()

	t.Run("workflow topology", func(t *testing.T) {
		out, err := executeCommand("workflow", "topology", "--api-url", ts.URL)
		if err != nil {
			t.Fatalf("workflow topology failed: %v, out: %s", err, out)
		}
		if !strings.Contains(out, "Slack Notifications") || !strings.Contains(out, "Pipeline Studio") {
			t.Errorf("unexpected topology output: %s", out)
		}
	})

	t.Run("workflow pipeline list", func(t *testing.T) {
		out, err := executeCommand("workflow", "pipeline", "--api-url", ts.URL)
		if err != nil {
			t.Fatalf("workflow pipeline failed: %v, out: %s", err, out)
		}
		if !strings.Contains(out, "Schedule Trigger") || !strings.Contains(out, "Slack Notifications") {
			t.Errorf("unexpected pipeline output: %s", out)
		}
	})

	t.Run("workflow test connection", func(t *testing.T) {
		out, err := executeCommand("workflow", "test", "slack", "webhook_url=https://hooks.slack.com/test", "--api-url", ts.URL)
		if err != nil {
			t.Fatalf("workflow test failed: %v, out: %s", err, out)
		}
		if !strings.Contains(out, "PASSED") || !strings.Contains(out, "Slack webhook verified") {
			t.Errorf("unexpected test connection output: %s", out)
		}
	})

	t.Run("workflow config save", func(t *testing.T) {
		out, err := executeCommand("workflow", "config", "slack", "webhook_url=https://hooks.slack.com/test", "channel=#alerts", "--api-url", ts.URL)
		if err != nil {
			t.Fatalf("workflow config failed: %v, out: %s", err, out)
		}
		if !strings.Contains(out, "Configuration saved successfully") {
			t.Errorf("unexpected config output: %s", out)
		}
	})

	t.Run("workflow deploy from file", func(t *testing.T) {
		tmpDir := t.TempDir()
		pipelineFile := filepath.Join(tmpDir, "pipeline.json")
		pipelineContent := `[{"id":"1","label":"Schedule Trigger","category":"trigger"},{"id":"9","label":"Slack Notifications","category":"notify"}]`
		if err := os.WriteFile(pipelineFile, []byte(pipelineContent), 0644); err != nil {
			t.Fatalf("failed to write temp pipeline file: %v", err)
		}

		out, err := executeCommand("workflow", "deploy", pipelineFile, "--api-url", ts.URL)
		if err != nil {
			t.Fatalf("workflow deploy failed: %v, out: %s", err, out)
		}
		if !strings.Contains(out, "Workflow pipeline deployed successfully") || !strings.Contains(out, "pipe-9999") {
			t.Errorf("unexpected deploy output: %s", out)
		}
	})
}





