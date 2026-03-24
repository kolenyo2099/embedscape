<script lang="ts">
	import "../app.css";
	import Progress from "$lib/components/Sidebar/Progress.svelte";
	import { isProcessing } from "$lib/stores/ui";
</script>

<slot />

{#if $isProcessing}
	<Progress />
{/if}
