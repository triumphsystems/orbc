<script lang="ts">
	import {
		Search,
		Plus,
		Play,
		Globe,
		FileText,
		Database,
		ShieldCheck,
		Cloud,
		MessageSquare,
		Mail,
		Sparkles,
		Radio,
		ChevronLeft,
		X
	} from '@lucide/svelte';
	import type { NodeTemplate } from './types';

	interface Props {
		onAddNode: (template: NodeTemplate) => void;
		onClose: () => void;
	}

	let { onAddNode, onClose }: Props = $props();
	let searchQuery = $state('');

	const nodeTemplates: NodeTemplate[] = [
		{
			typeId: 'trigger_cron',
			label: 'Schedule Trigger',
			category: 'trigger',
			adapterType: 'managed',
			iconName: 'Play',
			description: 'Cron schedule & webhook trigger',
			defaultConfig: { frequency: 'daily', schedule_time: '08:00', timezone: 'UTC' }
		},
		{
			typeId: 'proxy_discovery',
			label: 'Source Discovery',
			category: 'discovery',
			adapterType: 'managed',
			iconName: 'Globe',
			description: 'Multi-engine search & proxy retrieval',
			defaultConfig: { search_depth: 2, max_sources: 8, proxy_zone: 'datacenter' }
		},
		{
			typeId: 'doc_parser',
			label: 'Document & Table Parser',
			category: 'parsing',
			adapterType: 'managed',
			iconName: 'FileText',
			description: 'Document layout and table deconstruction',
			defaultConfig: { layout_analysis: true, table_format: 'markdown' }
		},
		{
			typeId: 'format_converter',
			label: 'Format Normalization & OCR',
			category: 'parsing',
			adapterType: 'managed',
			iconName: 'FileText',
			description: 'Convert DOCX/XLSX to PDF & run OCR',
			defaultConfig: { source_format: 'docx', ocr_enabled: true }
		},
		{
			typeId: 'schema_extractor',
			label: 'LLM Schema Extraction',
			category: 'extraction',
			adapterType: 'managed',
			iconName: 'Database',
			description: 'Structured JSON extraction & validation',
			defaultConfig: { temperature: 0.1, anomaly_detection: true }
		},
		{
			typeId: 'html_dossier',
			label: 'PDF Report Builder',
			category: 'dossier',
			adapterType: 'managed',
			iconName: 'Sparkles',
			description: 'Styled PDF summary & briefing generation',
			defaultConfig: { format: 'pdf', page_size: 'A4' }
		},
		{
			typeId: 'template_generator',
			label: 'Template Document Merger',
			category: 'dossier',
			adapterType: 'custom',
			iconName: 'FileText',
			description: 'Merge records into Word/PDF templates',
			defaultConfig: { template_id: 'default-report' }
		},
		{
			typeId: 'pii_redactor',
			label: 'PII Data Masking',
			category: 'compliance',
			adapterType: 'managed',
			iconName: 'ShieldCheck',
			description: 'Mask sensitive PII (SSN, emails, cards)',
			defaultConfig: { entities: 'EMAIL,SSN,CREDIT_CARD' }
		},
		{
			typeId: 's3_storage',
			label: 'S3 Object Storage',
			category: 'storage',
			adapterType: 'custom',
			iconName: 'Cloud',
			description: 'Upload JSON and reports to S3 bucket',
			defaultConfig: {
				bucket_name: 'orbit-exports',
				region: 'us-east-1',
				endpoint_url: '',
				access_key: '',
				secret_key: ''
			}
		},
		{
			typeId: 'sql_database',
			label: 'Database',
			category: 'storage',
			adapterType: 'custom',
			iconName: 'Database',
			description: 'Stream records to PostgreSQL, MySQL, or SQLite',
			defaultConfig: {
				database_url: 'postgresql://user:pass@localhost:5432/orbit_warehouse',
				table_name: 'extracted_data',
				upsert_key: 'id'
			}
		},
		{
			typeId: 'slack_alert',
			label: 'Slack Notifications',
			category: 'notify',
			adapterType: 'custom',
			iconName: 'MessageSquare',
			description: 'Slack channel alerts with report links',
			defaultConfig: { webhook_enabled: true, channel: '#orbit-alerts' }
		},
		{
			typeId: 'email_alert',
			label: 'Email Notifications',
			category: 'notify',
			adapterType: 'both',
			iconName: 'Mail',
			description: 'Managed platform email alerts & custom SMTP delivery',
			defaultConfig: {
				mode: 'managed',
				recipient_email: 'team@company.com',
				notify_on_anomaly: true,
				sender_address: 'alerts@company.com',
				smtp_host: 'smtp.example.com',
				smtp_port: 587,
				smtp_username: '',
				smtp_password: '',
				use_tls: true
			}
		},
		{
			typeId: 'webhook_alert',
			label: 'Outbound Webhooks',
			category: 'notify',
			adapterType: 'custom',
			iconName: 'Radio',
			description: 'HMAC-SHA256 signed event & record streaming',
			defaultConfig: {
				webhook_url: 'https://api.company.com/webhook',
				signing_secret: 'whsec_secret_key',
				timeout_sec: 15,
				max_retries: 3
			}
		}
	];

	const filteredTemplates = $derived(
		nodeTemplates.filter(
			(t) =>
				t.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
				t.description.toLowerCase().includes(searchQuery.toLowerCase())
		)
	);

	function handleDragStart(e: DragEvent, template: NodeTemplate) {
		if (e.dataTransfer) {
			e.dataTransfer.setData('application/json', JSON.stringify(template));
			e.dataTransfer.effectAllowed = 'copy';
		}
	}
