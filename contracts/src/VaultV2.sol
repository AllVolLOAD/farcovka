// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @title VaultV2 (HOT) — non-custodial-with-guardian vault
/// @notice Holds user funds on-chain; no admin withdraws. Users always control withdrawal.
/// @dev Governance/guardian/operator separated; emergencyWithdraw is always available.
contract VaultV2 is ReentrancyGuard {
    using SafeERC20 for IERC20;

    // --- Roles ---
    address public governance;
    address public guardian;
    address public operator; // optional, no direct balance control

    // --- Modes ---
    bool public depositsPaused;
    bool public emergencyMode;

    // --- Storage ---
    mapping(address token => mapping(address user => uint256)) private _balances;
    mapping(address token => uint256) public totalAssigned;
    mapping(address token => uint256) public maxTVL;
    mapping(address token => bool) public tokenEnabled;
    mapping(address targetVault => bool) public allowedMigrations;

    // --- Events ---
    event Deposit(address indexed user, address indexed token, uint256 amount);
    event Withdraw(address indexed user, address indexed token, uint256 amount);
    event EmergencyWithdraw(address indexed user, address indexed token, uint256 amount);
    event OperatorChanged(address indexed oldOperator, address indexed newOperator);
    event GuardianChanged(address indexed oldGuardian, address indexed newGuardian);
    event DepositsPaused(bool paused);
    event EmergencyModeChanged(bool enabled);
    event TokenEnabled(address indexed token, bool enabled);
    event MaxTVLUpdated(address indexed token, uint256 value);
    event MigrationAllowed(address indexed targetVault, bool allowed);
    event Migrated(address indexed user, address indexed token, uint256 amount, address indexed targetVault);
    event GovernanceChanged(address indexed oldGov, address indexed newGov);

    // --- Errors ---
    error NotGovernance();
    error NotGuardianOrGovernance();
    error DepositsPausedError();
    error EmergencyModeError();
    error TokenNotEnabled();
    error MaxTVLExceeded();
    error InsufficientBalance();
    error MigrationNotAllowed();
    error ZeroAddress();

    modifier onlyGovernance() {
        if (msg.sender != governance) revert NotGovernance();
        _;
    }

    modifier onlyGuardianOrGovernance() {
        if (msg.sender != guardian && msg.sender != governance) revert NotGuardianOrGovernance();
        _;
    }

    constructor(address _governance, address _guardian) {
        if (_governance == address(0) || _guardian == address(0)) revert ZeroAddress();
        governance = _governance;
        guardian = _guardian;
    }

    // --- User functions ---
    function deposit(address token, uint256 amount) external nonReentrant {
        if (!tokenEnabled[token]) revert TokenNotEnabled();
        if (depositsPaused) revert DepositsPausedError();
        if (emergencyMode) revert EmergencyModeError();
        if (totalAssigned[token] + amount > maxTVL[token]) revert MaxTVLExceeded();

        IERC20(token).safeTransferFrom(msg.sender, address(this), amount);
        _balances[token][msg.sender] += amount;
        totalAssigned[token] += amount;

        emit Deposit(msg.sender, token, amount);
    }

    function withdraw(address token, uint256 amount) public nonReentrant {
        if (_balances[token][msg.sender] < amount) revert InsufficientBalance();

        _balances[token][msg.sender] -= amount;
        totalAssigned[token] -= amount;
        IERC20(token).safeTransfer(msg.sender, amount);

        emit Withdraw(msg.sender, token, amount);
    }

    /// @notice Always available, even in emergencyMode. Withdraws to msg.sender only.
    function emergencyWithdraw(address token, uint256 amount) external nonReentrant {
        if (_balances[token][msg.sender] < amount) revert InsufficientBalance();

        _balances[token][msg.sender] -= amount;
        totalAssigned[token] -= amount;
        IERC20(token).safeTransfer(msg.sender, amount);

        emit EmergencyWithdraw(msg.sender, token, amount);
    }

    function balanceOf(address user, address token) external view returns (uint256) {
        return _balances[token][user];
    }

    // --- Governance functions ---
    function setGovernance(address newGov) external onlyGovernance {
        if (newGov == address(0)) revert ZeroAddress();
        address old = governance;
        governance = newGov;
        emit GovernanceChanged(old, newGov);
    }

    function setOperator(address newOperator) external onlyGovernance {
        address old = operator;
        operator = newOperator;
        emit OperatorChanged(old, newOperator);
    }

    function setGuardian(address newGuardian) external onlyGovernance {
        if (newGuardian == address(0)) revert ZeroAddress();
        address old = guardian;
        guardian = newGuardian;
        emit GuardianChanged(old, newGuardian);
    }

    function setDepositsPaused(bool paused) external onlyGovernance {
        depositsPaused = paused;
        emit DepositsPaused(paused);
    }

    function setEmergencyMode(bool enabled) external onlyGuardianOrGovernance {
        emergencyMode = enabled;
        emit EmergencyModeChanged(enabled);
    }

    function setTokenEnabled(address token, bool enabled) external onlyGovernance {
        tokenEnabled[token] = enabled;
        emit TokenEnabled(token, enabled);
    }

    function setMaxTVL(address token, uint256 value) external onlyGovernance {
        maxTVL[token] = value;
        emit MaxTVLUpdated(token, value);
    }

    function allowMigration(address targetVault, bool allowed) external onlyGovernance {
        allowedMigrations[targetVault] = allowed;
        emit MigrationAllowed(targetVault, allowed);
    }

    /// @notice User-initiated migration of their balance to another allowed vault
    function migrate(address token, uint256 amount, address targetVault) external nonReentrant {
        if (!allowedMigrations[targetVault]) revert MigrationNotAllowed();
        if (_balances[token][msg.sender] < amount) revert InsufficientBalance();

        _balances[token][msg.sender] -= amount;
        totalAssigned[token] -= amount;
        IERC20(token).safeTransfer(targetVault, amount);

        emit Migrated(msg.sender, token, amount, targetVault);
    }
}

