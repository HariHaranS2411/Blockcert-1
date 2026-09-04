class BlockCertException(Exception):
    """Base exception class for BlockCert application."""
    def __init__(self, message="An application error occurred", status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class BlockchainError(BlockCertException):
    """Raised when an on-chain transaction or call fails."""
    def __init__(self, message="Blockchain transaction failed", status_code=502):
        super().__init__(message, status_code)


class ContractNotDeployedError(BlockchainError):
    """Raised when the contract address is not configured or not deployed."""
    def __init__(self, message="Smart contract address not configured or not found on the blockchain network"):
        super().__init__(message, status_code=503)


class CertificateNotFoundError(BlockCertException):
    """Raised when a certificate cannot be found in the database or blockchain."""
    def __init__(self, message="Certificate not found", status_code=404):
        super().__init__(message, status_code)


class CertificateTamperedError(BlockCertException):
    """Raised when a certificate hash does not match the blockchain hash."""
    def __init__(self, message="Certificate document integrity check failed (Tampered)", status_code=400):
        super().__init__(message, status_code)
