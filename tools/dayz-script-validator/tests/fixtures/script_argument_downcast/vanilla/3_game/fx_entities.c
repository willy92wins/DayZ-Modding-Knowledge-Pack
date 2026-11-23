class Object : IEntity
{
    proto native void FX_SetOwner(Object owner);

    void FX_Touch(Object other)
    {
    }
}

class EntityAI : Object
{
    // A script method of the vanilla tree that takes an EntityAI, and a proto
    // that takes one.
    void FX_Hold(EntityAI item)
    {
    }

    proto native void FX_Show(EntityAI item);
}

class FX_Util
{
    static void FX_Store(EntityAI item)
    {
    }
}
