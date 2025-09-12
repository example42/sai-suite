"""Secure credential storage for SAI repository operations."""

import json
import logging
import os
import stat
from pathlib import Path
from typing import Dict, Optional, Any, Tuple, List
from dataclasses import dataclass, asdict
from enum import Enum
import base64
import hashlib

logger = logging.getLogger(__name__)


class CredentialType(str, Enum):
    """Types of credentials that can be stored."""
    SSH_KEY = "ssh_key"
    ACCESS_TOKEN = "access_token"
    USERNAME_PASSWORD = "username_password"
    API_KEY = "api_key"


@dataclass
class StoredCredential:
    """Represents a stored credential."""
    credential_type: CredentialType
    repository_url: str
    username: Optional[str] = None
    encrypted_data: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    last_used: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StoredCredential':
        """Create from dictionary."""
        return cls(**data)


class SimpleEncryption:
    """Simple encryption for credential storage.
    
    Note: This is a basic implementation for demonstration.
    In production, consider using more robust encryption libraries
    like cryptography or integrating with system keyrings.
    """
    
    def __init__(self, key: Optional[bytes] = None):
        """Initialize encryption with a key.
        
        Args:
            key: Encryption key. If None, derives from system info.
        """
        if key is None:
            # Derive key from system information (basic approach)
            # In production, use proper key derivation functions
            system_info = f"{os.getuid()}{os.getgid()}{Path.home()}"
            self.key = hashlib.sha256(system_info.encode()).digest()
        else:
            self.key = key
    
    def encrypt(self, data: str) -> str:
        """Encrypt string data.
        
        Args:
            data: String to encrypt
            
        Returns:
            Base64 encoded encrypted data
        """
        try:
            # Simple XOR encryption (for demonstration)
            # In production, use proper encryption algorithms
            data_bytes = data.encode('utf-8')
            encrypted = bytearray()
            
            for i, byte in enumerate(data_bytes):
                key_byte = self.key[i % len(self.key)]
                encrypted.append(byte ^ key_byte)
            
            return base64.b64encode(bytes(encrypted)).decode('ascii')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data.
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            
        Returns:
            Decrypted string
        """
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode('ascii'))
            decrypted = bytearray()
            
            for i, byte in enumerate(encrypted_bytes):
                key_byte = self.key[i % len(self.key)]
                decrypted.append(byte ^ key_byte)
            
            return bytes(decrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise


class SecureCredentialStore:
    """Secure storage for repository credentials."""
    
    def __init__(self, store_path: Optional[Path] = None):
        """Initialize credential store.
        
        Args:
            store_path: Path to credential store file
        """
        if store_path is None:
            store_path = Path.home() / ".sai" / "credentials" / "repository_credentials.json"
        
        self.store_path = store_path
        self.encryption = SimpleEncryption()
        
        # Ensure store directory exists with secure permissions
        self.store_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        
        # Set secure permissions on parent directory
        try:
            os.chmod(self.store_path.parent, stat.S_IRWXU)  # 700 - owner only
        except OSError as e:
            logger.warning(f"Could not set secure permissions on credential directory: {e}")
    
    def store_credential(
        self,
        repository_url: str,
        credential_type: CredentialType,
        credential_data: Dict[str, str],
        username: Optional[str] = None
    ) -> bool:
        """Store a credential securely.
        
        Args:
            repository_url: Repository URL this credential is for
            credential_type: Type of credential
            credential_data: Credential data to store
            username: Optional username associated with credential
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            logger.debug(f"Storing {credential_type} credential for {repository_url}")
            
            # Load existing credentials
            credentials = self._load_credentials()
            
            # Create credential key
            credential_key = self._get_credential_key(repository_url, credential_type, username)
            
            # Encrypt credential data
            encrypted_data = self.encryption.encrypt(json.dumps(credential_data))
            
            # Create stored credential
            from datetime import datetime
            stored_credential = StoredCredential(
                credential_type=credential_type,
                repository_url=repository_url,
                username=username,
                encrypted_data=encrypted_data,
                created_at=datetime.now().isoformat(),
                metadata={
                    'keys': list(credential_data.keys())  # Store keys for reference
                }
            )
            
            # Store credential
            credentials[credential_key] = stored_credential.to_dict()
            
            # Save to file
            return self._save_credentials(credentials)
            
        except Exception as e:
            logger.error(f"Failed to store credential: {e}")
            return False
    
    def retrieve_credential(
        self,
        repository_url: str,
        credential_type: CredentialType,
        username: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        """Retrieve a stored credential.
        
        Args:
            repository_url: Repository URL
            credential_type: Type of credential
            username: Optional username
            
        Returns:
            Decrypted credential data or None if not found
        """
        try:
            logger.debug(f"Retrieving {credential_type} credential for {repository_url}")
            
            # Load credentials
            credentials = self._load_credentials()
            
            # Get credential key
            credential_key = self._get_credential_key(repository_url, credential_type, username)
            
            if credential_key not in credentials:
                logger.debug(f"No credential found for key: {credential_key}")
                return None
            
            # Load stored credential
            stored_data = credentials[credential_key]
            stored_credential = StoredCredential.from_dict(stored_data)
            
            # Decrypt credential data
            if stored_credential.encrypted_data:
                decrypted_json = self.encryption.decrypt(stored_credential.encrypted_data)
                credential_data = json.loads(decrypted_json)
                
                # Update last used timestamp
                from datetime import datetime
                stored_credential.last_used = datetime.now().isoformat()
                credentials[credential_key] = stored_credential.to_dict()
                self._save_credentials(credentials)
                
                logger.debug(f"Successfully retrieved credential for {repository_url}")
                return credential_data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve credential: {e}")
            return None
    
    def delete_credential(
        self,
        repository_url: str,
        credential_type: CredentialType,
        username: Optional[str] = None
    ) -> bool:
        """Delete a stored credential.
        
        Args:
            repository_url: Repository URL
            credential_type: Type of credential
            username: Optional username
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            logger.debug(f"Deleting {credential_type} credential for {repository_url}")
            
            # Load credentials
            credentials = self._load_credentials()
            
            # Get credential key
            credential_key = self._get_credential_key(repository_url, credential_type, username)
            
            if credential_key in credentials:
                del credentials[credential_key]
                return self._save_credentials(credentials)
            else:
                logger.debug(f"No credential found to delete: {credential_key}")
                return True  # Not an error if it doesn't exist
            
        except Exception as e:
            logger.error(f"Failed to delete credential: {e}")
            return False
    
    def list_credentials(self) -> List[Dict[str, Any]]:
        """List all stored credentials (without sensitive data).
        
        Returns:
            List of credential metadata
        """
        try:
            credentials = self._load_credentials()
            
            result = []
            for key, data in credentials.items():
                stored_credential = StoredCredential.from_dict(data)
                result.append({
                    'repository_url': stored_credential.repository_url,
                    'credential_type': stored_credential.credential_type,
                    'username': stored_credential.username,
                    'created_at': stored_credential.created_at,
                    'last_used': stored_credential.last_used,
                    'metadata': stored_credential.metadata
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to list credentials: {e}")
            return []
    
    def clear_all_credentials(self) -> bool:
        """Clear all stored credentials.
        
        Returns:
            True if cleared successfully, False otherwise
        """
        try:
            logger.info("Clearing all stored credentials")
            return self._save_credentials({})
        except Exception as e:
            logger.error(f"Failed to clear credentials: {e}")
            return False
    
    def _get_credential_key(
        self,
        repository_url: str,
        credential_type: CredentialType,
        username: Optional[str] = None
    ) -> str:
        """Generate a unique key for a credential.
        
        Args:
            repository_url: Repository URL
            credential_type: Type of credential
            username: Optional username
            
        Returns:
            Unique credential key
        """
        # Normalize URL for consistent keys
        normalized_url = repository_url.lower().rstrip('/')
        if normalized_url.endswith('.git'):
            normalized_url = normalized_url[:-4]
        
        key_parts = [normalized_url, credential_type.value]
        if username:
            key_parts.append(username)
        
        return '|'.join(key_parts)
    
    def _load_credentials(self) -> Dict[str, Any]:
        """Load credentials from storage file.
        
        Returns:
            Dictionary of stored credentials
        """
        if not self.store_path.exists():
            return {}
        
        try:
            with open(self.store_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load credentials file: {e}")
            return {}
    
    def _save_credentials(self, credentials: Dict[str, Any]) -> bool:
        """Save credentials to storage file.
        
        Args:
            credentials: Dictionary of credentials to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Write to temporary file first for atomic operation
            temp_path = self.store_path.with_suffix('.tmp')
            
            with open(temp_path, 'w') as f:
                json.dump(credentials, f, indent=2)
            
            # Set secure file permissions (readable only by owner)
            os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR)  # 600
            
            # Atomic move
            temp_path.replace(self.store_path)
            
            logger.debug(f"Credentials saved to {self.store_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
            # Clean up temp file if it exists
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            return False


class SystemKeychainIntegration:
    """Integration with system keychain services."""
    
    def __init__(self):
        """Initialize keychain integration."""
        self._keyring_available = None
    
    def is_keyring_available(self) -> bool:
        """Check if system keyring is available.
        
        Returns:
            True if keyring is available, False otherwise
        """
        if self._keyring_available is not None:
            return self._keyring_available
        
        try:
            import keyring
            # Test keyring functionality
            keyring.get_keyring()
            self._keyring_available = True
            logger.debug("System keyring is available")
        except ImportError:
            logger.debug("keyring library not available")
            self._keyring_available = False
        except Exception as e:
            logger.debug(f"Keyring not available: {e}")
            self._keyring_available = False
        
        return self._keyring_available
    
    def store_in_keyring(self, service: str, username: str, password: str) -> bool:
        """Store credential in system keyring.
        
        Args:
            service: Service name (e.g., repository URL)
            username: Username
            password: Password or token
            
        Returns:
            True if stored successfully, False otherwise
        """
        if not self.is_keyring_available():
            return False
        
        try:
            import keyring
            keyring.set_password(service, username, password)
            logger.debug(f"Stored credential in keyring for {service}")
            return True
        except Exception as e:
            logger.error(f"Failed to store credential in keyring: {e}")
            return False
    
    def retrieve_from_keyring(self, service: str, username: str) -> Optional[str]:
        """Retrieve credential from system keyring.
        
        Args:
            service: Service name
            username: Username
            
        Returns:
            Password/token or None if not found
        """
        if not self.is_keyring_available():
            return None
        
        try:
            import keyring
            password = keyring.get_password(service, username)
            if password:
                logger.debug(f"Retrieved credential from keyring for {service}")
            return password
        except Exception as e:
            logger.error(f"Failed to retrieve credential from keyring: {e}")
            return None
    
    def delete_from_keyring(self, service: str, username: str) -> bool:
        """Delete credential from system keyring.
        
        Args:
            service: Service name
            username: Username
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.is_keyring_available():
            return False
        
        try:
            import keyring
            keyring.delete_password(service, username)
            logger.debug(f"Deleted credential from keyring for {service}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete credential from keyring: {e}")
            return False


class CredentialManager:
    """High-level credential management interface."""
    
    def __init__(self, prefer_keyring: bool = True):
        """Initialize credential manager.
        
        Args:
            prefer_keyring: Whether to prefer system keyring over file storage
        """
        self.secure_store = SecureCredentialStore()
        self.keychain = SystemKeychainIntegration()
        self.prefer_keyring = prefer_keyring and self.keychain.is_keyring_available()
        
        if self.prefer_keyring:
            logger.debug("Using system keyring for credential storage")
        else:
            logger.debug("Using file-based credential storage")
    
    def store_ssh_key(self, repository_url: str, ssh_key_path: str, username: Optional[str] = None) -> bool:
        """Store SSH key path for repository.
        
        Args:
            repository_url: Repository URL
            ssh_key_path: Path to SSH private key
            username: Optional username
            
        Returns:
            True if stored successfully, False otherwise
        """
        credential_data = {'ssh_key_path': ssh_key_path}
        return self.secure_store.store_credential(
            repository_url,
            CredentialType.SSH_KEY,
            credential_data,
            username
        )
    
    def store_access_token(self, repository_url: str, token: str, username: Optional[str] = None) -> bool:
        """Store access token for repository.
        
        Args:
            repository_url: Repository URL
            token: Access token
            username: Optional username
            
        Returns:
            True if stored successfully, False otherwise
        """
        if self.prefer_keyring:
            service_name = f"sai-repo:{repository_url}"
            return self.keychain.store_in_keyring(service_name, username or "token", token)
        else:
            credential_data = {'token': token}
            return self.secure_store.store_credential(
                repository_url,
                CredentialType.ACCESS_TOKEN,
                credential_data,
                username
            )
    
    def store_username_password(self, repository_url: str, username: str, password: str) -> bool:
        """Store username/password for repository.
        
        Args:
            repository_url: Repository URL
            username: Username
            password: Password
            
        Returns:
            True if stored successfully, False otherwise
        """
        if self.prefer_keyring:
            service_name = f"sai-repo:{repository_url}"
            return self.keychain.store_in_keyring(service_name, username, password)
        else:
            credential_data = {'username': username, 'password': password}
            return self.secure_store.store_credential(
                repository_url,
                CredentialType.USERNAME_PASSWORD,
                credential_data,
                username
            )
    
    def get_credentials(self, repository_url: str) -> Optional[Dict[str, str]]:
        """Get credentials for repository.
        
        Args:
            repository_url: Repository URL
            
        Returns:
            Dictionary with credential data or None if not found
        """
        # Try different credential types in order of preference
        
        # Try SSH key first
        ssh_creds = self.secure_store.retrieve_credential(
            repository_url, CredentialType.SSH_KEY
        )
        if ssh_creds:
            return {'auth_type': 'ssh', **ssh_creds}
        
        # Try access token
        if self.prefer_keyring:
            service_name = f"sai-repo:{repository_url}"
            token = self.keychain.retrieve_from_keyring(service_name, "token")
            if token:
                return {'auth_type': 'token', 'token': token}
        else:
            token_creds = self.secure_store.retrieve_credential(
                repository_url, CredentialType.ACCESS_TOKEN
            )
            if token_creds:
                return {'auth_type': 'token', **token_creds}
        
        # Try username/password
        if self.prefer_keyring:
            # We need to know the username to retrieve from keyring
            # This is a limitation of keyring-based storage
            pass
        else:
            user_pass_creds = self.secure_store.retrieve_credential(
                repository_url, CredentialType.USERNAME_PASSWORD
            )
            if user_pass_creds:
                return {'auth_type': 'basic', **user_pass_creds}
        
        return None
    
    def delete_credentials(self, repository_url: str) -> bool:
        """Delete all credentials for repository.
        
        Args:
            repository_url: Repository URL
            
        Returns:
            True if deleted successfully, False otherwise
        """
        success = True
        
        # Delete from secure store
        for cred_type in CredentialType:
            if not self.secure_store.delete_credential(repository_url, cred_type):
                success = False
        
        # Delete from keyring if available
        if self.prefer_keyring:
            service_name = f"sai-repo:{repository_url}"
            # Try common usernames
            for username in ["token", "oauth", "git"]:
                self.keychain.delete_from_keyring(service_name, username)
        
        return success