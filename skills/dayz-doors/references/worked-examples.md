# Verified worked examples

## Contents

- [How to use these examples](#how-to-use-these-examples)
- [Simple Door](#simple-door-door-plus-handle)
- [Door with Button](#door-with-button-static-controller)
- [Expert Mode](#expert-mode-door-plus-handle-plus-lever)
- [Cross-pattern diff](#cross-pattern-diff)
- [Source discrepancies](#source-discrepancies)

## How to use these examples

Each block is **[EXACT]** content from the supplied .cfg/config.cpp, with line endings normalized for Markdown. Originals are copied byte-for-byte under **assets/**.

Treat each pair side by side: model.cfg defines bones, selections, and sources; config.cpp binds Doors components, timing, sounds, and damage.

## Simple Door: door plus handle

### Side-by-side mapping

| Real model.cfg | Real config.cpp |
|---|---|
| **door1 -> ""**, **handle -> door1**. | One Doors entry **Door1**. |
| Door and handle source **door1**. | **component = "door1"**. |
| Handle **0..0.15**; door **0.15..1**. | **animPeriod = 1.3**; init values **0.0**. |

The handle follows the door transform. It reaches angle1 **-1.4** by phase **0.15**; then the door begins its rotation to **1.9**.

### [EXACT] model.cfg - assets/Door/Simple_Door.cfg

<!-- BEGIN VERBATIM: assets/Door/Simple_Door.cfg -->
~~~cpp
class cfgSkeletons
{
	class Simple_DoorSkeleton
	{
		skeletonInherit = "";
		isDiscrete = 0;
		SkeletonBones[]=
		{
			
			"door1","",
			"handle","door1",
		};
	};
};
class CfgModels
{
	class Default
	{
		sections[] = {};
		sectionsInherit="";
		skeletonName = "";
	};
	class Simple_Door:Default
	{
		skeletonName="Simple_DoorSkeleton";
		sections[]={};
		class Animations
		{
			class Door1
			{
				type = "rotation";
				selection = "door1";
				source = "door1";
				axis = "door1_axis";
				memory = 1; 
				minValue = 0.15; 
				maxValue = 1; 
				angle0 = 0; 
				angle1 = 1.9;
			};
			class handle
			{
				type = "rotation";
				selection = "handle";
				source = "door1";
				axis = "handle_axis";
				memory = 1; 
				minValue = 0; 
				maxValue = 0.15; 
				angle0 = 0; 
				angle1 = -1.4; 
			};
		};
	};
};
~~~
<!-- END VERBATIM: assets/Door/Simple_Door.cfg -->

### [EXACT] config.cpp - assets/Door/config.cpp

<!-- BEGIN VERBATIM: assets/Door/config.cpp -->
~~~cpp
class CfgPatches
{
	class Doors_Buttons_Lesson_Simple_Door
	{
		requiredAddons[] = {"DZ_Data"};
	};
};

class CfgVehicles
{
	class HouseNoDestruct;
	class land_Simple_Door: HouseNoDestruct
	{
		scope = 1;
		model = "Doors_Buttons_Lesson\Door\Simple_Door.p3d";
		class Doors
		{
			class Door1
			{
				displayName = "Door 1";
				component = "door1";
				soundPos = "door1_action";
				animPeriod = 1.3;
				initPhase = 0.0;
				initOpened = 0.0;
				soundOpen = "doorMetalSmallOpen";
				soundClose = "doorMetalSmallClose";
				soundLocked = "doorMetalSmallRattle";
				soundOpenABit = "doorMetalSmallOpenABit";
			};
		};
		class DamageSystem
		{
			class GlobalHealth
			{
				class Health
				{
					hitpoints = 1000;
				};
			};
			class GlobalArmor
			{
				class Projectile
				{
					class Health { damage = 0; };
					class Blood { damage = 0; };
					class Shock { damage = 0; };
				};
				class Melee
				{
					class Health { damage = 0; };
					class Blood { damage = 0; };
					class Shock { damage = 0; };
				};
			};
			class DamageZones
			{
				class Door1
				{
					class Health
					{
						hitpoints = 1000;
						transferToGlobalCoef = 0;
					};
					componentNames[] = {"door1"};
					fatalInjuryCoef = -1;
					class ArmorType
					{
						class Projectile
						{
							class Health { damage = 2; };
							class Blood { damage = 0; };
							class Shock { damage = 0; };
						};
						class Melee
						{
							class Health { damage = 2.5; };
							class Blood { damage = 0; };
							class Shock { damage = 0; };
						};
					};
				};
			};
		};
	};
};
~~~
<!-- END VERBATIM: assets/Door/config.cpp -->

## Door with Button: static controller

### Side-by-side mapping

| Real model.cfg | Real config.cpp |
|---|---|
| Only bone **door1 -> ""**; no button bone. | One Doors entry **Door1_Open**. |
| Moving **door1**; source **door1_open**. | **component = "door1_open"**. |
| Door phase **0..1**. | **soundPos = "door1_action"**, period **1.0**. |

The button is static. The tutorial places View Geometry selection and interaction point at the button as **door1_open**; interacting there drives moving selection **door1**.

### [EXACT] model.cfg - assets/Door_w_Button/Door_w_Button.cfg

<!-- BEGIN VERBATIM: assets/Door_w_Button/Door_w_Button.cfg -->
~~~cpp
class cfgSkeletons
{
	class Door_w_ButtonSkeleton
	{
		skeletonInherit = "";
		isDiscrete = 0;
		SkeletonBones[]=
		{
			"door1"	,""
		};
	};
};
class CfgModels
{
	class Default
	{
		Sections[] ={};
		sectionsInherit="";
		skeletonName = "";
	};
	class Door_w_Button:Default
	{
		skeletonName="Door_w_ButtonSkeleton";
		sections[]={};
		class Animations
		{
			class Door1
			{
				type = "rotation";
				selection = "door1";
				source = "door1_open";
				axis = "door1_axis";
				memory = 1; 
				minValue = 0.0; 
				maxValue = 1; 
				angle0 = 0; 
				angle1 = 1.9;
			};
		};
	};
};
~~~
<!-- END VERBATIM: assets/Door_w_Button/Door_w_Button.cfg -->

### [EXACT] config.cpp - assets/Door_w_Button/config.cpp

<!-- BEGIN VERBATIM: assets/Door_w_Button/config.cpp -->
~~~cpp
class CfgPatches
{
	class Doors_Buttons_Lesson_Door_w_Button
	{
		requiredAddons[] = {"DZ_Data"};
	};
};

class CfgVehicles
{
	class HouseNoDestruct;
	class land_Door_w_Button: HouseNoDestruct
	{
		scope = 1;
		model = "Doors_Buttons_Lesson\Door_w_Button\Door_w_Button.p3d";
		class Doors
		{
			class Door1_Open
			{
				displayName = "Door 1";
				component = "door1_open";
				soundPos = "door1_action";
				animPeriod = 1.0;
				initPhase = 0.0;
				initOpened = 0.0;
				soundOpen = "doorMetalSmallOpen";
				soundClose = "doorMetalSmallClose";
				soundLocked = "doorMetalSmallRattle";
				soundOpenABit = "doorMetalSmallOpenABit";
			};
		};
		class DamageSystem
		{
			class GlobalHealth
			{
				class Health
				{
					hitpoints = 1000;
				};
			};
			class GlobalArmor
			{
				class Projectile
				{
					class Health { damage = 0; };
					class Blood { damage = 0; };
					class Shock { damage = 0; };
				};
				class Melee
				{
					class Health { damage = 0; };
					class Blood { damage = 0; };
					class Shock { damage = 0; };
				};
			};
			class DamageZones
			{
				class Door1
				{
					class Health
					{
						hitpoints = 1000;
						transferToGlobalCoef = 0;
					};
					componentNames[] = {"door1"};
					fatalInjuryCoef = -1;
					class ArmorType
					{
						class Projectile
						{
							class Health { damage = 2; };
							class Blood { damage = 0; };
							class Shock { damage = 0; };
						};
						class Melee
						{
							class Health { damage = 2.5; };
							class Blood { damage = 0; };
							class Shock { damage = 0; };
						};
					};
				};
			};
		};
	};
};
~~~
<!-- END VERBATIM: assets/Door_w_Button/config.cpp -->

## Expert Mode: door plus handle plus lever

### Side-by-side mapping

| Real model.cfg | Real config.cpp |
|---|---|
| door root, handle child, lever root. | Main **Door1_Open**, secondary **Lever**. |
| All source **door1_open**. | Both component **door1_open**. |
| Door starts **0.10**; lever ends **0.5**. | Main **initOpened = 0.5**; Lever period **0.50**. |

The handle follows the moving door. The lever is an independent root at the controller. All three animations share one source.

? The real config has two Doors entries for one source/component, contradicting a universal one-entry-per-source rule. The secondary Lever also omits **soundPos** and all sounds. Preserve it; ask before reusing that duplicate mapping.

### [EXACT] model.cfg - assets/Expert_Mode/Expert_Mode.cfg

<!-- BEGIN VERBATIM: assets/Expert_Mode/Expert_Mode.cfg -->
~~~cpp
class cfgSkeletons
{
	class Expert_ModeSkeleton
	{
		skeletonInherit = "";
		isDiscrete = 0;
		SkeletonBones[]=
		{
			"door1"	,"",
			"handle","door1",
			"lever",""
		};
	};
};
class CfgModels
{
	class Default
	{
		Sections[] ={};
		sectionsInherit="";
		skeletonName = "";
	};
	class Expert_Mode:Default
	{
		skeletonName="Expert_ModeSkeleton";
		sections[]={};
		class Animations
		{
			class Door1
			{
				type = "rotation";
				selection = "door1";
				source = "door1_open";
				axis = "door1_axis";
				memory = 1; 
				minValue = 0.10; 
				maxValue = 1; 
				angle0 = 0; 
				angle1 = 1.9;
			};
			class Handle
			{
				type = "rotation";
				selection = "handle";
				source = "door1_open";
				axis = "handle_axis";
				memory = 1; 
				minValue = 0.0; 
				maxValue = 1.0; 
				angle0 = 0; 
				angle1 = -1.7;
			};
			class Lever
			{
				type = "rotation";
				selection = "lever";
				source = "door1_open";
				axis = "lever_axis";
				memory = 1; 
				minValue = 0.0; 
				maxValue = 0.5; 
				angle0 = 0; 
				angle1 = -0.88;
			};
		};
	};
};
~~~
<!-- END VERBATIM: assets/Expert_Mode/Expert_Mode.cfg -->

### [EXACT] config.cpp - assets/Expert_Mode/config.cpp

<!-- BEGIN VERBATIM: assets/Expert_Mode/config.cpp -->
~~~cpp
class CfgPatches
{
	class Doors_Buttons_Lesson_Expert_Mode
	{
		requiredAddons[] = {"DZ_Data"};
	};
};

class CfgVehicles
{
	class HouseNoDestruct;
	class land_Expert_Mode: HouseNoDestruct
	{
		scope = 1;
		model = "Doors_Buttons_Lesson\Expert_Mode\Expert_Mode.p3d";
		class Doors
		{
			class Door1_Open
			{
				displayName = "Door 1";
				component = "door1_open";
				soundPos = "door1_action";
				animPeriod = 1.0;
				initPhase = 0.0;
				initOpened = 0.5;
				soundOpen = "doorMetalSmallOpen";
				soundClose = "doorMetalSmallClose";
				soundLocked = "doorMetalSmallRattle";
				soundOpenABit = "doorMetalSmallOpenABit";
			};
			class Lever
			{
				displayName = "Lever";
				component = "door1_open";
				animPeriod = 0.50;
				initPhase = 0.0;
				initOpened = 0.0;
			};
		};
		class DamageSystem
		{
			class GlobalHealth
			{
				class Health
				{
					hitpoints = 1000;
				};
			};
			class GlobalArmor
			{
				class Projectile
				{
					class Health { damage = 0; };
					class Blood { damage = 0; };
					class Shock { damage = 0; };
				};
				class Melee
				{
					class Health { damage = 0; };
					class Blood { damage = 0; };
					class Shock { damage = 0; };
				};
			};
			class DamageZones
			{
				class Door1
				{
					class Health
					{
						hitpoints = 1000;
						transferToGlobalCoef = 0;
					};
					componentNames[] = {"door1"};
					fatalInjuryCoef = -1;
					class ArmorType
					{
						class Projectile
						{
							class Health { damage = 2; };
							class Blood { damage = 0; };
							class Shock { damage = 0; };
						};
						class Melee
						{
							class Health { damage = 2.5; };
							class Blood { damage = 0; };
							class Shock { damage = 0; };
						};
					};
				};
			};
		};
	};
};
~~~
<!-- END VERBATIM: assets/Expert_Mode/config.cpp -->

## Cross-pattern diff

| Concern | Simple Door | Door with Button | Expert Mode |
|---|---|---|---|
| Moving bones | Door + handle | Door only | Door + handle + lever |
| Parent graph | Handle follows door | Door root | Handle follows door; lever root |
| Interactive source | **door1** | **door1_open** at button | **door1_open** at lever |
| Static controller bone | N/A | Button omitted | N/A; lever animates |
| Phase sequencing | Handle 0..0.15; door 0.15..1 | Door 0..1 | Door 0.10..1; handle 0..1; lever 0..0.5 |
| Doors components | **door1** | **door1_open** | **door1_open** twice |
| DamageZone component | **door1** | **door1** | **door1** |

No pattern introduces **AnimationSources** or script calls; those belong to **dayz-animation-pipeline**.

## Source discrepancies

- Real files above are authoritative for packaged examples.
- Expert prose at **Welcome to novoGODs Expert_Mode Door mod.txt:128-137** shows **switchOpen/switchClose**.
- Real **assets/Expert_Mode/config.cpp:31-38** has neither sound.
- ? No in-game test established the exact purpose/behavior of the duplicate Expert Lever Doors entry.
