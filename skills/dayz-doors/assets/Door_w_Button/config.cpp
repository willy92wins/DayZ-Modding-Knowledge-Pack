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