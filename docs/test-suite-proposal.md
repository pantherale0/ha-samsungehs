# Samsung EHS test suite proposal

Replace the integration tests with a suite built on
`pytest-homeassistant-custom-component`. Run real Home Assistant config entries,
platforms, registries, coordinators, and actions. Mock the `pysamsungnasa` client
where the integration constructs it. Preserve the existing regression scenarios
as tests of observable states and outgoing device commands.

This is the original proposal. The baseline observations below predate its
implementation. See [CONTRIBUTING.md](../CONTRIBUTING.md#test-your-code-modification)
for current test commands. Research date: 27 October 2026.
Core sources were inspected on `dev`; the reference revision is
[`cf39cff80dd0`](https://github.com/home-assistant/core/tree/cf39cff80dd063e34c834d40e666708bb85bf116).
The replacement package is treated as unreleased, as requested. Its source API
is useful for planning but is not a promise about its first published release.

## What the current suite proves

Running `.venv/bin/python -m pytest -q` passes 863 cases and 17 subtests.
Neither Home Assistant pytest package is installed in that environment.
No coverage measurement was taken, so the passing result does not establish
compliance with Home Assistant's coverage requirements.

The current tests contain useful literal expectations for NASA message IDs,
payloads, enum values, address normalization, control priorities, and redaction.
Their main limitation is how they exercise the integration:

| Current pattern | Missing evidence |
| --- | --- |
| Repeated `SimpleNamespace` coordinators, entries, and devices | Real config-entry state, subentry associations, registry behavior, and cleanup |
| Entity construction followed by property reads | Platform setup, callbacks, state publication, translated names, and unit conversion |
| Direct service-handler calls and schema validation | Service registration, dispatcher validation, target resolution, and response handling |
| Mocked `async_create_entry` and `async_show_form` | Flow-manager validation, persisted entries, unique IDs, duplicates, and error recovery |
| `asyncio.run` and one manually constructed `HomeAssistant` | The plugin's managed event loop, fixtures, and teardown checks |
| Feature-history test files | Clear ownership by lifecycle, platform, and action |

`test_climate_control_priority` alone expands into 750 cases. Its expected result
also repeats the implementation's branching logic. Keep meaningful input classes
and literal expected outcomes rather than treating the case count as a target.

There is no integration-test workflow or pytest configuration in this checkout.
The commits workflow runs the independent commit-validator tests.

## Standards and reference integrations

Home Assistant's Bronze rule requires complete config-flow coverage, including
recovery after an error and created-entry unique IDs. Its Silver coverage rule
requires more than 95% coverage in every integration module and recommends
testing through entry setup, states, and actions. These are distinct from earning
an overall Gold or Platinum integration rating.
Sources: [config-flow coverage](https://contributors.home-assistant.io/core/quality-scale/config-flow-test-coverage/)
and [integration coverage](https://contributors.home-assistant.io/core/quality-scale/test-coverage/).

Use these concrete examples as references:

| Reference | Pattern to adopt here |
| --- | --- |
| AirGradient, [Platinum manifest](https://github.com/home-assistant/core/blob/cf39cff80dd063e34c834d40e666708bb85bf116/homeassistant/components/airgradient/manifest.json) and [fixtures](https://github.com/home-assistant/core/blob/cf39cff80dd063e34c834d40e666708bb85bf116/tests/components/airgradient/conftest.py) | Shared `MockConfigEntry`, autospecced client constructor, realistic library data, and function-scoped mocks |
| AirGradient [sensor tests](https://github.com/home-assistant/core/blob/cf39cff80dd063e34c834d40e666708bb85bf116/tests/components/airgradient/test_sensor.py) and [setup tests](https://github.com/home-assistant/core/blob/cf39cff80dd063e34c834d40e666708bb85bf116/tests/components/airgradient/test_init.py) | Registry and platform snapshots, separate default-enablement assertions, simulated time, actual unavailable states, and `SETUP_RETRY` |
| AirGradient [number tests](https://github.com/home-assistant/core/blob/cf39cff80dd063e34c834d40e666708bb85bf116/tests/components/airgradient/test_number.py) | Call `hass.services.async_call`, check library commands, and inject library failures through the same action |
| ista EcoTrend, [Gold manifest](https://github.com/home-assistant/core/blob/cf39cff80dd063e34c834d40e666708bb85bf116/homeassistant/components/ista_ecotrend/manifest.json) and [diagnostics tests](https://github.com/home-assistant/core/blob/cf39cff80dd063e34c834d40e666708bb85bf116/tests/components/ista_ecotrend/test_diagnostics.py) | Set up a real entry, request diagnostics through the HTTP helper, and snapshot the returned JSON |

AirGradient polls a local API and ista EcoTrend polls a cloud API. Borrow their
test structure, not their transport assumptions. Samsung EHS combines device
callbacks with a 15-second coordinator read cycle, despite its `local_push`
manifest classification. Both update paths need tests.

## Fixture design and file layout

Keep the existing flat `tests/` package and reorganize integration tests around
`test_init.py`, `test_config_flow.py`, `test_devices.py`, `test_coordinator.py`,
`test_entity.py`, the seven platform files, `test_services.py`,
`test_external_room_temperature.py`, `test_diagnostics.py`, and `test_helpers.py`.
Store input data in `tests/fixtures/` and reviewed snapshots in `tests/snapshots/`.
Leave `test_check_commits.py` independent of HA-specific fixtures and dependencies.

Add these shared fixtures in `tests/conftest.py`:

| Fixture | Responsibility |
| --- | --- |
| Custom-integration enablement | Request `enable_custom_integrations` for integration tests under the current package. Avoid a global `hass` dependency that affects commit-validator tests. |
| `mock_config_entry` | Return a version-2 `MockConfigEntry` with a fixed connection URL and ID. Provide real `ConfigSubentry` objects with fixed IDs for indoor, outdoor, and mixed-device cases. |
| `mock_nasa` | Patch `custom_components.samsungehs.SamsungNasa` with autospec. Configure async start, stop, reads, writes, and sends explicitly. Expose the nested transport connection state and captured discovery callback. |
| Device data | Use real message objects and enum values from `pysamsungnasa==3.0.1`. Give each device its own cache and callback collection. Use a small device double only where autospec cannot represent instance attributes. |
| `setup_integration` | Add the entry to `hass`, await `hass.config_entries.async_setup`, and drain scheduled work. Keep all seven platforms enabled in lifecycle tests. |
| Update delivery | Change the device cache and invoke the callbacks registered by production code. Support parser listeners for cross-device climate updates. Never write the expected state into HA directly. |
| `snapshot` | Select `HomeAssistantSnapshotExtension` so snapshots live beside this suite. Fix entry IDs and timestamps at the fixture source. |

Keep client patches active through teardown. Track callback registration and
removal, and make sends and writes inspectable. Do not mock integration entities,
the coordinator, flow-result methods, or HA registries in behavior tests.
An isolated flow test may patch integration setup to avoid starting platforms.

Use `entity_registry_enabled_by_default` only in all-entity tests. Separate tests
must exercise the actual defaults. Use `freezer` and `async_fire_time_changed`
for coordinator timing, with no real sleeps. Keep focused coordinator unit tests
for batching boundaries that are awkward to reach through a whole platform.

## Proposed test matrix

P0 establishes reliable setup and configuration. P1 covers platform behavior and
regressions. P2 completes edge cases and coverage. These are groups of scenarios,
not promised test counts.

| Priority and file | Scenarios and observable assertions |
| --- | --- |
| P0 `test_init.py` | Empty bus, indoor, outdoor, and mixed subentries load through HA. Assert `LOADED`, constructed connection configuration, runtime data, metadata reads, and expected platform states. Startup or metadata-read failure stops the client and produces `SETUP_RETRY`; a later successful retry loads without duplicate entities. |
| P0 `test_init.py` | Unload removes states and device callbacks, stops the client, and prevents later scheduled reads. Reload preserves registry identities and does not multiply listeners or commands. An options update reloads the intended entry. Exercise failed platform unloading separately. |
| P0 `test_init.py` | Migrate a version-1 host/port entry through HA to the exact version-2 socket URL and unique ID. Preserve applicable options and entry associations. A current-version entry still loads. Unsupported future versions cannot load. |
| P0 `test_config_flow.py` | Run user flow with `flow.async_init` and `async_configure`. Check initial form, serial and socket inputs, persisted data, title, version, unique ID, and duplicate-connection abort. Reconfigure to a new connection, to the existing connection, and to another entry's connection. Assert persistence, successful abort reason, and reload behavior. |
| P0 `test_config_flow.py` | Use HA's subentry flow manager for the device form. Cover canonical, dotted, colon, lowercase, and invalid addresses. After an invalid address, submit a valid value on the same flow and finish successfully. Assert stored canonical unique ID, parent association, duplicate-device behavior, and isolation between buses. Retain the small pure normalization table. |
| P0 `test_devices.py` | Invoke the captured library discovery callback. A new address creates one real subentry and reloads. Repeated discovery of an existing subentry must not duplicate it or repeatedly reload. Ignore `62` addresses. Two connections can discover devices independently. |
| P0 `test_coordinator.py` | Drive scheduled reads with simulated time. Initial-only reads happen once; recurring reads recur; disconnected transport reconnects. For 0, 1, 10, 11, and 21 message IDs, assert exact batches and destinations. Failed reads make affected entities unavailable; subsequent successful refresh restores them. Failed initial reads retry the required messages. |
| P1 `test_entity.py` | Assert entity and device registry records, subentry linkage, manufacturer, model, firmware, serial fallback, and stable unique IDs after reload. Device callbacks update `hass.states`; disconnect, failed refresh, and device removal publish unavailable states without exceptions. Unload detaches device and parser listeners, including climate's cross-device subscriptions. |
| P1 `test_sensor.py` | Snapshot indoor and outdoor entity states and registry records. Assert literal values for water-law target `0x427F`, offset `0x4248`, DHW temperature, three-way valve, defrost stage, and outdoor enums. Cover zero, missing data, `None`, and `ffff` according to each entity's availability contract. Under Fahrenheit configuration, a 2°C offset displays 3.6°F as a temperature difference. |
| P1 `test_binary_sensor.py` | Three/four-way valve-related status where applicable, thermo-on, defrost, and both external-sensor flags publish correct states. Missing flags remain unknown when available. Cache changes and connection changes publish updated states. Preserve the existing defrost enum cases. |
| P1 `test_sensor.py` | External room sensors for both zones transition through missing flag, enabled with valid reading, disabled, and enabled again. Missing temperature prevents availability. The other zone's flag cannot enable this zone. Verify both dependency message IDs are actually read, even when the corresponding binary sensor is disabled. |
| P1 `test_climate.py` | Publish room, water-out, and water-law control temperatures. Call `climate.set_temperature` and assert the literal destination message and value. Cover both external thermostat overrides, auto-mode priority, missing thermostat inputs, delayed reference data, and irrelevant FSV2093 changes. Cover all exposed HVAC modes, power actions, idle/heating/cooling/preheating/defrosting, and parser-driven outdoor status changes. |
| P1 `test_water_heater.py` | Current and target temperature, power, every advertised operation mode, startup reads, and unavailable state. Call HA temperature, operation-mode, and power actions. Assert device commands and multi-attribute writes. Invalid operation modes cannot send commands. |
| P1 `test_number.py` | Registered values, bounds, steps, units, availability, signed FSV values, and water-law control-dependent writes. Call `number.set_value`, assert the exact command and request mode, and reject out-of-range values before transport. Include custom `write_fn` and default-write paths. |
| P1 `test_select.py` | Options, displayed enum labels, missing values, unknown enum values, and every distinct zero-based or one-based encoding. Call `select.select_option`, assert the literal underlying enum or bytes, and reject invalid options without writes. |
| P1 `test_switch.py` | Reported on/off/unknown and unavailable states. Call turn-on and turn-off services and assert description-specific command values. |
| P1 `test_services.py` | All three integration actions register through `async_setup_component` before an entry loads. Read via `return_response=True` returns the expected JSON. Known and raw attribute IDs route to the selected device. Write targets the correct connection. Missing, foreign, removed, and unloaded targets fail through the dispatcher; no command reaches another bus. |
| P1 `test_external_room_temperature.py` | Preserve both zones, enable/disable, signed payloads, selector strings, missing temperature, nonfinite values, booleans, invalid zones, boundary values, disconnected transport, and transport exceptions. Call the registered service. Assert literal source `510000`, destination `B0FF20`, notification type, message IDs, and bytes. Check translated error keys and absence of sends on failure. |
| P1 `test_diagnostics.py` | Request diagnostics with `hass_client` and `get_diagnostics_for_config_entry` after setup. Snapshot connected, disconnected, missing-device, and no-interval cases. Add explicit negative assertions for connection URLs, addresses, host, and port in serialized output. Seed identity-bearing message attributes and decide which values must be redacted. Confirm source entry data remains intact. |
| P2 `test_helpers.py` | Small literal tables for pure control-source decisions and enum-label conversions. No HA fixture is needed for pure logic. Keep only combinations that demonstrate a distinct precedence or missing-input rule. |
| P2 platform and registry tests | Verify default disabled entities, config/diagnostic categories, units, device classes, state classes, translation keys, and resolved names. Add two devices and two entries to prove isolation. Enable a disabled entity and verify state creation and reads. |

Use platform snapshots to review entity inventories and metadata. Keep explicit
assertions for commands, state transitions, privacy, and error behavior. Expected
IDs, enum encodings, and payloads must come from literal fixture expectations,
not from looping over production descriptions to calculate both sides.

## Requirements that may reveal production defects

These are review targets inferred from source, not reproduced bug reports:

- Discovery checks `entry.options['device_addresses']` but stores discovered
  devices as subentries. Test repeated discovery against actual subentries.
- Climate registers parser listeners, while the shared removal hook removes
  device callbacks. Test complete listener cleanup after unload and reload.
- Reconfigure sets a flow unique ID and updates entry data. Verify the persisted
  entry unique ID follows the new connection and that unchanged input succeeds.
- Attribute services resolve a registry device using `device.config_entry_id`.
  Verify this against the installed HA registry API and subentry ownership.
- Diagnostics emits raw message dictionaries. Seed serial/model identity data
  rather than assuming redacting connection keys covers every identifier.
- The user flow does not test a connection. Full test coverage of today's flow
  will not satisfy the separate `test-before-configure` behavior requirement.

For each exposed defect, add a failing behavior test and fix production code in
the same change. Do not make the double imitate a broken API or encode the
current defect as the desired result. Do not add hypothetical reauthentication,
options, or repair flows merely to populate a test checklist.

## Prepare for pytest-home-assistant

The [current custom-component package README](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component/blob/master/README.md)
documents its helper namespace, required enablement fixture, asyncio setting,
and snapshot extension. The [new package README](https://github.com/home-assistant/core/blob/cf39cff80dd063e34c834d40e666708bb85bf116/packages/pytest-home-assistant/README.md)
documents the migration explicitly.

| Concern | Current suite proposal | Replacement package |
| --- | --- | --- |
| Dependency | Pin a published `pytest-homeassistant-custom-component` release compatible with HA 2026.10.4 | Replace it with a published matching `pytest-home-assistant` release when available |
| Helper imports | `pytest_homeassistant_custom_component.common`, `.components.diagnostics`, `.syrupy` | Change the prefix to `pytest_homeassistant`; retain the helper suffixes |
| Custom integrations | Explicit `enable_custom_integrations` fixture dependency | Enabled by the `hass` fixture by default; remove the wrapper |
| Plugin registration | Package entry point loads the plugin | Package entry point loads the bootstrap; no manual `pytest_plugins` registration |
| Fixture files | `tests/fixtures/` | Same default path; `ha_test_root` exists for alternate roots |
| Snapshots | Explicit HA extension fixture | Retain the extension and verify snapshot compatibility |
| Writable configuration | Use fixture-managed temporary paths when needed | Override `hass_config_dir` with `hass_tmp_config_dir` for tests that write configuration |

Do not install both packages together or add import fallbacks that silently pick
one. Keep direct helper imports and make the namespace replacement mechanically
searchable. The integration-owned setup and device fixtures remain unchanged.

Adopt `asyncio_mode = 'auto'`, function-scoped fixture loops, project-root Python
path, and `tests` discovery. The new README also requires `-p no:respx` so HA can
install its httpx alias before that plugin imports. Carry this into the new
environment and verify the current package's configuration separately.

Resolve dependencies as one compatible set rather than appending the plugin to
today's pins. The inspected [new pyproject](https://github.com/home-assistant/core/blob/cf39cff80dd063e34c834d40e666708bb85bf116/packages/pytest-home-assistant/pyproject.toml)
requires Python >=3.14.2 and pins pytest 9.0.3, whereas this repository currently
pins pytest 9.1.1. The first release may differ. Keep `pysamsungnasa` installed
explicitly because it is the integration's library, not a plugin dependency.

After publication, validate in a fresh environment containing only the new
package, its compatible HA version, the integration dependency, and coverage
tools. Run the same tests and inspect `pytest --trace-config` for overlapping
plugins. Review snapshot changes and missing fixtures before switching the
required job. An earlier source-checkout experiment must pin a Core SHA and use
a compatible Core build; it must not replace the supported release job.

## Delivery and acceptance

1. Add the pinned current plugin, pytest configuration, shared fixtures, and a
   required integration-test CI job. First prove one complete entry setup,
   callback-driven state update, service call, and unload across all platforms.
2. Add P0 flows, migration, discovery, retry, and coordinator tests. Fix defects
   these tests reproduce. Preserve old regressions until replacement assertions
   cover each one.
3. Move regression scenarios into the P1 platform/action tests. Replace the
   750-case product with explicit precedence cases and focused pure-helper
   cases. Delete obsolete factories and direct-handler tests as their successors
   land. Keep the independent commit-validator test command working.
4. Complete P2 coverage, snapshots, and dependency-upgrade checks. Document the
   install and test commands in `CONTRIBUTING.md`.
5. Switch packages after the new release can run the same suite in a clean
   environment. Remove the old dependency and fixture wrapper in that change.

CI should collect coverage only for `custom_components.samsungehs`, including
unimported modules. Require 100% config-flow coverage and more than 95% in each
other executable module. Generate coverage JSON and use a small per-file check;
`--cov-fail-under` alone checks only the aggregate. Report branch coverage and
inspect missing branches, without presenting that additional project choice as
an HA-mandated numeric branch threshold. Keep diagnostics fully covered.

Acceptance also requires every platform to load through HA, incoming callbacks
to publish states, actions to validate and route correctly, unload to stop
callbacks and scheduled work, and registry identities to survive reload. Tests
must use no real serial device or external network. Review snapshot updates
explicitly. Passing coverage alone does not establish those behaviors.
