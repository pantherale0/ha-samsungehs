# Changelog

## [1.3.0](https://github.com/pantherale0/ha-samsungehs/compare/v1.2.1...v1.3.0) (2026-10-26)


### Features

* add 3-way valve, defrost, DHW tank temperature and thermo on entities ([#26](https://github.com/pantherale0/ha-samsungehs/issues/26)) ([2948a2f](https://github.com/pantherale0/ha-samsungehs/commit/2948a2ffd80335035e394e0735d17b7008a80c38))
* add diagnostic sensors for operation and defrost status ([#35](https://github.com/pantherale0/ha-samsungehs/issues/35)) ([4fc79aa](https://github.com/pantherale0/ha-samsungehs/commit/4fc79aa5c3e03bf147397b395d1aaf9e35ee3941))
* add diagnostics support and tests for Samsung EHS integration ([#31](https://github.com/pantherale0/ha-samsungehs/issues/31)) ([ff3550a](https://github.com/pantherale0/ha-samsungehs/commit/ff3550a37d65e751d77531a616ac7d19d889aa09))
* add FSV 3083 booster heater capacity number entity ([#27](https://github.com/pantherale0/ha-samsungehs/issues/27)) ([adac7f7](https://github.com/pantherale0/ha-samsungehs/commit/adac7f7dd59ff2ee826b9e2622ba2b0352dab42d))
* external room temperature service ([#25](https://github.com/pantherale0/ha-samsungehs/issues/25)) ([6ed80aa](https://github.com/pantherale0/ha-samsungehs/commit/6ed80aa851b97fc70debd31879d8c45401a8a9ee))


### Bug Fixes

* update Home Assistant version to 2026.9.0 in hacs.json ([#32](https://github.com/pantherale0/ha-samsungehs/issues/32)) ([6e32983](https://github.com/pantherale0/ha-samsungehs/commit/6e3298329e4a0726add15b97b085060862658cfb))
* update pysamsungnasa to 3.0.1 ([#22](https://github.com/pantherale0/ha-samsungehs/issues/22)) ([8e771b9](https://github.com/pantherale0/ha-samsungehs/commit/8e771b93b165003ade18130e1c94e627e920f2ca))
* use FlowTemperature as the current temp for water_law_offset mode ([#34](https://github.com/pantherale0/ha-samsungehs/issues/34)) ([65d538b](https://github.com/pantherale0/ha-samsungehs/commit/65d538b671b87a162418a85f0f97a08267fcc175))
* validate the NASA address when adding a device ([#28](https://github.com/pantherale0/ha-samsungehs/issues/28)) ([3aad978](https://github.com/pantherale0/ha-samsungehs/commit/3aad9784d38078fbfbe1ff5c7c8e1e379b7ab067))

## [1.2.1](https://github.com/pantherale0/ha-samsungehs/compare/v1.2.0...v1.2.1) (2026-10-24)


### Bug Fixes

* read the water law target from 0x427F and add a water law offset sensor ([#17](https://github.com/pantherale0/ha-samsungehs/issues/17)) ([13ad29c](https://github.com/pantherale0/ha-samsungehs/commit/13ad29c708c0d739c27996ff0af1de0b2abbd379))
* requirements.txt to reduce vulnerabilities ([#14](https://github.com/pantherale0/ha-samsungehs/issues/14)) ([8fac5b7](https://github.com/pantherale0/ha-samsungehs/commit/8fac5b74acd532fa85c7b6b2a3e390ec84b2a897))

## [1.2.0](https://github.com/pantherale0/ha-samsungehs/compare/v1.1.1...v1.2.0) (2026-10-22)


### Features

* Add FSV entity support and improve temperature control logic ([#11](https://github.com/pantherale0/ha-samsungehs/issues/11)) ([2d5b80d](https://github.com/pantherale0/ha-samsungehs/commit/2d5b80dd0e56587969ad8e4290d68f4660af9493))

## [1.1.1](https://github.com/pantherale0/ha-samsungehs/compare/v1.1.0...v1.1.1) (2026-10-11)


### Bug Fixes

* ensure integration zip is included in release ([bbcaab6](https://github.com/pantherale0/ha-samsungehs/commit/bbcaab61ddb9f5cc82b3702851ecb867ed16be5d))

## [1.1.0](https://github.com/pantherale0/ha-samsungehs/compare/v1.0.0...v1.1.0) (2026-10-11)


### Features

* implement Conventional Commits validation and release automation ([65b4138](https://github.com/pantherale0/ha-samsungehs/commit/65b4138cf9d164ffc49f543095cd3d910a3d7860))
