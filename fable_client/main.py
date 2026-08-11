from ._cli import app


def run_cli():  # pragma: no cover
    app(max_content_width=120)


if __name__ == "__main__":  # pragma: no cover
    run_cli()
