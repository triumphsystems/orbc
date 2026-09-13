package ui

import (
	"time"

	"github.com/briandowns/spinner"
	"github.com/fatih/color"
)

func NewSpinner(msg string) *spinner.Spinner {
	s := spinner.New(spinner.CharSets[14], 100*time.Millisecond)
	s.Suffix = " " + color.CyanString(msg)
	s.Color("cyan")
	return s
}
