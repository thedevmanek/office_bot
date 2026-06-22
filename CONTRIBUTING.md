# Contributing

Contributions should make `office_bot`, the reference office-robot project
inside OpenHRI, easier to run, inspect, repair, or modify.

## Useful Contributions

- Fix setup, container, simulation, detector, UI, or documentation bugs.
- Add or improve object-search recipes under `recipes/trials/`.
- Improve the detector, localization, tracking, navigation, web UI, evaluator, or packaging tools.
- Document hardware parts, wiring, calibration, safety checks, or replacement options.
- Turn a repeatable workflow into a clear example or recipe.

## Local Checks

For docs, recipes, and helper scripts:

```bash
make repo-check
```

For ROS package changes:

```bash
make start
make test
```

For recipe changes:

```bash
make trial-plan TRIAL=<trial-id>
```

## Pull Request Checklist

- [ ] Changed docs have valid links.
- [ ] Changed recipes validate with `make trial-plan TRIAL=<trial-id>`.
- [ ] Changed docs match the current repo state.
- [ ] Hardware-facing changes update the BOM, readiness checklist, or swap guide.
- [ ] Code changes have focused tests or a clear reason tests are not applicable.
- [ ] No private paths, credentials, local machine details, or unpublished safety logs are included.
