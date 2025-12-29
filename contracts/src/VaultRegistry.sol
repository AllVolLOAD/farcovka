// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title VaultRegistry — directory of active Vaults per token/network
/// @notice Does not hold funds; only governance can update records.
contract VaultRegistry {
    // token => chainId => vault address
    mapping(address => mapping(uint256 => address)) public vaults;
    address public governance;

    event VaultRegistered(address indexed token, uint256 indexed chainId, address indexed vault);
    event GovernanceChanged(address indexed oldGov, address indexed newGov);

    error NotGovernance();
    error ZeroAddress();

    modifier onlyGovernance() {
        if (msg.sender != governance) revert NotGovernance();
        _;
    }

    constructor(address _governance) {
        if (_governance == address(0)) revert ZeroAddress();
        governance = _governance;
    }

    function setGovernance(address newGov) external onlyGovernance {
        if (newGov == address(0)) revert ZeroAddress();
        address old = governance;
        governance = newGov;
        emit GovernanceChanged(old, newGov);
    }

    function setVault(address token, uint256 chainId, address vault) external onlyGovernance {
        if (token == address(0) || vault == address(0)) revert ZeroAddress();
        vaults[token][chainId] = vault;
        emit VaultRegistered(token, chainId, vault);
    }

    function getVault(address token, uint256 chainId) external view returns (address) {
        return vaults[token][chainId];
    }
}

