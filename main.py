import typer
from typing import Optional
from .context import create_context, Context

app = typer.Typer(add_completion=False)

# global_context is created when the CLI runner starts
# we create lazily inside a callback to allow tests to patch create_context if needed
def _get_context() -> Context:
    # instantiate context once per process
    # tests can monkeypatch create_context to supply a test context
    global _CTX
    try:
        return _CTX
    except NameError:
        _CTX = create_context()
        return _CTX

@app.command()
def status(verbose: bool = typer.Option(False, "--verbose", "-v")):
    """Show service status."""
    ctx = _get_context()
    logger = ctx.logger
    if verbose:
        logger.setLevel("DEBUG")
    logger.info("Checking status")
    try:
        resp = ctx.http_client.get("/health")
        resp.raise_for_status()
        typer.echo(f"OK: {resp.text}")
    except Exception as exc:
        logger.exception("Status check failed")
        raise typer.Exit(code=1)

@app.command()
def deploy(tag: str = typer.Argument(..., help="Image tag to deploy")):
    """Trigger deployment."""
    ctx = _get_context()
    ctx.logger.info("Triggering deploy", extra={"tag": tag})
    # example: post to controller
    r = ctx.http_client.post("/deploy", json={"tag": tag})
    r.raise_for_status()
    typer.echo("Deploy started")
