// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title Ownable
 * @dev Contract module which provides a basic access control mechanism, where
 * there is an account (an owner) that can be granted exclusive access to
 * specific functions.
 */
abstract contract Ownable {
    address private _owner;

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    constructor() {
        _transferOwnership(msg.sender);
    }

    function owner() public view virtual returns (address) {
        return _owner;
    }

    modifier onlyOwner() {
        _checkOwner();
        _;
    }

    function _checkOwner() internal view virtual {
        require(owner() == msg.sender, "Ownable: caller is not the owner");
    }

    function transferOwnership(address newOwner) public virtual onlyOwner {
        require(newOwner != address(0), "Ownable: new owner is the zero address");
        _transferOwnership(newOwner);
    }

    function _transferOwnership(address newOwner) internal virtual {
        address oldOwner = _owner;
        _owner = newOwner;
        emit OwnershipTransferred(oldOwner, newOwner);
    }
}

/**
 * @title Certificate
 * @dev Blockchain registry for immutable academic and professional certificate verification.
 */
contract Certificate is Ownable {

    struct CertificateRecord {
        bytes32 certificateHash;
        address issuer;
        uint256 timestamp;
        bool exists;
    }

    // Mapping from unique Certificate ID (e.g. CERT-2025-0001) to on-chain record
    mapping(string => CertificateRecord) private certificates;

    // Event emitted whenever a certificate is minted/issued
    event CertificateIssued(
        string indexed certificateIdIndex,
        string certificateId,
        bytes32 certificateHash,
        address indexed issuer,
        uint256 timestamp
    );

    /**
     * @dev Issue and anchor a new certificate on the blockchain.
     * @param certificateId Unique human-readable certificate identifier
     * @param certificateHash SHA-256 hash of the certificate document (bytes32)
     */
    function issueCertificate(string calldata certificateId, bytes32 certificateHash) external onlyOwner {
        require(bytes(certificateId).length > 0, "Certificate: certificateId cannot be empty");
        require(certificateHash != bytes32(0), "Certificate: certificateHash cannot be empty");
        require(!certificates[certificateId].exists, "Certificate: duplicate certificateId already exists");

        certificates[certificateId] = CertificateRecord({
            certificateHash: certificateHash,
            issuer: msg.sender,
            timestamp: block.timestamp,
            exists: true
        });

        emit CertificateIssued(certificateId, certificateId, certificateHash, msg.sender, block.timestamp);
    }

    /**
     * @dev Verify if a given certificate ID matches the provided hash.
     * @param certificateId Unique certificate identifier
     * @param certificateHash SHA-256 hash of the document to verify
     * @return bool True if certificate exists and hash matches exactly
     */
    function verifyCertificate(string calldata certificateId, bytes32 certificateHash) external view returns (bool) {
        CertificateRecord memory record = certificates[certificateId];
        if (!record.exists) {
            return false;
        }
        return record.certificateHash == certificateHash;
    }

    /**
     * @dev Retrieve the stored hash, issuer, and issuance timestamp for a certificate ID.
     * @param certificateId Unique certificate identifier
     * @return certificateHash The SHA-256 fingerprint anchored on chain
     * @return issuer The address of the issuing authority
     * @return timestamp The block timestamp when the certificate was issued
     */
    function getCertificateHash(string calldata certificateId) external view returns (
        bytes32 certificateHash,
        address issuer,
        uint256 timestamp
    ) {
        CertificateRecord memory record = certificates[certificateId];
        require(record.exists, "Certificate: certificate not found");
        return (record.certificateHash, record.issuer, record.timestamp);
    }

    /**
     * @dev Check if a certificate ID has been registered.
     * @param certificateId Unique certificate identifier
     * @return bool True if registered
     */
    function certificateExists(string calldata certificateId) external view returns (bool) {
        return certificates[certificateId].exists;
    }
}
