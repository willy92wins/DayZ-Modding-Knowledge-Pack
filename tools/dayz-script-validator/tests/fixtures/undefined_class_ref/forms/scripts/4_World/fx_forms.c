#define FX_LOCAL_FLAG
#ifdef DIAG_DEVELOPER
#define FX_DIAG_ONLY_FLAG
#endif

class FX_Known
{
    static FX_Known Make()
    {
        return new FX_Known();
    }

    void Run(EntityAI target)
    {
    }
}

class FX_Forms<Class TItem>
{
    ref FX_Known Planner;
    TItem m_Item;

    void Exercise(EntityAI source)
    {
        FX_Known known = FX_Known.Make();
        Object createdA = new FX_MissingNew();
        EntityAI castB = FX_MissingCast.Cast(source);
        FX_MissingDecl declC;
        ref array<ref FX_MissingTemplateArg> listD;
        FX_MissingStatic.DoStatic();
        Planner.Run(source);
        int mode = EVanillaMode.A;
        TStringArray names = new TStringArray();
        PlayerBase player = PlayerBase.Cast(source);
        SurfaceDetectionParameters params = new SurfaceDetectionParameters();
        FX_MissingSpacedCall.Hook ();
        string fx_first, FX_Second;
        int length = FX_Second.Length();
#ifdef FX_SOME_OTHER_MOD
        FX_OptionalDependency.Hook();
        auto optional = new Param3<int, FX_MissingBehindTemplate, int>(0, null, 0);
#endif
        FX_MissingBehindTemplate.Sort();
#ifdef DIAG_DEVELOPER
        FX_MissingUnderVanillaMacro.Debug();
        FX_VanillaDiagOnly diag;
#else
        FX_MissingUnderVanillaElse.Hook();
#endif
#ifdef FX_FORMS_ON
        FX_MissingUnderConfigDefine.Hook();
#endif
#ifndef FX_FORMS_ON
        FX_DeadUnderIfndef.Hook();
#endif
#ifdef FX_LOCAL_FLAG
        FX_MissingUnderLocalDefine.Hook();
#else
        FX_DeadUnderElse.Hook();
#endif
#ifndef FX_DIAG_ONLY_FLAG
        FX_MissingUnderConditionalDefine.Hook();
#endif
#ifndef FX_CONDITIONAL_CONFIG_FLAG
        FX_MissingUnderConditionalConfigDefine.Hook();
#endif
    }
}
