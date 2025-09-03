#!/usr/bin/env python3
"""Demo script showcasing ExecutionEngine security features."""

import logging
import sys
from pathlib import Path

# Add the parent directory to the path so we can import sai modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sai.core.execution_engine import ExecutionEngine
from sai.models.saidata import SaiData, Metadata


def setup_logging():
    """Set up logging for the demo."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def create_mock_engine():
    """Create a mock execution engine for security testing."""
    # Create an engine with no providers for testing security functions
    return ExecutionEngine([])


def main():
    """Main security demo function."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    print("=== SAI ExecutionEngine Security Demo ===\n")
    
    try:
        # Create execution engine for testing security features
        print("1. Creating execution engine for security testing...")
        engine = create_mock_engine()
        print("✅ ExecutionEngine created")
        
        # Test command security validation
        print("\n2. Testing command security validation...")
        
        # Test safe commands
        safe_commands = [
            ['apt', 'install', 'vim'],
            ['brew', 'install', 'git'],
            ['systemctl', 'status', 'nginx'],
            ['ls', '-la'],
        ]
        
        print("   Testing safe commands:")
        for cmd in safe_commands:
            validation = engine._validate_command_security(cmd, False)
            status = "✅ SAFE" if validation['valid'] else "❌ BLOCKED"
            print(f"     {' '.join(cmd)}: {status}")
        
        # Test potentially dangerous commands
        dangerous_commands = [
            ['rm', '-rf', '/'],
            ['sh', '-c', 'rm -rf /'],
            ['python', '-c', 'import os; os.system("rm -rf /")'],
            ['bash', '-c', 'echo $(whoami) && rm -rf /'],
            ['cmd', '/c', 'del /f /s /q C:\\*'],
        ]
        
        print("\n   Testing potentially dangerous commands:")
        for cmd in dangerous_commands:
            validation = engine._validate_command_security(cmd, False)
            status = "✅ SAFE" if validation['valid'] else "❌ BLOCKED"
            reason = f" ({validation.get('error', 'No reason')})" if not validation['valid'] else ""
            print(f"     {' '.join(cmd[:2])}...: {status}{reason}")
        
        # Test command sanitization
        print("\n3. Testing command argument sanitization...")
        
        dirty_args = [
            'normal-arg',
            'arg\0with\0nulls',
            'arg\nwith\nnewlines',
            'very-long-arg-' + 'x' * 5000,  # Very long argument
            'arg with spaces',
        ]
        
        print("   Original → Sanitized:")
        sanitized = engine._sanitize_command_args(dirty_args)
        for orig, clean in zip(dirty_args, sanitized):
            orig_display = orig[:30] + '...' if len(orig) > 30 else orig
            clean_display = clean[:30] + '...' if len(clean) > 30 else clean
            print(f"     '{orig_display}' → '{clean_display}'")
        
        # Test privilege escalation
        print("\n4. Testing privilege escalation handling...")
        
        test_cmd = ['apt', 'install', 'vim']
        
        # Test without root requirement
        result_no_root = engine._handle_privilege_escalation(test_cmd, False)
        print(f"   Without root: {' '.join(result_no_root)}")
        
        # Test with root requirement
        result_with_root = engine._handle_privilege_escalation(test_cmd, True)
        print(f"   With root: {' '.join(result_with_root)}")
        
        # Test secure environment
        print("\n5. Testing secure environment generation...")
        
        secure_env = engine._get_secure_environment()
        print("   Secure environment variables:")
        for key, value in sorted(secure_env.items()):
            value_display = value[:50] + '...' if len(value) > 50 else value
            print(f"     {key}={value_display}")
        
        # Test PATH security
        print(f"\n   Secure PATH contains {len(secure_env.get('PATH', '').split(':'))} entries")
        
        # Test executable safety checks
        print("\n6. Testing executable safety checks...")
        
        safe_executables = ['apt', 'brew', 'systemctl', 'ls', 'cat', 'grep']
        dangerous_executables = ['rm', 'dd', 'format', 'shutdown', 'passwd']
        
        print("   Safe executables:")
        for exe in safe_executables:
            is_safe = engine._is_safe_executable(exe)
            status = "✅ ALLOWED" if is_safe else "❌ BLOCKED"
            print(f"     {exe}: {status}")
        
        print("\n   Potentially dangerous executables:")
        for exe in dangerous_executables:
            is_safe = engine._is_safe_executable(exe)
            status = "✅ ALLOWED" if is_safe else "❌ BLOCKED"
            print(f"     {exe}: {status}")
        
        # Test root command safety
        print("\n7. Testing root command safety checks...")
        
        root_commands = [
            ['apt', 'install', 'vim'],
            ['systemctl', 'restart', 'nginx'],
            ['rm', '-rf', '/'],
            ['dd', 'if=/dev/zero', 'of=/dev/sda'],
        ]
        
        print("   Root command safety:")
        for cmd in root_commands:
            is_safe = engine._is_safe_root_command(cmd)
            status = "✅ SAFE" if is_safe else "❌ DANGEROUS"
            cmd_display = ' '.join(cmd[:3]) + ('...' if len(cmd) > 3 else '')
            print(f"     {cmd_display}: {status}")
        
        print("\n🔒 Security demo completed successfully!")
        print("\nKey security features demonstrated:")
        print("  ✅ Command injection prevention")
        print("  ✅ Argument sanitization")
        print("  ✅ Privilege escalation handling")
        print("  ✅ Secure environment variables")
        print("  ✅ Executable safety validation")
        print("  ✅ Root command safety checks")
        
    except Exception as e:
        logger.error(f"Security demo failed: {e}")
        print(f"❌ Security demo failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())