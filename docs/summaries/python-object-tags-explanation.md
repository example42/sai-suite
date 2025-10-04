# Python Object Tags in YAML Files - Explanation

## The Problem

Some generated saidata YAML files contain Python object tags like:

```yaml
services:
- name: nginx
  service_name: nginx
  type: !!python/object/apply:saigen.models.saidata.ServiceType
  - systemd
  enabled: true
```

These tags cause issues when loading with `yaml.safe_load()` because they reference Python-specific object constructors.

## Root Cause

Python object tags appear in YAML when `yaml.dump()` is called on **Pydantic model instances directly** instead of on dictionaries.

### ❌ Wrong Way (Produces Python Tags)
```python
saidata = SaiData(...)  # Pydantic model instance
yaml.dump(saidata, f)   # Dumps the object directly - creates Python tags!
```

### ✅ Correct Way (Clean YAML)
```python
saidata = SaiData(...)  # Pydantic model instance
data = saidata.model_dump(exclude_none=True)  # Convert to dict first
yaml.dump(data, f)      # Dumps the dictionary - clean YAML!
```

## Why This Happens

When PyYAML encounters a Python object (like a Pydantic model or Enum), it:
1. Tries to serialize it as a Python-specific object
2. Adds `!!python/object/apply:` tags to preserve the type
3. This makes the YAML file Python-specific and not portable

### Enum Serialization Issue

Even though `SaiData` has `use_enum_values=True` in its config:

```python
class SaiData(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
```

This only affects Pydantic's internal serialization. If you dump the **object** directly with `yaml.dump()`, PyYAML doesn't know about Pydantic's config and serializes the enum as a Python object.

## Current Code Status

### ✅ Generation Engine (Correct)
```python
# saigen/core/generation_engine.py
async def save_saidata(self, saidata: SaiData, output_path: Path):
    data = saidata.model_dump(exclude_none=True)  # ✅ Converts to dict
    yaml.dump(data, f, default_flow_style=False, sort_keys=False, indent=2)
```

### ✅ ETL Module (Correct)
```python
# saigen/repositories/etl.py
async def load_saidata(self, saidata: SaiData, output_path: Path):
    data = saidata.model_dump(exclude_none=True)  # ✅ Converts to dict
    yaml.dump(data, f, default_flow_style=False, indent=2, sort_keys=False)
```

### ✅ Refresh Versions Command (Correct)
```python
# saigen/cli/commands/refresh_versions.py
def _save_saidata(saidata: SaiData, output_path: Path):
    data = saidata.model_dump(exclude_none=True)  # ✅ Converts to dict
    yaml.dump(data, f, default_flow_style=False, sort_keys=False, indent=2)
```

## How Files Got Python Tags

The files with Python tags (like `test-output/nginx.yaml` from October 4th) were likely created by:

1. **Older version of code** - Before `model_dump()` was consistently used
2. **Manual testing** - Someone might have dumped objects directly during testing
3. **Different code path** - Some other tool or script that doesn't use the standard save methods

## Solution Implemented

The `refresh-versions` command now handles both formats:

```python
def _load_saidata(file_path: Path) -> SaiData:
    # Read file content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove Python object tags
    import re
    content = re.sub(
        r'!!python/object/apply:[^\n]+\n\s*-\s*(\w+)',
        r'\1',
        content
    )
    
    # Parse cleaned YAML
    data = yaml.safe_load(content)
    return SaiData(**data)
```

This preprocessing step:
1. Detects Python object tags
2. Extracts the actual value (e.g., "systemd")
3. Removes the tag wrapper
4. Loads the cleaned YAML

## Prevention

To prevent Python tags in future files:

### 1. Always Use model_dump()
```python
# ✅ DO THIS
data = saidata.model_dump(exclude_none=True)
yaml.dump(data, f)

# ❌ DON'T DO THIS
yaml.dump(saidata, f)
```

### 2. Use Pydantic's JSON Mode
```python
# Alternative: Use Pydantic's JSON serialization
json_str = saidata.model_dump_json(exclude_none=True)
data = json.loads(json_str)
yaml.dump(data, f)
```

### 3. Configure YAML Dumper
```python
# Add custom representer for enums (if needed)
def enum_representer(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data.value)

yaml.add_representer(ServiceType, enum_representer)
```

## Verification

To check if a file has Python tags:

```bash
# Search for Python object tags
grep -n "!!python" saidata.yaml

# Count occurrences
grep -c "!!python" saidata.yaml
```

To clean a file:

```bash
# Use the refresh-versions command (it handles cleaning automatically)
saigen refresh-versions --check-only problematic.yaml

# Or manually with sed
sed -i.bak 's/!!python\/object\/apply:[^[:space:]]*[[:space:]]*-[[:space:]]*\([^[:space:]]*\)/\1/g' file.yaml
```

## Impact

### Files with Python Tags
- ❌ Cannot be loaded with `yaml.safe_load()`
- ❌ Not portable to other languages
- ❌ Harder to edit manually
- ✅ Can still be loaded with `yaml.unsafe_load()` (not recommended)
- ✅ Can be cleaned with preprocessing (our solution)

### Clean YAML Files
- ✅ Can be loaded with `yaml.safe_load()`
- ✅ Portable to any language
- ✅ Easy to edit manually
- ✅ Standard YAML format

## Recommendations

1. **For New Files**: Current code is correct, no action needed
2. **For Existing Files**: Use `refresh-versions` command which handles cleaning
3. **For Manual Editing**: Remove Python tags and replace with plain values
4. **For Validation**: Add a check in CI/CD to detect Python tags

## Example: Before and After

### Before (With Python Tags)
```yaml
services:
- name: nginx
  service_name: nginx
  type: !!python/object/apply:saigen.models.saidata.ServiceType
  - systemd
  enabled: true
```

### After (Clean YAML)
```yaml
services:
- name: nginx
  service_name: nginx
  type: systemd
  enabled: true
```

## Testing

The `refresh-versions` command includes a test for this:

```python
def test_load_saidata_with_python_tags(tmp_path):
    """Test loading saidata with Python object tags (legacy format)."""
    content = """version: '0.3'
metadata:
  name: test
services:
  - name: test-service
    type: !!python/object/apply:saigen.models.saidata.ServiceType
      - systemd
"""
    # Should load successfully despite Python tags
    saidata = _load_saidata(saidata_path)
    assert saidata.services[0].type == 'systemd'
```

## Conclusion

Python object tags in YAML files are a legacy issue from:
- Older code that didn't use `model_dump()`
- Direct serialization of Pydantic objects
- PyYAML's default behavior with Python objects

**Current Status**: 
- ✅ All current code uses `model_dump()` correctly
- ✅ `refresh-versions` command handles legacy files
- ✅ New files will be clean YAML
- ✅ Existing files can be cleaned automatically

**No action required** - the issue is understood and handled!
