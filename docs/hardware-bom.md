# Hardware BOM

This file records the physical bill of materials currently documented for the
OpenHRI `office_bot` reference build. It is a component reference for the early
hardware prototype, not a deployment-ready build sheet.

## Source Of Truth

- Simulation model: `dev_ws/src/office_bot_model/models/officebot_xacro/`.
- Runtime and launch behavior: `dev_ws/src/office_bot_model/launch/` and `dev_ws/src/object_detector/`.
- Hardware bringup: `hardware` branch.
- Readiness checks: [hardware-readiness-checklist.md](hardware-readiness-checklist.md).

## Recorded BOM

Total recorded spend so far: **£952.51**.

| Supplier | Category | Items | Total |
| --- | --- | --- | --- |
| AliExpress | Tools, wiring, connectors, power conversion | Multimeter, soldering kit, wiring connectors, silicone wire, DC-DC converters, desoldering braid, XT60 connectors, cable ties, gloves, insulating tape, polyimide tape, pliers | £51.11 |
| Pimoroni | Raspberry Pi compute kit | Raspberry Pi 5 16GB, official case with fan, official 27W UK PSU, micro-HDMI cable | £144.90 |
| AliExpress | Motor control and drivetrain | 4-channel encoder motor driver, four 96mm mecanum wheels, four 12V DC reducer motors with Hall encoders | £104.54 |
| AliExpress | Lidar | Unitree L2 Lidar | £238.69 |
| FlexiSpot | Physical structure | RW2 table | £39.99 |
| Axelera | AI acceleration | Axelera M.2 card, including customs | £260.00 |
| eBay | Battery, charger, and connectors | ECO-WORTHY 12V 30Ah LiFePO4 battery, ECO-WORTHY 5A 12V LiFePO4 charger, JST-PH 3-way prewired connector leads | £113.28 |

## Subsystem BOM

| Subsystem | Exact part | Required interface | Allowed alternatives | Notes |
| --- | --- | --- | --- | --- |
| Compute | Raspberry Pi 5 16GB RAM; official Raspberry Pi 5 case with fan; official Raspberry Pi 5 27W UK PSU; official micro-HDMI to HDMI cable | Runs ROS 2 nodes and container-supported tooling | Raspberry Pi class board or small Linux computer | Purchased from Pimoroni; full project-stack integration on hardware is in progress. |
| AI accelerator | Axelera M.2 card | Provides local acceleration for perception workloads | M.2 AI accelerator with supported Linux runtime | Purchased for £260 including customs; installed and working. |
| Chassis | FlexiSpot RW2 table | Supports sensor mounts and stable wheel geometry | Custom plate, extrusion, or printed chassis | Mounting and stability evidence is not documented in this branch. |
| Motor control | 4-channel encoder motor driver | Accepts velocity commands and reports usable odometry | Controller with documented ROS 2 bridge | Wiring, voltage limits, and calibration steps still need documentation. |
| Drive motors | 4x MOEBIUS 37-520 12V DC reducer motor with speed-measuring Hall encoder | Provides wheel actuation and encoder feedback | Equivalent 12V geared motors with encoder feedback | Confirm gear ratio, encoder resolution, wiring, current draw, and mounting. |
| Wheels | 4x 96mm high-hardness plastic mecanum wheel, rated 25kg big load | Matches controller model and odometry assumptions | Similar wheel diameter and traction | Update URDF/xacro when geometry changes. |
| Lidar | Unitree L2 Lidar | Publishes scan or point cloud for navigation | ROS 2-supported 2D lidar | Driver, frame, mount height, and scan quality still need bringup proof. |
| Camera | Installed camera, exact model not yet recorded | Publishes `/camera/image_raw` and camera info | USB or CSI camera with ROS 2 driver | Mounted and producing usable ROS data; record resolution, frame, and calibration notes. |
| Power conversion and wiring | Step-down DC-DC converter; 24V-to-12V DC converter; XT60 bullet connectors; black/red silicone wire; mini fast wiring connectors; 5-pack JST-PH 3-way prewired connector leads, 150mm | Safely distributes power to compute, sensors, and motion components | Equivalent rated converters and connectors | Verify voltage/current ratings, fuse strategy, cable gauges, and strain relief. |
| Battery | ECO-WORTHY 12V 30Ah LiFePO4 lithium battery; ECO-WORTHY 5A 12V LiFePO4 lithium battery charger with LCD screen | Powers compute, sensors, and motion safely | Equivalent LiFePO4 battery and compatible charger with safe discharge limits | Onboard battery power works, with observed runtime of more than 10 hours; document fuse, cutoff behavior, charging procedure, and mounting before shared hardware use. |
| Emergency stop | Physical emergency stop, exact model not yet recorded | Stops motion within documented operating conditions | Physical stop plus documented software stop | Installed on the left side of the robot; record activation behavior, recovery steps, and stop timing. |
| Tools and assembly consumables | Smart digital multimeter tester; JCD 80W soldering iron kit; desoldering braid; releasable cable ties; anti-static gloves; insulating tape; high-temp polyimide tape; universal pliers | Supports assembly, testing, repair, and insulation | Equivalent hand tools and rated consumables | Consumables are included for reproducibility but are not robot subsystems. |

