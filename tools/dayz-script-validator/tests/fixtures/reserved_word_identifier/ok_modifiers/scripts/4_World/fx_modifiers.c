// The four words in the positions vanilla uses them, and names that only
// start with them. None of this is a finding.
sealed class FX_SealedThing
{
}

class FX_Modifiers
{
    vector sealedPos;
    vector localOffset;
    EntityAI owner;
    int outCount;

    proto native owned string FX_GetName();

    void Fill(out array<string> names, local array<string> overridden, local bool check = false)
    {
        int count = 0;
    }

    void Read(notnull out array<EntityAI> items)
    {
    }
}
