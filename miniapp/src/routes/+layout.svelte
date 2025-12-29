<script lang="ts">
	import { onMount } from 'svelte';
	import { initWeb3Modal } from '$lib/walletconnect';

	onMount(() => {
		// Initialize Telegram WebApp
		if (window.Telegram?.WebApp) {
			const tg = window.Telegram.WebApp;
			tg.ready();
			tg.expand();
			
			// Apply Telegram theme
			document.body.style.backgroundColor = tg.backgroundColor;
		}

		// Initialize WalletConnect
		initWeb3Modal();
	});
</script>

<main>
	<slot />
</main>

<style>
	:global(body) {
		margin: 0;
		padding: 0;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
	}

	main {
		max-width: 100%;
		min-height: 100vh;
		padding: 1rem;
		box-sizing: border-box;
	}
</style>

