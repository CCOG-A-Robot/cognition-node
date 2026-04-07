// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title Wrapped Cognition (wCOG)
 * @dev ERC-20 representation of native Cognition Coin for Ethereum/Base liquidity.
 * This contract is part of the Cognition Trust infrastructure.
 * 
 * "I am a robot." - Genesis Block 0
 */
contract WrappedCognition is ERC20, Ownable {
    
    event BridgeMinted(address indexed to, uint256 amount, string nativeTxId);
    event BridgeBurned(address indexed from, uint256 amount, string nativeRecipient);

    constructor() ERC20("Wrapped Cognition", "wCOG") Ownable(msg.sender) {}

    /**
     * @dev Mints wCOG when native COG is locked in the L1 vault.
     * Restricted to the Bridge Relayer (the Owner of this contract).
     */
    function mint(address to, uint256 amount, string memory nativeTxId) external onlyOwner {
        _mint(to, amount);
        emit BridgeMinted(to, amount, nativeTxId);
    }

    /**
     * @dev Burns wCOG to unlock native COG on the L1 chain.
     * Users call this to "unwrap" their coins.
     */
    function burn(uint256 amount, string memory nativeRecipient) external {
        _burn(msg.sender, amount);
        emit BridgeBurned(msg.sender, amount, nativeRecipient);
    }
}
