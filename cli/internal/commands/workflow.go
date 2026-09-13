package commands

import (
	"encoding/json"
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/leoemaxie/orbit/cli/internal/formatters"
	"github.com/leoemaxie/orbit/cli/internal/ui"
	"github.com/spf13/cobra"
)

type AdapterInfo struct {
	ID          string `json:"id"`
	Stage       string `json:"stage"`
	Adapter     string `json:"adapter"`
	Category    string `json:"category"`
	Mode        string `json:"mode"`
	Engine      string `json:"engine"`
	Status      string `json:"status"`
	Description string `json:"description"`
}

var workflowCmd = &cobra.Command{
	Use:     "workflow",
	Aliases: []string{"wf", "pipeline"},
	Short:   "Manage workflow DAGs, adapter topology, and sink integrations",
	Long:    "Inspect adapter topology, view deployed pipeline nodes, test adapter connectivity, and deploy DAGs.",
	RunE: func(cmd *cobra.Command, args []string) error {
		return renderWorkflowTopology()
	},
}

var workflowTopologyCmd = &cobra.Command{
	Use:     "topology",
	Aliases: []string{"show", "adapters"},
	Short:   "Display available adapter studio topology and stage capabilities",
	RunE: func(cmd *cobra.Command, args []string) error {
		return renderWorkflowTopology()
	},
}

var workflowPipelineCmd = &cobra.Command{
	Use:     "pipeline",
	Aliases: []string{"list", "status"},
	Short:   "View currently deployed workflow pipeline nodes and configurations",
	RunE: func(cmd *cobra.Command, args []string) error {
		nodes, err := client.GetDeployedPipeline()
		if err != nil {
			ui.Error("Failed to fetch deployed pipeline: %v", err)
			return err
		}

		if jsonFlag {
			return formatters.PrintJSON(nodes)
		}

		if len(nodes) == 0 {
			ui.Warning("No custom pipeline DAG currently deployed. Standard default execution pipeline is active.")
			return nil
		}

		ui.PrintBanner()
		fmt.Printf("%s\n\n", ui.Cyan("🛰️ Deployed Workflow Pipeline DAG"))

		headers := []string{"Index", "Stage / Node", "Category", "Engine", "Status"}
		var rows [][]string
		for i, n := range nodes {
			label, _ := n["label"].(string)
			cat, _ := n["category"].(string)
			engine, _ := n["engine"].(string)
			status, _ := n["status"].(string)
			if status == "" {
				status = "ACTIVE"
			}

			rows = append(rows, []string{
				fmt.Sprintf("[%d]", i+1),
				ui.Cyan(label),
				cat,
				engine,
				ui.Green(strings.ToUpper(status)),
			})
		}

		formatters.RenderTable(headers, rows)
		return nil
	},
}

var workflowDeployCmd = &cobra.Command{
	Use:     "deploy <pipeline.json>",
	Aliases: []string{"apply"},
	Short:   "Deploy and activate a workflow pipeline DAG configuration",
	Example: `  orbc workflow deploy pipeline.json
  orbc workflow deploy - < pipeline.json`,
	Args: cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		filePath := args[0]
		var rawData []byte
		var err error

		if filePath == "-" {
			rawData, err = os.ReadFile("/dev/stdin")
		} else {
			rawData, err = os.ReadFile(filePath)
		}
		if err != nil {
			ui.Error("Failed to read pipeline configuration file: %v", err)
			return err
		}

		var nodes []map[string]interface{}
		// Support either direct array of nodes or an object with "nodes" key
		if err := json.Unmarshal(rawData, &nodes); err != nil {
			var wrapper struct {
				Nodes []map[string]interface{} `json:"nodes"`
			}
			if errWrap := json.Unmarshal(rawData, &wrapper); errWrap == nil && len(wrapper.Nodes) > 0 {
				nodes = wrapper.Nodes
			} else {
				ui.Error("Invalid pipeline JSON format. Must be an array of node objects or { \"nodes\": [...] }")
				return fmt.Errorf("invalid pipeline json: %w", err)
			}
		}

		ui.Info("Deploying workflow pipeline with %d node(s)...", len(nodes))
		resp, err := client.DeployWorkflow(nodes)
		if err != nil {
			ui.Error("Deployment failed: %v", err)
			return err
		}

		if jsonFlag {
			return formatters.PrintJSON(resp)
		}

		nodeCount := resp.NodeCount
		if nodeCount == 0 {
			nodeCount = len(nodes)
		}
		if resp.PipelineID != "" {
			ui.Success("Workflow pipeline deployed successfully! (Pipeline ID: %s, Nodes: %d)", resp.PipelineID, nodeCount)
		} else {
			ui.Success("Workflow pipeline deployed successfully! (Nodes: %d, Status: %s)", nodeCount, resp.Status)
		}
		return nil
	},
}

