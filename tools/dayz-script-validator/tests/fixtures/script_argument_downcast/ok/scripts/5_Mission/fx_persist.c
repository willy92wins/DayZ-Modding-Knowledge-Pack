class FX_PersistRecord
{
    Object m_RefEnt;
    EntityAI m_Owner;
}

class FX_Persist
{
    protected bool FX_SubtreeBorn(EntityAI root)
    {
        return root != null;
    }

    protected void FX_Note(Object target)
    {
    }

    bool FX_Check(FX_PersistRecord rec, EntityAI item, Object obj)
    {
        // The fix: the entity cast first.
        bool born = FX_SubtreeBorn(EntityAI.Cast(rec.m_RefEnt));
        // Narrowed with Class.CastTo first, then passed as an EntityAI.
        EntityAI narrowed;
        if (Class.CastTo(narrowed, obj))
            born = this.FX_SubtreeBorn(narrowed);
        // The same type, an up-cast and null.
        born = FX_SubtreeBorn(rec.m_Owner);
        born = FX_SubtreeBorn(item);
        FX_Note(item);
        FX_Note(rec.m_Owner);
        born = FX_SubtreeBorn(null);
        // A comment, a string and a branch that never compiles.
        // born = FX_SubtreeBorn(rec.m_RefEnt);
        string text = "FX_SubtreeBorn(obj)";
        return born;
    }
}

#if 0
class FX_Dead : FX_Persist
{
    void F(FX_PersistRecord rec)
    {
        FX_SubtreeBorn(rec.m_RefEnt);
    }
}
#endif
