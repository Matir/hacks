from trashdig.agents.types import Task, TaskType, TaskStatus, Hypothesis

def test_task_creation():
    task = Task(type=TaskType.SCAN, target="src/main.py")
    assert task.type == TaskType.SCAN
    assert task.target == "src/main.py"
    assert task.status == TaskStatus.PENDING
    assert isinstance(task.id, str)
    assert task.context == {}

def test_hypothesis_creation():
    hypo = Hypothesis(
        type=TaskType.HUNT,
        target="src/api.py",
        description="SQL Injection in login",
        confidence=0.8
    )
    assert hypo.type == TaskType.HUNT
    assert hypo.target == "src/api.py"
    assert hypo.description == "SQL Injection in login"
    assert hypo.confidence == 0.8
    assert hypo.status == TaskStatus.PENDING
