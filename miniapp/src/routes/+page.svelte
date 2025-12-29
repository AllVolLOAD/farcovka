<script lang="ts">
	import { goto } from '$app/navigation';
	import { apiClient } from '$lib/api';

	let checkingHot = false;
	let hotError = '';

	function goToCold() {
		goto('/cold');
	}

	async function goToHot() {
		// Не блокируем переход, даже если бэкенд недоступен
		hotError = '';
		checkingHot = true;
		try {
			const allowed = await apiClient.checkHotAccess();
			if (!allowed) {
				hotError = 'HOT режим доступен по приглашению. Обратитесь к администратору.';
				return;
			}
		} catch (err) {
			console.warn('HOT access check failed, продолжаем переход', err);
		} finally {
			checkingHot = false;
			goto('/hot');
		}
	}
</script>

<div class="container">
	<h1>🪙 FarCovka Wallet</h1>
	<p class="subtitle">Выберите режим работы мини-приложения</p>

	<div class="mode-grid">
		<div class="mode-card cold">
			<h2>❄️ COLD</h2>
			<ul>
				<li>Вы подключаете собственный Web3 кошелёк через WalletConnect</li>
				<li>Приватные ключи только у вас</li>
				<li>Сервис отслеживает депозит и уведомляет в боте</li>
			</ul>
			<button class="mode-button cold" on:click={goToCold}>
				Перейти в COLD
			</button>
		</div>

		<div class="mode-card hot">
			<h2>🔥 HOT</h2>
			<ul>
				<li>Средства хранятся на контракте-сейфе (custodial Web3)</li>
				<li>Мгновенные off-chain операции и балансы внутри miniapp</li>
				<li>Доступ включается вручную ограниченному кругу пользователей</li>
			</ul>
			<button class="mode-button hot" on:click={goToHot} disabled={checkingHot}>
				{checkingHot ? 'Проверяем доступ...' : 'Перейти в HOT'}
			</button>
			{#if hotError}
				<p class="error">{hotError}</p>
			{/if}
		</div>
	</div>

	<div class="info">
		<p>Можно переключаться между режимами в любое время.</p>
		<p>HOT режим находится в пилоте и выдаётся по запросу.</p>
	</div>
</div>

<style>
	.container {
		max-width: 720px;
		margin: 0 auto;
		padding: 2rem 1rem 3rem;
	}

	h1 {
		text-align: center;
		margin-bottom: 0.5rem;
		color: #0098EA;
	}

	.subtitle {
		text-align: center;
		color: #555;
		margin-bottom: 2rem;
	}

	.mode-grid {
		display: grid;
		gap: 1.5rem;
	}

	@media (min-width: 640px) {
		.mode-grid {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}

	.mode-card {
		background: white;
		border-radius: 16px;
		padding: 1.75rem;
		box-shadow: 0 12px 30px rgba(0, 0, 0, 0.08);
		display: flex;
		flex-direction: column;
		justify-content: space-between;
	}

	.mode-card h2 {
		margin: 0 0 1rem;
	}

	.mode-card ul {
		margin: 0 0 1.5rem;
		padding-left: 1.2rem;
		color: #444;
		line-height: 1.5;
	}

	.mode-button {
		width: 100%;
		padding: 0.9rem;
		font-size: 1rem;
		font-weight: 600;
		border: none;
		border-radius: 999px;
		color: white;
		cursor: pointer;
		transition: transform 0.2s, opacity 0.2s;
	}

	.mode-button:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.mode-button:hover:not(:disabled) {
		transform: translateY(-2px);
	}

	.mode-button.cold {
		background: linear-gradient(135deg, #38bdf8, #0ea5e9);
	}

	.mode-button.hot {
		background: linear-gradient(135deg, #fb7185, #f97316);
	}

	.error {
		color: #b91c1c;
		margin-top: 1rem;
		font-size: 0.9rem;
	}

	.info {
		text-align: center;
		color: #666;
		font-size: 0.95rem;
		margin-top: 2.5rem;
		line-height: 1.5;
	}
</style>

