# Default.yaml Package Name Policy - Clarification

## Issue Identified

The original requirements had the logic backwards for when to include package names in `default.yaml` provider sections.

## Corrected Logic

### Rule: Include Common Package Names in default.yaml

**If a package name is CONSISTENT across OS versions** → Include it in `default.yaml` provider section

**If a package name DIFFERS for specific OS versions** → Include the common name in `default.yaml`, override only where it differs

**NEVER include versions in provider sections of default.yaml** → Versions are always OS-specific

## Examples

### Example 1: Apache (Common Name Across OS Versions)

Most apt-based systems use `apache2` as the package name. Only a few exceptions exist.

```yaml
# default.yaml
metadata:
  name: apache
packages:
  - name: main
    package_name: httpd
    version: "2.4.58"  # Upstream version

providers:
  apt:
    packages:
      - name: main
        package_name: apache2  # ✅ Include because it's common across most OS versions
        # ❌ NO version here
```

```yaml
# ubuntu/22.04.yaml
providers:
  apt:
    packages:
      - name: main
        # package_name: apache2 (inherited from default.yaml)
        version: "2.4.52"  # ✅ Only version differs
```

```yaml
# debian/9.yaml (EXCEPTION - different package name)
providers:
  apt:
    packages:
      - name: main
        package_name: apache2-bin  # ✅ Override ONLY because Debian 9 differs
        version: "2.4.25"
```

### Example 2: Nginx (Name Varies by OS)

Ubuntu uses `nginx-core`, Debian uses `nginx`, others may vary.

```yaml
# default.yaml
metadata:
  name: nginx
packages:
  - name: main
    package_name: nginx
    version: "1.25.3"  # Upstream version

providers:
  apt:
    packages:
      - name: main
        package_name: nginx  # ✅ Include the most common name
        # ❌ NO version here
```

```yaml
# ubuntu/22.04.yaml
providers:
  apt:
    packages:
      - name: main
        package_name: nginx-core  # ✅ Override because Ubuntu differs
        version: "1.18.0"
```

```yaml
# debian/11.yaml
providers:
  apt:
    packages:
      - name: main
        # package_name: nginx (inherited from default.yaml - same as common)
        version: "1.18.0"  # ✅ Only version differs
```

### Example 3: PostgreSQL (Consistent Name)

PostgreSQL uses `postgresql` across all apt-based systems.

```yaml
# default.yaml
metadata:
  name: postgresql
packages:
  - name: main
    package_name: postgresql
    version: "16.1"  # Upstream version

providers:
  apt:
    packages:
      - name: main
        package_name: postgresql  # ✅ Include because it's consistent everywhere
        # ❌ NO version here
```

```yaml
# ubuntu/22.04.yaml
providers:
  apt:
    packages:
      - name: main
        # package_name: postgresql (inherited from default.yaml)
        version: "14.10"  # ✅ Only version differs
```

```yaml
# debian/11.yaml
providers:
  apt:
    packages:
      - name: main
        # package_name: postgresql (inherited from default.yaml)
        version: "13.13"  # ✅ Only version differs
```

## Benefits of This Approach

1. **Reduces Duplication**: Common package names defined once in default.yaml
2. **Clear Overrides**: OS-specific files only contain what's different
3. **Easier Maintenance**: Change common name in one place
4. **Explicit Exceptions**: Overrides clearly show where OS differs from norm
5. **Minimal OS Files**: Most OS-specific files only need version, not package_name

## Updated Requirements

### Requirement 1: Default Saidata Version Policy

**Acceptance Criteria (CORRECTED):**

1. WHEN default.yaml is created or updated, THE System SHALL set the top-level packages version field to the latest official upstream release version
2. **WHEN a package name is consistent across all OS versions for a provider, THE System SHALL include that package_name in default.yaml provider section**
3. **WHEN a package name differs for specific OS versions, THE System SHALL include the common package_name in default.yaml and only override in OS-specific files where it differs**
4. THE System SHALL NOT include version information in default.yaml provider sections, as versions are OS-specific
5. THE System SHALL document that default.yaml top-level versions represent upstream releases, not OS-packaged versions

## Implementation Impact

### For Refresh Command

When refreshing default.yaml:
- ✅ Update top-level `packages[].version` with upstream version
- ✅ Include common `package_name` in provider sections
- ❌ Never include `version` in provider sections

When refreshing OS-specific files:
- ✅ Always update `version` in provider sections
- ✅ Only update `package_name` if it differs from default.yaml
- ✅ If package_name matches default.yaml, don't include it (inherited)

### For Override Validation

The validation command should:
- ✅ Flag OS-specific files that include package_name identical to default.yaml (unnecessary duplication)
- ✅ Allow package_name overrides that differ from default.yaml (necessary exception)
- ✅ Require version in OS-specific files (always necessary)

## Summary

**The key principle**: default.yaml contains what's COMMON, OS-specific files contain what's DIFFERENT.

- Common package names → default.yaml
- Different package names → OS-specific override
- Versions → ALWAYS OS-specific, NEVER in default.yaml providers
