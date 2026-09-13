export interface SSEOptions<T = any> {
	url: string;
	onMessage?: (data: T, eventType: string) => void;
	onEvent?: Record<string, (data: any) => void>;
	onError?: (error: Event) => void;
	onOpen?: () => void;
	onClose?: () => void;
}

export interface SSEConnection {
	close: () => void;
	getEventSource: () => EventSource | null;
}

/**
 * Creates a robust  SSE (Server-Sent Events) connection.
 * Automatically wires event handlers and cleans up connections.
 */
export function createSSEConnection<T = any>(options: SSEOptions<T>): SSEConnection {
	let eventSource: EventSource | null = new EventSource(options.url);

	const handleEvent = (e: MessageEvent, eventName: string) => {
		try {
			const parsed = JSON.parse(e.data);
			if (options.onEvent && options.onEvent[eventName]) {
				options.onEvent[eventName](parsed);
			}
			if (options.onMessage) {
				options.onMessage(parsed, eventName);
			}
		} catch {
			if (options.onEvent && options.onEvent[eventName]) {
				options.onEvent[eventName](e.data);
			}
			if (options.onMessage) {
				options.onMessage(e.data as any, eventName);
			}
		}
	};

	if (options.onEvent) {
		for (const eventName of Object.keys(options.onEvent)) {
			eventSource.addEventListener(eventName, (e) => handleEvent(e as MessageEvent, eventName));
		}
	}

	eventSource.onmessage = (e) => handleEvent(e, 'message');

	if (options.onOpen) {
		eventSource.onopen = () => options.onOpen?.();
	}

	if (options.onError) {
		eventSource.onerror = (e) => options.onError?.(e);
	}

	return {
		close: () => {
			if (eventSource) {
				eventSource.close();
				eventSource = null;
				options.onClose?.();
			}
		},
		getEventSource: () => eventSource
	};
}
