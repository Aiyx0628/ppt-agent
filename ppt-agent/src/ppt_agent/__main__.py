from uvicorn import run

from ppt_agent.config import get_settings


def main() -> None:
    settings = get_settings()
    run(
        "ppt_agent.api.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )


if __name__ == "__main__":
    main()
