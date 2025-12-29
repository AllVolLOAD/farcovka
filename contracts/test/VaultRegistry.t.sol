// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {VaultRegistry} from "../VaultRegistry.sol";

contract VaultRegistryTest {
    VaultRegistry reg;
    address governance = address(this);

    function setUp() public {
        reg = new VaultRegistry(governance);
    }

    function testSetAndGetVault() public {
        address token = address(0x1);
        uint256 chainId = 11155111;
        address vault = address(0x2);

        reg.setVault(token, chainId, vault);
        assert(reg.getVault(token, chainId) == vault);
    }

    function testGovernanceTransfer() public {
        address newGov = address(0xBEEF);
        reg.setGovernance(newGov);
        bool reverted;
        try reg.setVault(address(0x1), 1, address(0x2)) {
            // should revert because msg.sender is old gov
        } catch {
            reverted = true;
        }
        assert(reverted);
    }
}

