package commands

import (
	"fmt"
	"os"
	"strings"

	"github.com/leoemaxie/orbit/cli/internal/config"
	"github.com/leoemaxie/orbit/cli/internal/ui"
	"github.com/leoemaxie/orbit/cli/pkg/orbc"
	"github.com/spf13/cobra"
)

var (
	apiURLFlag  string
	jsonFlag    bool
	formatFlag  string
	verboseFlag bool

	cfg    *config.Config
	client *orbc.Client
)

// RootCmd is the base command for orbc CLI.
var RootCmd = &cobra.Command{
	Use:           "orbc",
	Short:         "orbc - Autonomous Goal-Driven Web Data Operations CLI",
	SilenceUsage:  true,
	SilenceErrors: true,
	Long: `orbc is an agentic web-data automation CLI for Orbit.
Transform natural-language goals into recurring, verifiable web-data workflows.

"Set the goal. Walk away."`,
	PersistentPreRunE: func(cmd *cobra.Command, args []string) error {
		var err error
		cfg, err = config.LoadConfig()
		if err != nil {
			ui.Error("Error loading configuration: %v", err)
			return fmt.Errorf("error loading configuration: %w", err)
		}

		targetURL := cfg.APIURL
		if apiURLFlag != "" {
			targetURL = apiURLFlag
		}

		client = orbc.NewClient(targetURL, cfg.Timeout)

		// Format Precedence: CLI flag > Config file/Env > Default ("table")
		resolvedFormat := cfg.Format
		if formatFlag != "" {
			resolvedFormat = formatFlag
		}
		if jsonFlag {
			resolvedFormat = "json"
		}

		switch strings.ToLower(resolvedFormat) {
		case "json":
			jsonFlag = true
			formatFlag = "json"
		case "csv":
			formatFlag = "csv"
		case "table", "":
			formatFlag = "table"
		default:
			return fmt.Errorf("unsupported format '%s', choose from table, json, csv", resolvedFormat)
		}

		return nil
	},
}

func init() {
	RootCmd.PersistentFlags().StringVar(&apiURLFlag, "api-url", "", "Orbit API Base URL (default: http://localhost:8000)")
	RootCmd.PersistentFlags().StringVarP(&formatFlag, "format", "f", "", "Output format: table, json, csv")
	RootCmd.PersistentFlags().BoolVar(&jsonFlag, "json", false, "Output raw JSON (shorthand for --format json)")
	RootCmd.PersistentFlags().BoolVarP(&verboseFlag, "verbose", "v", false, "Enable verbose logging")

	// Add subcommands
	RootCmd.AddCommand(goalCmd)
	RootCmd.AddCommand(runCmd)
	RootCmd.AddCommand(retryCmd)
	RootCmd.AddCommand(listCmd)
	RootCmd.AddCommand(runsCmd)
	RootCmd.AddCommand(showCmd)
	RootCmd.AddCommand(dataCmd)
	RootCmd.AddCommand(rmCmd)
	RootCmd.AddCommand(scheduleCmd)
	RootCmd.AddCommand(workflowCmd)
	RootCmd.AddCommand(watchCmd)
	RootCmd.AddCommand(configCmd)
	RootCmd.AddCommand(versionCmd)
}

// Execute runs the root command.
func Execute() {
	if err := RootCmd.Execute(); err != nil {
		os.Exit(1)
	}
}
