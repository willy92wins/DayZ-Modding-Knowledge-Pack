// The dependency is named through a macro: its value is not read, so the
// dependency is unknown and the rule must not judge.
#define FX_DEPENDENCY "FX_Dep_Scripts"
class CfgPatches
{
    class FX_MacroConsumer
    {
        requiredAddons[] = {"DZ_Data", FX_DEPENDENCY};
    };
};
