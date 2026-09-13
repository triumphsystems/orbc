<script lang="ts">
	interface Props {
		configState: Record<string, any>;
		onChange: () => void;
	}

	let { configState, onChange }: Props = $props();

	function getPlaceholder(key: string): string {
		if (key.includes('uri') || key.includes('database_url'))
			return 'postgresql://user:pass@localhost:5432/orbit';
		if (key === 'webhook_url') return 'https://hooks.slack.com/... or https://api.site.com/webhook';
		if (key.includes('url')) return 'https://...';
		if (key === 'recipient_email') return 'team@company.com';
		if (key === 'sender_address') return 'alerts@yourdomain.com';
		if (key === 'smtp_host') return 'smtp.example.com';
		if (key === 'smtp_port') return '587';
		if (key.includes('table')) return 'orbit_extracted_records';
		if (key === 'bucket_name') return 'orbit-exports';
		if (key === 'region') return 'us-east-1';
		if (key === 'access_key') return 'AKIA...';
		if (key.includes('secret') || key.includes('password')) return '••••••••••••••••';
		return '';
	}
</script>

<!-- Hybrid Mode Selector for adapters supporting both (e.g. Email Notifications) -->
{#if 'mode' in configState}
	<div
		class="flex items-center rounded-lg bg-surface-800 p-0.5 border border-white/10 text-[11px] font-mono mb-1"
	>
		<button
			type="button"
			class="flex-1 py-1 px-2 rounded-md font-semibold text-center transition-colors {configState.mode ===
			'managed'
				? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
				: 'text-slate-400 hover:text-slate-200'}"
			onclick={() => {
				configState.mode = 'managed';
				onChange();
			}}
		>
			Managed
		</button>
		<button
			type="button"
			class="flex-1 py-1 px-2 rounded-md font-semibold text-center transition-colors {configState.mode ===
			'custom'
				? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
				: 'text-slate-400 hover:text-slate-200'}"
			onclick={() => {
				configState.mode = 'custom';
				onChange();
			}}
		>
			Custom
		</button>
	</div>
{/if}

<div class="overflow-y-auto max-h-[360px] space-y-2.5 font-mono text-xs pr-1 custom-scrollbar">
	{#each Object.entries(configState) as [key, value]}
		{#if key !== 'mode'}
			{@const isCustomOnly =
				key === 'sender_address' ||
				key.startsWith('smtp_') ||
				key === 'use_tls' ||
				key === 'api_key' ||
				key === 'base_url'}
			{#if !('mode' in configState) || configState.mode === 'custom' || !isCustomOnly}
				<div class="space-y-1">
					<label for={key} class="text-[10px] uppercase text-slate-400 font-semibold"
						>{key.replace(/_/g, ' ')}</label
					>
					{#if typeof value === 'boolean'}
						<div class="flex items-center gap-3 pt-0.5">
							<input
								type="checkbox"
								id={key}
								bind:checked={configState[key]}
								onchange={onChange}
								class="w-4 h-4 rounded bg-surface-800 border-white/20 text-orbit-cyan cursor-pointer"
							/>
							<span class="text-slate-300 text-xs">{configState[key] ? 'Enabled' : 'Disabled'}</span
							>
						</div>
					{:else if typeof value === 'number'}
						<input
							type="number"
							id={key}
							bind:value={configState[key]}
							oninput={onChange}
							class="w-full px-3 py-1.5 bg-surface-800 border border-white/10 rounded-lg text-slate-100 focus:outline-none focus:border-orbit-cyan/60"
						/>
					{:else}
						<input
							type={!key.includes('url') &&
							(key.includes('key') ||
								key.includes('secret') ||
								key.includes('password') ||
								key.includes('token'))
								? 'password'
								: 'text'}
							id={key}
							bind:value={configState[key]}
							oninput={onChange}
							placeholder={getPlaceholder(key)}
							class="w-full px-3 py-1.5 bg-surface-800 border border-white/10 rounded-lg text-slate-100 focus:outline-none focus:border-orbit-cyan/60"
						/>
					{/if}
				</div>
			{/if}
		{/if}
	{/each}
</div>