</script>

<aside
	class="w-full lg:w-72 bg-surface-900 border border-white/10 rounded-2xl p-3.5 sm:p-4 flex flex-col gap-3 sm:gap-4 shadow-xl shrink-0 max-h-[300px] sm:max-h-[360px] lg:max-h-none lg:h-[640px]"
>
	<div class="flex items-center justify-between">
		<div class="flex items-center gap-2">
			<h2 class="text-xs font-bold text-slate-200 uppercase tracking-wider font-mono">
				Adapter Library
			</h2>
			<span
				class="text-[10px] font-mono text-slate-400 bg-surface-800 px-1.5 py-0.5 rounded border border-white/5"
				>{filteredTemplates.length}</span
			>
		</div>
		<button
			type="button"
			onclick={onClose}
			class="flex items-center gap-1 px-2 py-1 rounded-lg text-slate-400 hover:text-white hover:bg-surface-800 transition-colors text-xs font-mono"
			title="Collapse sidebar"
		>
			<span class="lg:hidden">Hide</span>
			<ChevronLeft size={16} class="hidden lg:inline" />
			<X size={14} class="lg:hidden" />
		</button>
	</div>

	<div class="relative">
		<Search size={14} class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
		<input
			type="text"
			placeholder="Search adapters..."
			bind:value={searchQuery}
			class="w-full pl-8 pr-3 py-1.5 bg-surface-800 border border-white/10 rounded-lg text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-orbit-cyan"
		/>
	</div>

	<div class="flex-1 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
		{#each filteredTemplates as template}
			<div
				draggable="true"
				ondragstart={(e) => handleDragStart(e, template)}
				class="group p-2.5 bg-surface-800/80 hover:bg-surface-800 border border-white/5 hover:border-orbit-cyan/40 rounded-xl cursor-grab active:cursor-grabbing transition-all select-none relative flex items-center justify-between gap-2"
			>
				<div class="min-w-0 flex-1">
					<div class="flex items-center gap-1.5 mb-0.5">
						<span
							class="text-xs font-semibold text-slate-200 group-hover:text-orbit-cyan transition-colors truncate block"
							>{template.label}</span
						>
						<span
							class="text-[9px] font-mono uppercase px-1.5 py-0.2 rounded border shrink-0 {template.adapterType ===
							'managed'
								? 'bg-emerald-950/40 text-emerald-300 border-emerald-500/20'
								: 'bg-cyan-950/40 text-cyan-300 border-cyan-500/20'}"
						>
							{template.adapterType}
						</span>
					</div>
					<p class="text-[11px] font-mono text-slate-400 line-clamp-1">{template.description}</p>
				</div>
				<button
					type="button"
					onclick={() => onAddNode(template)}
					class="p-1.5 rounded bg-surface-700 hover:bg-orbit-cyan hover:text-void text-slate-300 transition-colors opacity-100 lg:opacity-0 lg:group-hover:opacity-100 shrink-0"
					title="Add to canvas"
				>
					<Plus size={13} />
				</button>
			</div>
		{/each}
	</div>
</aside>
