from __future__ import annotations
import typing
import pathlib
import subprocess
import shlex


HERE: typing.Final[pathlib.Path] = pathlib.Path(__file__).parent.resolve()


def run_kohya(
    script: str | pathlib.Path,
    *,
    accelerate: bool = True,
    args: str | typing.Sequence[str] = (),
    env: dict[str, str] | None = None,
) -> None:
    """
    Run a kohya script.
    The script is specified relative to the kohya-trainer folder.
    """
    
    kohya_path = HERE / "kohya-trainer"
    
    if isinstance(script, str):
        script = pathlib.Path(script)
    
    if not isinstance(args, str):
        args = shlex.join(args)
    
    runner: str = "python"
    if accelerate:
        runner = "accelerate launch --config_file=accelerate_config/config.yaml --num_cpu_threads_per_process=1"
    
    if env is None:
        env = {}
    
    env_str = " && ".join(f"set {key}={shlex.quote(value)}" for key, value in env.items())
    
    command = f"""\
    cd {kohya_path} && \
    call {pathlib.Path(".venv/Scripts/activate.bat")} && \
    {env_str} && \
    {runner} {script} {args}
    """
    
    subprocess.check_call(command, shell=True)


__all__ = [
    "run_kohya",
]
