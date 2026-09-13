import { api } from '$lib/api/client';
import type { AutomationOut, HealthStatus, RunOut } from '$lib/api/types';

export class OrbitStore {
	automations = $state<AutomationOut[]>([]);
	totalAutomations = $state<number>(0);
	selectedAutomation = $state<AutomationOut | null>(null);
	activeRun = $state<RunOut | null>(null);
	runsHistory = $state<RunOut[]>([]);
	health = $state<HealthStatus | null>(null);
	daemonConnected = $state<boolean>(false);

	loading = $state<boolean>(false);
	interpretingGoal = $state<boolean>(false);
	runningAutomation = $state<boolean>(false);
	errorMessage = $state<string | null>(null);
	sidebarCollapsed = $state<boolean>(false);

	initSidebar() {
		if (typeof window !== 'undefined') {
			const saved = localStorage.getItem('orbit_sidebar_collapsed');
			if (saved !== null) {
				this.sidebarCollapsed = saved === 'true';
			}
		}
	}

	toggleSidebar() {
		this.sidebarCollapsed = !this.sidebarCollapsed;
		if (typeof window !== 'undefined') {
			localStorage.setItem('orbit_sidebar_collapsed', String(this.sidebarCollapsed));
		}
	}

	// Derived metrics
	activeAutomationsCount = $derived(this.automations.filter((a) => a.active).length);

	async checkHealth() {
		try {
			const res = await api.getHealth();
			this.health = res;
			this.daemonConnected = true;
			this.errorMessage = null;
		} catch (err: any) {
			this.health = null;
			this.daemonConnected = false;
			// Don't override user errors, only set if clean
		}
	}

	async loadAutomations() {
		this.loading = true;
		try {
			const res = await api.listAutomations();
			this.automations = res.items;
			this.totalAutomations = res.total;
			this.daemonConnected = true;
			this.errorMessage = null;
		} catch (err: any) {
			this.errorMessage = err.message || 'Failed to connect to Orbit daemon';
			this.daemonConnected = false;
		} finally {
			this.loading = false;
		}
	}

	goalReasoningStage = $state<{ stage: string; message: string } | null>(null);

	async createGoal(goal: string): Promise<AutomationOut | null> {
		this.interpretingGoal = true;
		this.goalReasoningStage = { stage: 'analyzing', message: 'Analyzing goal objective...' };
		this.errorMessage = null;

		return new Promise<AutomationOut | null>((resolve) => {
			let resolved = false;

			const closeStream = api.streamGoalPlan(
				goal,
				(data) => {
					this.goalReasoningStage = data;
				},
				() => {},
				(res) => {
					if (!resolved) {
						resolved = true;
						this.automations = [res, ...this.automations];
						this.totalAutomations += 1;
						this.selectedAutomation = res;
						this.interpretingGoal = false;
						this.goalReasoningStage = null;
						resolve(res);
					}
				},
				async (err) => {
					if (!resolved) {
						resolved = true;
						try {
							const res = await api.createAutomation({ goal });
							this.automations = [res, ...this.automations];
							this.totalAutomations += 1;
							this.selectedAutomation = res;
							resolve(res);
						} catch (fallbackErr: any) {
							this.errorMessage =
								fallbackErr.message || err?.message || 'Goal interpretation failed';
							resolve(null);
						} finally {
							this.interpretingGoal = false;
							this.goalReasoningStage = null;
						}
					}
				}
			);
		});
	}

	async triggerRun(automationId: string): Promise<RunOut | null> {
		this.runningAutomation = true;
		this.errorMessage = null;
		try {
			const run = await api.runAutomation(automationId);
			this.activeRun = run;
			this.runsHistory = [run, ...this.runsHistory];
			return run;
		} catch (err: any) {
			this.errorMessage = err.message || 'Failed to trigger run';
			return null;
		} finally {
			this.runningAutomation = false;
		}
	}

	async retryRun(runId: string): Promise<RunOut | null> {
		this.runningAutomation = true;
		this.errorMessage = null;
		try {
			const run = await api.retryRun(runId);
			this.activeRun = run;
			this.runsHistory = this.runsHistory.map((r) => (r.id === run.id ? run : r));
			return run;
		} catch (err: any) {
			this.errorMessage = err.message || 'Failed to retry run';
			return null;
		} finally {
			this.runningAutomation = false;
		}
	}

	async loadRun(runId: string) {
		this.loading = true;
		try {
			const run = await api.getRun(runId);
			this.activeRun = run;
			this.errorMessage = null;
		} catch (err: any) {
			this.errorMessage = err.message || 'Run not found';
		} finally {
			this.loading = false;
		}
	}

	async loadAutomationRuns(automationId: string) {
		try {
			const runs = await api.listAutomationRuns(automationId);
			this.runsHistory = runs;
		} catch (err: any) {
			console.error('Failed to load runs history:', err);
		}
	}

	async deleteAutomation(id: string) {
		try {
			await api.deleteAutomation(id);
			this.automations = this.automations.filter((a) => a.id !== id);
			this.totalAutomations = Math.max(0, this.totalAutomations - 1);
			if (this.selectedAutomation?.id === id) {
				this.selectedAutomation = null;
			}
		} catch (err: any) {
			this.errorMessage = err.message || 'Failed to delete automation';
		}
	}
}

export const orbitStore = new OrbitStore();
