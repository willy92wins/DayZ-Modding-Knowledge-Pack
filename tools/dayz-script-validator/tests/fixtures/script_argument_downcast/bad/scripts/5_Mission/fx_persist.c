// Inbox 250d, DayZDiag 1.30.164289, on the mod this one stands for (two calls
// of this shape): "Unsafe down-casting, use 'EntityAI.Cast' for safe
// down-casting", "Types 'Object' and 'EntityAI' are unrelated" and "Cannot
// convert 'Object' to 'EntityAI' for argument '0' to method
// 'SubtreeBornInInventory'", and the Mission module did not compile.
class FX_PersistRecord
{
    Object m_RefEnt;
}

class FX_Persist
{
    protected bool FX_SubtreeBorn(EntityAI root)
    {
        return root != null;
    }

    bool FX_CheckOne(FX_PersistRecord rec)
    {
        return FX_SubtreeBorn(rec.m_RefEnt);
    }

    bool FX_CheckTwo(FX_PersistRecord rec)
    {
        return this.FX_SubtreeBorn(rec.m_RefEnt);
    }

    static bool FX_CheckThree(FX_Persist census, Object obj)
    {
        return census.FX_SubtreeBorn(obj);
    }
}
