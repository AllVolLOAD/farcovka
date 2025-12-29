<!-- ⚠️ ЗАМОРОЖЕНО: Разработка HOT режима приостановлена -->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api';

	type HotBalance = { token: string; balance: string };
	type DepositInfo = { vault_address: string; chain_id: number; note?: string };

	let balances: HotBalance[] = [];
	let loadingBalances = true;
	let balanceError = '';

	let depositInfo: DepositInfo | null = null;
	let depositError = '';

	let withdrawAmount = '';
	let withdrawAddress = '';
	let withdrawStatus = '';

	let orderType: 'buy' | 'sell' = 'buy';
	let orderAmount = '';
	let orderFiat = '';
	let orderRate = '';
	let orderStatus = '';

	onMount(() => {
		loadBalances();
	});

	function goHome() {
		goto('/');
	}

	async function loadBalances() {
		loadingBalances = true;
		balanceError = '';
		try {
			const data = await apiClient.getHotBalances();
			balances = data;
		} catch (err) {
			console.error('Failed to load balances', err);
			balanceError = 'Не удалось загрузить балансы HOT. Попробуйте позже.';
		} finally {
			loadingBalances = false;
		}
	}

	async function requestDeposit() {
		depositError = '';
		try {
			depositInfo = await apiClient.requestHotDeposit();
		} catch (err) {
			console.error('Deposit request failed', err);
			depositError = 'Не удалось получить адрес для депозита.';
		}
	}

	async function submitWithdraw() {
		withdrawStatus = '';
		if (!withdrawAmount || !withdrawAddress) {
			withdrawStatus = 'Укажите сумму и адрес вывода.';
			return;
		}

		try {
			const amount = Number(withdrawAmount);
			if (Number.isNaN(amount) || amount <= 0) {
				withdrawStatus = 'Некорректная сумма.';
				return;
			}

			const response = await apiClient.requestHotWithdraw({
				amount_crypto: amount,
				to_address: withdrawAddress
			});

			withdrawStatus = response.message;
			withdrawAmount = '';
			withdrawAddress = '';
			await loadBalances();
		} catch (err: any) {
			console.error('Withdraw request failed', err);
			const apiError = err?.response?.data?.detail;
			withdrawStatus = apiError ?? 'Ошибка создания запроса на вывод.';
		}
	}

	async function createHotOrder() {
		orderStatus = '';
		if (!orderAmount || !orderFiat || !orderRate) {
			orderStatus = 'Заполните сумму, фиат и курс.';
			return;
		}

		try {
			const payload = {
				wallet_mode: 'HOT',
				type: orderType,
				currency_pair: 'USD/RUB',
				amount_crypto: Number(orderAmount),
				amount_fiat: Number(orderFiat),
				rate: Number(orderRate)
			};
			await apiClient.createOrder(payload);
			orderStatus = 'Ордер создан. Проверяйте статус в разделе ордеров.';
			orderAmount = '';
			orderFiat = '';
			orderRate = '';
		} catch (err: any) {
			console.error('Failed to create HOT order', err);
			const apiError = err?.response?.data?.detail;
			orderStatus = apiError ?? 'Не удалось создать ордер.';
		}
	}
</script>

