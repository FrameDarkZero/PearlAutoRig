# PearlRig
## P.E.A.R.L. — Procedural Engine for Automated Rigging Layouts

PearlAutoRig (P.E.A.R.L.) is a modular Maya rigging framework focused on clean, repeatable rig setup.  
It begins with custom visual joint-placement locators and expands toward automated joint chains, module assembly, and a future Qt-driven auto-rig UI.

### Current Modules
- **CustomLocator**: artist-friendly, color-coded axis locators for joint placement and orientation clarity  
- **JointChainBuilder**: creates 3–4 joint placement chains (e.g., arms/legs), builds joints from locators, and supports side naming + orientation options

### Goals / Roadmap
- Locator-driven joint chain generation (in progress)
- Module-based rig building (spine, limbs, hands, etc.)
- Qt UI for fast, repeatable rig layouts
- Exportable build data for consistent results across characters

### Notes
This repository is actively evolving as part of a larger personal auto-rigging toolset.

### Related Projects

CustomLocator — Custom visual locator system used for joint placement.
https://github.com/FrameDarkZero/CustomLocator

