import asyncio
from collections.abc import Coroutine
from typing import TypeVar

T = TypeVar("T")


def run_async(coro: Coroutine[object, object, T]) -> T:
    """Run an async coroutine from Streamlit's synchronous context.

    Streamlit runs synchronously, but our service layer (httpx, aiosqlite)
    is fully async. This bridge lets pages call async functions cleanly.

    Usage:
        result = run_async(jira_client.search_issues("assignee = currentUser()"))
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # We're inside an existing event loop (e.g., Streamlit's internal loop)
        # Create a new loop in a thread to avoid conflict
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)
