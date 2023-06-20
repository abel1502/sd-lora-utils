from __future__ import annotations
import typing
import pathlib
import subprocess
import shlex
import platform
import asyncio


IS_WINDOWS: bool = platform.system() == "Windows"


def _make_cmd(
    script: str | pathlib.Path,
    *,
    kohya_path: str | pathlib.Path,
    accelerate: bool = True,
    args: str | typing.Sequence[str] = (),
    env: dict[str, str] | None = None,
    debug: bool = False,
) -> str:
    if isinstance(script, str):
        script = pathlib.Path(script)
    
    if isinstance(kohya_path, str):
        kohya_path = pathlib.Path(kohya_path)
    
    if not isinstance(args, str):
        if IS_WINDOWS:
            # shlex is unique to linux
            args = subprocess.list2cmdline(args)
        else:
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
    
    if IS_WINDOWS:
        activate_script = activate_script.with_suffix(".bat")
        env_str = " && ".join(f"set {key}={shlex.quote(value)}" for key, value in env.items())
    
    command: str = f"""\
    cd {kohya_path} && \
    call {activate_script} && \
    {env_str} && \
    {runner} {script} {args}
    """
    
    if debug:
        print(f"Running kohya command: {command}")
    
    return command


def run_kohya(
    script: str | pathlib.Path,
    *,
    kohya_path: str | pathlib.Path,
    accelerate: bool = True,
    args: str | typing.Sequence[str] = (),
    env: dict[str, str] | None = None,
    debug: bool = False,
) -> None:
    subprocess.check_call(_make_cmd(
        script=script,
        kohya_path=kohya_path,
        accelerate=accelerate,
        args=args,
        env=env,
        debug=debug,
    ), shell=True)


async def run_kohya_async(
    script: str | pathlib.Path,
    *,
    kohya_path: str | pathlib.Path,
    accelerate: bool = True,
    args: str | typing.Sequence[str] = (),
    env: dict[str, str] | None = None,
    debug: bool = False,
) -> None:
    cmd: str = _make_cmd(
        script=script,
        kohya_path=kohya_path,
        accelerate=accelerate,
        args=args,
        env=env,
        debug=debug,
    )
    
    process: asyncio.subprocess.Process = \
        await asyncio.create_subprocess_shell(cmd)
    
    retcode: int = await process.wait()
    
    if retcode:
        raise subprocess.CalledProcessError(retcode, cmd, )


__all__ = [
    "run_kohya",
    "run_kohya_async",
]
