from desktop_agent_dev.planner import Planner


def test_create_plan_has_three_steps() -> None:
    plan = Planner().create_plan("open app")
    assert plan.goal == "open app"
    assert len(plan.steps) == 3
