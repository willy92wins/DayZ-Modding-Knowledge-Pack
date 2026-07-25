class LF_UIProbe
{
	protected static bool s_Ran;
	protected static Widget s_LeafRoot;
	protected static Widget s_LfRoot;
	protected static Widget s_CrlfRoot;

	static void Run()
	{
		if (s_Ran)
			return;

		s_Ran = true;
		Log("[LF_UI_PROBE_BEGIN]|schema=dayz-ui-probe-v1");
		s_LeafRoot = ProbeLeaf();
		s_LfRoot = ProbeContinuation(
			"continuation-lf",
			"LF_UIProbe/gui/layouts/continuation-lf.layout"
		);
		s_CrlfRoot = ProbeContinuation(
			"continuation-crlf",
			"LF_UIProbe/gui/layouts/continuation-crlf.layout"
		);
		Log("[LF_UI_PROBE_END]|schema=dayz-ui-probe-v1");
	}

	protected static Widget ProbeLeaf()
	{
		Widget root = GetGame().GetWorkspace().CreateWidgets(
			"LF_UIProbe/gui/layouts/leaf-without-child-block.layout"
		);
		if (!root)
		{
			Log("[LF_UI_PROBE_RESULT]|case=leaf-without-child-block|status=load_failed");
			return null;
		}

		Widget leaf = root.FindAnyWidget("LeafButton");
		if (!leaf)
		{
			Log("[LF_UI_PROBE_RESULT]|case=leaf-without-child-block|status=widget_missing");
			return root;
		}

		Log(
			"[LF_UI_PROBE_RESULT]|case=leaf-without-child-block|status=loaded|name="
			+ leaf.GetName()
			+ "|type="
			+ leaf.GetTypeName()
		);
		return root;
	}

	protected static Widget ProbeContinuation(string caseId, string layoutPath)
	{
		Widget root = GetGame().GetWorkspace().CreateWidgets(layoutPath);
		if (!root)
		{
			Log("[LF_UI_PROBE_RESULT]|case=" + caseId + "|status=load_failed");
			return null;
		}

		Widget candidate = root.FindAnyWidget("ProbeButton");
		ButtonWidget button = ButtonWidget.Cast(candidate);
		if (!button)
		{
			Log("[LF_UI_PROBE_RESULT]|case=" + caseId + "|status=widget_missing");
			return root;
		}

		// Verified vanilla API: ButtonWidget.GetText(out string) returns void.
		string value;
		button.GetText(value);
		Log(
			"[LF_UI_PROBE_RESULT]|case="
			+ caseId
			+ "|status=loaded|value="
			+ value
		);
		return root;
	}

	static void Cleanup()
	{
		if (s_LeafRoot)
		{
			s_LeafRoot.Unlink();
			s_LeafRoot = null;
		}
		if (s_LfRoot)
		{
			s_LfRoot.Unlink();
			s_LfRoot = null;
		}
		if (s_CrlfRoot)
		{
			s_CrlfRoot.Unlink();
			s_CrlfRoot = null;
		}
		s_Ran = false;
	}

	protected static void Log(string message)
	{
		PrintToRPT(message);
	}
}

modded class MissionGameplay
{
	override void OnInit()
	{
		super.OnInit();

		#ifndef SERVER
		LF_UIProbe.Run();
		#endif
	}

	override void OnMissionFinish()
	{
		#ifndef SERVER
		LF_UIProbe.Cleanup();
		#endif

		super.OnMissionFinish();
	}
}