## Itemized Purchases

### AliExpress: Tools, Wiring, And Power Conversion

| Item | Product | Quantity | Total |
| --- | --- | ---: | ---: |
| 1 | Smart Digital Multimeter Tester | 1 | £6.14 |
| 2 | JCD Soldering Iron Kit 80W | 1 | £13.69 |
| 3 | Mini Fast Wiring Connectors | 1 | £2.95 |
| 4 | Black/Red Silicone Wire | 1 | £2.20 |
| 5 | Step Down DC-DC Converter | 1 | £3.94 |
| 6 | Desoldering Braid | 1 | £1.59 |
| 7 | XT60 Bullet Connectors | 1 | £1.69 |
| 8 | DC Converter, 24V to 12V | 1 | £12.69 |
| 9 | Releasable Cable Ties | 1 | £2.20 |
| 10 | Anti-static Gloves | 1 | £1.22 |
| 11 | Insulating Tape | 1 | £0.80 |
| 12 | High Temp Polyimide Tape | 1 | £1.60 |
| 13 | Universal Pliers | 1 | £1.40 |

Subtotal before discounts: £52.11. Discount: -£1.00. Grand total: **£51.11**.

### Pimoroni: Compute Kit

| Item | Product | Quantity | Total |
| --- | --- | ---: | ---: |
| 1 | Official Micro-HDMI to HDMI Cable, 1m, black | 1 | £4.50 |
| 2 | Raspberry Pi 5 Official Case with Fan, red/white | 1 | £7.75 |
| 3 | Raspberry Pi 5 Official 27W PSU, United Kingdom, white | 1 | £9.50 |
| 4 | Raspberry Pi 5, 16GB RAM | 1 | £95.75 |

Subtotal: £117.50. Shipping: £3.25. GB VAT at 20%: £24.15. Total: **£144.90**.

### AliExpress: Motor Control And Drivetrain

| Item | Product | Quantity | Total |
| --- | --- | ---: | ---: |
| 1 | 4-Channel Encoder Motor Driver | 1 | £18.09 |
| 2 | 25KG big-load 96mm high-hardness plastic mecanum wheel, omni-directional | 4 | £34.19 |
| 3 | MOEBIUS 37-520 12V DC reducer motor with speed-measuring Hall encoder | 4 | £52.26 |

Total: **£104.54**.

### AliExpress: Lidar

| Item | Product | Quantity | Total |
| --- | --- | ---: | ---: |
| 1 | Unitree L2 Lidar | 1 | £309.19 |

Subtotal before discounts: £309.00. Shipping: £7.46. AliExpress coupons: -£30.00. Price adjustment: -£47.77. Total: **£238.69**.

### FlexiSpot: Physical Structure

| Item | Product | Quantity | Total |
| --- | --- | ---: | ---: |
| 1 | RW2 Table | 1 | £39.99 |

Total: **£39.99**.

### Axelera: AI Acceleration

| Item | Product | Quantity | Total |
| --- | --- | ---: | ---: |
| 1 | Axelera M.2 card, including customs | 1 | £260.00 |

Total: **£260.00**.

### eBay: Battery, Charger, And Connectors

| Item | Product | Quantity | Total |
| --- | --- | ---: | ---: |
| 1 | JST-PH 2 or 3 Way Prewired Connector Lead Male Female Plug Socket, 150mm; pack size 5; MPN 930492; 3-way male | 1 | £5.30 |
| 2 | ECO-WORTHY 5A 12V LiFePO4 Lithium Battery Charger with LCD Screen, AC to DC | 1 | £32.99 |
| 3 | ECO-WORTHY 12V Lithium Battery 30Ah LiFePO4, 4000+ cycles | 1 | £74.99 |

Total: **£113.28**.

## Current Hardware Limits

- Supplier links, ordering notes, and replacement rules are incomplete.
- Readiness evidence for mounting, wiring, power, motion, sensor quality, and
  stop behavior is tracked separately in
  [hardware-readiness-checklist.md](hardware-readiness-checklist.md).
- Treat this BOM as a component reference, not assembly or deployment
  instructions.
