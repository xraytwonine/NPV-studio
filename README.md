# NPV-studio

Look, I am lazy. I don't want to read pages of manuals and poke around multiple freeware that's ultimately incohesive with a steep learning curve... but I ended up doing that anyways, so may be now you don't have to?

TL:DR - you should be able to fire it up and use the tool with the minimal instruction included on screen to make a Vortex importable NPV (AMM spawn only, I am considering photomode).

This is a guided desktop tool that turns V’s character-creator settings into a spawnable (AMM only), Vortex-ready NPV. 
It automates the difficult Blender, WolvenKit setup while keeping the game installation read-only.
This should simplify the NPV process allow more people to make custom characters for their artistic projects.

NPV Studio helps you create a non-player version of V—usually called an NPV—without requiring you to manually work through dozens of Blender and WolvenKit steps.

An NPV is a standalone copy of your character that can be spawned through Appearance Menu Mod. It does not replace your playable V, alter your savegame or change your character permanently.
The traditional NPV workflow involves:
•	Preparing and morphing the head in Blender.
•	Finding the correct meshes and appearances.
•	Editing
.app
and
.ent
resources.
•	Importing and compiling files with WolvenKit.
•	Creating an Appearance Menu Mod registration.
•	Arranging the correct Vortex archive structure.
•	Packaging everything without accidentally writing into the game.
NPV Studio connects those steps through one guided interface. You enter the same values shown in Cyberpunk 2077’s character creator, verify the required programs and select Build Vortex ZIP.
You do not need to understand Blender or WolvenKit to use the basic workflow. They still need to be installed, but NPV Studio operates them automatically.

Basic setup
1.	Extract the complete NPV Studio release to a writable folder.
2.	Run
NPV-Studio.exe
.
3.	Expand Dependencies and Paths.
4.	Review the dependency status list.
5.	Use the provided links to download anything missing.
6.	Select the required paths:
o	Cyberpunk 2077 installation folder
o	Writable build workspace
o	Blender executable
o	WolvenKit Blender IO Suite folder
o	WolvenKit CLI executable
o	Extracted NPV tutorial resource folder
7.	Select Save Paths and Refresh.
Green build requirements are ready.
INSTALL MOD
means an in-game mod is absent. This does not prevent NPV Studio from building the ZIP, but you will need that mod to use the applicable in-game feature.
Creating your character
You can enter the values manually or load a character file.
To copy an existing V:
1.	Install Appearance Change Unlocker if necessary.
2.	Open a mirror or the appearance editor in-game.
3.	Record the numbered values for your character.
4.	Enter those values into NPV Studio in the displayed order.
You can also start with one of the JSON files under the included
character templates
folder.
Choose:
•	A display name.
•	A unique internal namespace.
•	Feminine or masculine body frame.
•	Voice tone.
•	All visible character-creator selections.
•	A preset save folder.
•	A Vortex ZIP export folder.
Save the configuration as a preset if you want to reuse or adjust it later.
Building the NPV
1.	Select Validate Configuration.
2.	Correct any unsupported or missing selections reported by the program.
3.	Select Build Vortex ZIP.
4.	Allow Blender and WolvenKit to finish.
The build can take several minutes. NPV Studio runs Blender without the normal interactive export dialogs, so you should not need to dismiss Blender popups.
When successful, the bottom of the application will show:
•	The completed ZIP location.
•	Its SHA-256 checksum.
•	The number of packaged files.
•	The debug-log location.
Installing the result
1.	Open Vortex.
2.	Use Install From File.
3.	Select the ZIP produced by NPV Studio.
4.	Enable and deploy the mod.
5.	Start Cyberpunk 2077.
6.	Open Appearance Menu Mod.
7.	Open the Spawn tab.
8.	Search for the character’s display name.
9.	Spawn the character.
The generated NPV exposes one public appearance named
default








Installation instructions
1. Extract the complete release ZIP to a writable folder.
2. Run `NPV-Studio.exe`.
3. Expand **Dependencies and Paths** at the top.
4. Select any dependency paths that were not detected automatically.
5. Choose separate folders for saved character presets and completed Vortex ZIP exports.
6. Complete or load the character selections, validate, and select **Build Vortex ZIP** at the bottom.
7. Optional: Once you have your NPV zip, go to Vortex, select "Install from file" and browse for that zip. Alternatively you can drop your NPV into the game's mod folder manually.

NPV Studio creates `settings.json` and its default workspace beside the executable on first launch. The application bundles Python, Qt, its UI, and its unattended Blender worker; Python does not need to be installed separately.

## Build dependencies

The portable executable does not redistribute Cyberpunk, WolvenKit, Blender, the WolvenKit Blender IO Suite, or the reusable NPV source project. Their paths can be selected in the application.

