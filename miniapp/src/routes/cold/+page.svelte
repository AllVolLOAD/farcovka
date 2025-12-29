<!-- ⚠️ ЗАМОРОЖЕНО: Разработка COLD режима приостановлена -->
<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { openConnectModal, watchWalletAccount, getCurrentAccount } from '$lib/walletconnect';
	import { apiClient } from '$lib/api';

	let account: { address?: string; chainId?: number } | null = null;
	let quotes: any = null;
	let loading = false;
	let error = '';

	onMount(() => {
		const currentAccount = getCurrentAccount();
		if (currentAccount?.address) {
			account = currentAccount;
		}

		const unwatch = watchWalletAccount((acc) => {
			account = acc;
			if (acc.address) {
				handleWalletConnected(acc.address, acc.chainId);
			}
		});

		loadQuotes();
		return () => {
			unwatch();
		};
	});

	function goHome() {
		goto('/');
	}

	async function handleConnect() {
		try {
			loading = true;
			error = '';
			await openConnectModal();
		} catch (err: any) {
			error = err?.message ?? 'Не удалось подключить кошелёк';
			console.error('Connect error:', err);
		} finally {
			loading = false;
		}
	}

	async function handleWalletConnected(address: string, chainId: number) {
		try {
			console.log('Wallet connected:', address, 'Chain:', chainId);
			// TODO: integrate backend approval when ready
		} catch (err) {
			console.error('Error registering wallet:', err);
			error = 'Не удалось зарегистрировать кошелёк';
		}
	}

	async function loadQuotes() {
		try {
			quotes = await apiClient.getQuotes();
		} catch (err) {
			console.error('Error loading quotes:', err);
		}
	}

	function formatRate(rate: any) {
		if (!rate || !rate.length || !rate[0]) return 'N/A';
		const r = rate[0];
		return `${r.buy} / ${r.sell}`;
	}
</script>

<div class="container">
	<div class="header">
		<button class="back-button" on:click={goHome}>← Назад</button>
		<h1>❄️ COLD режим</h1>
		<p>Подключите внешний кошелёк через WalletConnect</p>
	</div>

	<div class="card">
		<h2>Курсы обмена</h2>
		{#if quotes}
			<div class="rates">
				<div class="rate-item">
					<span class="label">Admin:</span>
					<span class="value">{formatRate(quotes.admin)}</span>
				</div>
				<div class="rate-item">
					<span class="label">CBR:</span>
					<span class="value">{formatRate(quotes.cbr)}</span>
				</div>
				<div class="rate-item">
					<span class="label">RBC Buy:</span>
					<span class="value">{formatRate(quotes.rbc_buy)}</span>
				</div>
				<div class="rate-item">
					<span class="label">RBC Sell:</span>
					<span class="value">{formatRate(quotes.rbc_sell)}</span>
				</div>
			</div>
		{:else}
			<p class="loading">Загружаем курсы...</p>
		{/if}
	</div>

	<div class="card">
		<h2>Подключение кошелька</h2>
		{#if account?.address}
			<div class="wallet-info">
				<p class="success">✅ Кошелёк подключён</p>
				<p class="address">{account.address.slice(0, 6)}...{account.address.slice(-4)}</p>
				<p class="chain">Chain ID: {account.chainId}</p>
			</div>
		{:else}
			<button class="connect-button" on:click={handleConnect} disabled={loading}>
				{loading ? 'Подключаем...' : 'Подключить WalletConnect'}
			</button>
		{/if}

		{#if error}
			<p class="error">{error}</p>
		{/if}
	</div>

	<div class="info">
		<p>🔐 Приватные ключи хранятся только у вас.</p>
		<p>⚡ Мы лишь отслеживаем депозит и уведомляем бота.</p>
	</div>
</div>

<style>
	.container {
		max-width: 640px;
		margin: 0 auto;
		padding: 2rem 1rem 3rem;
	}

	.header {
		text-align: center;
		margin-bottom: 2rem;
	}

	.back-button {
		background: none;
		border: none;
		color: #0ea5e9;
		font-weight: 600;
		cursor: pointer;
		margin-bottom: 0.5rem;
	}

	h1 {
		margin: 0;
		color: #0ea5e9;
	}

	.card {
		background: white;
		border-radius: 16px;
		padding: 1.5rem;
		margin-bottom: 1.5rem;
		box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
	}

	h2 {
		margin: 0 0 1rem;
		font-size: 1.2rem;
	}

	.rates {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.rate-item {
		display: flex;
		justify-content: space-between;
		padding: 0.5rem 0;
		border-bottom: 1px solid #f1f5f9;
	}

	.rate-item:last-child {
		border-bottom: none;
	}

	.label {
		color: #64748b;
	}

	.value {
		font-weight: 600;
		color: #0ea5e9;
	}

	.loading {
		text-align: center;
		color: #94a3b8;
	}

	.connect-button {
		width: 100%;
		padding: 1rem;
		font-size: 1rem;
		font-weight: 600;
		color: white;
		background: linear-gradient(135deg, #38bdf8, #0ea5e9);
		border: none;
		border-radius: 12px;
		cursor: pointer;
		transition: transform 0.2s, opacity 0.2s;
	}

	.connect-button:hover:not(:disabled) {
		transform: translateY(-2px);
	}

	.connect-button:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.wallet-info {
		text-align: center;
	}

	.success {
		color: #10b981;
		font-weight: 600;
		margin-bottom: 0.5rem;
	}

	.address {
		font-family: monospace;
		font-size: 1.1rem;
		color: #1e293b;
		margin-bottom: 0.25rem;
	}

	.chain {
		color: #64748b;
		font-size: 0.9rem;
	}

	.error {
		color: #b91c1c;
		text-align: center;
		margin-top: 1rem;
	}

	.info {
		text-align: center;
		color: #475569;
		font-size: 0.95rem;
		line-height: 1.6;
	}
</style>