var workflowTestCmd = &cobra.Command{
	Use:     "test <adapter-id> [key=value...]",
	Aliases: []string{"test-connection", "check"},
	Short:   "Test connectivity and credentials for an adapter sink",
	Example: `  orbc workflow test slack webhook_url=https://hooks.slack.com/services/...
  orbc workflow test s3 bucket_name=orbit-exports region=us-east-1
  orbc workflow test email recipient=operator@company.com`,
	Args: cobra.MinimumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		adapterID := args[0]
		cfg, err := parseConfigKV(args[1:])
		if err != nil {
			ui.Error("Failed to parse config arguments: %v", err)
			return err
		}

		ui.Info("Testing connectivity for adapter '%s'...", adapterID)
		resp, err := client.TestAdapterConnection(adapterID, cfg)
		if err != nil {
			ui.Error("Connection test request failed: %v", err)
			return err
		}

		if jsonFlag {
			return formatters.PrintJSON(resp)
		}

		if resp.Success {
			ui.Success("Adapter '%s' connection test PASSED: %s", adapterID, resp.Message)
		} else {
			ui.Error("Adapter '%s' connection test FAILED: %s", adapterID, resp.Message)
			return fmt.Errorf("adapter connection test failed: %s", resp.Message)
		}

		return nil
	},
}

var workflowConfigCmd = &cobra.Command{
	Use:     "config <adapter-id> <key=value...>",
	Aliases: []string{"set-config", "configure"},
	Short:   "Save and persist custom adapter node configuration parameters",
	Example: `  orbc workflow config slack webhook_url=https://hooks.slack.com/... channel=#orbit-alerts
  orbc workflow config s3 bucket_name=my-vault region=eu-west-1 access_key=AKIA...`,
	Args: cobra.MinimumNArgs(2),
	RunE: func(cmd *cobra.Command, args []string) error {
		adapterID := args[0]
		cfg, err := parseConfigKV(args[1:])
		if err != nil {
			ui.Error("Failed to parse config arguments: %v", err)
			return err
		}

		resp, err := client.SaveAdapterConfig(adapterID, cfg)
		if err != nil {
			ui.Error("Failed to save adapter config: %v", err)
			return err
		}

		if jsonFlag {
			return formatters.PrintJSON(resp)
		}

		ui.Success("Configuration saved successfully for adapter '%s' (%s)", resp.AdapterID, resp.Message)
		return nil
	},
}

