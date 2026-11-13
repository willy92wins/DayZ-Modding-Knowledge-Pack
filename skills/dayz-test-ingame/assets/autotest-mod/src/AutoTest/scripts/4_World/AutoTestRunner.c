// Server side: walks the registry one test at a time and logs one line per result.
//   [AUTOTEST] PASS <name> <message>
//   [AUTOTEST] FAIL <name> <message>
//   [AUTOTEST] DONE passed=<n> failed=<n>      <- the line an outside script waits for
class AutoTestRunner
{
	static ref AutoTestRunner s_Instance;

	PlayerBase m_Player;
	int m_Index;
	int m_Passed;
	int m_Failed;

	static void Schedule(PlayerBase player, int delayMs)
	{
		if (s_Instance)
			return;   // one run per server start
		s_Instance = new AutoTestRunner();
		s_Instance.m_Player = player;
		// Godmode from the first moment: the character stands in the world while the client loads.
		player.SetAllowDamage(false);
		// The client is still loading when OnConnect fires; give it time to get a player entity.
		GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(s_Instance.Next, delayMs, false);
	}

	void Next()
	{
		array<ref AutoTestCase> all = AutoTestRegistry.All();
		if (m_Index >= all.Count())
		{
			m_Player.SetAllowDamage(false);
			Print("[AUTOTEST] DONE passed=" + m_Passed + " failed=" + m_Failed);
			return;
		}
		AutoTestCase t = all.Get(m_Index);
		m_Player.SetAllowDamage(t.NeedsDamage());   // godmode unless this test needs damage
		t.ServerSetup(m_Player);

		ScriptRPC rpc = new ScriptRPC();
		rpc.Write(t.Name());
		rpc.Send(m_Player, AUTOTEST_RPC_RUN, true, m_Player.GetIdentity());
		GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(Timeout, 20000, false, m_Index);
	}

	void OnResult(string name, bool passed, string msg)
	{
		array<ref AutoTestCase> all = AutoTestRegistry.All();
		if (m_Index >= all.Count() || all.Get(m_Index).Name() != name)
			return;   // late or duplicate answer

		string serverMsg;
		if (!all.Get(m_Index).ServerCheck(m_Player, serverMsg))
			passed = false;
		if (serverMsg != "")
			msg = msg + " | server: " + serverMsg;
		Finish(passed, name, msg);
	}

	void Timeout(int index)
	{
		if (index != m_Index)
			return;
		Finish(false, AutoTestRegistry.All().Get(m_Index).Name(), "no answer from the client");
	}

	protected void Finish(bool passed, string name, string msg)
	{
		if (passed)
		{
			m_Passed++;
			Print("[AUTOTEST] PASS " + name + " " + msg);
		}
		else
		{
			m_Failed++;
			Print("[AUTOTEST] FAIL " + name + " " + msg);
		}
		m_Index++;
		Next();
	}
}

// Client side: run the requested test half, retry while it fails, then answer the server.
class AutoTestClient
{
	static ref AutoTestClient s_Instance;

	static void Run(string name)
	{
		if (!s_Instance)
			s_Instance = new AutoTestClient();
		s_Instance.Try(name, 0);
	}

	void Try(string name, int attempt)
	{
		AutoTestCase t = AutoTestRegistry.Find(name);
		string msg;
		bool ok = false;
		if (t)
			ok = t.ClientCheck(msg);
		else
			msg = "unknown test";

		if (!ok && t && attempt < 10)
		{
			GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(Try, 500, false, name, attempt + 1);
			return;
		}

		Print("[AUTOTEST-CLIENT] " + name + " ok=" + ok + " " + msg);
		ScriptRPC rpc = new ScriptRPC();
		rpc.Write(name);
		rpc.Write(ok);
		rpc.Write(msg);
		rpc.Send(GetGame().GetPlayer(), AUTOTEST_RPC_RESULT, true);
	}
}

modded class PlayerBase
{
	override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
	{
		super.OnRPC(sender, rpc_type, ctx);

		if (rpc_type == AUTOTEST_RPC_RUN && !GetGame().IsDedicatedServer())
		{
			string runName;
			if (ctx.Read(runName))
				AutoTestClient.Run(runName);
		}
		else if (rpc_type == AUTOTEST_RPC_RESULT && GetGame().IsDedicatedServer())
		{
			string name;
			bool passed;
			string msg;
			if (ctx.Read(name) && ctx.Read(passed) && ctx.Read(msg) && AutoTestRunner.s_Instance)
				AutoTestRunner.s_Instance.OnResult(name, passed, msg);
		}
	}
}
