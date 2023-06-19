from __future__ import annotations
import typing
import pathlib
import subprocess
import shlex
import platform


def run_kohya(
    script: str | pathlib.Path,
    *,
    kohya_path: pathlib.Path,
    accelerate: bool = True,
    args: str | typing.Sequence[str] = (),
    env: dict[str, str] | None = None,
) -> None:
    """
    Run a kohya script.
    The script is specified relative to the kohya-trainer folder.
    """
    
    if isinstance(script, str):
        script = pathlib.Path(script)
    
    if not isinstance(args, str):
        args = shlex.join(args)
    
    runner: str = "python"
    if accelerate:
        # --config_file=accelerate_config/config.yaml
        # Let's use the default config, in fact
        runner = "accelerate launch --num_cpu_threads_per_process=1"
    
    if env is None:
        env = {}
    
    activate_script = pathlib.Path("venv/Scripts/activate")
    env_str = "export " + " ".join(f"{key}={shlex.quote(value)}" for key, value in env.items())
    
    if platform.system() == "Windows":
        activate_script = activate_script.with_suffix(".bat")
        env_str = " && ".join(f"set {key}={shlex.quote(value)}" for key, value in env.items())
    
    command = f"""\
    cd {kohya_path} && \
    call {activate_script} && \
    {env_str} && \
    {runner} {script} {args}
    """
    
    subprocess.check_call(command, shell=True)


__all__ = [
    "run_kohya",
]
