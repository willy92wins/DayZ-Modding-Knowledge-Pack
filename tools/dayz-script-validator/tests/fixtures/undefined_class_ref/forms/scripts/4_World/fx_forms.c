#define FX_LOCAL_FLAG

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
#ifdef FX_SOME_OTHER_MOD
        FX_OptionalDependency.Hook();
#endif
#ifdef DIAG_DEVELOPER
        FX_MissingUnderVanillaMacro.Debug();
        FX_VanillaDiagOnly diag;
#endif
#ifdef FX_FORMS_ON
        FX_MissingUnderConfigDefine.Hook();
#endif
#ifdef FX_LOCAL_FLAG
        FX_MissingUnderLocalDefine.Hook();
#else
        FX_MissingUnderElse.Hook();
#endif
    }
}
