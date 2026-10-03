class CfgPatches
{
    class FX_Forms
    {
        requiredAddons[] = {"DZ_Data"};
    };
};

class CfgMods
{
    class FX_Forms
    {
        defines[] = {"FX_FORMS_ON"};
    };
#ifdef FX_OPTIONAL_MOD
    class FX_FormsOptional
    {
        defines[] = {"FX_CONDITIONAL_CONFIG_FLAG"};
    };
#endif
};
