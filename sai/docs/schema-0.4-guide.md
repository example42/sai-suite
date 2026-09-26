# SaiData 0.4 format

SaiData 0.4 extends 0.3 with machine-readable provenance and software
reference data. Existing 0.3 records remain valid under the 0.3 schema. A
0.4 record declares `version: "0.4"` and is validated against the 0.4 schema.
The executable installation fields retain their 0.3 meaning.
The record value `0.4` names the data format. A sai-suite package release may
use a patch version such as `0.4.0` without changing that value.

## Evidence

Any structured record node in a 0.4 record may have an `evidence` list. This
includes metadata, resource entries, provider entries, compatibility entries,
and the new licence, setting, and command-interface entries. Scalar values and
free-form maps such as environment variables do not carry Evidence; attach it
to their containing record. Each entry has:

| Field | Meaning |
| --- | --- |
| `kind` | `capture`, `primary_source`, or `scenario_step` |
| `source` | Stable URL or repository-relative capture path |
| `version` | Software version to which the observation applies |
| `date` | Observation date in `YYYY-MM-DD` form |
| `span` | Optional location within a capture or document |
| `step` | Optional Scenario step identifier |
| `runner` | Optional logical runner label, never a hostname or address |
| `image_digest` | Optional digest of the executed image |
| `architecture` | Optional observed architecture |

`kind`, `source`, `version`, and `date` are required for every Evidence entry.
`scenario_step` also requires `step`. Evidence is inert metadata: sai must
preserve it when parsing and serializing a record, and must never interpret it
as a command, condition, or install instruction. A publisher may require
Evidence for a particular record; sai itself does not.

## Licences and identifiers

`metadata.licenses` is an optional list. Each item has `spdx_id` (or a
human-readable `name` when no SPDX identifier applies), `as_of_version`, and
optional `before_version`. The interval starts at `as_of_version` and ends
before `before_version`. Several items may cover one interval to represent a
choice of licences. The scalar `metadata.license` remains accepted for 0.3
compatibility, but does not express version ranges. `NOASSERTION` is not a
licence identifier.

`metadata.identifiers` holds optional `purl`, `cpe`, and `repology` strings.
These are identifiers for joining external data, not install instructions.

## Configuration settings

`settings` is an optional list of configuration keys. Each item has `key`,
`type` (`string`, `integer`, `number`, `boolean`, or `enum`), and `scope`
(`file`, `runtime_command`, `environment`, or `flag`). A `file` scoped setting
also has `file`, the logical name of a `files` entry. `change_effect` is
`immediate`, `reload`, or `restart`. Optional `defaults` records provide
`value`, `as_of_version`, and optional `before_version`. A setting can be
overridden in a provider configuration using the existing provider merge
convention. A missing default means unknown, not an empty value.

## Command interface

The existing `commands` list names executable commands. Each command may now
also contain a recursive `subcommands` list and `flags` and `positionals`
lists. `subcommands` nodes have a `name` and may themselves contain the same
three lists. A flag has `name`, optional `aliases`, `value_type`, and
`description`. A positional has `name`, optional `value_type`, `required`,
and `description`. The existing `commands[].arguments` list remains the
execution argument list from 0.3. The new tree describes the interface and
does not supply arguments to sai actions.

## Kubernetes provider

`providers.kubernetes` may contain `charts`, `operators`, and `manifests`.
Each entry has `name`, `publisher`, `version`, `source`, and `digest` so the
origin and exact artifact are clear. `charts` may additionally name a Helm
repository and chart. These are descriptions of Kubernetes installation
artifacts. They do not cause sai to deploy a cluster resource unless a
separate executable provider implementation exists.

## Example

The openskills.info Tool pilots contain draft 0.4 records at
`courses/it/redis-fundamentals/tool/saidata.yaml` and
`courses/it/git-fundamentals/tool/saidata.yaml` in that repository.
Their primary-source Evidence records a review, not an executed Scenario.
Neither record is a verified installation reference yet.

```yaml
version: "0.4"
metadata:
  name: example
  identifiers:
    purl: pkg:generic/example
    cpe: cpe:2.3:a:example:example:*:*:*:*:*:*:*:*
    repology: example
  licenses:
    - spdx_id: Apache-2.0
      as_of_version: "1.0"
      evidence:
        - kind: primary_source
          source: https://example.org/example/1.0/LICENSE
          version: "1.0"
          date: "2026-09-24"
files:
  - name: config
    path: /etc/example/example.conf
settings:
  - key: max_clients
    type: integer
    scope: file
    file: config
    change_effect: reload
    defaults:
      - value: 100
        as_of_version: "1.0"
commands:
  - name: examplectl
    subcommands:
      - name: status
        flags:
          - name: --verbose
            value_type: boolean
providers:
  kubernetes:
    manifests:
      - name: example
        publisher: Example Project
        version: "1.0"
        source: https://example.org/example/1.0/manifest.yaml
        digest: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
```
