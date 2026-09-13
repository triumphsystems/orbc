BINARY_NAME=orbc
BUILD_DIR=bin
PROD_API_URL ?= https://orbit-wtsx.onrender.com
DEV_API_URL ?= http://localhost:8000

.PHONY: all build build-prod build-dev clean test test-cover cross-compile

all: build

# Interactive build: prompts user if in terminal and PROD_URL is not explicitly passed
build:
	@mkdir -p $(BUILD_DIR)
	@TARGET_URL="$(PROD_URL)"; \
	if [ -z "$$TARGET_URL" ]; then \
		if [ -t 0 ]; then \
			printf "Bake in production backend URL ($(PROD_API_URL))? [Y/n]: "; \
			read ans; \
			case "$$ans" in \
				[nN]*) TARGET_URL="$(DEV_API_URL)" ;; \
				*)     TARGET_URL="$(PROD_API_URL)" ;; \
			esac; \
		else \
			TARGET_URL="$(PROD_API_URL)"; \
		fi; \
	fi; \
	echo "Building $(BINARY_NAME) with DefaultAPIURL: $$TARGET_URL"; \
	CGO_ENABLED=0 go build \
		-ldflags "-s -w -X github.com/leoemaxie/orbit/cli/internal/config.DefaultAPIURL=$$TARGET_URL" \
		-o $(BUILD_DIR)/$(BINARY_NAME) ./cmd/orbc

# Explicit Production Build
build-prod:
	@mkdir -p $(BUILD_DIR)
	@echo "Building production $(BINARY_NAME) -> $(PROD_API_URL)"
	CGO_ENABLED=0 go build \
		-ldflags "-s -w -X github.com/leoemaxie/orbit/cli/internal/config.DefaultAPIURL=$(PROD_API_URL)" \
		-o $(BUILD_DIR)/$(BINARY_NAME) ./cmd/orbc

# Explicit Local Development Build
build-dev:
	@mkdir -p $(BUILD_DIR)
	@echo "Building local development $(BINARY_NAME) -> $(DEV_API_URL)"
	CGO_ENABLED=0 go build \
		-ldflags "-s -w -X github.com/leoemaxie/orbit/cli/internal/config.DefaultAPIURL=$(DEV_API_URL)" \
		-o $(BUILD_DIR)/$(BINARY_NAME) ./cmd/orbc

test:
	go test -v ./...

test-cover:
	go test -v -cover ./...

clean:
	rm -rf $(BUILD_DIR)

cross-compile:
	@mkdir -p $(BUILD_DIR)
	@TARGET_URL="$(PROD_URL)"; \
	if [ -z "$$TARGET_URL" ]; then TARGET_URL="$(PROD_API_URL)"; fi; \
	echo "Cross-compiling $(BINARY_NAME) matrix with DefaultAPIURL: $$TARGET_URL"; \
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags "-s -w -X github.com/leoemaxie/orbit/cli/internal/config.DefaultAPIURL=$$TARGET_URL" -o $(BUILD_DIR)/$(BINARY_NAME)-linux-amd64 ./cmd/orbc; \
	CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -ldflags "-s -w -X github.com/leoemaxie/orbit/cli/internal/config.DefaultAPIURL=$$TARGET_URL" -o $(BUILD_DIR)/$(BINARY_NAME)-linux-arm64 ./cmd/orbc; \
	CGO_ENABLED=0 GOOS=darwin GOARCH=arm64 go build -ldflags "-s -w -X github.com/leoemaxie/orbit/cli/internal/config.DefaultAPIURL=$$TARGET_URL" -o $(BUILD_DIR)/$(BINARY_NAME)-darwin-arm64 ./cmd/orbc; \
	CGO_ENABLED=0 GOOS=darwin GOARCH=amd64 go build -ldflags "-s -w -X github.com/leoemaxie/orbit/cli/internal/config.DefaultAPIURL=$$TARGET_URL" -o $(BUILD_DIR)/$(BINARY_NAME)-darwin-amd64 ./cmd/orbc; \
	CGO_ENABLED=0 GOOS=windows GOARCH=amd64 go build -ldflags "-s -w -X github.com/leoemaxie/orbit/cli/internal/config.DefaultAPIURL=$$TARGET_URL" -o $(BUILD_DIR)/$(BINARY_NAME)-windows-amd64.exe ./cmd/orbc
