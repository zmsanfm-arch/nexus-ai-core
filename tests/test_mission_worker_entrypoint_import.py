def test_mission_worker_entrypoint_imports_web_studio_handlers():
    from app.mission_worker_entrypoint import run
    from app.agents.web_studio import WEB_STUDIO_ROLE_PROMPTS

    assert callable(run)
    assert len(WEB_STUDIO_ROLE_PROMPTS) == 21