func renderWorkflowTopology() error {
	var adapters []AdapterInfo

	serverNodes, err := client.GetWorkflowTopology()
	if err == nil && len(serverNodes) > 0 {
		for _, n := range serverNodes {
			adapters = append(adapters, AdapterInfo{
				ID:          n.ID,
				Stage:       fmt.Sprintf("[%s] %s", n.Category, n.Label),
				Adapter:     n.Label,
				Category:    n.Category,
				Mode:        n.Mode,
				Engine:      n.Engine,
				Status:      n.Status,
				Description: n.Description,
			})
		}
	} else {
		// Offline fallback display
		adapters = []AdapterInfo{
			{ID: "1", Stage: "1. Trigger", Adapter: "Schedule Trigger", Category: "Trigger", Mode: "both", Engine: "Cron & Webhook Engine", Status: "ACTIVE", Description: "Cron schedule & webhook trigger"},
			{ID: "2", Stage: "2. Discovery", Adapter: "Source Discovery", Category: "Retrieval", Mode: "both", Engine: "Search Engine & Proxies", Status: "ACTIVE", Description: "Search engine & web proxy retrieval"},
			{ID: "3", Stage: "3. Parser", Adapter: "Document & Table Parser", Category: "Document", Mode: "managed", Engine: "Layout Analysis Engine", Status: "ACTIVE", Description: "Document layout analysis & table extraction"},
			{ID: "5", Stage: "4. Extraction", Adapter: "LLM Schema Extraction", Category: "Extraction", Mode: "both", Engine: "LLM Extraction Engine", Status: "ACTIVE", Description: "Structured JSON record extraction & validation"},
			{ID: "6", Stage: "5. Reports", Adapter: "PDF Report Generator", Category: "Reports", Mode: "both", Engine: "HTML-to-PDF Engine", Status: "ACTIVE", Description: "Automated PDF reports with PII data masking"},
			{ID: "7", Stage: "6. Storage", Adapter: "S3 Object Storage", Category: "Storage", Mode: "custom", Engine: "S3-Compatible Storage", Status: "ACTIVE", Description: "S3 bucket archival & presigned download links"},
			{ID: "9", Stage: "7. Notifications", Adapter: "Slack Notifications", Category: "Alerts", Mode: "custom", Engine: "Slack Incoming Webhook", Status: "ACTIVE", Description: "Slack alert webhook with report links"},
		}
	}

	if jsonFlag {
		return formatters.PrintJSON(adapters)
	}

	ui.PrintBanner()
	fmt.Printf("%s\n", ui.Cyan("🛰️ Orbit Pipeline Studio Topology"))
	fmt.Println(ui.Gray("Modular adapter pipeline from source discovery to storage and notification sinks:"))
	fmt.Println()

	fmt.Printf("  %s\n", ui.White("[Trigger] ──► [Discovery] ──► [DocParser] ──► [LLMExtractor] ──► [ReportGen] ──► [S3 / Slack]"))
	fmt.Println()

	headers := []string{"ID", "Stage / Adapter", "Category", "Engine", "Mode", "Status"}
	var rows [][]string
	for _, a := range adapters {
		rows = append(rows, []string{
			a.ID,
			ui.Cyan(a.Adapter),
			a.Category,
			a.Engine,
			a.Mode,
			ui.Green(strings.ToUpper(a.Status)),
		})
	}

	formatters.RenderTable(headers, rows)
	return nil
}

func parseConfigKV(args []string) (map[string]interface{}, error) {
	cfg := make(map[string]interface{})
	for _, arg := range args {
		arg = strings.TrimSpace(arg)
		if strings.HasPrefix(arg, "@") {
			// Read from json file
			filePath := strings.TrimPrefix(arg, "@")
			raw, err := os.ReadFile(filePath)
			if err != nil {
				return nil, fmt.Errorf("failed to read config file '%s': %w", filePath, err)
			}
			var fileMap map[string]interface{}
			if err := json.Unmarshal(raw, &fileMap); err != nil {
				return nil, fmt.Errorf("invalid json in '%s': %w", filePath, err)
			}
			for k, v := range fileMap {
				cfg[k] = v
			}
			continue
		}

		if strings.HasPrefix(arg, "{") && strings.HasSuffix(arg, "}") {
			var jsonMap map[string]interface{}
			if err := json.Unmarshal([]byte(arg), &jsonMap); err == nil {
				for k, v := range jsonMap {
					cfg[k] = v
				}
				continue
			}
		}

		if strings.Contains(arg, "=") {
			parts := strings.SplitN(arg, "=", 2)
			k := strings.TrimSpace(parts[0])
			v := strings.TrimSpace(parts[1])

			if b, err := strconv.ParseBool(v); err == nil {
				cfg[k] = b
			} else if num, err := strconv.Atoi(v); err == nil {
				cfg[k] = num
			} else {
				cfg[k] = v
			}
		}
	}
	return cfg, nil
}

func init() {
	workflowCmd.AddCommand(workflowTopologyCmd)
	workflowCmd.AddCommand(workflowPipelineCmd)
	workflowCmd.AddCommand(workflowDeployCmd)
	workflowCmd.AddCommand(workflowTestCmd)
	workflowCmd.AddCommand(workflowConfigCmd)
}

