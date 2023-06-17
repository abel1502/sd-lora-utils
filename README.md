### Stable Diffusion LoRA utils
This is just a bunch of convenience scripts I've thrown together.

Note: some things require that https://github.com/kohya-ss/sd-scripts is
installed in this directory under the name of `kohya-trainer`, as well as set
to a specific commit. I will perhaps introduce a utility script to automate
this later at some point. If you face the need to do this, the commit is
`5050971ac687dca70ba0486a583d283e8ae324e2`. Also be prepared to manually deal
with some extra dependencies, I guess. Also, the venv is assumed to be in the
`.venv` subfolder there.

The specific components are:
 - `dataset-editor`: a web interface for convenient dataset manipulation.
   Initially based on https://github.com/gpt2ent/sd-dataset-editor/, but has
   gone through a lot of refactoring and enhancement. 
 - `kohya-runner.py`: A complementary script to run kohya's scripts under the
   right environment. Automatically accounts for venv, accelerate and so on.
 - `train-lora.py`: A helper to launch LoRA training though kohya's scripts.
   Note that the configs must be created manually. This project includes sample
   configs for your convenience.