<div class="container">
	<div class="header">
		<button class="back-button" on:click={goHome}>← Назад</button>
		<h1>🔥 HOT режим</h1>
		<p>Быстрые off-chain операции и управление балансом</p>
	</div>

	<section class="card">
		<div class="card-head">
			<h2>Баланс</h2>
		<button class="refresh-button" on:click={loadBalances} disabled={loadingBalances}>
				{loadingBalances ? '...' : 'Обновить'}
			</button>
		</div>
		{#if balanceError}
			<p class="error">{balanceError}</p>
		{:else if loadingBalances}
			<p class="loading">Загружаем...</p>
		{:else if balances.length === 0}
			<p>Нет активов. Попробуйте пополнить Vault.</p>
		{:else}
			<ul class="balance-list">
				{#each balances as bal}
					<li>
						<span>{bal.token}</span>
						<strong>{bal.balance}</strong>
					</li>
				{/each}
			</ul>
		{/if}
	</section>

	<section class="card">
		<h2>Депозит</h2>
		<p>Получите актуальный адрес Vault для пополнения HOT кошелька.</p>
		<button class="primary" on:click={requestDeposit}>Получить адрес</button>
		{#if depositError}
			<p class="error">{depositError}</p>
		{/if}
		{#if depositInfo}
			<div class="deposit-info">
				<p><span>Vault:</span> {depositInfo.vault_address}</p>
				<p><span>Chain ID:</span> {depositInfo.chain_id}</p>
				{#if depositInfo.note}
					<p class="note">{depositInfo.note}</p>
				{/if}
			</div>
		{/if}
	</section>

	<section class="card">
		<h2>Вывод</h2>
		<div class="form-grid">
			<label>
				<span>Сумма (USDT)</span>
				<input type="number" min="0" step="0.0001" bind:value={withdrawAmount} />
			</label>
			<label>
				<span>Адрес получателя</span>
				<input type="text" placeholder="0x..." bind:value={withdrawAddress} />
			</label>
		</div>
		<button class="primary" on:click={submitWithdraw}>Запросить вывод</button>
		{#if withdrawStatus}
			<p class="status">{withdrawStatus}</p>
		{/if}
	</section>

	<section class="card">
		<h2>Ордер внутри HOT</h2>
		<div class="form-grid">
			<label>
				<span>Тип</span>
				<select bind:value={orderType}>
					<option value="buy">Buy</option>
					<option value="sell">Sell</option>
				</select>
			</label>
			<label>
				<span>Сумма (USDT)</span>
				<input type="number" min="0" step="0.0001" bind:value={orderAmount} />
			</label>
			<label>
				<span>Сумма фиат (RUB)</span>
				<input type="number" min="0" step="0.01" bind:value={orderFiat} />
			</label>
			<label>
				<span>Курс</span>
				<input type="number" min="0" step="0.01" bind:value={orderRate} />
			</label>
		</div>
		<button class="primary" on:click={createHotOrder}>Создать ордер</button>
		{#if orderStatus}
			<p class="status">{orderStatus}</p>
		{/if}
	</section>
</div>

<style>
	.container {
		max-width: 720px;
		margin: 0 auto;
		padding: 2rem 1rem 3rem;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.header {
		text-align: center;
	}

	.back-button {
		background: none;
		border: none;
		color: #fb7185;
		font-weight: 600;
		cursor: pointer;
		margin-bottom: 0.5rem;
	}

	h1 {
		margin: 0;
		color: #fb7185;
	}

	.card {
		background: white;
		border-radius: 16px;
		padding: 1.5rem;
		box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
	}

	.card-head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
	}

	.refresh-button {
		background: none;
		border: 1px solid #f97316;
		color: #f97316;
		padding: 0.35rem 0.9rem;
		border-radius: 999px;
		cursor: pointer;
	}

	.balance-list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: 0.6rem;
	}

	.balance-list li {
		display: flex;
		justify-content: space-between;
		font-size: 1.05rem;
	}

	.primary {
		width: 100%;
		padding: 0.9rem;
		font-size: 1rem;
		font-weight: 600;
		color: white;
		border: none;
		border-radius: 12px;
		margin-top: 1rem;
		cursor: pointer;
		background: linear-gradient(135deg, #fb7185, #f97316);
	}

	.deposit-info {
		margin-top: 1rem;
		padding: 1rem;
		border-radius: 12px;
		background: #fff7ed;
		color: #9a3412;
	}

	.deposit-info span {
		font-weight: 600;
	}

	.note {
		margin-top: 0.5rem;
		font-size: 0.9rem;
	}

	.form-grid {
		display: grid;
		gap: 1rem;
		margin-top: 1rem;
	}

	label {
		display: flex;
		flex-direction: column;
		font-size: 0.9rem;
		color: #475569;
		gap: 0.35rem;
	}

	input,
	select {
		padding: 0.75rem;
		border: 1px solid #e2e8f0;
		border-radius: 12px;
		font-size: 1rem;
	}

	.loading {
		color: #94a3b8;
	}

	.error {
		color: #b91c1c;
		margin-top: 1rem;
	}

	.status {
		margin-top: 0.75rem;
		color: #475569;
	}
</style>