Appearance Menu Mod Appearance creator mod and Codeware are in-game runtime mods. They are not used to build the ZIP and appear as **Install Mod** rather than failed build dependencies when absent.

## Output folders

- **Build workspace:** temporary copies, generated resources, reports, and debug logs.
- **Preset folder:** reusable JSON character configurations.
- **Vortex ZIP export folder:** finished Vortex-installable ZIPs and checksum manifests.

The Cyberpunk installation is always treated as read-only. NPV Studio does not deploy files into the game and does not write into Vortex staging.

Main features
•  Body rigs and /Custom Hairs are currently not supported - vanilla body/hair only - I am working on this.
•  Feminine and masculine V support.
•  Character selections arranged in the same order as the in-game creator.
•  Load and save reusable character presets.
•  Supports NPV Studio JSON presets and simplified TXT character sheets.
•  Automates head morph generation through Blender.
•  Automates REDengine resource conversion and packing through WolvenKit CLI.
•  Creates the AMM custom-entity registration automatically.
•  Produces a minimized, Vortex-installable ZIP.
•  Includes a generic starter outfit.
•  Includes empty Appearance Creator Mod slots for adding clothing and accessories later.
•  Feminine NPVs include the tested dual-body and seam-fix options. This is due to how the game handles big boobs for player character vs NPV.
•  Build logs clearly identify unsupported selections or failed external tools.
•  Never installs directly into Cyberpunk 2077.
•  Never writes into Vortex staging.
•  Treats the game installation as a strictly read-only resource.

Clothing and accessory slots
Generated characters include empty Appearance Creator Mod slots:
•	Five face slots.
•	Five head slots.
•	Five torso slots.
•	Five leg slots.
•	Five item/accessory slots.
•	Two hand slots.
•	Two arm slots.
•	Two feet slots.
These slots begin empty and disabled. With Appearance Creator Mod installed, you can assign clothing or accessory meshes to them in-game. This should allow for some complex clothing/accessory arrangements.
Safety
NPV Studio follows a nondestructive build process:
•	Cyberpunk 2077 is a read-only source.
•	Reusable NPV resources are copied into an isolated workspace.
•	Original template resources are not edited.
•	Blender and WolvenKit output remains inside the selected workspace.
•	Finished mods are written only to the selected ZIP export folder.
•	Nothing is installed into the game automatically.
•	Nothing is written into Vortex staging automatically.
Final NPV Installation remains under the user’s control.
Current limitations
•	NPV Studio does not extract character values directly from a savegame. Values must be entered manually or loaded from a preset.
•	Modded hairstyles and custom character-creator additions require their own verified mappings.
•	Unsupported selections are stopped during validation rather than guessed.
•	Genital, pubic-hair, piercing-color and cheek-makeup-color values are preserved in presets but are not all compiled visually yet.
•	Cyberpunk handles clothing deformation differently for NPCs. Arbitrary clothing is not guaranteed to fit every body option.
•	The included starter outfit is intended as a safe baseline.
•	Custom clothing refits may still require individual Blender work.
•	Major Cyberpunk, Blender, WolvenKit or Blender add-on updates may require a corresponding NPV Studio update.


HARD Requirements
mods (install manually or via vortex):
•  Cyber Engine Tweaks
•  Appearance Menu Mod
•  Appearance Creator Mod


Software:
Blender
•  NPV Studio was developed around Blender 5.1.
Download Blender
•  Cyberpunk-Blender-add-on 
•  WolvenKit Blender IO Suite
This add-on gives Blender the Cyberpunk-specific import and export functionality used by the automated head builder.
Download the WolvenKit Blender IO Suite
•  WolvenKit CLI for Windows
Download the Windows console package—not the Linux console package and not only the desktop application. The executable selected in NPV Studio should be
WolvenKit.CLI.exe
Download WolvenKit releases
•  NPV tutorial source resources
Download the resource made by ManaVortex
tutorial_npv_wolvenkit_2_3
source package from manavortex’s NPV resource page.
This download is a source project, not a playable mod. Do not install it through Vortex. Extract it to a normal folder and select that folder inside NPV Studio. The resource page also explicitly identifies it as a source project rather than a mod-manager package. 
Download the NPV source resources

Optional development tool
•	WolvenKit desktop
The desktop application is useful for manually examining resources but is not required by NPV Studio’s automated build process.


Shout outs
ManaVortex for being the most responsive and active modder helping community members! Also for being the creator of NPV guide, source project and extensive Cyberpunk modding documentation.
•  NoraLee — pioneering NPV research and workflows.
•  WolvenKit contributors — REDengine resource tools and Blender integration.
•  MaximiliumM Appearance Menu Mod, Appearance Creator Mod
•  yamashi Cyber Engine Tweaks 
•  psiberx Codeware




"NPV Studio" is completely vibe coded via Chatgpt Codex

