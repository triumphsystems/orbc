package ui

import (
	"fmt"

	"github.com/fatih/color"
)

var (
	Cyan    = color.New(color.FgCyan, color.Bold).SprintFunc()
	Green   = color.New(color.FgGreen, color.Bold).SprintFunc()
	Yellow  = color.New(color.FgYellow, color.Bold).SprintFunc()
	Red     = color.New(color.FgRed, color.Bold).SprintFunc()
	Magenta = color.New(color.FgMagenta, color.Bold).SprintFunc()
	Gray    = color.New(color.FgHiBlack).SprintFunc()
	White   = color.New(color.FgWhite, color.Bold).SprintFunc()
)

// PrintBanner prints the Orbit CLI header banner.
func PrintBanner() {
	fmt.Printf("%s %s\n", Cyan("✦ Orbit:"), Gray("Autonomous Goal-Driven Web Data Operations"))
	fmt.Println(Gray("─────────────────────────────────────────────────────────────"))
}

// Header prints a styled section header.
func Header(title string) {
	fmt.Printf("%s\n", Cyan(title))
	fmt.Println(Gray("─────────────────────────────────────────────────────────────"))
}

// FormatStatus returns a colored status badge.
func FormatStatus(status string) string {
	switch status {
	case "verified":
		return Green("[VERIFIED]")
	case "alerting":
		return Magenta("[ALERT TRIGGERED]")
	case "evaluating":
		return Yellow("[EVALUATING]")
	case "discovering", "retrieving", "extracting", "validating", "storing":
		return Cyan(fmt.Sprintf("[%s]", status))
	case "failed":
		return Red("[FAILED]")
	default:
		return Gray(fmt.Sprintf("[%s]", status))
	}
}

// Success prints a green checkmark item.
func Success(format string, a ...interface{}) {
	fmt.Printf("  %s %s\n", Green("✓"), fmt.Sprintf(format, a...))
}

// Info prints a cyan info item.
func Info(format string, a ...interface{}) {
	fmt.Printf("  %s %s\n", Cyan("•"), fmt.Sprintf(format, a...))
}

// Warning prints a yellow warning item.
func Warning(format string, a ...interface{}) {
	fmt.Printf("  %s %s\n", Yellow("⚠"), fmt.Sprintf(format, a...))
}

// Error prints a red error item.
func Error(format string, a ...interface{}) {
	fmt.Printf("  %s %s\n", Red("✖"), fmt.Sprintf(format, a...))
}

// ShortID safely truncates an identifier to at most 8 characters without panicking.
func ShortID(id string) string {
	if len(id) > 8 {
		return id[:8]
	}
	return id
}
