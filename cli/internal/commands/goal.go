package commands

import (
	"fmt"
	"strings"

	"github.com/spf13/cobra"
	"github.com/leoemaxie/orbit/cli/internal/formatters"
	"github.com/leoemaxie/orbit/cli/internal/ui"
)

var (
	runImmediatelyFlag bool
	quietFlag          bool
)

var goalCmd = &cobra.Command{
	Use:   "goal <prompt>",
	Short: "Interpret a natural-language goal and create an autonomous web-data automation",
	Example: `  # Static threshold alert
  orbc goal "Every day at 8AM, find cheapest PS5 in Nigeria and alert if price < 400000 NGN"

  # Relative historical price drop alert
  orbc goal "Daily at 8 AM, track PS5 prices and alert me when the lowest price drops by 10%"

  # Tech job monitoring with immediate run
  orbc goal "Weekly, monitor Python remote jobs paying > $150k" --run`,
	Args: cobra.MinimumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		goalText := strings.Join(args, " ")

		if jsonFlag {
			auto, err := client.CreateAutomation(goalText)
			if err != nil {
				return err
			}
			return formatters.PrintJSON(auto)
		}

		if quietFlag {
			auto, err := client.CreateAutomation(goalText)
			if err != nil {
				return err
			}
			fmt.Println(auto.ID)
			return nil
		}

		ui.PrintBanner()
		fmt.Printf("Goal: \"%s\"\n\n", ui.White(goalText))

		spinner := ui.NewSpinner("Interpreting goal and synthesizing execution plan...")
		spinner.Start()

		auto, err := client.CreateAutomation(goalText)
		spinner.Stop()

		if err != nil {
			ui.Error("Failed to interpret goal: %v", err)
			return err
		}

		ui.Success("Goal interpreted successfully!")
		ui.Info("Automation ID : %s", ui.Cyan(auto.ID))
		ui.Info("Domain        : %s", ui.Yellow(auto.Plan.Domain))
		ui.Info("Objective     : %s", auto.Plan.Objective)
		ui.Info("Target Entity : %s", ui.Cyan(auto.Plan.ExtractionSchema.EntityName))
		ui.Info("Search Query  : %s", auto.Plan.SearchQuery)
		ui.Info("Frequency     : %s", ui.Magenta(auto.Plan.Frequency))
		if auto.Plan.Condition != "" {
			ui.Info("Condition     : %s", ui.Yellow(auto.Plan.Condition))
		}
		if auto.Plan.ScheduleTime != "" {
			ui.Info("Schedule Time : %s (%s)", auto.Plan.ScheduleTime, auto.Plan.Timezone)
		}

		fmt.Println()
		ui.Info("Dynamic Extraction Schema:")
		for _, f := range auto.Plan.ExtractionSchema.Fields {
			reqStr := ""
			if f.Required {
				reqStr = " (required)"
			}
			fmt.Printf("    - %s [%s]%s: %s\n", ui.Cyan(f.Name), f.Type, reqStr, f.Description)
		}
		fmt.Println()

		if runImmediatelyFlag {
			fmt.Printf("%s\n\n", ui.Cyan("🚀 Triggering immediate execution..."))
			return executeRun(auto.ID)
		}

		fmt.Printf("To execute this automation now, run:\n  %s\n", ui.Cyan(fmt.Sprintf("orbc run %s", auto.ID)))
		return nil
	},
}

func init() {
	goalCmd.Flags().BoolVar(&runImmediatelyFlag, "run", false, "Immediately trigger execution after interpretation")
	goalCmd.Flags().BoolVarP(&quietFlag, "quiet", "q", false, "Print only the automation ID")
}
