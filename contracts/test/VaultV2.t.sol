// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Minimal self-contained tests without forge-std cheats; uses simple asserts.
import {VaultV2} from "../VaultV2.sol";
import {MockERC20} from "./MockERC20.sol";

contract VaultV2Test {
    VaultV2 vault;
    MockERC20 token;

    address governance = address(0xA11CE);
    address guardian = address(0xBEEF);
    address user = address(this); // Using this as user for simplicity (no prank)

    function setUp() public {
        vault = new VaultV2(governance, guardian);
        token = new MockERC20("Mock", "MOCK");

        // enable token, set maxTVL
        vault.setTokenEnabled(address(token), true);
        vault.setMaxTVL(address(token), type(uint256).max);
        token.mint(user, 1_000 ether);
        token.approve(address(vault), type(uint256).max);
    }

    function testDepositWithdraw() public {
        setUp();
        uint256 amt = 100 ether;
        vault.deposit(address(token), amt);
        assert(token.balanceOf(address(vault)) == amt);
        assert(vaultBalance(user) == amt);

        vault.withdraw(address(token), 40 ether);
        assert(vaultBalance(user) == 60 ether);
        assert(token.balanceOf(address(this)) == 1_000 ether - 60 ether);
    }

    function testEmergencyWithdrawAlways() public {
        setUp();
        uint256 amt = 50 ether;
        vault.deposit(address(token), amt);
        // Governance pauses deposits and flips emergency
        vault.setDepositsPaused(true);
        vault.setEmergencyMode(true);
        vault.emergencyWithdraw(address(token), amt);
        assert(vaultBalance(user) == 0);
        assert(token.balanceOf(address(this)) == 1_000 ether);
    }

    function testMigrationAllowedOnly() public {
        setUp();
        uint256 amt = 10 ether;
        vault.deposit(address(token), amt);

        address target = address(0xCAFE);
        // not allowed yet
        bool reverted;
        try vault.migrate(address(token), amt, target) {} catch {
            reverted = true;
        }
        assert(reverted);

        // allow and migrate
        vault.allowMigration(target, true);
        uint256 balBefore = token.balanceOf(target);
        vault.migrate(address(token), amt, target);
        assert(vaultBalance(user) == 0);
        assert(token.balanceOf(target) == balBefore + amt);
    }

    function vaultBalance(address u) internal view returns (uint256) {
        return vault.balanceOf(u, address(token));
    }
}

