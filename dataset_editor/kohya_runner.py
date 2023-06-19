from __future__ import annotations
import typing
import pathlib
import subprocess
import shlex
import platform
import asyncio


def _make_cmd(
    script: str | pathlib.Path,
    *,
    kohya_path: pathlib.Path,
    accelerate: bool = True,
    args: str | typing.Sequence[str] = (),
    env: dict[str, str] | None = None,
) -> str:
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
    
    return f"""\
    cd {kohya_path} && \
    call {activate_script} && \
    {env_str} && \
    {runner} {script} {args}
    """


def run_kohya(
    script: str | pathlib.Path,
    *,
    kohya_path: pathlib.Path,
    accelerate: bool = True,
    args: str | typing.Sequence[str] = (),
    env: dict[str, str] | None = None,
) -> None:
    subprocess.check_call(_make_cmd(
        script=script,
        kohya_path=kohya_path,
        accelerate=accelerate,
        args=args,
        env=env,
    ), shell=True)


async def run_kohya_async(
    script: str | pathlib.Path,
    *,
    kohya_path: pathlib.Path,
    accelerate: bool = True,
    args: str | typing.Sequence[str] = (),
    env: dict[str, str] | None = None,
) -> None:
    cmd: str = _make_cmd(
        script=script,
        kohya_path=kohya_path,
        accelerate=accelerate,
        args=args,
        env=env,
    )
    
    process: asyncio.subprocess.Process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    
    retcode: int = await process.wait()
    
    if retcode:
        raise subprocess.CalledProcessError(retcode, cmd)


__all__ = [
    "run_kohya",
    "run_kohya_async",
]
