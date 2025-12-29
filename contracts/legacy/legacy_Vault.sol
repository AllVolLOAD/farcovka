// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title FarCovka HOT Vault
 * @notice Custodial smart contract that stores ERC-20 assets on behalf of users.
 * Deposits emit events that backend listens to, withdrawals are initiated by service admin.
 */
contract Vault {
    /// @dev Minimal ERC-20 interface
    interface IERC20 {
        function transfer(address to, uint256 amount) external returns (bool);
        function transferFrom(address from, address to, uint256 amount) external returns (bool);
    }

    IERC20 public immutable asset;
    address public admin;

    mapping(address => uint256) public balances;

    event Deposit(address indexed user, uint256 amount);
    event Withdraw(address indexed user, address indexed to, uint256 amount);
    event AdminUpdated(address indexed previousAdmin, address indexed newAdmin);

    modifier onlyAdmin() {
        require(msg.sender == admin, "Vault: not admin");
        _;
    }

    constructor(address tokenAddress, address initialAdmin) {
        require(tokenAddress != address(0), "Vault: token is zero");
        require(initialAdmin != address(0), "Vault: admin is zero");
        asset = IERC20(tokenAddress);
        admin = initialAdmin;
        emit AdminUpdated(address(0), initialAdmin);
    }

    function setAdmin(address newAdmin) external onlyAdmin {
        require(newAdmin != address(0), "Vault: admin is zero");
        emit AdminUpdated(admin, newAdmin);
        admin = newAdmin;
    }

    /**
     * @notice Deposit tokens into the vault.
     * User must approve the Vault contract beforehand.
     */
    function deposit(uint256 amount) external {
        require(amount > 0, "Vault: amount is zero");
        require(asset.transferFrom(msg.sender, address(this), amount), "Vault: transfer failed");
        balances[msg.sender] += amount;
        emit Deposit(msg.sender, amount);
    }

    /**
     * @notice Withdraw tokens from the vault to specified address.
     * Can only be called by admin on behalf of user (after KYC / checks).
     */
    function withdraw(address user, address to, uint256 amount) external onlyAdmin {
        require(user != address(0) && to != address(0), "Vault: zero address");
        require(amount > 0, "Vault: amount is zero");
        uint256 userBalance = balances[user];
        require(userBalance >= amount, "Vault: insufficient balance");

        balances[user] = userBalance - amount;
        require(asset.transfer(to, amount), "Vault: transfer failed");
        emit Withdraw(user, to, amount);
    }
}

