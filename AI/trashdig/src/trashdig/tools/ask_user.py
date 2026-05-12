from collections.abc import Awaitable, Callable

from google.adk.tools import FunctionTool


def create_ask_user_tool(on_ask: Callable[[str], Awaitable[str]]) -> FunctionTool:
    """Creates a tool that allows the agent to ask the user a question.

    Args:
        on_ask: A callback function that takes the question and returns the answer.
    """

    async def ask_user(question: str) -> str:
        """Asks the user a question for clarification or expert insight.

        Use this when you encounter ambiguities in business logic, need to confirm
        a hypothesis that requires domain knowledge, or are unsure how to proceed
        autonomously.

        Args:
            question: The question to ask the user.
        """
        answer = await on_ask(question)
        if not answer:
            return "[User Response]: User skipped this question."
        return f"[User Response]: {answer}"

    return FunctionTool(func=ask_user)
