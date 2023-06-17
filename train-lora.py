from __future__ import annotations
import typing
import pathlib
import argparse
import subprocess
import toml
import os


parser = argparse.ArgumentParser(
    description="A script to initiate kohya's LoRA training"
)

parser.add_argument(
    "project_name",
    type=str,
    help="The name of the LoRA project to train",
)

parser.add_argument(
    "--root",
    type=pathlib.Path,
    default=pathlib.Path("E:\\Media\\LoRAs\\"),
    help="The root folder containing datasets and trained models",
)

parser.add_argument(
    "--gen-config",
    action="store_true",
    help="Automatically generate config files for the project. This will never overwrite existing config files",
)


HERE: typing.Final[pathlib.Path] = pathlib.Path(__file__).parent.resolve()


def main() -> None:
    args = parser.parse_args()
    
    project_path: pathlib.Path = args.root / args.project_name
    
    if args.gen_config:
        raise NotImplementedError("Automatic config generation is not yet implemented")
    
    # TODO: Also allow autogenerating configs
    
    command = f"""\
    cd {HERE / "kohya-trainer"} && \
    call .venv\\Scripts\\activate.bat && \
    set TF_CPP_MIN_LOG_LEVEL="3" && set BITSANDBYTES_NOWELCOME="1" && set SAFETENSORS_FAST_GPU="1" && \
    accelerate launch --config_file=accelerate_config/config.yaml --num_cpu_threads_per_process=1 \
        train_network.py --dataset_config={project_path / "dataset_config.toml"} --config_file={project_path / "training_config.toml"}
    """
    
    subprocess.check_call(command, shell=True)
    
    print("Done!")


if __name__ == "__main__":
    exit(main())
