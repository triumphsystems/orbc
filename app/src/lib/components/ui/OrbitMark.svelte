<script lang="ts">
	interface Props {
		size?: 'sm' | 'md' | 'lg';
		animated?: boolean;
	}

	let { size = 'md', animated = true }: Props = $props();

	const iconSizes = {
		sm: 'w-7 h-7',
		md: 'w-9 h-9',
		lg: 'w-12 h-12'
	};
</script>

<div class="relative {iconSizes[size]} shrink-0 flex items-center justify-center">
	<!-- Outer Diffuse Glow -->
	{#if animated}
		<div class="absolute -inset-1 bg-orbit-cyan/15 rounded-full blur-md animate-pulse-slow"></div>
	{/if}

	<svg
		viewBox="0 0 100 100"
		class="w-full h-full relative z-10 overflow-visible"
		fill="none"
		xmlns="http://www.w3.org/2000/svg"
	>
		<defs>
			<linearGradient id="orb-grad-{size}" x1="0%" y1="0%" x2="100%" y2="100%">
				<stop offset="0%" stop-color="#00F2FE" />
				<stop offset="50%" stop-color="#38BDF8" />
				<stop offset="100%" stop-color="#3B82F6" />
			</linearGradient>

			<linearGradient id="ring-grad-1-{size}" x1="0%" y1="0%" x2="100%" y2="100%">
				<stop offset="0%" stop-color="#00F2FE" stop-opacity="0.9" />
				<stop offset="50%" stop-color="#8B5CF6" stop-opacity="0.6" />
				<stop offset="100%" stop-color="#00F2FE" stop-opacity="0.2" />
			</linearGradient>

			<linearGradient id="ring-grad-2-{size}" x1="100%" y1="0%" x2="0%" y2="100%">
				<stop offset="0%" stop-color="#8B5CF6" stop-opacity="0.8" />
				<stop offset="70%" stop-color="#38BDF8" stop-opacity="0.3" />
				<stop offset="100%" stop-color="#10B981" stop-opacity="0.6" />
			</linearGradient>

			<filter id="core-glow-{size}" x="-30%" y="-30%" width="160%" height="160%">
				<feGaussianBlur stdDeviation="2.5" result="blur" />
				<feMerge>
					<feMergeNode in="blur" />
					<feMergeNode in="SourceGraphic" />
				</feMerge>
			</filter>
		</defs>

		<!-- Outer Diffuse Radial Beacon -->
		<circle cx="50" cy="50" r="32" fill="#00F2FE" opacity="0.04" />

		<!-- Orbit Ring 2 (Tilted +35deg) - Back Layer -->
		<g transform="rotate(35 50 50)">
			<ellipse
				cx="50"
				cy="50"
				rx="40"
				ry="13"
				stroke="url(#ring-grad-2-{size})"
				stroke-width="1.75"
				opacity="0.75"
			/>
			<!-- Satellite node on Orbit 2 -->
			<circle cx="14" cy="50" r="3" fill="#8B5CF6" filter="url(#core-glow-{size})" />
			<circle cx="14" cy="50" r="1.5" fill="#FFFFFF" />
		</g>

		<!-- Orbit Ring 1 (Tilted -26deg) - Primary Layer -->
		<g transform="rotate(-26 50 50)">
			<ellipse
				cx="50"
				cy="50"
				rx="44"
				ry="15"
				stroke="url(#ring-grad-1-{size})"
				stroke-width="2.25"
				stroke-dasharray="4 2.5"
			/>
			<!-- Beacon Probe on Orbit 1 -->
			<g>
				<circle cx="92" cy="50" r="4" fill="#00F2FE" filter="url(#core-glow-{size})" />
				<circle cx="92" cy="50" r="2" fill="#FFFFFF" />
				{#if animated}
					<!-- Subtle pulse radar wave on probe -->
					<circle cx="92" cy="50" r="7" stroke="#00F2FE" stroke-width="1" opacity="0.4">
						<animate attributeName="r" values="4;9;4" dur="2.5s" repeatCount="indefinite" />
						<animate
							attributeName="opacity"
							values="0.8;0;0.8"
							dur="2.5s"
							repeatCount="indefinite"
						/>
					</circle>
				{/if}
			</g>

			{#if animated}
				<!-- Native SVG rotation centered strictly at (50, 50) -->
				<animateTransform
					attributeName="transform"
					type="rotate"
					from="-26 50 50"
					to="334 50 50"
					dur="20s"
					repeatCount="indefinite"
				/>
			{/if}
		</g>

		<!-- Central Planetary Data Core -->
		<circle cx="50" cy="50" r="14" fill="url(#orb-grad-{size})" filter="url(#core-glow-{size})" />
		<circle cx="50" cy="50" r="8.5" fill="#07090E" opacity="0.45" />
		<circle cx="50" cy="50" r="4" fill="#FFFFFF" opacity="0.95" />
	</svg>
</div>
