"""Security utilities for SAI repository operations."""

import hashlib
import logging
import os
import re
import subprocess
import tempfile
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SecurityLevel(str, Enum):
    """Security validation levels."""
    STRICT = "strict"
    MODERATE = "moderate"
    PERMISSIVE = "permissive"


@dataclass
class SecurityValidationResult:
    """Result of a security validation check."""
    is_valid: bool
    security_level: SecurityLevel
    issues: List[str]
    warnings: List[str]
    recommendations: List[str]
    
    @property
    def has_issues(self) -> bool:
        """Check if there are any security issues."""
        return len(self.issues) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are any security warnings."""
        return len(self.warnings) > 0


@dataclass
class GitSignatureInfo:
    """Information about git signature verification."""
    is_signed: bool
    is_valid: bool
    signer: Optional[str] = None
    key_id: Optional[str] = None
    signature_type: Optional[str] = None  # "gpg", "ssh"
    trust_level: Optional[str] = None
    error_message: Optional[str] = None


class RepositorySecurityValidator:
    """Validates repository operations for security compliance."""
    
    def __init__(self, security_level: SecurityLevel = SecurityLevel.MODERATE):
        """Initialize the security validator.
        
        Args:
            security_level: Security validation level
        """
        self.security_level = security_level
        
        # URL validation patterns
        self._safe_url_patterns = [
            r'^https://github\.com/[\w\-\.]+/[\w\-\.]+/?(?:\.git)?$',
            r'^https://gitlab\.com/[\w\-\.]+/[\w\-\.]+/?(?:\.git)?$',
            r'^https://bitbucket\.org/[\w\-\.]+/[\w\-\.]+/?(?:\.git)?$',
            r'^git@github\.com:[\w\-\.]+/[\w\-\.]+\.git$',
            r'^git@gitlab\.com:[\w\-\.]+/[\w\-\.]+\.git$',
        ]
        
        # Dangerous URL patterns
        self._dangerous_url_patterns = [
            r'.*[;&|`$(){}[\]\\].*',  # Shell metacharacters
            r'.*\.\./.*',  # Path traversal
            r'^file://.*',  # Local file URLs
            r'^ftp://.*',  # Insecure FTP
            r'.*localhost.*',  # Local addresses
            r'.*127\.0\.0\.1.*',  # Loopback
            r'.*192\.168\..*',  # Private networks
            r'.*10\..*',  # Private networks
            r'.*172\.(1[6-9]|2[0-9]|3[01])\..*',  # Private networks
        ]
    
    def validate_repository_url(self, url: str) -> SecurityValidationResult:
        """Validate repository URL for security compliance.
        
        Args:
            url: Repository URL to validate
            
        Returns:
            SecurityValidationResult with validation details
        """
        issues = []
        warnings = []
        recommendations = []
        
        logger.debug(f"Validating repository URL: {url}")
        
        # Basic URL format validation
        try:
            parsed = urllib.parse.urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                issues.append("Invalid URL format")
                return SecurityValidationResult(
                    is_valid=False,
                    security_level=self.security_level,
                    issues=issues,
                    warnings=warnings,
                    recommendations=["Use a valid URL format (https://... or git@...)"]
                )
        except Exception as e:
            issues.append(f"URL parsing failed: {e}")
            return SecurityValidationResult(
                is_valid=False,
                security_level=self.security_level,
                issues=issues,
                warnings=warnings,
                recommendations=["Use a valid URL format"]
            )
        
        # Check for dangerous patterns
        for pattern in self._dangerous_url_patterns:
            if re.match(pattern, url, re.IGNORECASE):
                if self.security_level == SecurityLevel.STRICT:
                    issues.append(f"URL contains potentially dangerous pattern: {pattern}")
                else:
                    warnings.append(f"URL contains potentially risky pattern: {pattern}")
        
        # Protocol security checks
        if parsed.scheme == 'http':
            if self.security_level == SecurityLevel.STRICT:
                issues.append("HTTP URLs are not secure (use HTTPS)")
            else:
                warnings.append("HTTP URLs are not secure, consider using HTTPS")
                recommendations.append("Use HTTPS instead of HTTP for better security")
        
        elif parsed.scheme not in ['https', 'git', 'ssh']:
            if self.security_level in [SecurityLevel.STRICT, SecurityLevel.MODERATE]:
                issues.append(f"Unsupported or insecure protocol: {parsed.scheme}")
            else:
                warnings.append(f"Protocol may not be secure: {parsed.scheme}")
        
        # Check against known safe patterns
        is_known_safe = any(re.match(pattern, url) for pattern in self._safe_url_patterns)
        if not is_known_safe:
            if self.security_level == SecurityLevel.STRICT:
                warnings.append("URL is not from a known trusted source")
                recommendations.append("Consider using repositories from trusted sources like GitHub, GitLab, or Bitbucket")
            else:
                logger.debug(f"URL not in known safe patterns: {url}")
        
        # Domain validation
        if parsed.netloc:
            domain_issues = self._validate_domain(parsed.netloc)
            if self.security_level == SecurityLevel.STRICT:
                issues.extend(domain_issues)
            else:
                warnings.extend(domain_issues)
        
        is_valid = len(issues) == 0
        
        return SecurityValidationResult(
            is_valid=is_valid,
            security_level=self.security_level,
            issues=issues,
            warnings=warnings,
            recommendations=recommendations
        )
    
    def _validate_domain(self, domain: str) -> List[str]:
        """Validate domain for security issues.
        
        Args:
            domain: Domain to validate
            
        Returns:
            List of security issues found
        """
        issues = []
        
        # Remove port if present
        domain_only = domain.split(':')[0]
        
        # Check for IP addresses (should use domain names)
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', domain_only):
            issues.append("Direct IP addresses are discouraged, use domain names")
        
        # Check for suspicious domains
        suspicious_patterns = [
            r'.*\.tk$',  # Free TLD often used maliciously
            r'.*\.ml$',  # Free TLD often used maliciously
            r'.*\.ga$',  # Free TLD often used maliciously
            r'.*\.cf$',  # Free TLD often used maliciously
        ]
        
        for pattern in suspicious_patterns:
            if re.match(pattern, domain_only, re.IGNORECASE):
                issues.append(f"Domain uses potentially suspicious TLD: {domain_only}")
        
        return issues
    
    def validate_file_path(self, file_path: str, base_path: Optional[Path] = None) -> SecurityValidationResult:
        """Validate file path for security issues like path traversal.
        
        Args:
            file_path: File path to validate
            base_path: Base path for relative path validation
            
        Returns:
            SecurityValidationResult with validation details
        """
        issues = []
        warnings = []
        recommendations = []
        
        logger.debug(f"Validating file path: {file_path}")
        
        # Check for path traversal attempts
        if '..' in file_path:
            issues.append("Path contains parent directory references (..)")
            recommendations.append("Use absolute paths or paths within the allowed directory")
        
        # Check for absolute paths that might be dangerous
        if file_path.startswith('/'):
            if self.security_level == SecurityLevel.STRICT:
                issues.append("Absolute paths are not allowed")
            else:
                warnings.append("Absolute paths should be used carefully")
        
        # Check for suspicious characters
        suspicious_chars = ['|', '&', ';', '`', '$', '(', ')', '{', '}', '[', ']', '\\']
        found_chars = [char for char in suspicious_chars if char in file_path]
        if found_chars:
            issues.append(f"Path contains suspicious characters: {', '.join(found_chars)}")
        
        # Check for null bytes
        if '\x00' in file_path:
            issues.append("Path contains null bytes")
        
        # Validate against base path if provided
        if base_path:
            try:
                resolved_path = (base_path / file_path).resolve()
                if not str(resolved_path).startswith(str(base_path.resolve())):
                    issues.append("Path escapes the allowed base directory")
            except Exception as e:
                issues.append(f"Path resolution failed: {e}")
        
        is_valid = len(issues) == 0
        
        return SecurityValidationResult(
            is_valid=is_valid,
            security_level=self.security_level,
            issues=issues,
            warnings=warnings,
            recommendations=recommendations
        )


class GitSignatureVerifier:
    """Handles git signature verification operations."""
    
    def __init__(self):
        """Initialize the git signature verifier."""
        self._gpg_available = None
        self._git_available = None
    
    def is_gpg_available(self) -> bool:
        """Check if GPG is available for signature verification.
        
        Returns:
            True if GPG is available, False otherwise
        """
        if self._gpg_available is not None:
            return self._gpg_available
        
        try:
            result = subprocess.run(
                ['gpg', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            self._gpg_available = result.returncode == 0
            if self._gpg_available:
                logger.debug("GPG is available for signature verification")
            else:
                logger.debug("GPG is not available")
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            logger.debug("GPG availability check failed")
            self._gpg_available = False
        
        return self._gpg_available
    
    def is_git_available(self) -> bool:
        """Check if git is available for signature verification.
        
        Returns:
            True if git is available, False otherwise
        """
        if self._git_available is not None:
            return self._git_available
        
        try:
            result = subprocess.run(
                ['git', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            self._git_available = result.returncode == 0
            if self._git_available:
                logger.debug("Git is available for signature verification")
            else:
                logger.debug("Git is not available")
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            logger.debug("Git availability check failed")
            self._git_available = False
        
        return self._git_available
    
    def verify_commit_signature(self, repo_path: Path, commit_hash: Optional[str] = None) -> GitSignatureInfo:
        """Verify git commit signature.
        
        Args:
            repo_path: Path to git repository
            commit_hash: Specific commit hash to verify (defaults to HEAD)
            
        Returns:
            GitSignatureInfo with verification results
        """
        if not self.is_git_available():
            return GitSignatureInfo(
                is_signed=False,
                is_valid=False,
                error_message="Git is not available"
            )
        
        commit_ref = commit_hash or "HEAD"
        logger.debug(f"Verifying signature for commit {commit_ref} in {repo_path}")
        
        try:
            # Check if commit is signed
            result = subprocess.run(
                ['git', '-C', str(repo_path), 'verify-commit', commit_ref],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Commit is signed and valid
                signature_info = self._parse_git_signature_output(result.stderr)
                return GitSignatureInfo(
                    is_signed=True,
                    is_valid=True,
                    signer=signature_info.get('signer'),
                    key_id=signature_info.get('key_id'),
                    signature_type=signature_info.get('signature_type', 'gpg'),
                    trust_level=signature_info.get('trust_level')
                )
            else:
                # Check if it's unsigned or invalid
                if 'no signature found' in result.stderr.lower():
                    return GitSignatureInfo(
                        is_signed=False,
                        is_valid=False,
                        error_message="Commit is not signed"
                    )
                else:
                    return GitSignatureInfo(
                        is_signed=True,
                        is_valid=False,
                        error_message=result.stderr.strip()
                    )
        
        except subprocess.TimeoutExpired:
            return GitSignatureInfo(
                is_signed=False,
                is_valid=False,
                error_message="Signature verification timed out"
            )
        except Exception as e:
            return GitSignatureInfo(
                is_signed=False,
                is_valid=False,
                error_message=f"Signature verification failed: {e}"
            )
    
    def verify_tag_signature(self, repo_path: Path, tag_name: str) -> GitSignatureInfo:
        """Verify git tag signature.
        
        Args:
            repo_path: Path to git repository
            tag_name: Tag name to verify
            
        Returns:
            GitSignatureInfo with verification results
        """
        if not self.is_git_available():
            return GitSignatureInfo(
                is_signed=False,
                is_valid=False,
                error_message="Git is not available"
            )
        
        logger.debug(f"Verifying signature for tag {tag_name} in {repo_path}")
        
        try:
            # Check if tag is signed
            result = subprocess.run(
                ['git', '-C', str(repo_path), 'verify-tag', tag_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Tag is signed and valid
                signature_info = self._parse_git_signature_output(result.stderr)
                return GitSignatureInfo(
                    is_signed=True,
                    is_valid=True,
                    signer=signature_info.get('signer'),
                    key_id=signature_info.get('key_id'),
                    signature_type=signature_info.get('signature_type', 'gpg'),
                    trust_level=signature_info.get('trust_level')
                )
            else:
                # Check if it's unsigned or invalid
                if 'no signature found' in result.stderr.lower():
                    return GitSignatureInfo(
                        is_signed=False,
                        is_valid=False,
                        error_message="Tag is not signed"
                    )
                else:
                    return GitSignatureInfo(
                        is_signed=True,
                        is_valid=False,
                        error_message=result.stderr.strip()
                    )
        
        except subprocess.TimeoutExpired:
            return GitSignatureInfo(
                is_signed=False,
                is_valid=False,
                error_message="Tag signature verification timed out"
            )
        except Exception as e:
            return GitSignatureInfo(
                is_signed=False,
                is_valid=False,
                error_message=f"Tag signature verification failed: {e}"
            )
    
    def _parse_git_signature_output(self, output: str) -> Dict[str, str]:
        """Parse git signature verification output.
        
        Args:
            output: Git signature verification output
            
        Returns:
            Dictionary with parsed signature information
        """
        info = {}
        
        # Parse GPG signature information
        lines = output.split('\n')
        for line in lines:
            line = line.strip()
            
            if 'Good signature from' in line:
                # Extract signer information
                match = re.search(r'Good signature from "([^"]+)"', line)
                if match:
                    info['signer'] = match.group(1)
            
            elif 'using RSA key' in line or 'using DSA key' in line:
                # Extract key ID
                match = re.search(r'using \w+ key (\w+)', line)
                if match:
                    info['key_id'] = match.group(1)
            
            elif 'Primary key fingerprint:' in line:
                # Extract fingerprint
                match = re.search(r'Primary key fingerprint: (.+)', line)
                if match:
                    info['fingerprint'] = match.group(1).strip()
            
            elif 'WARNING' in line.upper():
                # Extract trust level warnings
                if 'trust' in line.lower():
                    info['trust_level'] = 'warning'
        
        return info


class ChecksumValidator:
    """Enhanced checksum validation with multiple algorithms."""
    
    SUPPORTED_ALGORITHMS = {
        'md5': hashlib.md5,
        'sha1': hashlib.sha1,
        'sha256': hashlib.sha256,
        'sha512': hashlib.sha512,
        'sha3_256': hashlib.sha3_256,
        'sha3_512': hashlib.sha3_512,
    }
    
    def __init__(self):
        """Initialize the checksum validator."""
        pass
    
    def validate_file_checksum(
        self,
        file_path: Path,
        expected_checksum: str,
        algorithm: str = 'sha256'
    ) -> Tuple[bool, str, Optional[str]]:
        """Validate file checksum with enhanced security.
        
        Args:
            file_path: Path to file to validate
            expected_checksum: Expected checksum value
            algorithm: Hash algorithm to use
            
        Returns:
            Tuple of (is_valid, calculated_checksum, error_message)
        """
        algorithm = algorithm.lower()
        
        if algorithm not in self.SUPPORTED_ALGORITHMS:
            return False, "", f"Unsupported algorithm: {algorithm}"
        
        if not file_path.exists():
            return False, "", f"File does not exist: {file_path}"
        
        try:
            logger.debug(f"Calculating {algorithm} checksum for {file_path}")
            
            hasher = self.SUPPORTED_ALGORITHMS[algorithm]()
            
            with open(file_path, 'rb') as f:
                # Read in chunks to handle large files efficiently
                while chunk := f.read(8192):
                    hasher.update(chunk)
            
            calculated_checksum = hasher.hexdigest().lower()
            expected_checksum = expected_checksum.lower()
            
            is_valid = calculated_checksum == expected_checksum
            
            if is_valid:
                logger.debug(f"Checksum validation passed: {calculated_checksum}")
            else:
                logger.warning(f"Checksum validation failed: expected {expected_checksum}, got {calculated_checksum}")
            
            return is_valid, calculated_checksum, None
            
        except Exception as e:
            error_msg = f"Checksum calculation failed: {e}"
            logger.error(error_msg)
            return False, "", error_msg
    
    def calculate_file_checksum(self, file_path: Path, algorithm: str = 'sha256') -> Tuple[Optional[str], Optional[str]]:
        """Calculate file checksum.
        
        Args:
            file_path: Path to file
            algorithm: Hash algorithm to use
            
        Returns:
            Tuple of (checksum, error_message)
        """
        is_valid, checksum, error = self.validate_file_checksum(file_path, "", algorithm)
        if error:
            return None, error
        return checksum, None


class PathTraversalProtector:
    """Protects against path traversal attacks during extraction."""
    
    def __init__(self, base_path: Path):
        """Initialize path traversal protector.
        
        Args:
            base_path: Base path that all extracted files must be within
        """
        self.base_path = base_path.resolve()
        logger.debug(f"Path traversal protection enabled for base path: {self.base_path}")
    
    def validate_extraction_path(self, member_path: str) -> Tuple[bool, Optional[str]]:
        """Validate that an extraction path is safe.
        
        Args:
            member_path: Path from archive member
            
        Returns:
            Tuple of (is_safe, error_message)
        """
        # Normalize the path
        member_path = member_path.strip()
        
        # Check for obvious path traversal attempts
        if member_path.startswith('/'):
            return False, f"Absolute path not allowed: {member_path}"
        
        if '..' in member_path:
            return False, f"Parent directory reference not allowed: {member_path}"
        
        if member_path.startswith('~'):
            return False, f"Home directory reference not allowed: {member_path}"
        
        # Check for null bytes
        if '\x00' in member_path:
            return False, f"Null byte in path: {member_path}"
        
        # Resolve the full path and check it's within base path
        try:
            full_path = (self.base_path / member_path).resolve()
            if not str(full_path).startswith(str(self.base_path)):
                return False, f"Path escapes base directory: {member_path}"
        except Exception as e:
            return False, f"Path resolution failed: {e}"
        
        return True, None
    
    def get_safe_extraction_path(self, member_path: str) -> Optional[Path]:
        """Get safe extraction path for a member.
        
        Args:
            member_path: Path from archive member
            
        Returns:
            Safe path within base directory, or None if unsafe
        """
        is_safe, error = self.validate_extraction_path(member_path)
        if not is_safe:
            logger.warning(f"Unsafe extraction path blocked: {error}")
            return None
        
        return self.base_path / member_path