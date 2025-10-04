"""Checksum validation system for saidata 0.3 schema.

This module provides checksum format validation and verification utilities
for sources, binaries, and scripts sections in saidata files.
"""

import re
import hashlib
from typing import Optional, Tuple, List
from enum import Enum


class ChecksumAlgorithm(Enum):
    """Supported checksum algorithms."""
    SHA256 = "sha256"
    SHA512 = "sha512"
    MD5 = "md5"


class ChecksumValidationError(Exception):
    """Raised when checksum validation fails."""
    pass


class ChecksumValidator:
    """Validates checksum formats and provides verification utilities."""
    
    # Supported algorithms and their expected hash lengths
    ALGORITHM_SPECS = {
        ChecksumAlgorithm.SHA256: {
            'length': 64,
            'pattern': r'^[a-fA-F0-9]{64}$',
            'hashlib_name': 'sha256'
        },
        ChecksumAlgorithm.SHA512: {
            'length': 128,
            'pattern': r'^[a-fA-F0-9]{128}$',
            'hashlib_name': 'sha512'
        },
        ChecksumAlgorithm.MD5: {
            'length': 32,
            'pattern': r'^[a-fA-F0-9]{32}$',
            'hashlib_name': 'md5'
        }
    }
    
    # Pattern for checksum format: algorithm:hash
    CHECKSUM_FORMAT_PATTERN = re.compile(r'^([a-zA-Z0-9]+):([a-fA-F0-9]+)$')
    
    def parse_checksum(self, checksum: str) -> Tuple[ChecksumAlgorithm, str]:
        """Parse checksum string into algorithm and hash components.
        
        Args:
            checksum: Checksum string in format "algorithm:hash"
            
        Returns:
            Tuple of (algorithm, hash_value)
            
        Raises:
            ChecksumValidationError: If checksum format is invalid
        """
        if not checksum:
            raise ChecksumValidationError("Checksum cannot be empty")
        
        match = self.CHECKSUM_FORMAT_PATTERN.match(checksum)
        if not match:
            raise ChecksumValidationError(
                f"Invalid checksum format: {checksum}. Expected format: algorithm:hash"
            )
        
        algorithm_str, hash_value = match.groups()
        
        # Convert algorithm string to enum
        try:
            algorithm = ChecksumAlgorithm(algorithm_str.lower())
        except ValueError:
            supported_algorithms = [alg.value for alg in ChecksumAlgorithm]
            raise ChecksumValidationError(
                f"Unsupported algorithm: {algorithm_str}. "
                f"Supported algorithms: {', '.join(supported_algorithms)}"
            )
        
        return algorithm, hash_value
    
    def validate_checksum(self, checksum: str) -> List[str]:
        """Validate checksum format and return any errors.
        
        Args:
            checksum: Checksum string to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not checksum:
            errors.append("Checksum cannot be empty")
            return errors
        
        if not isinstance(checksum, str):
            errors.append("Checksum must be a string")
            return errors
        
        try:
            algorithm, hash_value = self.parse_checksum(checksum)
            
            # Validate hash format for the algorithm
            if not self._validate_algorithm_and_hash(algorithm, hash_value):
                spec = self.ALGORITHM_SPECS[algorithm]
                errors.append(
                    f"Invalid {algorithm.value} hash format. "
                    f"Expected {spec['length']} hexadecimal characters, got {len(hash_value)}"
                )
                
        except ChecksumValidationError as e:
            errors.append(str(e))
        
        return errors
    
    def compute_checksum(self, data: bytes, algorithm: ChecksumAlgorithm) -> str:
        """Compute checksum for given data using specified algorithm.
        
        Args:
            data: Binary data to compute checksum for
            algorithm: Checksum algorithm to use
            
        Returns:
            Checksum string in format "algorithm:hash"
            
        Raises:
            ChecksumValidationError: If algorithm is not supported
        """
        if algorithm not in self.ALGORITHM_SPECS:
            raise ChecksumValidationError(f"Unsupported algorithm: {algorithm}")
        
        spec = self.ALGORITHM_SPECS[algorithm]
        hasher = hashlib.new(spec['hashlib_name'])
        hasher.update(data)
        hash_value = hasher.hexdigest()
        
        return f"{algorithm.value}:{hash_value}"
    
    def _validate_algorithm_and_hash(self, algorithm: ChecksumAlgorithm, hash_value: str) -> bool:
        """Validate that hash value matches the expected format for the algorithm.
        
        Args:
            algorithm: Checksum algorithm
            hash_value: Hash value to validate
            
        Returns:
            True if hash format is valid for the algorithm
        """
        if algorithm not in self.ALGORITHM_SPECS:
            return False
        
        spec = self.ALGORITHM_SPECS[algorithm]
        pattern = re.compile(spec['pattern'])
        return bool(pattern.match(hash_value))
    
    def _constant_time_compare(self, a: str, b: str) -> bool:
        """Compare two strings in constant time to prevent timing attacks.
        
        Args:
            a: First string
            b: Second string
            
        Returns:
            True if strings are equal
        """
        if len(a) != len(b):
            return False
        
        result = 0
        for x, y in zip(a, b):
            result |= ord(x) ^ ord(y)
        
        return result == 0